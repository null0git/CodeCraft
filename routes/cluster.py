#!/usr/bin/env python3
"""
Cluster Management Routes for CrackPi
Handles cluster operations, health monitoring, and failover
"""

from flask import Blueprint, request, jsonify, render_template
from flask_login import login_required, current_user
from datetime import datetime
import logging
from typing import Dict, List

logger = logging.getLogger(__name__)

cluster_bp = Blueprint('cluster', __name__, url_prefix='/cluster')

# Global cluster manager instance (will be set by main app)
cluster_manager = None

def set_cluster_manager(manager):
    """Set the cluster manager instance"""
    global cluster_manager
    cluster_manager = manager

@cluster_bp.route('/')
@login_required
def cluster_dashboard():
    """Cluster management dashboard"""
    if not cluster_manager:
        return render_template('error.html', 
                             error="Cluster management not initialized"), 500
    
    cluster_info = cluster_manager.get_cluster_info()
    
    return render_template('cluster/dashboard.html',
                         cluster_info=cluster_info,
                         current_node_id=cluster_manager.node_id)

@cluster_bp.route('/nodes')
@login_required
def cluster_nodes():
    """Display cluster nodes"""
    if not cluster_manager:
        return jsonify({'error': 'Cluster management not available'}), 500
    
    cluster_info = cluster_manager.get_cluster_info()
    nodes = cluster_info.get('cluster_state', {}).get('nodes', {})
    
    return render_template('cluster/nodes.html',
                         nodes=nodes,
                         cluster_info=cluster_info)

@cluster_bp.route('/health')
@login_required
def cluster_health():
    """Cluster health monitoring"""
    if not cluster_manager:
        return jsonify({'error': 'Cluster management not available'}), 500
    
    cluster_info = cluster_manager.get_cluster_info()
    
    # Calculate health metrics
    nodes = cluster_info.get('cluster_state', {}).get('nodes', {})
    health_data = {
        'total_nodes': len(nodes),
        'healthy_nodes': len([n for n in nodes.values() if n.get('health_status') == 'healthy']),
        'degraded_nodes': len([n for n in nodes.values() if n.get('health_status') == 'degraded']),
        'failed_nodes': len([n for n in nodes.values() if n.get('health_status') == 'failed']),
        'cluster_state': cluster_info
    }
    
    return render_template('cluster/health.html', health_data=health_data)

