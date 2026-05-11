#!/usr/bin/env python3
"""
CrackPi Unified Client-Server Communication System
Handles all communication between clients and server with terminal integration
"""

import os
import sys
import time
import json
import logging
import threading
import subprocess
import socket
import requests
from typing import Dict, List, Optional, Callable
from datetime import datetime
import psutil
import netifaces

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class CrackPiUnifiedClient:
    """Unified client with all communication features and terminal integration"""
    
    def __init__(self, server_url: str = None, client_id: str = None):
        self.server_url = server_url or self.discover_server()
        self.client_id = client_id or self.generate_client_id()
        self.session = requests.Session()
        self.session.timeout = 10
        
        # Connection state
        self.running = False
        self.connected = False
        self.last_heartbeat = 0
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = 50
        
        # Job management
        self.current_job = None
        self.job_thread = None
        self.stop_current_job = False
        
        # Terminal integration
        self.terminal_sessions = {}
        self.terminal_threads = {}
        
        # System monitoring
        self.system_info = self.collect_system_info()
        
        logger.info(f"CrackPi Unified Client initialized - ID: {self.client_id}")
        logger.info(f"Server URL: {self.server_url}")
    
    def discover_server(self) -> str:
        """Auto-discover CrackPi server on the network"""
        logger.info("Discovering CrackPi server...")
        
        # Get local network range
        try:
            import ipaddress
            # Get default gateway
            gateways = netifaces.gateways()
            default_gateway = gateways['default'][netifaces.AF_INET][0]
            
            # Get network interface info
            for interface in netifaces.interfaces():
                if interface == 'lo':
                    continue
                try:
                    addrs = netifaces.ifaddresses(interface)
                    if netifaces.AF_INET in addrs:
                        for addr_info in addrs[netifaces.AF_INET]:
                            ip = addr_info['addr']
                            netmask = addr_info.get('netmask', '255.255.255.0')
                            
                            # Create network range
                            network = ipaddress.IPv4Network(f"{ip}/{netmask}", strict=False)
                            
                            # Scan common IPs in network
                            for host_ip in [str(network.network_address + 1), default_gateway]:
                                for port in [5000, 8080, 80]:
                                    try:
                                        url = f"http://{host_ip}:{port}"
                                        response = requests.get(f"{url}/api/ping", timeout=2)
                                        if response.status_code == 200:
                                            logger.info(f"Found CrackPi server at {url}")
                                            return url
                                    except:
                                        continue
                except:
                    continue
        except Exception as e:
            logger.debug(f"Network discovery error: {e}")
        
        # Default fallback
        return "http://localhost:5000"
    
    def generate_client_id(self) -> str:
        """Generate unique client ID"""
        import hashlib
        import platform
        
        # Get unique system identifiers
        hostname = platform.node()
        mac = self.get_mac_address()
        cpu_info = platform.processor()
        timestamp = str(int(time.time()))
        
        unique_string = f"{hostname}-{mac}-{cpu_info}-{timestamp}"
        return hashlib.sha256(unique_string.encode()).hexdigest()[:16]
    
    def get_mac_address(self) -> str:
        """Get primary MAC address"""
        try:
            for interface in netifaces.interfaces():
                if interface != 'lo':
                    addrs = netifaces.ifaddresses(interface)
                    if netifaces.AF_LINK in addrs:
                        return addrs[netifaces.AF_LINK][0]['addr']
        except:
            pass
        return "00:00:00:00:00:00"
    
    def collect_system_info(self) -> Dict:
        """Collect comprehensive system information"""
        try:
            import platform
            
            # CPU information
            cpu_freq = psutil.cpu_freq()
            cpu_info = {
                'model': platform.processor() or platform.machine(),
                'cores': psutil.cpu_count(),
                'frequency': cpu_freq.current if cpu_freq else 0,
                'architecture': platform.machine()
            }
            
            # Memory information
            memory = psutil.virtual_memory()
            memory_info = {
                'total': memory.total,
                'available': memory.available,
                'used': memory.used,
                'percentage': memory.percent
            }
            
            # Disk information
            disk = psutil.disk_usage('/')
            disk_info = {
                'total': disk.total,
                'used': disk.used,
                'free': disk.free,
                'percentage': (disk.used / disk.total) * 100
            }
            
            # Network information
            network_info = {
                'hostname': platform.node(),
                'ip_address': self.get_local_ip(),
                'mac_address': self.get_mac_address(),
                'interfaces': list(netifaces.interfaces())
            }
            
            # OS information
            os_info = {
                'system': platform.system(),
                'release': platform.release(),
                'version': platform.version(),
                'username': os.getenv('USER', 'unknown'),
                'python_version': platform.python_version()
            }
            
            return {
                'client_id': self.client_id,
                'timestamp': datetime.utcnow().isoformat(),
                'cpu': cpu_info,
                'memory': memory_info,
                'disk': disk_info,
                'network': network_info,
                'os': os_info,
                'capabilities': {
                    'terminal_access': True,
                    'cracking_tools': self.check_cracking_tools(),
                    'max_concurrent_jobs': 1
                }
            }
            
        except Exception as e:
            logger.error(f"Error collecting system info: {e}")
            return {'client_id': self.client_id, 'error': str(e)}
    
    def get_local_ip(self) -> str:
        """Get local IP address"""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except:
            return "127.0.0.1"
    
    def check_cracking_tools(self) -> Dict:
        """Check availability of password cracking tools"""
        tools = {}
        
        # Check for hashcat
        try:
            result = subprocess.run(['hashcat', '--version'], 
                                  capture_output=True, text=True, timeout=5)
            tools['hashcat'] = {
                'available': result.returncode == 0,
                'version': result.stdout.strip() if result.returncode == 0 else None
            }
        except:
            tools['hashcat'] = {'available': False, 'version': None}
        
        # Check for john
        try:
            result = subprocess.run(['john', '--version'], 
                                  capture_output=True, text=True, timeout=5)
            tools['john'] = {
                'available': result.returncode == 0,
                'version': result.stdout.strip() if result.returncode == 0 else None
            }
        except:
            tools['john'] = {'available': False, 'version': None}
        
        # Python hashlib is always available
        tools['python_hashlib'] = {
            'available': True,
            'version': f"Python {sys.version}"
        }
        
        return tools
    
    def connect_to_server(self) -> bool:
        """Establish connection to server"""
        try:
            # Test basic connectivity
            response = self.session.get(f"{self.server_url}/api/ping")
            if response.status_code != 200:
                return False
            
            # Register with server
            registration_data = {
                'client_id': self.client_id,
                'system_info': self.system_info,
                'timestamp': datetime.utcnow().isoformat()
            }
            
            response = self.session.post(
                f"{self.server_url}/api/clients/register",
                json=registration_data
            )
            
            if response.status_code == 200:
                self.connected = True
                self.reconnect_attempts = 0
                logger.info("Successfully connected to server")
                return True
            else:
                logger.error(f"Registration failed: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Connection error: {e}")
            return False
    
    def send_heartbeat(self) -> bool:
        """Send heartbeat to server with current status"""
        try:
            heartbeat_data = {
                'client_id': self.client_id,
                'status': 'working' if self.current_job else 'idle',
                'timestamp': datetime.utcnow().isoformat(),
                'system_metrics': self.get_current_metrics(),
                'current_job': self.current_job.get('job_id') if self.current_job else None
            }
            
            response = self.session.post(
                f"{self.server_url}/api/clients/heartbeat",
                json=heartbeat_data
            )
            
            if response.status_code == 200:
                self.last_heartbeat = time.time()
                
                # Check for server commands
                result = response.json()
                self.handle_server_commands(result)
                return True
            else:
                return False
                
        except Exception as e:
            logger.error(f"Heartbeat error: {e}")
            return False
    
    def handle_server_commands(self, response_data: Dict):
        """Handle commands received from server in heartbeat response"""
        commands = response_data.get('commands', [])

        for command in commands:
            # Server sends {'command': 'start_job', ...} as the top-level keys
            command_type = command.get('command') or command.get('type')

            if command_type == 'start_job':
                # The whole command dict IS the job descriptor
                self.handle_job_assignment(command)
            elif command_type == 'stop_job':
                self.stop_current_job_execution()
            elif command_type == 'terminal_command':
                self.handle_terminal_command(command)
            elif command_type == 'system_update':
                self.handle_system_update(command)
            else:
                logger.debug(f"Unknown command type: {command_type}")

    def handle_job_assignment(self, job_data: Dict):
        """Handle new job assignment — job_data is the full command dict from server"""
        if self.current_job:
            logger.warning("Received new job while already working, ignoring")
            return

        job_id = job_data.get('job_id')
        logger.info(f"Received job assignment: job_id={job_id} name={job_data.get('job_name')}")
        self.current_job = job_data
        self.stop_current_job = False

        self.job_thread = threading.Thread(
            target=self.execute_cracking_job,
            args=(job_data,),
            daemon=True
        )
        self.job_thread.start()

    def execute_cracking_job(self, job_data: Dict):
        """Execute password cracking job using Python hashlib (always available)"""
        job_id = job_data.get('job_id', 'unknown')
        hash_type = job_data.get('hash_type', 'md5').lower()
        attack_mode = job_data.get('attack_mode', 'bruteforce')
        hashes = job_data.get('hashes', [])  # [{'id':..,'hash':..,'salt':..,'username':..}]
        wordlist_path = job_data.get('wordlist_path')
        mask = job_data.get('mask', '?d?d?d?d?d?d')

        if not hashes:
            logger.warning(f"Job {job_id} has no hashes, marking complete")
            self.report_job_status(job_id, 'completed',
                                   {'message': 'No hashes to crack', 'level': 'warning'})
            self.current_job = None
            return

        logger.info(f"Starting job {job_id}: {hash_type}, {len(hashes)} hashes, mode={attack_mode}")
        self.report_job_status(job_id, 'running', {'message': f'Started cracking {len(hashes)} hashes', 'level': 'info'})

        # Build a lookup dict: normalized_hash → hash_record
        target_map = {h['hash'].strip().lower(): h for h in hashes}
        cracked_count = 0
        attempts = 0

        def try_password(password: str) -> bool:
            """Try a password against all remaining targets. Returns True to continue."""
            nonlocal cracked_count, attempts
            if self.stop_current_job:
                return False
            attempts += 1

            # Compute hash
            try:
                alg = hash_type.replace('-', '').replace('_', '')
                if alg in ('md5', 'sha1', 'sha224', 'sha256', 'sha384', 'sha512',
                           'sha3224', 'sha3256', 'sha3384', 'sha3512', 'blake2b512'):
                    alg_map = {
                        'md5': 'md5', 'sha1': 'sha1', 'sha224': 'sha224',
                        'sha256': 'sha256', 'sha384': 'sha384', 'sha512': 'sha512',
                        'sha3224': 'sha3_224', 'sha3256': 'sha3_256',
                        'sha3384': 'sha3_384', 'sha3512': 'sha3_512',
                        'blake2b512': 'blake2b',
                    }
                    h = hashlib.new(alg_map.get(alg, alg), password.encode()).hexdigest()
                else:
                    h = hashlib.md5(password.encode()).hexdigest()
            except Exception:
                h = hashlib.md5(password.encode()).hexdigest()

            if h in target_map:
                rec = target_map.pop(h)
                cracked_count += 1
                logger.info(f"CRACKED: {rec['hash'][:16]}... → {password}")
                self.report_password_found(job_id, rec['hash'], password, attempts)
                if attempts % 5000 == 0 or not target_map:
                    self.report_progress(job_id, (cracked_count / len(hashes)) * 100, attempts, password)

            if attempts % 50000 == 0:
                pct = (cracked_count / len(hashes)) * 100
                self.report_progress(job_id, pct, attempts, password)

            return bool(target_map)  # Stop when all cracked

        try:
            import hashlib as _hashlib_import
            hashlib = _hashlib_import

            if attack_mode == 'dictionary' and wordlist_path and os.path.exists(wordlist_path):
                logger.info(f"Dictionary attack using {wordlist_path}")
                with open(wordlist_path, 'r', encoding='utf-8', errors='ignore') as wf:
                    for line in wf:
                        word = line.rstrip('\n')
                        if not try_password(word):
                            break
                        if self.stop_current_job:
                            break
            else:
                # Brute-force: use digits 0-9 up to 8 chars (safe default for demo)
                logger.info("Brute-force attack (digits 0-9, 1-8 chars)")
                import itertools
                import string
                charset = string.digits
                found_all = False
                for length in range(1, 9):
                    if found_all or self.stop_current_job:
                        break
                    for combo in itertools.product(charset, repeat=length):
                        if self.stop_current_job or not target_map:
                            found_all = True
                            break
                        pw = ''.join(combo)
                        try_password(pw)

            if self.stop_current_job:
                self.report_job_status(job_id, 'cancelled', {'message': 'Job cancelled', 'level': 'info'})
            else:
                self.report_job_status(job_id, 'completed', {
                    'message': f'Completed: {cracked_count}/{len(hashes)} hashes cracked in {attempts} attempts',
                    'level': 'info'
                })

        except Exception as e:
            logger.error(f"Job execution error: {e}")
            self.report_job_status(job_id, 'failed', {'message': str(e), 'level': 'error'})

        finally:
            self.current_job = None
            self.stop_current_job = False
    
    def handle_terminal_command(self, command_data: Dict):
        """Handle terminal command — execute and POST response to /terminal/api/response"""
        session_id = command_data.get('session_id', 'default')
        command_id = command_data.get('command_id', '')
        command = command_data.get('command', '')

        logger.info(f"Executing terminal command [{command_id}]: {command}")

        try:
            result = subprocess.run(
                command, shell=True, capture_output=True, text=True, timeout=30
            )
            response_data = {
                'command_id': command_id,
                'session_id': session_id,
                'stdout': result.stdout,
                'stderr': result.stderr,
                'return_code': result.returncode,
                'timestamp': datetime.utcnow().isoformat()
            }
        except subprocess.TimeoutExpired:
            response_data = {
                'command_id': command_id,
                'session_id': session_id,
                'stdout': '',
                'stderr': 'Command timed out (30s limit)',
                'return_code': 124,
                'timestamp': datetime.utcnow().isoformat()
            }
        except Exception as e:
            response_data = {
                'command_id': command_id,
                'session_id': session_id,
                'stdout': '',
                'stderr': str(e),
                'return_code': 1,
                'timestamp': datetime.utcnow().isoformat()
            }

        try:
            self.session.post(
                f"{self.server_url}/terminal/api/response",
                json=response_data,
                timeout=5
            )
        except Exception as e:
            logger.error(f"Failed to send terminal response: {e}")

    def _terminal_polling_loop(self):
        """Background thread: poll server for pending terminal commands"""
        logger.info("Terminal polling thread started")
        while self.running:
            if self.connected:
                try:
                    resp = self.session.get(
                        f"{self.server_url}/terminal/api/commands/{self.client_id}",
                        timeout=5
                    )
                    if resp.status_code == 200:
                        data = resp.json()
                        for cmd in data.get('commands', []):
                            threading.Thread(
                                target=self.handle_terminal_command,
                                args=(cmd,),
                                daemon=True
                            ).start()
                except Exception:
                    pass
            time.sleep(2)
    
    def handle_system_update(self, command_data: Dict):
        """Handle system update command"""
        update_type = command_data.get('update_type')
        
        if update_type == 'refresh_system_info':
            self.system_info = self.collect_system_info()
            logger.info("System information refreshed")
        elif update_type == 'restart_client':
            logger.info("Restart requested by server")
            self.restart_client()
    
    def get_current_metrics(self) -> Dict:
        """Get current system metrics"""
        try:
            return {
                'cpu_usage': psutil.cpu_percent(interval=1),
                'memory_usage': psutil.virtual_memory().percent,
                'disk_usage': psutil.disk_usage('/').percent,
                'network_latency': self.measure_latency(),
                'load_average': os.getloadavg() if hasattr(os, 'getloadavg') else [0, 0, 0],
                'uptime': time.time() - psutil.boot_time(),
                'processes': len(psutil.pids())
            }
        except Exception as e:
            logger.error(f"Error getting metrics: {e}")
            return {}
    
    def measure_latency(self) -> float:
        """Measure network latency to server"""
        try:
            start_time = time.time()
            response = self.session.get(f"{self.server_url}/api/ping", timeout=2)
            if response.status_code == 200:
                return (time.time() - start_time) * 1000
        except:
            pass
        return 999.9
    
    def report_job_status(self, job_id: str, status: str, details: Dict = None):
        """Report job status to server"""
        try:
            status_data = {
                'client_id': self.client_id,
                'job_id': job_id,
                'status': status,
                'timestamp': datetime.utcnow().isoformat(),
                'details': details or {}
            }
            
            self.session.post(
                f"{self.server_url}/api/jobs/{job_id}/status",
                json=status_data
            )
        except Exception as e:
            logger.error(f"Error reporting job status: {e}")
    
    def report_progress(self, job_id: str, progress_percent: float, attempts: int, current_password: str):
        """Report job progress to server"""
        try:
            progress_data = {
                'client_id': self.client_id,
                'job_id': job_id,
                'progress_percent': progress_percent,
                'attempts': attempts,
                'current_password': current_password,
                'timestamp': datetime.utcnow().isoformat()
            }
            
            self.session.post(
                f"{self.server_url}/api/jobs/{job_id}/progress",
                json=progress_data
            )
        except Exception as e:
            logger.debug(f"Error reporting progress: {e}")
    
    def report_password_found(self, job_id: str, hash_value: str, password: str, attempts: int):
        """Report successful password crack"""
        try:
            crack_data = {
                'client_id': self.client_id,
                'job_id': job_id,
                'hash_value': hash_value,
                'password': password,
                'attempts': attempts,
                'timestamp': datetime.utcnow().isoformat()
            }
            
            self.session.post(
                f"{self.server_url}/api/jobs/{job_id}/password-found",
                json=crack_data
            )
        except Exception as e:
            logger.error(f"Error reporting password found: {e}")
    
    def stop_current_job_execution(self):
        """Stop current job"""
        if self.current_job:
            logger.info("Stopping current job")
            self.stop_current_job = True
    
    def restart_client(self):
        """Restart the client"""
        logger.info("Restarting client...")
        self.stop()
        time.sleep(2)
        os.execv(sys.executable, ['python'] + sys.argv)
    
    def run_main_loop(self):
        """Main client loop — retries indefinitely with exponential backoff"""
        while self.running:
            try:
                if not self.connected:
                    if self.connect_to_server():
                        logger.info("Connected to server")
                        self.reconnect_attempts = 0
                    else:
                        self.reconnect_attempts += 1
                        wait_time = min(60, 2 ** min(self.reconnect_attempts, 6))
                        logger.info(f"Reconnect attempt {self.reconnect_attempts}, "
                                    f"retrying in {wait_time}s...")
                        time.sleep(wait_time)
                        continue

                # Send heartbeat — server will include job commands in response
                if not self.send_heartbeat():
                    logger.warning("Heartbeat failed, marking disconnected")
                    self.connected = False
                    self.reconnect_attempts = 0  # Reset so backoff restarts
                    continue

                time.sleep(5)  # Heartbeat interval

            except KeyboardInterrupt:
                logger.info("Shutdown signal received")
                break
            except Exception as e:
                logger.error(f"Main loop error: {e}")
                time.sleep(5)
    
    def check_for_jobs(self):
        """Check server for new job assignments"""
        try:
            response = self.session.get(
                f"{self.server_url}/api/clients/{self.client_id}/jobs"
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get('job'):
                    self.handle_job_assignment(result['job'])
        except Exception as e:
            logger.debug(f"Error checking for jobs: {e}")
    
    def start(self):
        """Start the unified client"""
        logger.info("Starting CrackPi Unified Client...")
        self.running = True

        # Start terminal polling background thread
        term_thread = threading.Thread(target=self._terminal_polling_loop, daemon=True)
        term_thread.start()

        try:
            self.run_main_loop()
        except Exception as e:
            logger.error(f"Client error: {e}")
        finally:
            self.stop()
    
    def stop(self):
        """Stop the client"""
        logger.info("Stopping CrackPi Unified Client...")
        self.running = False
        
        # Stop current job
        self.stop_current_job_execution()
        
        # Notify server
        try:
            disconnect_data = {
                'client_id': self.client_id,
                'timestamp': datetime.utcnow().isoformat()
            }
            
            self.session.post(
                f"{self.server_url}/api/clients/disconnect",
                json=disconnect_data,
                timeout=5
            )
        except:
            pass
        
        logger.info("Client stopped")

def main():
    """Main entry point"""
    import argparse
    import signal
    
    parser = argparse.ArgumentParser(description='CrackPi Unified Client')
    parser.add_argument('--server', '-s', help='Server URL')
    parser.add_argument('--client-id', '-c', help='Client ID')
    parser.add_argument('--log-level', '-l', 
                       choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
                       default='INFO', help='Log level')
    
    args = parser.parse_args()
    
    # Set log level
    logging.getLogger().setLevel(getattr(logging, args.log_level))
    
    # Create client
    client = CrackPiUnifiedClient(
        server_url=args.server,
        client_id=args.client_id
    )
    
    # Signal handlers
    def signal_handler(signum, frame):
        logger.info(f"Received signal {signum}")
        client.stop()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Start client
    try:
        client.start()
    except Exception as e:
        logger.error(f"Failed to start client: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()