#!/usr/bin/env python3
"""
CrackPi Network Scanner - Discover clients on LAN
Auto-discovers CrackPi clients using nmap and socket scanning
"""

import os
import sys
import json
import socket
import subprocess
import threading
import time
from typing import List, Dict
import logging
from concurrent.futures import ThreadPoolExecutor
import argparse
import requests

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class CrackPiNetworkScanner:
    """Advanced network scanner for discovering CrackPi clients and servers"""
    
    def __init__(self):
        self.discovered_devices = []
        self.crackpi_ports = [5000, 8080, 3000, 5001]
        self.common_ssh_ports = [22, 2222]
        self.timeout = 3
        
    def get_network_range(self) -> str:
        """Get the current network range for scanning"""
        try:
            # Get default gateway and network
            result = subprocess.run(['ip', 'route', 'show', 'default'], 
                                  capture_output=True, text=True)
            if result.returncode == 0:
                # Extract network interface
                lines = result.stdout.strip().split('\n')
                for line in lines:
                    if 'default via' in line:
                        parts = line.split()
                        interface = parts[-1]
                        break
                else:
                    interface = 'eth0'  # fallback
                
                # Get IP and subnet for interface
                result = subprocess.run(['ip', 'addr', 'show', interface], 
                                      capture_output=True, text=True)
                if result.returncode == 0:
                    for line in result.stdout.split('\n'):
                        if 'inet ' in line and not '127.0.0.1' in line:
                            ip_cidr = line.split()[1]
                            # Convert to network range (e.g., 192.168.1.0/24)
                            ip, prefix = ip_cidr.split('/')
                            octets = ip.split('.')
                            octets[3] = '0'
                            network = '.'.join(octets) + '/' + prefix
                            return network
            
            # Fallback to common ranges
            return "192.168.1.0/24"
            
        except Exception as e:
            logger.error(f"Error getting network range: {e}")
            return "192.168.1.0/24"
    
    def scan_port(self, host: str, port: int) -> bool:
        """Scan a specific port on a host"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(self.timeout)
            result = sock.connect_ex((host, port))
            sock.close()
            return result == 0
        except:
            return False
    
    def check_crackpi_service(self, host: str, port: int) -> Dict:
        """Check if host is running CrackPi service"""
        try:
            # Try to connect to CrackPi API endpoint
            url = f"http://{host}:{port}"
            response = requests.get(f"{url}/api/ping", timeout=3)
            
            if response.status_code == 200:
                # Try to get system info
                try:
                    info_response = requests.get(f"{url}/api/system/info", timeout=2)
                    if info_response.status_code == 200:
                        system_info = info_response.json()
                    else:
                        system_info = {}
                except:
                    system_info = {}
                
                return {
                    'type': 'crackpi_server',
                    'url': url,
                    'system_info': system_info,
                    'responsive': True
                }
            
        except:
            pass
        
        # Check if it looks like a CrackPi client
        if self.scan_port(host, port):
            return {
                'type': 'potential_client',
                'url': f"http://{host}:{port}",
                'responsive': True
            }
        
        return None
    
    def scan_host(self, host: str) -> Dict:
        """Comprehensively scan a single host"""
        host_info = {
            'ip': host,
            'hostname': None,
            'mac_address': None,
            'open_ports': [],
            'services': [],
            'crackpi_services': [],
            'ssh_available': False,
            'os_fingerprint': None
        }
        
        # Try to resolve hostname
        try:
            hostname = socket.gethostbyaddr(host)[0]
            host_info['hostname'] = hostname
        except:
            pass
        
        # Scan common ports
        common_ports = [21, 22, 23, 25, 53, 80, 110, 443, 993, 995] + self.crackpi_ports
        
        with ThreadPoolExecutor(max_workers=20) as executor:
            port_results = list(executor.map(
                lambda p: (p, self.scan_port(host, p)), 
                common_ports
            ))
        
        for port, is_open in port_results:
            if is_open:
                host_info['open_ports'].append(port)
                
                # Check for SSH
                if port in self.common_ssh_ports:
                    host_info['ssh_available'] = True
                
                # Check for CrackPi services
                if port in self.crackpi_ports:
                    crackpi_info = self.check_crackpi_service(host, port)
                    if crackpi_info:
                        host_info['crackpi_services'].append(crackpi_info)
        
        # Try to get MAC address
        try:
            arp_result = subprocess.run(['arp', '-n', host], 
                                      capture_output=True, text=True)
            if arp_result.returncode == 0:
                for line in arp_result.stdout.split('\n'):
                    if host in line:
                        parts = line.split()
                        if len(parts) >= 3:
                            mac = parts[2]
                            if ':' in mac and len(mac) == 17:
                                host_info['mac_address'] = mac
                        break
        except:
            pass
        
        return host_info
    
    def scan_network_range(self, network_range: str = None) -> List[Dict]:
        """Scan entire network range for devices"""
        if not network_range:
            network_range = self.get_network_range()
        
        logger.info(f"Scanning network range: {network_range}")
        
        # Generate host list
        if '/' in network_range:
            # CIDR notation
            import ipaddress
            network = ipaddress.IPv4Network(network_range, strict=False)
            hosts = [str(ip) for ip in network.hosts()]
        else:
            # Assume it's a base IP, scan .1-.254
            base = '.'.join(network_range.split('.')[:-1])
            hosts = [f"{base}.{i}" for i in range(1, 255)]
        
        logger.info(f"Scanning {len(hosts)} hosts...")
        
        # First, do a quick ping sweep to find live hosts
        live_hosts = self.ping_sweep(hosts)
        logger.info(f"Found {len(live_hosts)} live hosts")
        
        # Then scan live hosts in detail
        discovered_devices = []
        with ThreadPoolExecutor(max_workers=10) as executor:
            host_results = list(executor.map(self.scan_host, live_hosts))
        
        for host_info in host_results:
            if host_info['open_ports'] or host_info['crackpi_services']:
                discovered_devices.append(host_info)
        
        self.discovered_devices = discovered_devices
        return discovered_devices
    
    def ping_sweep(self, hosts: List[str]) -> List[str]:
        """Quick ping sweep to find live hosts"""
        live_hosts = []
        
        def ping_host(host):
            try:
                result = subprocess.run(['ping', '-c', '1', '-W', '1', host], 
                                      capture_output=True, text=True)
                return host if result.returncode == 0 else None
            except:
                return None
        
        with ThreadPoolExecutor(max_workers=50) as executor:
            results = list(executor.map(ping_host, hosts))
        
        live_hosts = [host for host in results if host]
        return live_hosts
    
    def find_crackpi_servers(self) -> List[Dict]:
        """Find CrackPi servers on the network"""
        servers = []
        for device in self.discovered_devices:
            for service in device.get('crackpi_services', []):
                if service.get('type') == 'crackpi_server':
                    servers.append({
                        'ip': device['ip'],
                        'hostname': device.get('hostname'),
                        'url': service['url'],
                        'system_info': service.get('system_info', {}),
                        'mac_address': device.get('mac_address')
                    })
        return servers
    
    def find_potential_clients(self) -> List[Dict]:
        """Find devices that could be configured as CrackPi clients"""
        potential_clients = []
        
        for device in self.discovered_devices:
            # Look for Raspberry Pi or Linux devices with SSH
            if device.get('ssh_available'):
                # Check if it looks like a Raspberry Pi
                hostname = device.get('hostname', '').lower()
                is_raspberry_pi = any(indicator in hostname for indicator in 
                                    ['raspberrypi', 'pi', 'rpi'])
                
                potential_clients.append({
                    'ip': device['ip'],
                    'hostname': device.get('hostname'),
                    'mac_address': device.get('mac_address'),
                    'ssh_available': True,
                    'is_raspberry_pi': is_raspberry_pi,
                    'open_ports': device['open_ports'],
                    'setup_command': f"ssh pi@{device['ip']}"
                })
        
        return potential_clients
    
    def generate_setup_commands(self, server_ip: str) -> Dict:
        """Generate setup commands for discovered clients"""
        commands = {
            'server_setup': [
                f"# Setup CrackPi Server on {server_ip}",
                f"git clone https://github.com/your-repo/crackpi.git",
                f"cd crackpi",
                f"chmod +x setup_server.sh",
                f"./setup_server.sh",
                f"# Access web interface at: http://{server_ip}:5000"
            ],
            'client_setup': []
        }
        
        potential_clients = self.find_potential_clients()
        for client in potential_clients:
            client_ip = client['ip']
            commands['client_setup'].append(f"# Setup client on {client_ip}")
            commands['client_setup'].append(f"ssh pi@{client_ip}")
            commands['client_setup'].append(f"git clone https://github.com/your-repo/crackpi.git")
            commands['client_setup'].append(f"cd crackpi")
            commands['client_setup'].append(f"chmod +x setup_client.sh")
            commands['client_setup'].append(f"./setup_client.sh {server_ip}")
            commands['client_setup'].append("")
        
        return commands
    
    def export_results(self, filename: str = 'crackpi_network_scan.json'):
        """Export scan results to JSON file"""
        results = {
            'scan_timestamp': time.time(),
            'network_range': self.get_network_range(),
            'total_devices': len(self.discovered_devices),
            'crackpi_servers': self.find_crackpi_servers(),
            'potential_clients': self.find_potential_clients(),
            'all_devices': self.discovered_devices,
            'setup_commands': self.generate_setup_commands(
                self.find_crackpi_servers()[0]['ip'] if self.find_crackpi_servers() else 'SERVER_IP'
            )
        }
        
        with open(filename, 'w') as f:
            json.dump(results, f, indent=2)
        
        logger.info(f"Results exported to {filename}")
        return results

def main():
    """Main function for network scanning"""
    parser = argparse.ArgumentParser(description='CrackPi Network Scanner')
    parser.add_argument('--network', '-n', 
                       help='Network range to scan (e.g., 192.168.1.0/24)')
    parser.add_argument('--output', '-o', 
                       default='crackpi_scan_results.json',
                       help='Output file for results')
    parser.add_argument('--verbose', '-v', 
                       action='store_true',
                       help='Verbose output')
    parser.add_argument('--servers-only', '-s',
                       action='store_true',
                       help='Only scan for CrackPi servers')
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Create scanner
    scanner = CrackPiNetworkScanner()
    
    print("🔍 CrackPi Network Scanner")
    print("=" * 40)
    
    # Scan network
    devices = scanner.scan_network_range(args.network)
    
    # Find CrackPi servers
    servers = scanner.find_crackpi_servers()
    if servers:
        print(f"\n✅ Found {len(servers)} CrackPi Server(s):")
        for server in servers:
            print(f"  • {server['ip']} ({server.get('hostname', 'Unknown')})")
            print(f"    URL: {server['url']}")
            print(f"    MAC: {server.get('mac_address', 'Unknown')}")
    else:
        print("\n❌ No CrackPi servers found")
    
    if not args.servers_only:
        # Find potential clients
        clients = scanner.find_potential_clients()
        if clients:
            print(f"\n🔧 Found {len(clients)} Potential Client(s):")
            for client in clients:
                indicator = "🥧" if client['is_raspberry_pi'] else "💻"
                print(f"  {indicator} {client['ip']} ({client.get('hostname', 'Unknown')})")
                print(f"    SSH: {'✅' if client['ssh_available'] else '❌'}")
                print(f"    MAC: {client.get('mac_address', 'Unknown')}")
                print(f"    Setup: {client['setup_command']}")
        else:
            print("\n❌ No potential clients found")
    
    # Export results
    results = scanner.export_results(args.output)
    
    print(f"\n📄 Results exported to: {args.output}")
    print(f"📊 Total devices scanned: {len(devices)}")
    
    # Show setup commands
    if servers and not args.servers_only:
        print("\n🚀 Quick Setup Commands:")
        print("-" * 30)
        setup_commands = results['setup_commands']
        
        if setup_commands['client_setup']:
            print("Client Setup Commands:")
            for cmd in setup_commands['client_setup'][:10]:  # Show first 10 lines
                print(f"  {cmd}")
            if len(setup_commands['client_setup']) > 10:
                print(f"  ... and {len(setup_commands['client_setup'])-10} more lines")

if __name__ == '__main__':
    main()