@cluster_bp.route('/failover')
@login_required
def failover_history():
    """Display failover history"""
    if not cluster_manager:
        return render_template('error.html', 
                             error="Cluster management not initialized"), 500
    
    # Get failover history from database
    try:
        import sqlite3
        conn = sqlite3.connect(cluster_manager.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT event_type, old_leader, new_leader, reason, timestamp
            FROM failover_log 
            ORDER BY timestamp DESC 
            LIMIT 50
        ''')
        
        failover_events = []
        for row in cursor.fetchall():
            failover_events.append({
                'event_type': row[0],
                'old_leader': row[1],
                'new_leader': row[2],
                'reason': row[3],
                'timestamp': row[4]
            })
        
        conn.close()
        
    except Exception as e:
        logger.error(f"Error fetching failover history: {e}")
        failover_events = []
    
    return render_template('cluster/failover.html', 
                         failover_events=failover_events)

# API Routes for cluster communication

@cluster_bp.route('/api/info', methods=['GET'])
def api_cluster_info():
    """Get cluster information (used by other nodes)"""
    if not cluster_manager:
        return jsonify({'error': 'Cluster management not available'}), 500
    
    return jsonify(cluster_manager.get_cluster_info())

@cluster_bp.route('/api/vote', methods=['POST'])
def api_vote_request():
    """Handle vote request from candidate"""
    if not cluster_manager:
        return jsonify({'error': 'Cluster management not available'}), 500
    
    vote_request = request.get_json()
    if not vote_request:
        return jsonify({'error': 'Invalid vote request'}), 400
    
    try:
        result = cluster_manager.handle_vote_request(vote_request)
        return jsonify(result)
    except Exception as e:
        logger.error(f"Vote request error: {e}")
        return jsonify({'error': 'Vote processing failed'}), 500

@cluster_bp.route('/api/heartbeat', methods=['POST'])
def api_heartbeat():
    """Handle heartbeat from leader"""
    if not cluster_manager:
        return jsonify({'error': 'Cluster management not available'}), 500
    
    heartbeat_data = request.get_json()
    if not heartbeat_data:
        return jsonify({'error': 'Invalid heartbeat data'}), 400
    
    try:
        result = cluster_manager.handle_heartbeat(heartbeat_data)
        return jsonify(result)
    except Exception as e:
        logger.error(f"Heartbeat processing error: {e}")
        return jsonify({'error': 'Heartbeat processing failed'}), 500

@cluster_bp.route('/api/join', methods=['POST'])
def api_join_cluster():
    """Handle cluster join request"""
    if not cluster_manager:
        return jsonify({'error': 'Cluster management not available'}), 500
    
    join_request = request.get_json()
    if not join_request:
        return jsonify({'error': 'Invalid join request'}), 400
    
    try:
        node_info = join_request.get('node_info')
        if not node_info:
            return jsonify({'error': 'Missing node information'}), 400
        
        # Add node to cluster (if we're the leader)
        if cluster_manager.role == 'leader':
            from utils.cluster_manager import ClusterNode
            
            node = ClusterNode(
                node_id=node_info['node_id'],
                hostname=node_info['hostname'],
                ip_address=node_info['ip_address'],
                port=node_info['port'],
                role='follower',
                last_seen=datetime.utcnow(),
                health_status='healthy',
                load_metrics=node_info.get('load_metrics', {})
            )
            
            cluster_manager.cluster_state.nodes[node.node_id] = node
            cluster_manager._save_known_node(node)
            
            if cluster_manager.on_node_join:
                cluster_manager.on_node_join(node)
            
            logger.info(f"Node joined cluster: {node.node_id}")
            
            return jsonify({
                'success': True,
                'leader_id': cluster_manager.node_id,
                'term': cluster_manager.current_term,
                'cluster_state': cluster_manager.cluster_state.to_dict()
            })
        else:
            # Redirect to leader
            return jsonify({
                'success': False,
                'leader_id': cluster_manager.cluster_state.leader_node_id,
                'error': 'Not cluster leader'
            }), 302
            
    except Exception as e:
        logger.error(f"Cluster join error: {e}")
        return jsonify({'error': 'Join processing failed'}), 500

@cluster_bp.route('/api/leave', methods=['POST'])
def api_leave_cluster():
    """Handle cluster leave request"""
    if not cluster_manager:
        return jsonify({'error': 'Cluster management not available'}), 500
    
    leave_request = request.get_json()
    if not leave_request:
        return jsonify({'error': 'Invalid leave request'}), 400
    
    try:
        node_id = leave_request.get('node_id')
        if not node_id:
            return jsonify({'error': 'Missing node ID'}), 400
        
        # Remove node from cluster (if we're the leader)
        if cluster_manager.role == 'leader':
            if node_id in cluster_manager.cluster_state.nodes:
                node = cluster_manager.cluster_state.nodes[node_id]
                del cluster_manager.cluster_state.nodes[node_id]
                
                if cluster_manager.on_node_leave:
                    cluster_manager.on_node_leave(node)
                
                cluster_manager._log_failover_event(
                    'node_left',
                    reason=f'Node {node_id} left cluster gracefully'
                )
                
                logger.info(f"Node left cluster: {node_id}")
                
                return jsonify({'success': True})
            else:
                return jsonify({'error': 'Node not found'}), 404
        else:
            return jsonify({'error': 'Not cluster leader'}), 403
            
    except Exception as e:
        logger.error(f"Cluster leave error: {e}")
        return jsonify({'error': 'Leave processing failed'}), 500

@cluster_bp.route('/api/status', methods=['GET'])
def api_cluster_status():
    """Get detailed cluster status"""
    if not cluster_manager:
        return jsonify({'error': 'Cluster management not available'}), 500
    
    try:
        cluster_info = cluster_manager.get_cluster_info()
        
        # Add additional status information
        status_data = {
            'cluster_info': cluster_info,
            'current_node': {
                'id': cluster_manager.node_id,
                'role': cluster_manager.role,
                'hostname': cluster_manager.hostname,
                'ip_address': cluster_manager.ip_address,
                'port': cluster_manager.port,
                'load_metrics': cluster_manager._get_current_load_metrics()
            },
            'uptime': (datetime.utcnow() - cluster_manager.current_node.last_seen).total_seconds() if cluster_manager.current_node else 0,
            'threads_active': len([t for t in cluster_manager.threads.values() if t.is_alive()]) if cluster_manager.threads else 0
        }
        
        return jsonify(status_data)
        
    except Exception as e:
        logger.error(f"Status request error: {e}")
        return jsonify({'error': 'Status retrieval failed'}), 500

@cluster_bp.route('/api/force-election', methods=['POST'])
@login_required
def api_force_election():
    """Force a new leader election (admin only)"""
    if not current_user.is_admin:
        return jsonify({'error': 'Admin access required'}), 403
    
    if not cluster_manager:
        return jsonify({'error': 'Cluster management not available'}), 500
    
    try:
        logger.info(f"Forced election triggered by user: {current_user.username}")
        
        cluster_manager._log_failover_event(
            'forced_election',
            old_leader=cluster_manager.cluster_state.leader_node_id,
            reason=f'Manual election triggered by {current_user.username}'
        )
        
        # Start new election
        cluster_manager.start_leader_election()
        
        return jsonify({
            'success': True,
            'message': 'Leader election initiated'
        })
        
    except Exception as e:
        logger.error(f"Forced election error: {e}")
        return jsonify({'error': 'Election initiation failed'}), 500

@cluster_bp.route('/api/metrics', methods=['GET'])
def api_cluster_metrics():
    """Get cluster performance metrics"""
    if not cluster_manager:
        return jsonify({'error': 'Cluster management not available'}), 500
    
    try:
        cluster_info = cluster_manager.get_cluster_info()
        nodes = cluster_info.get('cluster_state', {}).get('nodes', {})
        
        # Aggregate metrics
        total_cpu = 0
        total_memory = 0
        total_disk = 0
        node_count = 0
        
        for node in nodes.values():
            load_metrics = node.get('load_metrics', {})
            if load_metrics:
                total_cpu += load_metrics.get('cpu_usage', 0)
                total_memory += load_metrics.get('memory_usage', 0)
                total_disk += load_metrics.get('disk_usage', 0)
                node_count += 1
        
        # Add current node
        current_metrics = cluster_manager._get_current_load_metrics()
        if current_metrics:
            total_cpu += current_metrics.get('cpu_usage', 0)
            total_memory += current_metrics.get('memory_usage', 0)
            total_disk += current_metrics.get('disk_usage', 0)
            node_count += 1
        
        # Calculate averages
        avg_cpu = total_cpu / node_count if node_count > 0 else 0
        avg_memory = total_memory / node_count if node_count > 0 else 0
        avg_disk = total_disk / node_count if node_count > 0 else 0
        
        metrics_data = {
            'cluster_averages': {
                'cpu_usage': round(avg_cpu, 2),
                'memory_usage': round(avg_memory, 2),
                'disk_usage': round(avg_disk, 2)
            },
            'node_metrics': {},
            'cluster_health': {
                'total_nodes': node_count,
                'healthy_nodes': len([n for n in nodes.values() if n.get('health_status') == 'healthy']),
                'leader_node': cluster_info.get('leader_id'),
                'current_term': cluster_info.get('term')
            }
        }
        
        # Individual node metrics
        for node_id, node in nodes.items():
            metrics_data['node_metrics'][node_id] = {
                'hostname': node.get('hostname'),
                'health_status': node.get('health_status'),
                'load_metrics': node.get('load_metrics', {}),
                'last_seen': node.get('last_seen')
            }
        
        # Add current node
        metrics_data['node_metrics'][cluster_manager.node_id] = {
            'hostname': cluster_manager.hostname,
            'health_status': 'healthy',
            'load_metrics': current_metrics,
            'last_seen': datetime.utcnow().isoformat()
        }
        
        return jsonify(metrics_data)
        
    except Exception as e:
        logger.error(f"Metrics request error: {e}")
        return jsonify({'error': 'Metrics retrieval failed'}), 500