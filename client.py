#!/usr/bin/env python3
"""
CrackPi Client Daemon
Connects to the CrackPi server and handles password cracking tasks.

Usage:
    python client.py                                  # auto-detect server
    python client.py --server http://192.168.1.10:5000
    python client.py --server http://192.168.1.10:5000 --client-id mypi01

The server communicates via HTTP REST — no SocketIO required.
"""

import os
import sys
import time
import json
import hashlib
import logging
import signal
import socket
import subprocess
import threading
import itertools
import string
import platform
from datetime import datetime

# ── optional imports (graceful fallback if missing) ──────────────────────────
try:
    import requests
except ImportError:
    print("ERROR: 'requests' is not installed. Run: pip install requests")
    sys.exit(1)

try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False

try:
    import netifaces
    HAS_NETIFACES = True
except ImportError:
    HAS_NETIFACES = False

# ── logging — stdout only (no /var/log writes that need root) ─────────────────
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
class CrackPiClient:
    """
    CrackPi HTTP client daemon.
    Registers with the server, sends heartbeats, executes cracking jobs,
    and polls the terminal command queue — all via plain HTTP REST.
    """

    HEARTBEAT_INTERVAL = 5    # seconds between heartbeats
    TERMINAL_POLL_INTERVAL = 2  # seconds between terminal command polls

    def __init__(self, server_url: str = None, client_id: str = None):
        self.server_url = (server_url or self._discover_server()).rstrip('/')
        self.client_id  = client_id or self._generate_client_id()

        self.session = requests.Session()
        self.session.headers.update({'Content-Type': 'application/json'})

        self.running   = False
        self.connected = False
        self.reconnect_attempts = 0

        self.current_job       = None
        self.stop_current_job  = False
        self.job_thread        = None

        self.system_info = self._collect_system_info()

    # ── Server discovery ──────────────────────────────────────────────────────

    def _discover_server(self) -> str:
        """Scan the local network for a CrackPi server; fall back to localhost."""
        logger.info("Auto-discovering CrackPi server…")
        candidates = ['http://localhost:5000', 'http://127.0.0.1:5000']

        if HAS_NETIFACES:
            try:
                gateways = netifaces.gateways()
                gw = gateways.get('default', {}).get(netifaces.AF_INET, [None])[0]
                if gw:
                    candidates.insert(0, f"http://{gw}:5000")
            except Exception:
                pass

        for url in candidates:
            try:
                r = requests.get(f"{url}/api/ping", timeout=2)
                if r.status_code == 200:
                    logger.info(f"Found CrackPi server at {url}")
                    return url
            except Exception:
                pass

        logger.warning("Server not found on local network — defaulting to http://localhost:5000")
        return 'http://localhost:5000'

    # ── Identity ──────────────────────────────────────────────────────────────

    def _generate_client_id(self) -> str:
        """Stable ID derived from hostname + MAC (changes only if hardware changes)."""
        hostname = platform.node()
        mac = self._get_mac()
        uid = hashlib.sha256(f"{hostname}-{mac}".encode()).hexdigest()[:16]
        logger.info(f"Generated client ID: {uid}")
        return uid

    def _get_mac(self) -> str:
        if HAS_NETIFACES:
            try:
                for iface in netifaces.interfaces():
                    if iface == 'lo':
                        continue
                    addrs = netifaces.ifaddresses(iface)
                    if netifaces.AF_LINK in addrs:
                        mac = addrs[netifaces.AF_LINK][0].get('addr', '')
                        if mac and mac != '00:00:00:00:00:00':
                            return mac
            except Exception:
                pass
        # Fallback: read from /sys
        try:
            for iface in os.listdir('/sys/class/net'):
                if iface == 'lo':
                    continue
                mac_path = f'/sys/class/net/{iface}/address'
                if os.path.exists(mac_path):
                    with open(mac_path) as f:
                        mac = f.read().strip()
                    if mac and mac != '00:00:00:00:00:00':
                        return mac
        except Exception:
            pass
        return '00:00:00:00:00:00'

    def _get_local_ip(self) -> str:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(('8.8.8.8', 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return '127.0.0.1'

    # ── System info ───────────────────────────────────────────────────────────

    def _collect_system_info(self) -> dict:
        info = {
            'client_id': self.client_id,
            'timestamp': datetime.utcnow().isoformat(),
            'network': {
                'hostname':    platform.node(),
                'ip_address':  self._get_local_ip(),
                'mac_address': self._get_mac(),
            },
            'os': {
                'system':  platform.system(),
                'release': platform.release(),
                'version': platform.version(),
            },
        }

        if HAS_PSUTIL:
            try:
                freq = psutil.cpu_freq()
                info['cpu'] = {
                    'model':     platform.processor() or platform.machine(),
                    'cores':     psutil.cpu_count(logical=True),
                    'frequency': freq.current if freq else 0,
                    'architecture': platform.machine(),
                }
                mem = psutil.virtual_memory()
                info['memory'] = {
                    'total':      mem.total,
                    'available':  mem.available,
                    'percentage': mem.percent,
                }
                disk = psutil.disk_usage('/')
                info['disk'] = {
                    'total':      disk.total,
                    'used':       disk.used,
                    'free':       disk.free,
                    'percentage': disk.percent,
                }
            except Exception as e:
                logger.debug(f"psutil error: {e}")
        else:
            info['cpu'] = {
                'model': platform.processor() or platform.machine(),
                'cores': os.cpu_count() or 1,
                'architecture': platform.machine(),
            }

        info['capabilities'] = {
            'cracking_tools': self._check_tools(),
            'terminal_access': True,
        }
        return info

    def _get_current_metrics(self) -> dict:
        if not HAS_PSUTIL:
            return {}
        try:
            return {
                'cpu_usage':     psutil.cpu_percent(interval=0.5),
                'memory_usage':  psutil.virtual_memory().percent,
                'disk_usage':    psutil.disk_usage('/').percent,
                'load_average':  list(os.getloadavg()) if hasattr(os, 'getloadavg') else [0, 0, 0],
                'uptime':        time.time() - psutil.boot_time(),
            }
        except Exception:
            return {}

    def _check_tools(self) -> dict:
        tools = {}
        for name, cmd in [('hashcat', ['hashcat', '--version']),
                          ('john',    ['john', '--version'])]:
            try:
                r = subprocess.run(cmd, capture_output=True, text=True, timeout=4)
                tools[name] = {'available': r.returncode == 0,
                               'version':   r.stdout.strip()[:60] if r.returncode == 0 else None}
            except Exception:
                tools[name] = {'available': False, 'version': None}
        tools['python_hashlib'] = {'available': True, 'version': f"Python {platform.python_version()}"}
        return tools

    # ── Server communication ──────────────────────────────────────────────────

    def _post(self, path: str, data: dict, timeout: int = 8) -> requests.Response | None:
        try:
            return self.session.post(
                f"{self.server_url}{path}",
                data=json.dumps(data),
                timeout=timeout
            )
        except requests.exceptions.ConnectionError:
            logger.warning(f"Cannot reach server at {self.server_url}{path}")
        except requests.exceptions.Timeout:
            logger.warning(f"Request timed out: {path}")
        except Exception as e:
            logger.debug(f"POST {path} error: {e}")
        return None

    def _get(self, path: str, timeout: int = 6) -> requests.Response | None:
        try:
            return self.session.get(f"{self.server_url}{path}", timeout=timeout)
        except Exception as e:
            logger.debug(f"GET {path} error: {e}")
        return None

    def _safe_json(self, response) -> dict | None:
        """Parse JSON safely — never raises even on empty / HTML responses."""
        if response is None:
            return None
        try:
            return response.json()
        except Exception:
            return None

    # ── Connection / heartbeat ────────────────────────────────────────────────

    def connect(self) -> bool:
        """Ping server then register."""
        # 1. Verify server is a CrackPi instance
        r = self._get('/api/ping', timeout=5)
        if r is None or r.status_code != 200:
            return False
        data = self._safe_json(r)
        if not data or data.get('status') != 'ok':
            logger.warning("Server responded but doesn't look like CrackPi")
            return False

        # 2. Register
        r = self._post('/api/clients/register', {
            'client_id':   self.client_id,
            'system_info': self.system_info,
            'timestamp':   datetime.utcnow().isoformat(),
        })
        if r is None or r.status_code != 200:
            logger.error(f"Registration failed: {r.status_code if r else 'no response'}")
            return False

        logger.info(f"Registered with server — client_id={self.client_id}")
        self.connected        = True
        self.reconnect_attempts = 0
        return True

    def send_heartbeat(self) -> bool:
        """Send heartbeat; process any job commands returned by server."""
        r = self._post('/api/clients/heartbeat', {
            'client_id':      self.client_id,
            'status':         'working' if self.current_job else 'idle',
            'timestamp':      datetime.utcnow().isoformat(),
            'system_metrics': self._get_current_metrics(),
            'current_job':    self.current_job.get('job_id') if self.current_job else None,
        })
        if r is None or r.status_code != 200:
            return False

        data = self._safe_json(r)
        if data:
            self._handle_commands(data.get('commands', []))
        return True

    def _handle_commands(self, commands: list):
        for cmd in commands:
            cmd_type = cmd.get('command') or cmd.get('type')
            if cmd_type == 'start_job':
                self._handle_job_assignment(cmd)
            elif cmd_type == 'stop_job':
                self.stop_current_job = True
            elif cmd_type == 'terminal_command':
                threading.Thread(target=self._exec_terminal_cmd, args=(cmd,), daemon=True).start()
            else:
                logger.debug(f"Unknown command: {cmd_type}")

    # ── Terminal polling ──────────────────────────────────────────────────────

    def _terminal_polling_loop(self):
        """Background thread: poll for pending terminal commands every 2 s."""
        logger.debug("Terminal polling thread started")
        while self.running:
            if self.connected:
                r = self._get(f"/terminal/api/commands/{self.client_id}", timeout=5)
                data = self._safe_json(r)
                if data:
                    for cmd in data.get('commands', []):
                        threading.Thread(
                            target=self._exec_terminal_cmd,
                            args=(cmd,),
                            daemon=True
                        ).start()
            time.sleep(self.TERMINAL_POLL_INTERVAL)

    def _exec_terminal_cmd(self, cmd: dict):
        """Execute a shell command and POST the result back to the server."""
        command_id = cmd.get('command_id', '')
        session_id = cmd.get('session_id', '')
        command    = cmd.get('command', '')

        logger.info(f"Terminal [{command_id[:12]}]: {command[:80]}")

        try:
            result = subprocess.run(
                command, shell=True, capture_output=True,
                text=True, timeout=30
            )
            payload = {
                'command_id':  command_id,
                'session_id':  session_id,
                'stdout':      result.stdout,
                'stderr':      result.stderr,
                'return_code': result.returncode,
                'timestamp':   datetime.utcnow().isoformat(),
            }
        except subprocess.TimeoutExpired:
            payload = {
                'command_id':  command_id,
                'session_id':  session_id,
                'stdout':      '',
                'stderr':      'Command timed out (30 s limit)',
                'return_code': 124,
                'timestamp':   datetime.utcnow().isoformat(),
            }
        except Exception as e:
            payload = {
                'command_id':  command_id,
                'session_id':  session_id,
                'stdout':      '',
                'stderr':      str(e),
                'return_code': 1,
                'timestamp':   datetime.utcnow().isoformat(),
            }

        self._post('/terminal/api/response', payload, timeout=5)

    # ── Job execution ─────────────────────────────────────────────────────────

    def _handle_job_assignment(self, job_data: dict):
        if self.current_job:
            logger.warning("Already running a job — ignoring new assignment")
            return
        logger.info(f"Job assigned: id={job_data.get('job_id')} name={job_data.get('job_name')}")
        self.current_job      = job_data
        self.stop_current_job = False
        self.job_thread = threading.Thread(
            target=self._execute_job, args=(job_data,), daemon=True
        )
        self.job_thread.start()

    def _execute_job(self, job_data: dict):
        job_id     = job_data.get('job_id', 'unknown')
        hash_type  = (job_data.get('hash_type') or 'md5').lower()
        attack_mode = job_data.get('attack_mode', 'bruteforce')
        hashes     = job_data.get('hashes', [])
        wordlist   = job_data.get('wordlist_path')
        mask       = job_data.get('mask', '?d?d?d?d?d?d')

        if not hashes:
            logger.warning(f"Job {job_id} has no hashes to crack")
            self._report_status(job_id, 'completed', 'No hashes to crack')
            self.current_job = None
            return

        logger.info(f"Starting job {job_id}: {hash_type}, {len(hashes)} hashes, mode={attack_mode}")
        self._report_status(job_id, 'running', f'Cracking {len(hashes)} hashes')

        # Build target map: normalised_hash_hex → hash_record
        target_map = {h['hash'].strip().lower(): h for h in hashes}
        total      = len(hashes)
        cracked    = 0
        attempts   = 0

        # ── Hash function lookup ──────────────────────────────────────────────
        ALG_MAP = {
            'md5':        'md5',     'sha1':       'sha1',
            'sha224':     'sha224',  'sha256':     'sha256',
            'sha384':     'sha384',  'sha512':     'sha512',
            'sha3-224':   'sha3_224','sha3-256':   'sha3_256',
            'sha3-384':   'sha3_384','sha3-512':   'sha3_512',
            'blake2b':    'blake2b', 'blake2b-512':'blake2b',
            'sha3_224':   'sha3_224','sha3_256':   'sha3_256',
            'sha3_384':   'sha3_384','sha3_512':   'sha3_512',
        }
        alg_name = ALG_MAP.get(hash_type, 'md5')

        def compute_hash(password: str) -> str:
            try:
                return hashlib.new(alg_name, password.encode()).hexdigest()
            except Exception:
                return hashlib.md5(password.encode()).hexdigest()

        def try_password(pw: str) -> bool:
            """Try pw; returns True to keep going, False to stop."""
            nonlocal cracked, attempts
            if self.stop_current_job or not target_map:
                return False
            attempts += 1
            h = compute_hash(pw)
            if h in target_map:
                rec = target_map.pop(h)
                cracked += 1
                logger.info(f"  CRACKED: {rec['hash'][:16]}... → {pw}")
                self._report_password_found(job_id, rec['hash'], pw, attempts)
            # Progress every 50 k attempts or whenever something is cracked
            if attempts % 50_000 == 0 or (cracked and attempts % 500 == 0):
                pct = (cracked / total) * 100
                self._report_progress(job_id, pct, attempts, pw)
            return bool(target_map) and not self.stop_current_job

        try:
            if attack_mode == 'dictionary' and wordlist and os.path.exists(wordlist):
                logger.info(f"Dictionary attack using wordlist: {wordlist}")
                with open(wordlist, 'r', encoding='utf-8', errors='ignore') as fh:
                    for line in fh:
                        if not try_password(line.rstrip('\n')):
                            break
            else:
                # Brute-force over digits 0-9 lengths 1-8 by default
                logger.info("Brute-force attack (digits, length 1-8)")
                charset = string.digits
                done = False
                for length in range(1, 9):
                    if done or self.stop_current_job:
                        break
                    for combo in itertools.product(charset, repeat=length):
                        if not try_password(''.join(combo)):
                            done = True
                            break

            if self.stop_current_job:
                self._report_status(job_id, 'cancelled', 'Stopped by server')
            else:
                msg = f"Done: {cracked}/{total} cracked in {attempts:,} attempts"
                logger.info(f"Job {job_id} complete — {msg}")
                self._report_status(job_id, 'completed', msg)

        except Exception as e:
            logger.error(f"Job {job_id} error: {e}")
            self._report_status(job_id, 'failed', str(e))
        finally:
            self.current_job      = None
            self.stop_current_job = False

    # ── Reporting helpers ─────────────────────────────────────────────────────

    def _report_status(self, job_id, status: str, message: str):
        self._post(f'/api/jobs/{job_id}/status', {
            'client_id': self.client_id,
            'job_id':    job_id,
            'status':    status,
            'timestamp': datetime.utcnow().isoformat(),
            'details':   {'message': message, 'level': 'info'},
        })

    def _report_progress(self, job_id, pct: float, attempts: int, current_pw: str):
        self._post(f'/api/jobs/{job_id}/progress', {
            'client_id':        self.client_id,
            'job_id':           job_id,
            'progress_percent': pct,
            'attempts':         attempts,
            'current_password': current_pw,
            'timestamp':        datetime.utcnow().isoformat(),
        })

    def _report_password_found(self, job_id, hash_value: str, password: str, attempts: int):
        self._post(f'/api/jobs/{job_id}/password-found', {
            'client_id':  self.client_id,
            'job_id':     job_id,
            'hash_value': hash_value,
            'password':   password,
            'attempts':   attempts,
            'timestamp':  datetime.utcnow().isoformat(),
        })

    # ── Main loop ─────────────────────────────────────────────────────────────

    def start(self):
        """Start the client daemon — runs until stopped or interrupted."""
        self.running = True
        logger.info(f"Starting CrackPi client {self.client_id}")
        logger.info(f"Server: {self.server_url}")

        # Terminal polling in background
        threading.Thread(target=self._terminal_polling_loop, daemon=True).start()

        while self.running:
            try:
                if not self.connected:
                    if self.connect():
                        logger.info("Connected to server")
                    else:
                        self.reconnect_attempts += 1
                        wait = min(60, 2 ** min(self.reconnect_attempts, 6))
                        logger.info(f"Reconnect attempt {self.reconnect_attempts} — retrying in {wait}s")
                        time.sleep(wait)
                        continue

                if not self.send_heartbeat():
                    logger.warning("Heartbeat failed — reconnecting…")
                    self.connected = False
                    self.reconnect_attempts = 0
                    continue

                time.sleep(self.HEARTBEAT_INTERVAL)

            except KeyboardInterrupt:
                logger.info("Interrupted — shutting down")
                break
            except Exception as e:
                logger.error(f"Unexpected error in main loop: {e}")
                time.sleep(5)

        self.stop()

    def stop(self):
        """Gracefully shut down the client."""
        self.running         = False
        self.stop_current_job = True
        try:
            self._post('/api/clients/disconnect', {
                'client_id': self.client_id,
                'timestamp': datetime.utcnow().isoformat(),
            }, timeout=3)
        except Exception:
            pass
        logger.info("CrackPi client stopped")


# ═══════════════════════════════════════════════════════════════════════════════
def main():
    import argparse

    parser = argparse.ArgumentParser(description='CrackPi client daemon')
    parser.add_argument('--server', '-s',
                        help='Server URL (default: auto-detect, then http://localhost:5000)')
    parser.add_argument('--client-id', '-c',
                        help='Fixed client ID (default: auto-generated from hardware)')
    parser.add_argument('--log-level', '-l',
                        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
                        default='INFO',
                        help='Log verbosity')
    args = parser.parse_args()

    logging.getLogger().setLevel(getattr(logging, args.log_level))

    client = CrackPiClient(
        server_url=args.server,
        client_id=args.client_id,
    )

    def _shutdown(signum, frame):
        logger.info(f"Signal {signum} received — stopping")
        client.running = False

    signal.signal(signal.SIGINT,  _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)

    client.start()


if __name__ == '__main__':
    main()
