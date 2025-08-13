#!/usr/bin/env python3
"""
Cluster Management with Automatic Failover for CrackPi
Implements leader election, health monitoring, and state synchronization
"""

import os
import time
import json
import threading
import hashlib
import socket
import logging
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Callable
from dataclasses import dataclass, asdict
from concurrent.futures import ThreadPoolExecutor, as_completed
import sqlite3

logger = logging.getLogger(__name__)

@dataclass
class ClusterNode:
    """Represents a cluster node"""
    node_id: str
    hostname: str
    ip_address: str
    port: int
    role: str  # 'leader', 'follower', 'candidate'
    last_seen: datetime
    health_status: str  # 'healthy', 'degraded', 'failed'
    load_metrics: Dict
    is_active: bool = True
    
    def to_dict(self):
        data = asdict(self)
        data['last_seen'] = self.last_seen.isoformat()
        return data
    
    @classmethod
    def from_dict(cls, data: Dict):
        data['last_seen'] = datetime.fromisoformat(data['last_seen'])
        return cls(**data)

@dataclass
class ClusterState:
    """Represents the current cluster state"""
    leader_node_id: Optional[str]
    nodes: Dict[str, ClusterNode]
    term: int  # Election term for leader election
    last_heartbeat: datetime
    sync_timestamp: datetime
    
    def to_dict(self):
        return {
            'leader_node_id': self.leader_node_id,
            'nodes': {k: v.to_dict() for k, v in self.nodes.items()},
            'term': self.term,
            'last_heartbeat': self.last_heartbeat.isoformat(),
            'sync_timestamp': self.sync_timestamp.isoformat()
        }

