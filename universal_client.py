#!/usr/bin/env python3
"""
Universal CrackPi Client - All-in-One Client Script
Combines enhanced and normal client functionality in a single script
"""

import os
import sys
import time
import json
import logging
import hashlib
import itertools
import threading
import signal
import socket
import platform
import psutil
import requests
import subprocess
import argparse
from datetime import datetime
from typing import Dict, Optional, Callable, List
from utils.advanced_cracker import AdvancedPasswordCracker, DistributedHashManager

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class UniversalCrackPiClient:
    """Universal client with all features combined"""
    
    def __init__(self, server_url: str = None, client_mode: str = 'enhanced'):
        self.server_url = server_url or self.discover_server()
        self.client_id = self.generate_client_id()
        self.client_mode = client_mode  # 'enhanced', 'normal', or 'auto'
        self.session = requests.Session()
        self.session.timeout = 10
        
        # Connection state
        self.running = False
        self.connected = False
        self.last_heartbeat = 0
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = 50
        
        # Job management
        self.current_jobs = {}  # Support multiple concurrent jobs
        self.job_threads = {}
        self.stop_jobs = set()
        
        # Terminal integration
        self.terminal_sessions = {}
        self.terminal_threads = {}
        
        # Advanced cracking components
        self.advanced_cracker = AdvancedPasswordCracker()
        self.hash_manager = DistributedHashManager()
        
        # System monitoring
        self.system_info = self.collect_system_info()
        
        # Capabilities detection
        self.capabilities = self.detect_capabilities()
        
        logger.info(f"Universal CrackPi Client initialized - ID: {self.client_id}")
        logger.info(f"Mode: {self.client_mode}, Server: {self.server_url}")
        logger.info(f"Capabilities: {self.capabilities}")
    
    def detect_capabilities(self) -> Dict:
        """Auto-detect client capabilities and set appropriate mode"""
        capabilities = {
            'cpu_cores': psutil.cpu_count(),
            'memory_gb': psutil.virtual_memory().total / (1024**3),
            'has_gpu': self.detect_gpu(),
            'cracking_tools': self.check_cracking_tools(),
            'network_speed': self.measure_network_speed(),
            'recommended_mode': 'normal'
        }
        
        # Determine recommended mode based on capabilities
        if capabilities['cpu_cores'] >= 4 and capabilities['memory_gb'] >= 4:
            capabilities['recommended_mode'] = 'enhanced'
        elif capabilities['has_gpu'] or capabilities['cracking_tools']['hashcat']['available']:
            capabilities['recommended_mode'] = 'enhanced'
        
        # Auto-set mode if not specified
        if self.client_mode == 'auto':
            self.client_mode = capabilities['recommended_mode']
            logger.info(f"Auto-detected mode: {self.client_mode}")
        
        return capabilities
    
    def detect_gpu(self) -> bool:
        """Detect if GPU is available for cracking"""
        try:
            # Check for NVIDIA GPU
            result = subprocess.run(['nvidia-smi'], capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                return True
        except:
            pass
        
        try:
            # Check for AMD GPU
            result = subprocess.run(['rocm-smi'], capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                return True
        except:
            pass
        
        return False
    
    def check_cracking_tools(self) -> Dict:
        """Check availability of password cracking tools"""
        tools = {}
        
        # Check for hashcat
        try:
            result = subprocess.run(['hashcat', '--version'], 
                                  capture_output=True, text=True, timeout=5)
            tools['hashcat'] = {
                'available': result.returncode == 0,
                'version': result.stdout.strip() if result.returncode == 0 else None,
                'gpu_support': self.detect_gpu()
            }
        except:
            tools['hashcat'] = {'available': False, 'version': None, 'gpu_support': False}
        
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
            'version': f"Python {sys.version}",
            'algorithms': list(hashlib.algorithms_available)
        }
        
        return tools
    
    def measure_network_speed(self) -> float:
        """Measure network speed to server"""
        try:
            start_time = time.time()
            response = requests.get(f"{self.server_url}/api/ping", timeout=5)
            if response.status_code == 200:
                latency = (time.time() - start_time) * 1000
                return latency
        except:
            pass
        return 999.9
    
    def discover_server(self) -> str:
        """Auto-discover CrackPi server on the network"""
        logger.info("Discovering CrackPi server...")
        
        try:
            import netifaces
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
            import netifaces
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
                'architecture': platform.machine(),
                'usage': psutil.cpu_percent(interval=1)
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
                'client_mode': self.client_mode,
                'timestamp': datetime.utcnow().isoformat(),
                'cpu': cpu_info,
                'memory': memory_info,
                'disk': disk_info,
                'network': network_info,
                'os': os_info,
                'capabilities': self.capabilities
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
                'client_mode': self.client_mode,
                'system_info': self.system_info,
                'capabilities': self.capabilities,
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
            # Update system info periodically
            if time.time() - getattr(self, '_last_sysinfo_update', 0) > 60:
                self.system_info = self.collect_system_info()
                self._last_sysinfo_update = time.time()
            
            heartbeat_data = {
                'client_id': self.client_id,
                'client_mode': self.client_mode,
                'status': 'working' if self.current_jobs else 'idle',
                'timestamp': datetime.utcnow().isoformat(),
                'system_metrics': self.get_current_metrics(),
                'active_jobs': list(self.current_jobs.keys()),
                'capabilities': self.capabilities
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
        """Handle commands from server"""
        commands = response_data.get('commands', [])
        
        for command in commands:
            command_type = command.get('type')
            
            if command_type == 'start_job':
                self.handle_job_assignment(command.get('job_data'))
            elif command_type == 'stop_job':
                job_id = command.get('job_id')
                self.stop_job_execution(job_id)
            elif command_type == 'terminal_command':
                self.handle_terminal_command(command)
            elif command_type == 'system_update':
                self.handle_system_update(command)
            elif command_type == 'capability_test':
                self.handle_capability_test(command)
    
    def handle_job_assignment(self, job_data: Dict):
        """Handle new job assignment with multi-job support"""
        job_id = job_data.get('job_id', 'unknown')
        
        if job_id in self.current_jobs:
            logger.warning(f"Job {job_id} already running")
            return
        
        logger.info(f"Received job assignment: {job_id}")
        self.current_jobs[job_id] = job_data
        
        # Start job in separate thread
        job_thread = threading.Thread(
            target=self.execute_cracking_job,
            args=(job_data,),
            daemon=True
        )
        self.job_threads[job_id] = job_thread
        job_thread.start()
    
    def execute_cracking_job(self, job_data: Dict):
        """Execute password cracking job with advanced techniques"""
        job_id = job_data.get('job_id', 'unknown')
        
        try:
            # Extract job parameters
            attack_config = {
                'mode': job_data.get('attack_mode', 'brute_force'),
                'hash_type': job_data.get('hash_type', 'md5'),
                'wordlist': job_data.get('wordlist_path'),
                'charset': job_data.get('charset', 'digits'),
                'min_length': job_data.get('min_length', 4),
                'max_length': job_data.get('max_length', 8),
                'start_password': job_data.get('start_password'),
                'end_password': job_data.get('end_password'),
                'mask': job_data.get('mask'),
                'max_words': job_data.get('max_words', 100000),
                'max_combinations': job_data.get('max_combinations', 10000)
            }
            
            hashes_to_crack = job_data.get('hashes', [])
            if not hashes_to_crack:
                # Single hash mode (legacy)
                hash_value = job_data.get('hash_value')
                if hash_value:
                    hashes_to_crack = [hash_value]
            
            logger.info(f"Starting job {job_id}: {attack_config['mode']} attack")
            logger.info(f"Hash count: {len(hashes_to_crack)}")
            
            # Report job started
            self.report_job_status(job_id, 'started')
            
            total_hashes = len(hashes_to_crack)
            completed_hashes = 0
            found_passwords = {}
            
            # Process each hash
            for i, target_hash in enumerate(hashes_to_crack):
                if job_id in self.stop_jobs:
                    break
                
                logger.info(f"Processing hash {i+1}/{total_hashes}: {target_hash[:16]}...")
                
                # Progress callback for individual hash
                def progress_callback(progress_percent: float, attempts: int, current_password: str):
                    if job_id in self.stop_jobs:
                        return False
                    
                    overall_progress = ((completed_hashes + (progress_percent / 100)) / total_hashes) * 100
                    
                    if attempts % 1000 == 0:
                        self.report_progress(job_id, overall_progress, attempts, current_password, target_hash)
                    
                    return True
                
                # Execute advanced cracking
                result = self.advanced_cracker.crack_hash(
                    target_hash=target_hash,
                    hash_type=attack_config['hash_type'],
                    attack_config=attack_config,
                    progress_callback=progress_callback
                )
                
                if result.get('success'):
                    password = result['password']
                    found_passwords[target_hash] = password
                    logger.info(f"PASSWORD FOUND for {target_hash[:16]}: {password}")
                    self.report_password_found(job_id, target_hash, password, result['attempts'])
                
                completed_hashes += 1
                
                # Report individual hash completion
                hash_progress = (completed_hashes / total_hashes) * 100
                self.report_progress(job_id, hash_progress, result.get('attempts', 0), '', target_hash)
            
            # Job completion
            if job_id not in self.stop_jobs:
                self.report_job_status(job_id, 'completed', {
                    'total_hashes': total_hashes,
                    'found_passwords': found_passwords,
                    'completion_rate': len(found_passwords) / total_hashes if total_hashes > 0 else 0
                })
            else:
                self.report_job_status(job_id, 'stopped')
                
        except Exception as e:
            logger.error(f"Job execution error: {e}")
            self.report_job_status(job_id, 'failed', {'error': str(e)})
        
        finally:
            # Cleanup
            if job_id in self.current_jobs:
                del self.current_jobs[job_id]
            if job_id in self.job_threads:
                del self.job_threads[job_id]
            if job_id in self.stop_jobs:
                self.stop_jobs.remove(job_id)
    
    def stop_job_execution(self, job_id: str = None):
        """Stop job execution"""
        if job_id:
            if job_id in self.current_jobs:
                logger.info(f"Stopping job: {job_id}")
                self.stop_jobs.add(job_id)
        else:
            # Stop all jobs
            logger.info("Stopping all jobs")
            for job_id in list(self.current_jobs.keys()):
                self.stop_jobs.add(job_id)
    
    def handle_terminal_command(self, command_data: Dict):
        """Handle terminal command from server"""
        session_id = command_data.get('session_id', 'default')
        command = command_data.get('command', '')
        
        logger.info(f"Executing terminal command: {command}")
        
        try:
            # Execute command
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            # Send result back to server
            response_data = {
                'client_id': self.client_id,
                'session_id': session_id,
                'command': command,
                'stdout': result.stdout,
                'stderr': result.stderr,
                'return_code': result.returncode,
                'timestamp': datetime.utcnow().isoformat()
            }
            
            self.session.post(
                f"{self.server_url}/terminal/api/response",
                json=response_data
            )
            
        except subprocess.TimeoutExpired:
            logger.error(f"Terminal command timed out: {command}")
        except Exception as e:
            logger.error(f"Terminal command error: {e}")
    
    def handle_system_update(self, command_data: Dict):
        """Handle system update command"""
        update_type = command_data.get('update_type')
        
        if update_type == 'refresh_system_info':
            self.system_info = self.collect_system_info()
            logger.info("System information refreshed")
        elif update_type == 'restart_client':
            logger.info("Restart requested by server")
            self.restart_client()
        elif update_type == 'update_capabilities':
            self.capabilities = self.detect_capabilities()
            logger.info("Capabilities updated")
    
    def handle_capability_test(self, command_data: Dict):
        """Handle capability testing request"""
        test_type = command_data.get('test_type', 'benchmark')
        
        if test_type == 'benchmark':
            result = self.run_benchmark()
            self.report_capability_test_result('benchmark', result)
        elif test_type == 'tool_test':
            result = self.test_cracking_tools()
            self.report_capability_test_result('tool_test', result)
    
    def run_benchmark(self) -> Dict:
        """Run performance benchmark"""
        logger.info("Running performance benchmark...")
        
        try:
            # Simple MD5 benchmark
            start_time = time.time()
            attempts = 0
            target_hash = hashlib.md5(b"test123").hexdigest()
            
            for i in range(10000):
                test_password = f"test{i:03d}"
                test_hash = hashlib.md5(test_password.encode()).hexdigest()
                attempts += 1
                
                if test_hash == target_hash:
                    break
            
            duration = time.time() - start_time
            hashes_per_second = attempts / duration if duration > 0 else 0
            
            return {
                'duration': duration,
                'attempts': attempts,
                'hashes_per_second': hashes_per_second,
                'cpu_usage': psutil.cpu_percent(),
                'memory_usage': psutil.virtual_memory().percent
            }
            
        except Exception as e:
            logger.error(f"Benchmark error: {e}")
            return {'error': str(e)}
    
    def test_cracking_tools(self) -> Dict:
        """Test available cracking tools"""
        logger.info("Testing cracking tools...")
        
        results = {}
        
        # Test hashcat
        if self.capabilities['cracking_tools']['hashcat']['available']:
            try:
                result = subprocess.run(
                    ['hashcat', '--benchmark', '--machine-readable'],
                    capture_output=True, text=True, timeout=30
                )
                results['hashcat'] = {
                    'available': True,
                    'benchmark_output': result.stdout[:500]  # Truncate for size
                }
            except Exception as e:
                results['hashcat'] = {'available': False, 'error': str(e)}
        
        # Test john
        if self.capabilities['cracking_tools']['john']['available']:
            try:
                result = subprocess.run(
                    ['john', '--test'],
                    capture_output=True, text=True, timeout=30
                )
                results['john'] = {
                    'available': True,
                    'test_output': result.stdout[:500]  # Truncate for size
                }
            except Exception as e:
                results['john'] = {'available': False, 'error': str(e)}
        
        return results
    
    def get_current_metrics(self) -> Dict:
        """Get current system metrics"""
        try:
            return {
                'cpu_usage': psutil.cpu_percent(interval=1),
                'memory_usage': psutil.virtual_memory().percent,
                'disk_usage': psutil.disk_usage('/').percent,
                'network_latency': self.measure_network_speed(),
                'load_average': os.getloadavg() if hasattr(os, 'getloadavg') else [0, 0, 0],
                'uptime': time.time() - psutil.boot_time(),
                'processes': len(psutil.pids()),
                'active_jobs': len(self.current_jobs)
            }
        except Exception as e:
            logger.error(f"Error getting metrics: {e}")
            return {}
    
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
    
    def report_progress(self, job_id: str, progress_percent: float, attempts: int, 
                       current_password: str, current_hash: str = ''):
        """Report job progress to server"""
        try:
            progress_data = {
                'client_id': self.client_id,
                'job_id': job_id,
                'progress_percent': progress_percent,
                'attempts': attempts,
                'current_password': current_password,
                'current_hash': current_hash,
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
    
    def report_capability_test_result(self, test_type: str, result: Dict):
        """Report capability test results"""
        try:
            test_data = {
                'client_id': self.client_id,
                'test_type': test_type,
                'result': result,
                'timestamp': datetime.utcnow().isoformat()
            }
            
            self.session.post(
                f"{self.server_url}/api/clients/capability-test",
                json=test_data
            )
        except Exception as e:
            logger.error(f"Error reporting capability test: {e}")
    
    def poll_terminal_commands(self):
        """Poll server for terminal commands"""
        while self.running:
            try:
                response = self.session.get(
                    f"{self.server_url}/terminal/api/commands/{self.client_id}",
                    timeout=5
                )
                
                if response.status_code == 200:
                    result = response.json()
                    commands = result.get('commands', [])
                    
                    for command_data in commands:
                        self.handle_terminal_command(command_data)
                        
            except Exception as e:
                logger.debug(f"Terminal polling error: {e}")
            
            time.sleep(5)
    
    def run_main_loop(self):
        """Main client loop"""
        # Start terminal polling thread
        terminal_thread = threading.Thread(target=self.poll_terminal_commands, daemon=True)
        terminal_thread.start()
        
        while self.running:
            try:
                if not self.connected:
                    if self.connect_to_server():
                        logger.info("Connected to server")
                    else:
                        self.reconnect_attempts += 1
                        if self.reconnect_attempts >= self.max_reconnect_attempts:
                            logger.error("Max reconnection attempts reached")
                            break
                        
                        wait_time = min(30, 2 ** min(self.reconnect_attempts, 5))
                        logger.info(f"Reconnecting in {wait_time} seconds...")
                        time.sleep(wait_time)
                        continue
                
                # Send heartbeat
                if not self.send_heartbeat():
                    self.connected = False
                    continue
                
                time.sleep(10)  # Main loop interval
                
            except KeyboardInterrupt:
                logger.info("Shutdown signal received")
                break
            except Exception as e:
                logger.error(f"Main loop error: {e}")
                time.sleep(5)
    
    def restart_client(self):
        """Restart the client"""
        logger.info("Restarting client...")
        self.stop()
        time.sleep(2)
        os.execv(sys.executable, ['python'] + sys.argv)
    
    def start(self):
        """Start the universal client"""
        logger.info(f"Starting Universal CrackPi Client in {self.client_mode} mode...")
        self.running = True
        
        try:
            self.run_main_loop()
        except Exception as e:
            logger.error(f"Client error: {e}")
        finally:
            self.stop()
    
    def stop(self):
        """Stop the client"""
        logger.info("Stopping Universal CrackPi Client...")
        self.running = False
        
        # Stop all jobs
        self.stop_job_execution()
        
        # Wait for job threads to finish
        for job_thread in self.job_threads.values():
            if job_thread.is_alive():
                job_thread.join(timeout=5)
        
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
    parser = argparse.ArgumentParser(description='Universal CrackPi Client')
    parser.add_argument('--server', '-s', help='Server URL')
    parser.add_argument('--mode', '-m', 
                       choices=['enhanced', 'normal', 'auto'],
                       default='auto', help='Client mode')
    parser.add_argument('--log-level', '-l', 
                       choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
                       default='INFO', help='Log level')
    
    args = parser.parse_args()
    
    # Set log level
    logging.getLogger().setLevel(getattr(logging, args.log_level))
    
    # Create client
    client = UniversalCrackPiClient(
        server_url=args.server,
        client_mode=args.mode
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