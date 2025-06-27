import os
import json
import time
import threading
import logging
from datetime import datetime, timedelta
from flask import request
from flask_socketio import emit, disconnect
from app import app, db
from models import Client, Job, Hash, JobLog, Settings
from utils.network_utils import scan_network, get_network_info
from utils.system_utils import get_system_info
from utils.hash_utils import identify_hash_type, prepare_cracking_job

# Global variables for tracking connections
connected_clients = {}
client_threads = {}

class ClientManager:
    def __init__(self):
        self.clients = {}
        self.job_queue = []
        self.running = True
        self.lock = threading.Lock()
        
    def add_client(self, client_id, client_data):
        with self.lock:
            self.clients[client_id] = client_data
            
    def remove_client(self, client_id):
        with self.lock:
            if client_id in self.clients:
                del self.clients[client_id]
                
    def get_client(self, client_id):
        with self.lock:
            return self.clients.get(client_id)
            
    def get_all_clients(self):
        with self.lock:
            return dict(self.clients)
            
    def assign_job(self, job_id, client_id):
        """Assign a job to a specific client"""
        job = Job.query.get(job_id)
        client = Client.query.filter_by(client_id=client_id).first()
        
        if not job or not client:
            return False
            
        job.client_id = client.id
        job.status = 'running'
        job.started_at = datetime.utcnow()
        
        client.status = 'working'
        
        db.session.commit()
        
        # Send job to client via WebSocket
        socketio.emit('job_assigned', {
            'job_id': job.id,
            'hash_type': job.hash_type.name,
            'hashes': [h.hash_value for h in job.hashes if not h.is_cracked],
            'attack_mode': job.attack_mode,
            'wordlist_path': job.wordlist_path,
            'rules_path': job.rules_path,
            'mask': job.mask
        }, room=client_id)
        
        return True
        
    def process_job_queue(self):
        """Process pending jobs and assign them to available clients"""
        while self.running:
            try:
                # Get pending jobs
                pending_jobs = Job.query.filter_by(status='pending').order_by(Job.priority.asc(), Job.created_at.asc()).all()
                
                # Get available clients
                available_clients = Client.query.filter_by(status='connected').all()
                
                for job in pending_jobs:
                    if available_clients:
                        # Assign to the first available client
                        client = available_clients.pop(0)
                        if self.assign_job(job.id, client.client_id):
                            app.logger.info(f"Assigned job {job.id} to client {client.client_id}")
                            
                time.sleep(5)  # Check every 5 seconds
                
            except Exception as e:
                app.logger.error(f"Error in job queue processing: {e}")
                time.sleep(10)

client_manager = ClientManager()

@socketio.on('connect')
def handle_connect():
    client_ip = request.environ.get('REMOTE_ADDR')
    app.logger.info(f"Client attempting to connect from {client_ip}")
    
@socketio.on('disconnect')
def handle_disconnect():
    client_ip = request.environ.get('REMOTE_ADDR')
    app.logger.info(f"Client disconnected from {client_ip}")
    
    # Find and update client status
    client = Client.query.filter_by(ip_address=client_ip).first()
    if client:
        client.status = 'disconnected'
        client.last_seen = datetime.utcnow()
        db.session.commit()
        client_manager.remove_client(client.client_id)
        
        # Emit client update to web interface
        socketio.emit('client_update', {
            'client_id': client.client_id,
            'status': 'disconnected'
        }, broadcast=True)

@socketio.on('client_register')
def handle_client_register(data):
    """Handle client registration"""
    try:
        client_id = data.get('client_id')
        system_info = data.get('system_info', {})
        
        app.logger.info(f"Client {client_id} registering with system info: {system_info}")
        
        # Check if client exists, if not create it
        client = Client.query.filter_by(client_id=client_id).first()
        if not client:
            client = Client(client_id=client_id)
            db.session.add(client)
            
        # Update client information
        client.hostname = system_info.get('hostname')
        client.ip_address = request.environ.get('REMOTE_ADDR')
        client.mac_address = system_info.get('mac_address')
        client.cpu_model = system_info.get('cpu_model')
        client.cpu_cores = system_info.get('cpu_cores')
        client.cpu_frequency = system_info.get('cpu_frequency')
        client.ram_total = system_info.get('ram_total')
        client.disk_total = system_info.get('disk_total')
        client.os_info = system_info.get('os_info')
        client.username = system_info.get('username')
        client.status = 'connected'
        client.last_seen = datetime.utcnow()
        
        db.session.commit()
        
        # Add to client manager
        client_manager.add_client(client_id, {
            'socket_id': request.sid,
            'client_data': client
        })
        
        # Send registration confirmation
        emit('registration_confirmed', {'client_id': client_id})
        
        # Broadcast client update to web interface
        socketio.emit('client_update', {
            'client_id': client_id,
            'status': 'connected',
            'system_info': system_info
        }, broadcast=True)
        
        app.logger.info(f"Client {client_id} registered successfully")
        
    except Exception as e:
        app.logger.error(f"Error registering client: {e}")
        emit('error', {'message': 'Registration failed'})

