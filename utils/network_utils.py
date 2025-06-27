import socket
import subprocess
import ipaddress
import logging
import netifaces
import nmap
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

def get_network_info() -> Dict:
    """
    Get information about the current network
    """
    try:
        # Get default gateway
        gateways = netifaces.gateways()
        default_gateway = gateways.get('default', {}).get(netifaces.AF_INET)
        
        if not default_gateway:
            return None
            
        gateway_ip = default_gateway[0]
        interface = default_gateway[1]
        
        # Get interface information
        interface_info = netifaces.ifaddresses(interface)
        if netifaces.AF_INET not in interface_info:
            return None
            
        inet_info = interface_info[netifaces.AF_INET][0]
        ip_address = inet_info['addr']
        netmask = inet_info['netmask']
        
        # Calculate network
        network = ipaddress.IPv4Network(f"{ip_address}/{netmask}", strict=False)
        
        return {
            'interface': interface,
            'ip_address': ip_address,
            'netmask': netmask,
            'gateway': gateway_ip,
            'network': str(network)
        }
        
    except Exception as e:
        logger.error(f"Error getting network info: {e}")
        return None

def scan_network(network_range: str, timeout: int = 10) -> List[Dict]:
    """
    Scan the network for active hosts
    """
    active_hosts = []
    
    try:
        nm = nmap.PortScanner()
        
        # Perform ping scan
        result = nm.scan(hosts=network_range, arguments=f'-sn -T4 --host-timeout {timeout}s')
        
        for host in nm.all_hosts():
            if nm[host].state() == 'up':
                host_info = {
                    'ip': host,
                    'hostname': nm[host].hostname() or 'Unknown',
                    'state': nm[host].state(),
                    'mac': None,
                    'vendor': None
                }
                
                # Get MAC address and vendor if available
                if 'mac' in nm[host]['addresses']:
                    host_info['mac'] = nm[host]['addresses']['mac']
                    
                # Try to get vendor information
                if nm[host].get('vendor'):
                    host_info['vendor'] = nm[host]['vendor'].get(host_info['mac'], 'Unknown')
                
                active_hosts.append(host_info)
                
    except Exception as e:
        logger.error(f"Error scanning network {network_range}: {e}")
    
    return active_hosts

def get_local_ip() -> str:
    """
    Get the local IP address
    """
    try:
        # Connect to a remote server to determine local IP
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
        return local_ip
    except Exception:
        return "127.0.0.1"

def get_mac_address(interface: str = None) -> str:
    """
    Get MAC address of the specified interface or default interface
    """
    try:
        if not interface:
            # Get default interface
            gateways = netifaces.gateways()
            default_gateway = gateways.get('default', {}).get(netifaces.AF_INET)
            if default_gateway:
                interface = default_gateway[1]
        
        if interface:
            interface_info = netifaces.ifaddresses(interface)
            if netifaces.AF_LINK in interface_info:
                return interface_info[netifaces.AF_LINK][0]['addr']
                
    except Exception as e:
        logger.error(f"Error getting MAC address: {e}")
    
    return "00:00:00:00:00:00"

def ping_host(host: str, timeout: int = 5) -> bool:
    """
    Ping a host to check if it's reachable
    """
    try:
        result = subprocess.run(
            ['ping', '-c', '1', '-W', str(timeout), host],
            capture_output=True,
            text=True
        )
        return result.returncode == 0
    except Exception as e:
        logger.error(f"Error pinging {host}: {e}")
        return False

def measure_latency(host: str, port: int = 80, timeout: int = 5) -> float:
    """
    Measure network latency to a host
    """
    try:
        import time
        
        start_time = time.time()
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        
        result = sock.connect_ex((host, port))
        end_time = time.time()
        
        sock.close()
        
        if result == 0:
            return (end_time - start_time) * 1000  # Return in milliseconds
        else:
            return float('inf')  # Connection failed
            
    except Exception as e:
        logger.error(f"Error measuring latency to {host}: {e}")
        return float('inf')

def discover_crackpi_clients(network_range: str, server_port: int = 5000) -> List[Dict]:
    """
    Discover CrackPi clients on the network by scanning for open ports
    """
    potential_clients = []
    
    try:
        nm = nmap.PortScanner()
        
        # Scan for hosts with the CrackPi client port open
        result = nm.scan(
            hosts=network_range,
            ports=str(server_port),
            arguments='-sS -T4 --host-timeout 10s'
        )
        
        for host in nm.all_hosts():
            if nm[host].state() == 'up':
                tcp_ports = nm[host].get('tcp', {})
                if server_port in tcp_ports and tcp_ports[server_port]['state'] == 'open':
                    client_info = {
                        'ip': host,
                        'hostname': nm[host].hostname() or 'Unknown',
                        'port': server_port,
                        'state': 'potential_client'
                    }
                    
                    if 'mac' in nm[host]['addresses']:
                        client_info['mac'] = nm[host]['addresses']['mac']
                    
                    potential_clients.append(client_info)
                    
    except Exception as e:
        logger.error(f"Error discovering CrackPi clients: {e}")
    
    return potential_clients

def check_port_open(host: str, port: int, timeout: int = 5) -> bool:
    """
    Check if a specific port is open on a host
    """
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((host, port))
        sock.close()
        return result == 0
    except Exception as e:
        logger.error(f"Error checking port {port} on {host}: {e}")
        return False