class ClusterManager:
    """Manages cluster operations with automatic failover"""
    
    def __init__(self, node_config: Dict, cluster_config: Dict = None):
        self.node_id = self._generate_node_id(node_config)
        self.hostname = node_config.get('hostname', socket.gethostname())
        self.ip_address = node_config.get('ip_address', self._get_local_ip())
        self.port = node_config.get('port', 5000)
        
        # Cluster configuration
        self.cluster_config = cluster_config or {}
        self.election_timeout = self.cluster_config.get('election_timeout', 30)
        self.heartbeat_interval = self.cluster_config.get('heartbeat_interval', 5)
        self.health_check_interval = self.cluster_config.get('health_check_interval', 10)
        self.max_failed_health_checks = self.cluster_config.get('max_failed_health_checks', 3)
        
        # Current node state
        self.role = 'follower'
        self.current_term = 0
        self.voted_for = None
        self.last_heartbeat_received = datetime.utcnow()
        
        # Cluster state
        self.cluster_state = ClusterState(
            leader_node_id=None,
            nodes={},
            term=0,
            last_heartbeat=datetime.utcnow(),
            sync_timestamp=datetime.utcnow()
        )
        
        # Threading
        self.running = False
        self.threads = {}
        self.executor = ThreadPoolExecutor(max_workers=10)
        
        # Database for persistence
        self.db_path = 'cluster_state.db'
        self._init_database()
        
        # Callbacks
        self.on_leadership_change = None
        self.on_node_join = None
        self.on_node_leave = None
        self.on_cluster_health_change = None
        
        # Known cluster nodes
        self.known_nodes = set()
        self._load_known_nodes()
        
        # Current node
        self.current_node = ClusterNode(
            node_id=self.node_id,
            hostname=self.hostname,
            ip_address=self.ip_address,
            port=self.port,
            role=self.role,
            last_seen=datetime.utcnow(),
            health_status='healthy',
            load_metrics={}
        )
        
        logger.info(f"Cluster Manager initialized - Node ID: {self.node_id}")
    
    def _generate_node_id(self, config: Dict) -> str:
        """Generate unique node ID"""
        unique_data = f"{config.get('hostname', socket.gethostname())}-{config.get('ip_address', self._get_local_ip())}-{config.get('port', 5000)}"
        return hashlib.sha256(unique_data.encode()).hexdigest()[:16]
    
    def _get_local_ip(self) -> str:
        """Get local IP address"""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except:
            return "127.0.0.1"
    
    def _init_database(self):
        """Initialize cluster state database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Create tables
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS cluster_state (
                    id INTEGER PRIMARY KEY,
                    state_data TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS known_nodes (
                    node_id TEXT PRIMARY KEY,
                    hostname TEXT,
                    ip_address TEXT,
                    port INTEGER,
                    last_seen DATETIME
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS failover_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_type TEXT,
                    old_leader TEXT,
                    new_leader TEXT,
                    reason TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Database initialization error: {e}")
    
    def _load_known_nodes(self):
        """Load known cluster nodes from database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('SELECT node_id, hostname, ip_address, port FROM known_nodes')
            rows = cursor.fetchall()
            
            for row in rows:
                node_id, hostname, ip_address, port = row
                self.known_nodes.add(f"{ip_address}:{port}")
                
            conn.close()
            logger.info(f"Loaded {len(self.known_nodes)} known nodes")
            
        except Exception as e:
            logger.debug(f"Error loading known nodes: {e}")
    
    def _save_known_node(self, node: ClusterNode):
        """Save node to known nodes database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO known_nodes 
                (node_id, hostname, ip_address, port, last_seen)
                VALUES (?, ?, ?, ?, ?)
            ''', (node.node_id, node.hostname, node.ip_address, 
                  node.port, node.last_seen))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Error saving known node: {e}")
    
    def _save_cluster_state(self):
        """Persist cluster state to database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            state_json = json.dumps(self.cluster_state.to_dict())
            cursor.execute(
                'INSERT INTO cluster_state (state_data) VALUES (?)',
                (state_json,)
            )
            
            # Keep only recent states
            cursor.execute(
                'DELETE FROM cluster_state WHERE id NOT IN (SELECT id FROM cluster_state ORDER BY timestamp DESC LIMIT 10)'
            )
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Error saving cluster state: {e}")
    
    def _log_failover_event(self, event_type: str, old_leader: str = None, 
                           new_leader: str = None, reason: str = None):
        """Log failover events"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO failover_log (event_type, old_leader, new_leader, reason)
                VALUES (?, ?, ?, ?)
            ''', (event_type, old_leader, new_leader, reason))
            
            conn.commit()
            conn.close()
            
            logger.info(f"Failover event logged: {event_type} - {reason}")
            
        except Exception as e:
            logger.error(f"Error logging failover event: {e}")
    
    def discover_cluster_nodes(self) -> List[str]:
        """Discover other cluster nodes on the network"""
        discovered_nodes = []
        
        try:
            import ipaddress
            import netifaces
            
            # Get network interfaces
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
                            
                            # Scan common server IPs
                            for host_ip in network.hosts():
                                if str(host_ip) == self.ip_address:
                                    continue
                                    
                                for port in [5000, 5001, 5002, 8080]:
                                    try:
                                        url = f"http://{host_ip}:{port}/api/cluster/info"
                                        response = requests.get(url, timeout=2)
                                        if response.status_code == 200:
                                            discovered_nodes.append(f"{host_ip}:{port}")
                                            break
                                    except:
                                        continue
                                        
                        break  # Only scan first valid interface
                except:
                    continue
                    
        except Exception as e:
            logger.debug(f"Node discovery error: {e}")
        
        # Also include known nodes
        discovered_nodes.extend(list(self.known_nodes))
        
        return list(set(discovered_nodes))
    
    def start_leader_election(self):
        """Start leader election process"""
        logger.info("Starting leader election")
        
        self.current_term += 1
        self.role = 'candidate'
        self.voted_for = self.node_id
        
        # Reset election timer
        self.last_heartbeat_received = datetime.utcnow()
        
        # Request votes from other nodes
        votes_received = 1  # Vote for self
        total_nodes = len(self.cluster_state.nodes) + 1
        
        discovered_nodes = self.discover_cluster_nodes()
        
        # Send vote requests
        vote_futures = []
        for node_addr in discovered_nodes:
            future = self.executor.submit(self._request_vote, node_addr)
            vote_futures.append(future)
        
        # Collect votes
        for future in as_completed(vote_futures, timeout=10):
            try:
                if future.result():
                    votes_received += 1
            except:
                continue
        
        # Check if majority achieved
        if votes_received > total_nodes // 2:
            self._become_leader()
        else:
            self.role = 'follower'
            logger.info("Election failed - insufficient votes")
    
    def _request_vote(self, node_addr: str) -> bool:
        """Request vote from a cluster node"""
        try:
            vote_request = {
                'term': self.current_term,
                'candidate_id': self.node_id,
                'last_log_index': 0,  # Simplified for now
                'last_log_term': 0
            }
            
            url = f"http://{node_addr}/api/cluster/vote"
            response = requests.post(url, json=vote_request, timeout=5)
            
            if response.status_code == 200:
                result = response.json()
                return result.get('vote_granted', False)
                
        except Exception as e:
            logger.debug(f"Vote request failed for {node_addr}: {e}")
        
        return False
    
    def _become_leader(self):
        """Become cluster leader"""
        old_leader = self.cluster_state.leader_node_id
        
        self.role = 'leader'
        self.cluster_state.leader_node_id = self.node_id
        self.cluster_state.term = self.current_term
        
        logger.info(f"Became cluster leader - Term: {self.current_term}")
        
        # Log failover event
        self._log_failover_event(
            'leader_elected',
            old_leader=old_leader,
            new_leader=self.node_id,
            reason='Election won'
        )
        
        # Notify callback
        if self.on_leadership_change:
            self.on_leadership_change(True, old_leader, self.node_id)
        
        # Start leader duties
        self._start_leader_duties()
    
    def _start_leader_duties(self):
        """Start leader-specific tasks"""
        # Send heartbeats to followers
        if 'heartbeat_sender' not in self.threads:
            heartbeat_thread = threading.Thread(
                target=self._send_heartbeats,
                daemon=True
            )
            self.threads['heartbeat_sender'] = heartbeat_thread
            heartbeat_thread.start()
        
        # Coordinate cluster operations
        if 'cluster_coordinator' not in self.threads:
            coordinator_thread = threading.Thread(
                target=self._coordinate_cluster,
                daemon=True
            )
            self.threads['cluster_coordinator'] = coordinator_thread
            coordinator_thread.start()
    
    def _send_heartbeats(self):
        """Send heartbeats to follower nodes"""
        while self.running and self.role == 'leader':
            try:
                heartbeat_data = {
                    'term': self.current_term,
                    'leader_id': self.node_id,
                    'timestamp': datetime.utcnow().isoformat(),
                    'cluster_state': self.cluster_state.to_dict()
                }
                
                discovered_nodes = self.discover_cluster_nodes()
                
                # Send heartbeats to all nodes
                for node_addr in discovered_nodes:
                    self.executor.submit(self._send_heartbeat_to_node, node_addr, heartbeat_data)
                
                time.sleep(self.heartbeat_interval)
                
            except Exception as e:
                logger.error(f"Heartbeat error: {e}")
                time.sleep(1)
    
    def _send_heartbeat_to_node(self, node_addr: str, heartbeat_data: Dict):
        """Send heartbeat to specific node"""
        try:
            url = f"http://{node_addr}/api/cluster/heartbeat"
            response = requests.post(url, json=heartbeat_data, timeout=3)
            
            if response.status_code == 200:
                # Update node status
                result = response.json()
                node_info = result.get('node_info')
                
                if node_info:
                    node = ClusterNode.from_dict(node_info)
                    self.cluster_state.nodes[node.node_id] = node
                    self._save_known_node(node)
            
        except Exception as e:
            logger.debug(f"Heartbeat failed for {node_addr}: {e}")
            # Mark node as potentially failed
            self._handle_node_failure(node_addr)
    
    def _coordinate_cluster(self):
        """Coordinate cluster-wide operations"""
        while self.running and self.role == 'leader':
            try:
                # Monitor cluster health
                self._monitor_cluster_health()
                
                # Balance workload
                self._balance_cluster_workload()
                
                # Sync cluster state
                self._sync_cluster_state()
                
                time.sleep(self.health_check_interval)
                
            except Exception as e:
                logger.error(f"Cluster coordination error: {e}")
                time.sleep(5)
    
    def _monitor_cluster_health(self):
        """Monitor overall cluster health"""
        healthy_nodes = 0
        total_nodes = len(self.cluster_state.nodes)
        
        for node in self.cluster_state.nodes.values():
            if node.health_status == 'healthy':
                healthy_nodes += 1
            
            # Check if node is stale
            time_since_seen = datetime.utcnow() - node.last_seen
            if time_since_seen > timedelta(seconds=self.heartbeat_interval * 3):
                node.health_status = 'failed'
                self._handle_node_failure(f"{node.ip_address}:{node.port}")
        
        # Calculate cluster health
        if total_nodes > 0:
            health_percentage = (healthy_nodes / total_nodes) * 100
            
            if health_percentage < 50:
                logger.warning(f"Cluster health degraded: {health_percentage:.1f}%")
                if self.on_cluster_health_change:
                    self.on_cluster_health_change('degraded', health_percentage)
            elif health_percentage < 30:
                logger.error(f"Cluster health critical: {health_percentage:.1f}%")
                if self.on_cluster_health_change:
                    self.on_cluster_health_change('critical', health_percentage)
    
    def _balance_cluster_workload(self):
        """Balance workload across cluster nodes"""
        # This would integrate with the job distribution system
        # For now, just log the intent
        active_nodes = [n for n in self.cluster_state.nodes.values() 
                       if n.health_status == 'healthy' and n.is_active]
        
        if len(active_nodes) > 0:
            logger.debug(f"Cluster workload: {len(active_nodes)} active nodes")
    
    def _sync_cluster_state(self):
        """Synchronize cluster state across nodes"""
        self.cluster_state.sync_timestamp = datetime.utcnow()
        self._save_cluster_state()
    
    def _handle_node_failure(self, node_addr: str):
        """Handle node failure detection"""
        logger.warning(f"Node failure detected: {node_addr}")
        
        # Find and mark node as failed
        for node_id, node in self.cluster_state.nodes.items():
            if f"{node.ip_address}:{node.port}" == node_addr:
                node.health_status = 'failed'
                node.is_active = False
                
                if self.on_node_leave:
                    self.on_node_leave(node)
                
                self._log_failover_event(
                    'node_failed',
                    reason=f'Node {node_addr} became unresponsive'
                )
                break
    
    def handle_vote_request(self, vote_request: Dict) -> Dict:
        """Handle incoming vote request"""
        term = vote_request.get('term', 0)
        candidate_id = vote_request.get('candidate_id')
        
        # Grant vote if conditions are met
        vote_granted = False
        
        if term > self.current_term:
            self.current_term = term
            self.voted_for = None
            self.role = 'follower'
        
        if (term == self.current_term and 
            (self.voted_for is None or self.voted_for == candidate_id)):
            vote_granted = True
            self.voted_for = candidate_id
            self.last_heartbeat_received = datetime.utcnow()
        
        return {
            'term': self.current_term,
            'vote_granted': vote_granted
        }
    
    def handle_heartbeat(self, heartbeat_data: Dict) -> Dict:
        """Handle incoming heartbeat from leader"""
        term = heartbeat_data.get('term', 0)
        leader_id = heartbeat_data.get('leader_id')
        
        # Update term and leader if necessary
        if term >= self.current_term:
            self.current_term = term
            self.role = 'follower'
            self.cluster_state.leader_node_id = leader_id
            self.last_heartbeat_received = datetime.utcnow()
            
            # Update cluster state
            cluster_state_data = heartbeat_data.get('cluster_state')
            if cluster_state_data:
                # Selective update to avoid conflicts
                self.cluster_state.term = cluster_state_data.get('term', self.cluster_state.term)
                self.cluster_state.last_heartbeat = datetime.utcnow()
        
        # Return current node info
        self.current_node.last_seen = datetime.utcnow()
        self.current_node.role = self.role
        self.current_node.load_metrics = self._get_current_load_metrics()
        
        return {
            'term': self.current_term,
            'success': True,
            'node_info': self.current_node.to_dict()
        }
    
    def _get_current_load_metrics(self) -> Dict:
        """Get current node load metrics"""
        try:
            import psutil
            return {
                'cpu_usage': psutil.cpu_percent(interval=1),
                'memory_usage': psutil.virtual_memory().percent,
                'disk_usage': psutil.disk_usage('/').percent,
                'active_connections': len(psutil.net_connections()),
                'load_average': os.getloadavg()[0] if hasattr(os, 'getloadavg') else 0
            }
        except:
            return {}
    
    def check_leader_timeout(self):
        """Check if leader has timed out"""
        if self.role != 'leader':
            time_since_heartbeat = datetime.utcnow() - self.last_heartbeat_received
            if time_since_heartbeat > timedelta(seconds=self.election_timeout):
                logger.warning("Leader timeout detected - starting election")
                self.start_leader_election()
    
    def get_cluster_info(self) -> Dict:
        """Get current cluster information"""
        return {
            'node_id': self.node_id,
            'role': self.role,
            'term': self.current_term,
            'leader_id': self.cluster_state.leader_node_id,
            'cluster_state': self.cluster_state.to_dict(),
            'node_count': len(self.cluster_state.nodes),
            'healthy_nodes': len([n for n in self.cluster_state.nodes.values() 
                                if n.health_status == 'healthy'])
        }
    
    def start(self):
        """Start cluster manager"""
        logger.info("Starting Cluster Manager")
        self.running = True
        
        # Start main monitoring thread
        monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.threads['monitor'] = monitor_thread
        monitor_thread.start()
        
        # Start leader timeout checker
        timeout_thread = threading.Thread(target=self._timeout_checker, daemon=True)
        self.threads['timeout_checker'] = timeout_thread
        timeout_thread.start()
        
        # Try to discover and join existing cluster
        self._attempt_cluster_join()
    
    def _monitor_loop(self):
        """Main monitoring loop"""
        while self.running:
            try:
                # Update current node status
                self.current_node.last_seen = datetime.utcnow()
                self.current_node.load_metrics = self._get_current_load_metrics()
                
                # Save periodic state
                if self.role == 'leader':
                    self._save_cluster_state()
                
                time.sleep(5)
                
            except Exception as e:
                logger.error(f"Monitor loop error: {e}")
                time.sleep(1)
    
    def _timeout_checker(self):
        """Check for various timeouts"""
        while self.running:
            try:
                self.check_leader_timeout()
                time.sleep(1)
            except Exception as e:
                logger.error(f"Timeout checker error: {e}")
                time.sleep(1)
    
    def _attempt_cluster_join(self):
        """Attempt to join existing cluster"""
        discovered_nodes = self.discover_cluster_nodes()
        
        for node_addr in discovered_nodes:
            try:
                url = f"http://{node_addr}/api/cluster/info"
                response = requests.get(url, timeout=3)
                
                if response.status_code == 200:
                    cluster_info = response.json()
                    leader_id = cluster_info.get('leader_id')
                    
                    if leader_id:
                        logger.info(f"Found existing cluster with leader: {leader_id}")
                        self.cluster_state.leader_node_id = leader_id
                        self.current_term = cluster_info.get('term', 0)
                        self.role = 'follower'
                        return
                        
            except Exception as e:
                logger.debug(f"Failed to contact {node_addr}: {e}")
        
        # No existing cluster found, start election
        logger.info("No existing cluster found - starting election")
        time.sleep(2)  # Small delay to allow other nodes to start
        self.start_leader_election()
    
    def stop(self):
        """Stop cluster manager"""
        logger.info("Stopping Cluster Manager")
        self.running = False
        
        # Stop all threads
        for thread in self.threads.values():
            if thread.is_alive():
                thread.join(timeout=5)
        
        self.executor.shutdown(wait=True)
        
        # Log shutdown
        self._log_failover_event(
            'node_shutdown',
            reason=f'Node {self.node_id} shutting down gracefully'
        )