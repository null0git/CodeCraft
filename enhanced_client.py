#!/usr/bin/env python3
"""
Enhanced CrackPi Client - Distributed Password Cracking Agent  
Connects to main server and performs distributed password cracking with range assignment
Includes terminal integration and full communication features
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
from datetime import datetime
from typing import Dict, Optional, Callable

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/var/log/crackpi/client.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class EnhancedCrackPiClient:
    """Enhanced client with range-based distributed cracking"""
    
    def __init__(self, server_url: str = None, client_id: str = None):
        self.server_url = server_url or self.discover_server()
        self.client_id = client_id or self.generate_client_id()
        self.running = False
        self.current_job = None
        self.stop_current_job = False
        self.metrics_thread = None
        self.heartbeat_thread = None
        self.session = requests.Session()
        
        # System information
        self.system_info = self.collect_system_info()
        
        # Job tracking
        self.jobs_completed = 0
        self.hashes_cracked = 0
        self.total_attempts = 0
        
        # Terminal integration
        self.command_poll_interval = 5
        self.terminal_thread = None
        
        logger.info(f"Enhanced CrackPi Client initialized - ID: {self.client_id}")
        logger.info(f"Server URL: {self.server_url}")
        
    def discover_server(self) -> str:
        """Auto-discover CrackPi server on the network"""
        logger.info("Discovering CrackPi server on network...")
        
        # Try common ports and IPs
        common_ips = [
            '192.168.1.100', '192.168.1.1', '192.168.0.1',
            '10.0.0.1', '172.16.0.1'
        ]
        
        for ip in common_ips:
            for port in [5000, 8080, 80]:
                try:
                    url = f"http://{ip}:{port}"
                    response = self.session.get(f"{url}/api/ping", timeout=2)
                    if response.status_code == 200:
                        logger.info(f"Found CrackPi server at {url}")
                        return url
                except:
                    continue
        
        # Default fallback
        return "http://localhost:5000"
    
    def generate_client_id(self) -> str:
        """Generate unique client ID based on system information"""
        hostname = platform.node()
        mac = self.get_mac_address()
        unique_string = f"{hostname}-{mac}-{int(time.time())}"
        return hashlib.md5(unique_string.encode()).hexdigest()[:16]
    
    def get_mac_address(self) -> str:
        """Get primary MAC address"""
        try:
            import netifaces
            interfaces = netifaces.interfaces()
            for interface in interfaces:
                if interface != 'lo':  # Skip loopback
                    addrs = netifaces.ifaddresses(interface)
                    if netifaces.AF_LINK in addrs:
                        return addrs[netifaces.AF_LINK][0]['addr']
        except:
            pass
        
        # Fallback method
        try:
            return ':'.join(['{:02x}'.format((hash(platform.node()) >> i) & 0xff) 
                           for i in range(0, 48, 8)])
        except:
            return "00:00:00:00:00:00"
    
    def collect_system_info(self) -> Dict:
        """Collect comprehensive system information"""
        try:
            # CPU information
            cpu_freq = psutil.cpu_freq()
            cpu_info = {
                'model': platform.processor() or 'Unknown CPU',
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
                'mac_address': self.get_mac_address()
            }
            
            # OS information
            os_info = {
                'system': platform.system(),
                'release': platform.release(),
                'version': platform.version(),
                'username': os.getenv('USER', 'unknown')
            }
            
            return {
                'client_id': self.client_id,
                'timestamp': datetime.utcnow().isoformat(),
                'cpu': cpu_info,
                'memory': memory_info,
                'disk': disk_info,
                'network': network_info,
                'os': os_info,
                'cracking_tools': self.check_cracking_tools()
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
            import subprocess
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
            'version': f"Python {platform.python_version()}"
        }
        
        return tools
    
    def register_with_server(self) -> bool:
        """Register this client with the server"""
        try:
            registration_data = {
                'client_id': self.client_id,
                'system_info': self.system_info,
                'capabilities': {
                    'max_concurrent_jobs': 1,
                    'supported_hash_types': ['md5', 'sha1', 'sha256', 'sha512'],
                    'preferred_tool': 'python_hashlib'
                }
            }
            
            response = self.session.post(
                f"{self.server_url}/api/clients/register",
                json=registration_data,
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                logger.info(f"Successfully registered with server: {result.get('message')}")
                return True
            else:
                logger.error(f"Registration failed: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Error registering with server: {e}")
            return False
    
    def send_heartbeat(self):
        """Send periodic heartbeat to server"""
        while self.running:
            try:
                current_metrics = self.get_current_metrics()
                heartbeat_data = {
                    'client_id': self.client_id,
                    'status': 'working' if self.current_job else 'idle',
                    'metrics': current_metrics,
                    'current_job': self.current_job.get('job_id') if self.current_job else None,
                    'timestamp': datetime.utcnow().isoformat()
                }
                
                response = self.session.post(
                    f"{self.server_url}/api/clients/heartbeat",
                    json=heartbeat_data,
                    timeout=5
                )
                
                if response.status_code == 200:
                    # Check for new job assignments
                    result = response.json()
                    if result.get('new_job') and not self.current_job:
                        self.handle_job_assignment(result['new_job'])
                
            except Exception as e:
                logger.error(f"Heartbeat error: {e}")
            
            time.sleep(10)  # Send heartbeat every 10 seconds
    
    def get_current_metrics(self) -> Dict:
        """Get current system metrics"""
        try:
            return {
                'cpu_usage': psutil.cpu_percent(interval=1),
                'memory_usage': psutil.virtual_memory().percent,
                'disk_usage': psutil.disk_usage('/').percent,
                'network_latency': self.measure_latency(),
                'uptime': time.time() - psutil.boot_time()
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
                return (time.time() - start_time) * 1000  # Convert to milliseconds
        except:
            pass
        return 999.9  # High latency on error
    
    def poll_for_jobs(self):
        """Poll server for new job assignments"""
        while self.running:
            if not self.current_job:
                try:
                    response = self.session.get(
                        f"{self.server_url}/api/clients/{self.client_id}/jobs",
                        timeout=5
                    )
                    
                    if response.status_code == 200:
                        result = response.json()
                        if result.get('job'):
                            self.handle_job_assignment(result['job'])
                            
                except Exception as e:
                    logger.error(f"Error polling for jobs: {e}")
            
            time.sleep(5)  # Poll every 5 seconds
    
    def handle_job_assignment(self, job_data: Dict):
        """Handle new job assignment from server"""
        logger.info(f"Received job assignment: {job_data.get('job_id')}")
        
        self.current_job = job_data
        self.stop_current_job = False
        
        # Start job in separate thread
        job_thread = threading.Thread(
            target=self.execute_cracking_job,
            args=(job_data,),
            daemon=True
        )
        job_thread.start()
    
    def execute_cracking_job(self, job_data: Dict):
        """Execute a distributed password cracking job"""
        job_id = job_data.get('job_id')
        hash_value = job_data.get('hash_value')
        hash_type = job_data.get('hash_type', 'md5')
        start_password = job_data.get('start_password')
        end_password = job_data.get('end_password')
        charset = job_data.get('charset', 'digits')
        
        logger.info(f"Starting job {job_id}: cracking {hash_type} hash")
        logger.info(f"Range: {start_password} to {end_password}")
        
        try:
            # Report job started
            self.report_job_status(job_id, 'started')
            
            # Progress callback function
            def progress_callback(progress_percent: float, attempts: int, current_password: str):
                if self.stop_current_job:
                    return False  # Signal to stop
                
                # Report progress every 1000 attempts
                if attempts % 1000 == 0:
                    self.report_progress(job_id, progress_percent, attempts, current_password)
                
                return True  # Continue processing
            
            # Password found callback
            def password_found_callback(password: str, attempts: int):
                logger.info(f"PASSWORD FOUND: {password} (after {attempts} attempts)")
                self.report_password_found(job_id, hash_value, password, attempts)
            
            # Execute the cracking
            result = HashCracker.crack_hash(
                target_hash=hash_value,
                hash_type=hash_type,
                start_password=start_password,
                end_password=end_password,
                charset=charset,
                progress_callback=progress_callback
            )
            
            if result.get('success'):
                password_found_callback(result['password'], result['attempts'])
                self.report_job_status(job_id, 'completed', {
                    'password_found': result['password'],
                    'attempts': result['attempts']
                })
                self.hashes_cracked += 1
            else:
                logger.info(f"Job {job_id} completed - password not found in assigned range")
                self.report_job_status(job_id, 'completed', {
                    'password_found': None,
                    'attempts': result.get('attempts', 0),
                    'message': 'Range completed, password not found'
                })
            
            self.jobs_completed += 1
            
        except Exception as e:
            logger.error(f"Error executing job {job_id}: {e}")
            self.report_job_status(job_id, 'failed', {'error': str(e)})
        
        finally:
            self.current_job = None
            self.stop_current_job = False
    
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
            
            response = self.session.post(
                f"{self.server_url}/api/jobs/{job_id}/status",
                json=status_data,
                timeout=5
            )
            
            if response.status_code != 200:
                logger.error(f"Failed to report job status: {response.status_code}")
                
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
            
            response = self.session.post(
                f"{self.server_url}/api/jobs/{job_id}/progress",
                json=progress_data,
                timeout=5
            )
            
        except Exception as e:
            logger.debug(f"Error reporting progress: {e}")
    
    def report_password_found(self, job_id: str, hash_value: str, password: str, attempts: int):
        """Report that a password was successfully cracked"""
        try:
            crack_data = {
                'client_id': self.client_id,
                'job_id': job_id,
                'hash_value': hash_value,
                'password': password,
                'attempts': attempts,
                'timestamp': datetime.utcnow().isoformat()
            }
            
            response = self.session.post(
                f"{self.server_url}/api/jobs/{job_id}/password-found",
                json=crack_data,
                timeout=5
            )
            
            if response.status_code == 200:
                logger.info("Successfully reported password crack to server")
            
        except Exception as e:
            logger.error(f"Error reporting password found: {e}")
    
    def stop_current_job_execution(self):
        """Stop the currently executing job"""
        if self.current_job:
            logger.info(f"Stopping current job: {self.current_job.get('job_id')}")
            self.stop_current_job = True
    
    def start(self):
        """Start the enhanced client daemon"""
        logger.info("Starting Enhanced CrackPi Client...")
        self.running = True
        
        # Register with server
        if not self.register_with_server():
            logger.error("Failed to register with server. Exiting.")
            return False
        
        # Start background threads
        self.heartbeat_thread = threading.Thread(target=self.send_heartbeat, daemon=True)
        self.heartbeat_thread.start()
        
        # Start job polling thread
        job_thread = threading.Thread(target=self.poll_for_jobs, daemon=True)
        job_thread.start()
        
        # Start terminal command polling thread
        self.terminal_thread = threading.Thread(target=self.poll_terminal_commands, daemon=True)
        self.terminal_thread.start()
        
        logger.info("Enhanced CrackPi Client started successfully")
        logger.info(f"Client ID: {self.client_id}")
        logger.info(f"Server: {self.server_url}")
        
        try:
            # Keep main thread alive
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Shutdown signal received")
        finally:
            self.stop()
        
        return True
    
    def stop(self):
        """Stop the client daemon"""
        logger.info("Stopping Enhanced CrackPi Client...")
        self.running = False
        
        # Stop current job
        self.stop_current_job_execution()
        
        # Notify server of disconnect
        try:
            disconnect_data = {
                'client_id': self.client_id,
                'timestamp': datetime.utcnow().isoformat(),
                'stats': {
                    'jobs_completed': self.jobs_completed,
                    'hashes_cracked': self.hashes_cracked,
                    'total_attempts': self.total_attempts
                }
            }
            
            self.session.post(
                f"{self.server_url}/api/clients/disconnect",
                json=disconnect_data,
                timeout=5
            )
        except:
            pass
        
        logger.info("Enhanced CrackPi Client stopped")
    
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
                        self.execute_terminal_command(command_data)
                        
            except Exception as e:
                logger.debug(f"Terminal polling error: {e}")
            
            time.sleep(self.command_poll_interval)
    
    def execute_terminal_command(self, command_data: Dict):
        """Execute terminal command and send response"""
        command_id = command_data.get('command_id')
        session_id = command_data.get('session_id')
        command = command_data.get('command', '')
        
        logger.info(f"Executing terminal command: {command}")
        
        try:
            # Execute command with timeout
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            # Send response back to server
            response_data = {
                'command_id': command_id,
                'session_id': session_id,
                'stdout': result.stdout,
                'stderr': result.stderr,
                'return_code': result.returncode,
                'timestamp': datetime.utcnow().isoformat()
            }
            
            self.session.post(
                f"{self.server_url}/terminal/api/response",
                json=response_data,
                timeout=5
            )
            
            logger.info(f"Terminal command completed: {command_id}")
            
        except subprocess.TimeoutExpired:
            logger.error(f"Terminal command timed out: {command}")
            # Send timeout response
            response_data = {
                'command_id': command_id,
                'session_id': session_id,
                'stdout': '',
                'stderr': 'Command timed out after 30 seconds',
                'return_code': 124,
                'timestamp': datetime.utcnow().isoformat()
            }
            
            self.session.post(
                f"{self.server_url}/terminal/api/response",
                json=response_data,
                timeout=5
            )
            
        except Exception as e:
            logger.error(f"Terminal command error: {e}")
            # Send error response
            response_data = {
                'command_id': command_id,
                'session_id': session_id,
                'stdout': '',
                'stderr': f'Command execution error: {str(e)}',
                'return_code': 1,
                'timestamp': datetime.utcnow().isoformat()
            }
            
            self.session.post(
                f"{self.server_url}/terminal/api/response",
                json=response_data,
                timeout=5
            )

def signal_handler(signum, frame):
    """Handle shutdown signals"""
    logger.info(f"Received signal {signum}")
    if 'client' in globals():
        client.stop()
    sys.exit(0)

def main():
    """Main entry point for enhanced client"""
    # Setup signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Parse command line arguments
    import argparse
    parser = argparse.ArgumentParser(description='Enhanced CrackPi Client')
    parser.add_argument('--server', '-s', 
                       help='Server URL (default: auto-discover)')
    parser.add_argument('--client-id', '-c',
                       help='Client ID (default: auto-generate)')
    parser.add_argument('--log-level', '-l', 
                       choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
                       default='INFO',
                       help='Log level')
    
    args = parser.parse_args()
    
    # Set log level
    logging.getLogger().setLevel(getattr(logging, args.log_level))
    
    # Create and start client
    global client
    client = EnhancedCrackPiClient(
        server_url=args.server,
        client_id=args.client_id
    )
    
    try:
        client.start()
    except Exception as e:
        logger.error(f"Failed to start client: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()