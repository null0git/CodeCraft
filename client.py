#!/usr/bin/env python3
"""
CrackPi Client Daemon
Connects to the main server and handles password cracking tasks
"""

import os
import sys
import time
import json
import uuid
import hashlib
import logging
import signal
import subprocess
import threading
from datetime import datetime
import socketio
from utils.system_utils import get_system_info, get_system_metrics
from utils.hash_utils import run_cracking_job

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/var/log/crackpi-client.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class CrackPiClient:
    def __init__(self, server_url, client_id=None):
        self.server_url = server_url
        self.client_id = client_id or self.generate_client_id()
        self.running = False
        self.current_job = None
        self.job_thread = None
        
        # Initialize SocketIO client
        self.sio = socketio.Client(reconnection=True, reconnection_attempts=0, reconnection_delay=5)
        self.setup_socketio_handlers()
        
        # System metrics thread
        self.metrics_thread = None
        
    def generate_client_id(self):
        """Generate a unique client ID based on system info"""
        system_info = get_system_info()
        unique_string = f"{system_info.get('hostname', 'unknown')}-{system_info.get('mac_address', uuid.uuid4().hex)}"
        return hashlib.md5(unique_string.encode()).hexdigest()[:16]
    
    def setup_socketio_handlers(self):
        """Setup SocketIO event handlers"""
        
        @self.sio.event
        def connect():
            logger.info(f"Connected to server at {self.server_url}")
            self.register_with_server()
            
        @self.sio.event
        def disconnect():
            logger.info("Disconnected from server")
            
        @self.sio.event
        def registration_confirmed(data):
            logger.info(f"Registration confirmed by server: {data}")
            
        @self.sio.event
        def job_assigned(data):
            logger.info(f"Job assigned: {data}")
            self.handle_job_assignment(data)
            
        @self.sio.event
        def job_cancelled(data):
            logger.info(f"Job cancelled: {data}")
            self.cancel_current_job()
            
        @self.sio.event
        def error(data):
            logger.error(f"Server error: {data}")
            
    def register_with_server(self):
        """Register this client with the server"""
        try:
            system_info = get_system_info()
            registration_data = {
                'client_id': self.client_id,
                'system_info': system_info
            }
            
            self.sio.emit('client_register', registration_data)
            logger.info(f"Sent registration data for client {self.client_id}")
            
        except Exception as e:
            logger.error(f"Error registering with server: {e}")
    
    def send_system_metrics(self):
        """Send periodic system metrics to server"""
        while self.running:
            try:
                metrics = get_system_metrics()
                self.sio.emit('system_metrics', {
                    'client_id': self.client_id,
                    'metrics': metrics
                })
                
                time.sleep(30)  # Send metrics every 30 seconds
                
            except Exception as e:
                logger.error(f"Error sending system metrics: {e}")
                time.sleep(60)  # Wait longer on error
    
    def handle_job_assignment(self, job_data):
        """Handle a new job assignment from the server"""
        try:
            if self.current_job:
                logger.warning("Already working on a job, cancelling current job")
                self.cancel_current_job()
            
            self.current_job = job_data
            
            # Start job in a separate thread
            self.job_thread = threading.Thread(target=self.execute_job, args=(job_data,))
            self.job_thread.daemon = True
            self.job_thread.start()
            
        except Exception as e:
            logger.error(f"Error handling job assignment: {e}")
            self.report_job_failure(job_data.get('job_id'), str(e))
    
    def execute_job(self, job_data):
        """Execute a cracking job"""
        job_id = job_data.get('job_id')
        
        try:
            logger.info(f"Starting job {job_id}")
            
            # Prepare job parameters
            hash_type = job_data.get('hash_type')
            hashes = job_data.get('hashes', [])
            attack_mode = job_data.get('attack_mode', 'dictionary')
            wordlist_path = job_data.get('wordlist_path')
            rules_path = job_data.get('rules_path')
            mask = job_data.get('mask')
            
            # Create temporary hash file
            hash_file = f"/tmp/job_{job_id}_hashes.txt"
            with open(hash_file, 'w') as f:
                for hash_value in hashes:
                    f.write(f"{hash_value}\n")
            
            # Progress callback function
            def progress_callback(progress, estimated_time):
                self.sio.emit('job_progress', {
                    'job_id': job_id,
                    'progress': progress,
                    'estimated_time': estimated_time
                })
            
            # Password found callback
            def password_found_callback(hash_value, password):
                self.sio.emit('password_cracked', {
                    'job_id': job_id,
                    'hash_value': hash_value,
                    'password': password,
                    'client_id': self.client_id
                })
            
            # Run the cracking job
            result = run_cracking_job(
                hash_file=hash_file,
                hash_type=hash_type,
                attack_mode=attack_mode,
                wordlist_path=wordlist_path,
                rules_path=rules_path,
                mask=mask,
                progress_callback=progress_callback,
                password_found_callback=password_found_callback
            )
            
            if result['success']:
                logger.info(f"Job {job_id} completed successfully")
            else:
                logger.error(f"Job {job_id} failed: {result['error']}")
                self.report_job_failure(job_id, result['error'])
            
            # Clean up
            if os.path.exists(hash_file):
                os.remove(hash_file)
                
        except Exception as e:
            logger.error(f"Error executing job {job_id}: {e}")
            self.report_job_failure(job_id, str(e))
        finally:
            self.current_job = None
            self.job_thread = None
    
    def report_job_failure(self, job_id, error_message):
        """Report job failure to the server"""
        try:
            self.sio.emit('job_failed', {
                'job_id': job_id,
                'error_message': error_message,
                'client_id': self.client_id
            })
        except Exception as e:
            logger.error(f"Error reporting job failure: {e}")
    
    def cancel_current_job(self):
        """Cancel the currently running job"""
        if self.current_job and self.job_thread:
            logger.info(f"Cancelling current job {self.current_job.get('job_id')}")
            # Note: In a real implementation, you would need to properly terminate
            # the hashcat/john process. For now, we just reset the job state.
            self.current_job = None
            # The job thread will finish naturally
    
    def start(self):
        """Start the client daemon"""
        self.running = True
        logger.info(f"Starting CrackPi client {self.client_id}")
        
        try:
            # Connect to server
            self.sio.connect(self.server_url)
            
            # Start metrics thread
            self.metrics_thread = threading.Thread(target=self.send_system_metrics)
            self.metrics_thread.daemon = True
            self.metrics_thread.start()
            
            # Keep the client running
            while self.running:
                time.sleep(1)
                
        except KeyboardInterrupt:
            logger.info("Received interrupt signal, shutting down...")
            self.stop()
        except Exception as e:
            logger.error(f"Error in client main loop: {e}")
            self.stop()
    
    def stop(self):
        """Stop the client daemon"""
        self.running = False
        
        if self.current_job:
            self.cancel_current_job()
        
        if self.sio.connected:
            self.sio.disconnect()
        
        logger.info("CrackPi client stopped")

def signal_handler(signum, frame):
    """Handle shutdown signals"""
    logger.info(f"Received signal {signum}, shutting down...")
    if 'client' in globals():
        client.stop()
    sys.exit(0)

def main():
    """Main entry point"""
    # Setup signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Get server URL from environment or use default
    server_url = os.environ.get('CRACKPI_SERVER_URL', 'http://192.168.1.100:5000')
    
    # Get client ID from environment or generate one
    client_id = os.environ.get('CRACKPI_CLIENT_ID')
    
    # Create and start client
    global client
    client = CrackPiClient(server_url, client_id)
    client.start()

if __name__ == '__main__':
    main()
