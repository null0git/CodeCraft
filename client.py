#!/usr/bin/env python3
"""
CrackPi Client Daemon — Distributed Keyspace Worker
=====================================================
Implements the worker side of the coordinator-worker keyspace algorithm:

  Step 6  Receive start_index and end_index from coordinator
  Step 7  Convert indexes to passwords and test them (parallel with other workers)
  Step 8  Report found password immediately; coordinator stops all workers
  Step 9  On reconnect, pick up a failed range automatically

Usage:
    python client.py                                       # auto-detect server
    python client.py --server http://192.168.1.10:5000
    python client.py --server http://192.168.1.10:5000 --client-id mypi01
    python client.py --log-level DEBUG
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
import string
import platform
from datetime import datetime

# ── Dependencies ──────────────────────────────────────────────────────────────
try:
    import requests
except ImportError:
    print("ERROR: 'requests' not installed.  Run: pip install requests")
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

# ── Logging — stdout only (no /var/log writes) ────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
#  Keyspace math (self-contained — no server-side import needed)
# ═══════════════════════════════════════════════════════════════════════════════

def index_to_password(index: int, charset: str, min_len: int, max_len: int) -> str | None:
    """
    Step 2 (worker side): Convert a global 0-based index to a password.

    Passwords are enumerated in ascending length order, then lexicographically
    within each length group (using the charset order).

    index 0                 → charset[0] repeated min_len times
    index len(charset)^min_len  → first password of length min_len+1
    Returns None when index is beyond the keyspace.
    """
    c = len(charset)
    offset = 0
    for length in range(min_len, max_len + 1):
        group = c ** length
        if index < offset + group:
            local = index - offset
            chars = []
            for _ in range(length):
                chars.append(charset[local % c])
                local //= c
            return ''.join(reversed(chars))
        offset += group
    return None


def total_keyspace(charset: str, min_len: int, max_len: int) -> int:
    """Step 3: Total number of passwords across all lengths."""
    c = len(charset)
    return sum(c ** i for i in range(min_len, max_len + 1))


# ═══════════════════════════════════════════════════════════════════════════════
#  CrackPiClient
# ═══════════════════════════════════════════════════════════════════════════════

class CrackPiClient:
    HEARTBEAT_INTERVAL   = 5   # seconds
    TERMINAL_POLL_SECS   = 2   # seconds

    def __init__(self, server_url: str = None, client_id: str = None):
        self.server_url = (server_url or self._discover_server()).rstrip('/')
        self.client_id  = client_id or self._generate_client_id()

        self.session = requests.Session()
        self.session.headers.update({'Content-Type': 'application/json'})

        self.running            = False
        self.connected          = False
        self.reconnect_attempts = 0

        self.current_job        = None
        self.stop_current_job   = False
        self.job_thread         = None

        self.system_info = self._collect_system_info()

    # ── Server discovery ──────────────────────────────────────────────────────

    def _discover_server(self) -> str:
        logger.info("Auto-discovering CrackPi server…")
        candidates = ['http://localhost:5000', 'http://127.0.0.1:5000']
        if HAS_NETIFACES:
            try:
                gw = netifaces.gateways().get('default', {}).get(netifaces.AF_INET, [None])[0]
                if gw:
                    candidates.insert(0, f"http://{gw}:5000")
            except Exception:
                pass
        for url in candidates:
            try:
                r = requests.get(f"{url}/api/ping", timeout=2)
                if r.status_code == 200:
                    logger.info(f"Found server at {url}")
                    return url
            except Exception:
                pass
        logger.warning("Server not found — defaulting to http://localhost:5000")
        return 'http://localhost:5000'

    # ── Identity ──────────────────────────────────────────────────────────────

    def _generate_client_id(self) -> str:
        mac = self._get_mac()
        uid = hashlib.sha256(f"{platform.node()}-{mac}".encode()).hexdigest()[:16]
        logger.info(f"Client ID: {uid}")
        return uid

    def _get_mac(self) -> str:
        if HAS_NETIFACES:
            try:
                for iface in netifaces.interfaces():
                    if iface == 'lo':
                        continue
                    addrs = netifaces.ifaddresses(iface)
                    mac = addrs.get(netifaces.AF_LINK, [{}])[0].get('addr', '')
                    if mac and mac != '00:00:00:00:00:00':
                        return mac
            except Exception:
                pass
        try:
            for iface in os.listdir('/sys/class/net'):
                if iface == 'lo':
                    continue
                p = f'/sys/class/net/{iface}/address'
                if os.path.exists(p):
                    mac = open(p).read().strip()
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

    # ── System info / metrics ─────────────────────────────────────────────────

    def _collect_system_info(self) -> dict:
        info: dict = {
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
            },
            'cpu': {
                'model':        platform.processor() or platform.machine(),
                'cores':        os.cpu_count() or 1,
                'architecture': platform.machine(),
            },
        }
        if HAS_PSUTIL:
            try:
                mem  = psutil.virtual_memory()
                disk = psutil.disk_usage('/')
                freq = psutil.cpu_freq()
                info['cpu']['frequency']        = freq.current if freq else 0
                info['cpu']['cores']            = psutil.cpu_count(logical=True)
                info['memory'] = {'total': mem.total, 'percentage': mem.percent}
                info['disk']   = {'total': disk.total, 'percentage': disk.percent}
            except Exception:
                pass
        info['capabilities'] = {'terminal_access': True, 'distributed_bruteforce': True}
        return info

    def _get_current_metrics(self) -> dict:
        if not HAS_PSUTIL:
            return {}
        try:
            return {
                'cpu_usage':    psutil.cpu_percent(interval=0.3),
                'memory_usage': psutil.virtual_memory().percent,
                'disk_usage':   psutil.disk_usage('/').percent,
                'load_average': list(os.getloadavg()) if hasattr(os, 'getloadavg') else [0, 0, 0],
                'uptime':       time.time() - psutil.boot_time(),
            }
        except Exception:
            return {}

    # ── HTTP helpers ──────────────────────────────────────────────────────────

    def _post(self, path: str, data: dict, timeout: int = 8):
        try:
            return self.session.post(
                f"{self.server_url}{path}",
                data=json.dumps(data, default=str),
                timeout=timeout
            )
        except requests.exceptions.ConnectionError:
            logger.warning(f"Connection refused: {self.server_url}{path}")
        except requests.exceptions.Timeout:
            logger.warning(f"Request timed out: {path}")
        except Exception as e:
            logger.debug(f"POST {path}: {e}")
        return None

    def _get(self, path: str, timeout: int = 6):
        try:
            return self.session.get(f"{self.server_url}{path}", timeout=timeout)
        except Exception as e:
            logger.debug(f"GET {path}: {e}")
        return None

    def _safe_json(self, response) -> dict | None:
        if response is None:
            return None
        try:
            return response.json()
        except Exception:
            return None

    # ── Connection ────────────────────────────────────────────────────────────

    def connect(self) -> bool:
        r = self._get('/api/ping', timeout=5)
        data = self._safe_json(r)
        if not data or data.get('status') != 'ok':
            return False

        r = self._post('/api/clients/register', {
            'client_id':   self.client_id,
            'system_info': self.system_info,
            'timestamp':   datetime.utcnow().isoformat(),
        })
        if r is None or r.status_code != 200:
            logger.error(f"Registration failed: {r.status_code if r else 'no response'}")
            return False

        logger.info(f"Registered — client_id={self.client_id}")
        self.connected          = True
        self.reconnect_attempts = 0
        return True

    # ── Heartbeat ─────────────────────────────────────────────────────────────

    def send_heartbeat(self) -> bool:
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
            t = cmd.get('command') or cmd.get('type')
            if t == 'start_job':
                self._handle_job_assignment(cmd)
            elif t == 'stop_job':
                logger.info(f"Server requested job stop: {cmd.get('reason', '')}")
                self.stop_current_job = True
            elif t == 'terminal_command':
                threading.Thread(target=self._exec_terminal_cmd, args=(cmd,), daemon=True).start()
            else:
                logger.debug(f"Unknown command: {t}")

    # ── Terminal polling ──────────────────────────────────────────────────────

    def _terminal_polling_loop(self):
        while self.running:
            if self.connected:
                r    = self._get(f"/terminal/api/commands/{self.client_id}", timeout=5)
                data = self._safe_json(r)
                if data:
                    for cmd in data.get('commands', []):
                        threading.Thread(target=self._exec_terminal_cmd,
                                         args=(cmd,), daemon=True).start()
            time.sleep(self.TERMINAL_POLL_SECS)

    def _exec_terminal_cmd(self, cmd: dict):
        command_id = cmd.get('command_id', '')
        session_id = cmd.get('session_id', '')
        command    = cmd.get('command', '')
        logger.info(f"Terminal [{command_id[:8]}]: {command[:80]}")
        try:
            result = subprocess.run(command, shell=True, capture_output=True,
                                    text=True, timeout=30)
            payload = {'stdout': result.stdout, 'stderr': result.stderr,
                       'return_code': result.returncode}
        except subprocess.TimeoutExpired:
            payload = {'stdout': '', 'stderr': 'Timed out (30 s)', 'return_code': 124}
        except Exception as e:
            payload = {'stdout': '', 'stderr': str(e), 'return_code': 1}
        self._post('/terminal/api/response', {
            'command_id': command_id, 'session_id': session_id,
            'timestamp': datetime.utcnow().isoformat(), **payload,
        }, timeout=5)

    # ── Job dispatch ──────────────────────────────────────────────────────────

    def _handle_job_assignment(self, job_data: dict):
        if self.current_job:
            logger.warning("Already running a job — ignoring new assignment")
            return
        logger.info(f"Job assigned: id={job_data.get('job_id')} "
                    f"name={job_data.get('job_name')} "
                    f"mode={job_data.get('attack_mode')}")
        self.current_job      = job_data
        self.stop_current_job = False
        self.job_thread = threading.Thread(
            target=self._execute_job, args=(job_data,), daemon=True
        )
        self.job_thread.start()

    # ── Job execution ─────────────────────────────────────────────────────────

    def _execute_job(self, job_data: dict):
        """
        Route to the correct attack engine based on attack_mode.
        Distributed brute-force uses the index-based keyspace traversal.
        """
        job_id      = job_data.get('job_id', 'unknown')
        attack_mode = job_data.get('attack_mode', 'bruteforce')
        hashes      = job_data.get('hashes', [])

        if not hashes:
            logger.warning(f"Job {job_id} has no hashes")
            self._report_status(job_id, 'completed', 'No hashes to crack')
            self.current_job = None
            return

        logger.info(f"Starting job {job_id}: {len(hashes)} hashes, mode={attack_mode}")
        self._report_status(job_id, 'running',
                            f"Worker started: {len(hashes)} hashes, mode={attack_mode}")

        # Build hash-lookup table
        target_map = {h['hash'].strip().lower(): h for h in hashes}

        if attack_mode == 'bruteforce' and job_data.get('charset'):
            self._execute_bruteforce_indexed(job_id, job_data, target_map)
        elif attack_mode == 'dictionary':
            self._execute_dictionary(job_id, job_data, target_map)
        else:
            # Generic brute-force fallback (digits only)
            self._execute_bruteforce_fallback(job_id, job_data, target_map)

        self.current_job      = None
        self.stop_current_job = False

    # ── Distributed brute-force (Steps 2, 6, 7) ──────────────────────────────

    def _execute_bruteforce_indexed(self, job_id, job_data: dict, target_map: dict):
        """
        Step 6 — Worker Processing:
          starts at its assigned start_index,
          converts indexes into password candidates,
          tests candidates,
          increments indexes sequentially,
          stops when reaching its end index.

        Step 7 — Parallel Execution:
          Workers process their ranges simultaneously.
          They never communicate with each other directly.
        """
        charset     = job_data['charset']          # exact string, e.g. '0123456789abc…'
        min_len     = int(job_data.get('min_length', 1))
        max_len     = int(job_data.get('max_length', 8))
        start_idx   = int(job_data.get('start_index', 0))
        end_idx     = int(job_data.get('end_index', total_keyspace(charset, min_len, max_len) - 1))
        hash_type   = (job_data.get('hash_type') or 'md5').lower()
        assignment_id = job_data.get('assignment_id')

        range_size  = end_idx - start_idx + 1
        total_h     = len(target_map)

        logger.info(f"Keyspace range: [{start_idx:,} → {end_idx:,}]  "
                    f"({range_size:,} passwords)  charset='{job_data.get('charset_name', charset[:8])}' "
                    f"len={min_len}-{max_len}")

        compute_hash = self._make_hash_fn(hash_type)
        cracked      = 0
        attempts     = 0
        last_report  = time.time()

        for idx in range(start_idx, end_idx + 1):
            if self.stop_current_job or not target_map:
                break

            password = index_to_password(idx, charset, min_len, max_len)
            if password is None:
                break

            attempts += 1
            h = compute_hash(password)
            if h in target_map:
                rec = target_map.pop(h)
                cracked += 1
                logger.info(f"  CRACKED [{idx}]: {rec['hash'][:16]}... → {password!r}")
                self._report_password_found(job_id, rec['hash'], password, attempts)

            # Progress report every 10 s or every 100 k attempts
            if attempts % 100_000 == 0 or time.time() - last_report >= 10:
                pct = ((idx - start_idx + 1) / range_size) * 100
                self._report_progress(job_id, pct, attempts, password)
                logger.info(f"  Progress: {pct:.1f}%  idx={idx:,}  "
                             f"cracked={cracked}/{total_h}  rate~{attempts/(time.time()-last_report+0.001):.0f}/s")
                last_report = time.time()

        # Final report
        if self.stop_current_job:
            # Server found the password via another worker (Step 8)
            logger.info(f"Job {job_id} stopped by coordinator (password found by another worker)")
            self._report_status(job_id, 'cancelled', 'Stopped by coordinator')
        else:
            # This worker finished its range without finding remaining passwords
            logger.info(f"Job {job_id} range complete: {cracked}/{total_h} cracked, "
                        f"{attempts:,} passwords tried")
            # Notify coordinator that this range is exhausted
            self._post(f'/api/jobs/{job_id}/range-complete', {
                'client_id':    self.client_id,
                'assignment_id': assignment_id,
                'attempts':     attempts,
                'cracked':      cracked,
                'timestamp':    datetime.utcnow().isoformat(),
            })

    # ── Dictionary attack ─────────────────────────────────────────────────────

    def _execute_dictionary(self, job_id, job_data: dict, target_map: dict):
        hash_type    = (job_data.get('hash_type') or 'md5').lower()
        wordlist     = job_data.get('wordlist_path')
        compute_hash = self._make_hash_fn(hash_type)
        total_h      = len(target_map)
        cracked = attempts = 0

        if wordlist and os.path.exists(wordlist):
            logger.info(f"Dictionary attack: {wordlist}")
            with open(wordlist, 'r', encoding='utf-8', errors='ignore') as fh:
                for line in fh:
                    if self.stop_current_job or not target_map:
                        break
                    pw = line.rstrip('\n')
                    attempts += 1
                    h = compute_hash(pw)
                    if h in target_map:
                        rec = target_map.pop(h)
                        cracked += 1
                        self._report_password_found(job_id, rec['hash'], pw, attempts)
                    if attempts % 100_000 == 0:
                        self._report_progress(job_id, 0, attempts, pw)
        else:
            logger.warning(f"Wordlist not found: {wordlist} — skipping")

        status = 'cancelled' if self.stop_current_job else 'completed'
        self._report_status(job_id, status,
                            f"{cracked}/{total_h} cracked in {attempts:,} attempts")

    # ── Fallback brute-force (no keyspace params) ─────────────────────────────

    def _execute_bruteforce_fallback(self, job_id, job_data: dict, target_map: dict):
        """
        Simple digit-only brute-force when no start/end index or charset is given.
        Used for non-distributed single-worker jobs.
        """
        hash_type    = (job_data.get('hash_type') or 'md5').lower()
        compute_hash = self._make_hash_fn(hash_type)
        total_h      = len(target_map)
        cracked = attempts = 0

        logger.info("Fallback brute-force: digits, length 1-8")
        for length in range(1, 9):
            if self.stop_current_job or not target_map:
                break
            for combo in self._iter_combos(string.digits, length):
                if self.stop_current_job or not target_map:
                    break
                pw = ''.join(combo)
                attempts += 1
                h = compute_hash(pw)
                if h in target_map:
                    rec = target_map.pop(h)
                    cracked += 1
                    self._report_password_found(job_id, rec['hash'], pw, attempts)
                if attempts % 50_000 == 0:
                    self._report_progress(job_id, 0, attempts, pw)

        status = 'cancelled' if self.stop_current_job else 'completed'
        self._report_status(job_id, status,
                            f"{cracked}/{total_h} cracked in {attempts:,} attempts")

    @staticmethod
    def _iter_combos(charset: str, length: int):
        """Yield all character tuples of `length` from `charset`."""
        import itertools
        yield from itertools.product(charset, repeat=length)

    # ── Hash functions ────────────────────────────────────────────────────────

    @staticmethod
    def _make_hash_fn(hash_type: str):
        """Return a fast closure that hashes a password string."""
        ALG_MAP = {
            'md5':        'md5',     'sha1':      'sha1',
            'sha224':     'sha224',  'sha256':    'sha256',
            'sha384':     'sha384',  'sha512':    'sha512',
            'sha3-224':   'sha3_224','sha3-256':  'sha3_256',
            'sha3-384':   'sha3_384','sha3-512':  'sha3_512',
            'sha3_224':   'sha3_224','sha3_256':  'sha3_256',
            'sha3_384':   'sha3_384','sha3_512':  'sha3_512',
            'blake2b':    'blake2b', 'blake2b-512':'blake2b',
            'ntlm':       'md4',
        }
        alg = ALG_MAP.get(hash_type.lower(), 'md5')

        def _hash(pw: str) -> str:
            try:
                return hashlib.new(alg, pw.encode('utf-8', errors='replace')).hexdigest().lower()
            except Exception:
                return hashlib.md5(pw.encode('utf-8', errors='replace')).hexdigest()

        return _hash

    # ── Reporting ─────────────────────────────────────────────────────────────

    def _report_status(self, job_id, status: str, message: str):
        self._post(f'/api/jobs/{job_id}/status', {
            'client_id': self.client_id, 'job_id': job_id,
            'status': status, 'timestamp': datetime.utcnow().isoformat(),
            'details': {'message': message, 'level': 'info'},
        })

    def _report_progress(self, job_id, pct: float, attempts: int, current_pw: str):
        self._post(f'/api/jobs/{job_id}/progress', {
            'client_id': self.client_id, 'job_id': job_id,
            'progress_percent': pct, 'attempts': attempts,
            'current_password': current_pw,
            'timestamp': datetime.utcnow().isoformat(),
        })

    def _report_password_found(self, job_id, hash_value: str, password: str, attempts: int):
        """Step 8: report cracked password; coordinator will stop all workers."""
        logger.info(f"Reporting cracked password to coordinator")
        self._post(f'/api/jobs/{job_id}/password-found', {
            'client_id': self.client_id, 'job_id': job_id,
            'hash_value': hash_value, 'password': password,
            'attempts': attempts, 'timestamp': datetime.utcnow().isoformat(),
        })

    # ── Main loop ─────────────────────────────────────────────────────────────

    def start(self):
        self.running = True
        logger.info(f"Starting CrackPi client {self.client_id}")
        logger.info(f"Server: {self.server_url}")

        threading.Thread(target=self._terminal_polling_loop, daemon=True).start()

        while self.running:
            try:
                if not self.connected:
                    if self.connect():
                        logger.info("Connected to server")
                    else:
                        self.reconnect_attempts += 1
                        wait = min(60, 2 ** min(self.reconnect_attempts, 6))
                        logger.info(f"Reconnect attempt {self.reconnect_attempts} — "
                                    f"waiting {wait}s")
                        time.sleep(wait)
                        continue

                if not self.send_heartbeat():
                    logger.warning("Heartbeat failed — reconnecting…")
                    self.connected          = False
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
        self.running          = False
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

    parser = argparse.ArgumentParser(description='CrackPi distributed worker client')
    parser.add_argument('--server', '-s',
                        help='Server URL (default: auto-detect → localhost:5000)')
    parser.add_argument('--client-id', '-c',
                        help='Fixed client ID (default: hardware-derived)')
    parser.add_argument('--log-level', '-l',
                        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
                        default='INFO')
    args = parser.parse_args()

    logging.getLogger().setLevel(getattr(logging, args.log_level))

    client = CrackPiClient(server_url=args.server, client_id=args.client_id)

    def _shutdown(signum, frame):
        logger.info(f"Signal {signum} — stopping")
        client.running = False

    signal.signal(signal.SIGINT,  _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)

    client.start()


if __name__ == '__main__':
    main()