@socketio.on('system_metrics')
def handle_system_metrics(data):
    """Handle periodic system metrics from clients"""
    try:
        client_id = data.get('client_id')
        metrics = data.get('metrics', {})
        
        client = Client.query.filter_by(client_id=client_id).first()
        if client:
            client.cpu_usage = metrics.get('cpu_usage', 0.0)
            client.ram_usage = metrics.get('ram_usage', 0.0)
            client.disk_usage = metrics.get('disk_usage', 0.0)
            client.network_latency = metrics.get('network_latency', 0.0)
            client.last_seen = datetime.utcnow()
            
            db.session.commit()
            
            # Broadcast metrics update to web interface
            socketio.emit('metrics_update', {
                'client_id': client_id,
                'metrics': metrics
            }, broadcast=True)
            
    except Exception as e:
        app.logger.error(f"Error updating system metrics: {e}")

@socketio.on('job_progress')
def handle_job_progress(data):
    """Handle job progress updates from clients"""
    try:
        job_id = data.get('job_id')
        progress = data.get('progress', 0.0)
        estimated_time = data.get('estimated_time', 0)
        
        job = Job.query.get(job_id)
        if job:
            job.progress_percent = progress
            job.estimated_time = estimated_time
            db.session.commit()
            
            # Broadcast progress update to web interface
            socketio.emit('job_progress_update', {
                'job_id': job_id,
                'progress': progress,
                'estimated_time': estimated_time
            }, broadcast=True)
            
    except Exception as e:
        app.logger.error(f"Error updating job progress: {e}")

@socketio.on('password_cracked')
def handle_password_cracked(data):
    """Handle password cracked notifications from clients"""
    try:
        job_id = data.get('job_id')
        hash_value = data.get('hash_value')
        password = data.get('password')
        client_id = data.get('client_id')
        
        # Find the hash and update it
        hash_obj = Hash.query.filter_by(job_id=job_id, hash_value=hash_value).first()
        if hash_obj:
            hash_obj.is_cracked = True
            hash_obj.cracked_password = password
            hash_obj.cracked_at = datetime.utcnow()
            
            # Find client
            client = Client.query.filter_by(client_id=client_id).first()
            if client:
                hash_obj.cracked_by_client_id = client.id
                
            # Update job progress
            job = Job.query.get(job_id)
            if job:
                job.cracked_hashes += 1
                job.progress_percent = (job.cracked_hashes / job.total_hashes) * 100
                
                # Check if job is complete
                if job.cracked_hashes == job.total_hashes:
                    job.status = 'completed'
                    job.completed_at = datetime.utcnow()
                    job.actual_time = int((job.completed_at - job.started_at).total_seconds())
                    
                    # Update client status
                    if client:
                        client.status = 'connected'
                        
            db.session.commit()
            
            # Broadcast password cracked notification
            socketio.emit('password_cracked', {
                'job_id': job_id,
                'hash_value': hash_value,
                'password': password,
                'client_id': client_id,
                'cracked_at': datetime.utcnow().isoformat()
            }, broadcast=True)
            
            app.logger.info(f"Password cracked for job {job_id}: {hash_value} -> {password}")
            
    except Exception as e:
        app.logger.error(f"Error handling cracked password: {e}")

@socketio.on('job_failed')
def handle_job_failed(data):
    """Handle job failure notifications from clients"""
    try:
        job_id = data.get('job_id')
        error_message = data.get('error_message', 'Unknown error')
        client_id = data.get('client_id')
        
        job = Job.query.get(job_id)
        if job:
            job.status = 'failed'
            job.completed_at = datetime.utcnow()
            
            # Update client status
            client = Client.query.filter_by(client_id=client_id).first()
            if client:
                client.status = 'connected'
                
            # Log the error
            log_entry = JobLog(
                job_id=job_id,
                client_id=client.id if client else None,
                level='error',
                message=f"Job failed: {error_message}"
            )
            db.session.add(log_entry)
            db.session.commit()
            
            # Broadcast job failure notification
            socketio.emit('job_failed', {
                'job_id': job_id,
                'error_message': error_message,
                'client_id': client_id
            }, broadcast=True)
            
            app.logger.error(f"Job {job_id} failed on client {client_id}: {error_message}")
            
    except Exception as e:
        app.logger.error(f"Error handling job failure: {e}")

def start_background_tasks():
    """Start background tasks for the server"""
    # Start job queue processor
    job_thread = threading.Thread(target=client_manager.process_job_queue)
    job_thread.daemon = True
    job_thread.start()
    
    # Start network scanner
    def network_scanner():
        while True:
            try:
                # Scan for potential clients on the network
                network_info = get_network_info()
                if network_info:
                    active_hosts = scan_network(network_info['network'])
                    app.logger.debug(f"Found {len(active_hosts)} active hosts on network")
                    
                # Clean up old disconnected clients
                cutoff_time = datetime.utcnow() - timedelta(minutes=30)
                old_clients = Client.query.filter(
                    Client.status == 'disconnected',
                    Client.last_seen < cutoff_time
                ).all()
                
                for client in old_clients:
                    app.logger.info(f"Removing old client {client.client_id}")
                    db.session.delete(client)
                    
                db.session.commit()
                
            except Exception as e:
                app.logger.error(f"Error in network scanner: {e}")
                
            time.sleep(300)  # Scan every 5 minutes
    
    scanner_thread = threading.Thread(target=network_scanner)
    scanner_thread.daemon = True
    scanner_thread.start()

# Start background tasks when the module is imported
start_background_tasks()
