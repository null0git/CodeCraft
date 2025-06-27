import os
import platform
import socket
import subprocess
import logging
import psutil
from typing import Dict

logger = logging.getLogger(__name__)

def get_system_info() -> Dict:
    """
    Get comprehensive system information
    """
    try:
        # Basic system information
        info = {
            'hostname': socket.gethostname(),
            'platform': platform.platform(),
            'architecture': platform.architecture()[0],
            'processor': platform.processor(),
            'python_version': platform.python_version(),
            'os_info': f"{platform.system()} {platform.release()}",
            'username': os.getenv('USER', os.getenv('USERNAME', 'unknown'))
        }
        
        # CPU information
        try:
            info['cpu_model'] = get_cpu_model()
            info['cpu_cores'] = psutil.cpu_count(logical=False)
            info['cpu_threads'] = psutil.cpu_count(logical=True)
            
            # Get CPU frequency
            cpu_freq = psutil.cpu_freq()
            if cpu_freq:
                info['cpu_frequency'] = cpu_freq.current
            else:
                info['cpu_frequency'] = 0.0
                
        except Exception as e:
            logger.error(f"Error getting CPU info: {e}")
            info['cpu_model'] = 'Unknown'
            info['cpu_cores'] = 1
            info['cpu_threads'] = 1
            info['cpu_frequency'] = 0.0
        
        # Memory information
        try:
            mem = psutil.virtual_memory()
            info['ram_total'] = mem.total
            info['ram_available'] = mem.available
        except Exception as e:
            logger.error(f"Error getting memory info: {e}")
            info['ram_total'] = 0
            info['ram_available'] = 0
        
        # Disk information
        try:
            disk = psutil.disk_usage('/')
            info['disk_total'] = disk.total
            info['disk_free'] = disk.free
        except Exception as e:
            logger.error(f"Error getting disk info: {e}")
            info['disk_total'] = 0
            info['disk_free'] = 0
        
        # Network information
        try:
            from .network_utils import get_mac_address, get_local_ip
            info['ip_address'] = get_local_ip()
            info['mac_address'] = get_mac_address()
        except Exception as e:
            logger.error(f"Error getting network info: {e}")
            info['ip_address'] = '127.0.0.1'
            info['mac_address'] = '00:00:00:00:00:00'
        
        return info
        
    except Exception as e:
        logger.error(f"Error getting system info: {e}")
        return {
            'hostname': 'unknown',
            'platform': 'unknown',
            'architecture': 'unknown',
            'processor': 'unknown',
            'python_version': platform.python_version(),
            'os_info': 'unknown',
            'username': 'unknown',
            'cpu_model': 'unknown',
            'cpu_cores': 1,
            'cpu_threads': 1,
            'cpu_frequency': 0.0,
            'ram_total': 0,
            'ram_available': 0,
            'disk_total': 0,
            'disk_free': 0,
            'ip_address': '127.0.0.1',
            'mac_address': '00:00:00:00:00:00'
        }

def get_cpu_model() -> str:
    """
    Get CPU model name
    """
    try:
        if platform.system() == 'Linux':
            with open('/proc/cpuinfo', 'r') as f:
                for line in f:
                    if line.startswith('model name'):
                        return line.split(':')[1].strip()
        elif platform.system() == 'Darwin':  # macOS
            result = subprocess.run(
                ['sysctl', '-n', 'machdep.cpu.brand_string'],
                capture_output=True, text=True
            )
            if result.returncode == 0:
                return result.stdout.strip()
        elif platform.system() == 'Windows':
            result = subprocess.run(
                ['wmic', 'cpu', 'get', 'name', '/value'],
                capture_output=True, text=True
            )
            if result.returncode == 0:
                for line in result.stdout.split('\n'):
                    if line.startswith('Name='):
                        return line.split('=')[1].strip()
    except Exception as e:
        logger.error(f"Error getting CPU model: {e}")
    
    return platform.processor() or 'Unknown'

def get_system_metrics() -> Dict:
    """
    Get current system metrics
    """
    try:
        metrics = {}
        
        # CPU usage
        metrics['cpu_usage'] = psutil.cpu_percent(interval=1)
        
        # Memory usage
        mem = psutil.virtual_memory()
        metrics['ram_usage'] = mem.percent
        metrics['ram_used'] = mem.used
        metrics['ram_total'] = mem.total
        
        # Disk usage
        disk = psutil.disk_usage('/')
        metrics['disk_usage'] = (disk.used / disk.total) * 100
        metrics['disk_used'] = disk.used
        metrics['disk_total'] = disk.total
        
        # Network I/O
        net_io = psutil.net_io_counters()
        metrics['network_bytes_sent'] = net_io.bytes_sent
        metrics['network_bytes_recv'] = net_io.bytes_recv
        
        # Load average (Linux/Unix only)
        if hasattr(os, 'getloadavg'):
            load_avg = os.getloadavg()
            metrics['load_avg_1min'] = load_avg[0]
            metrics['load_avg_5min'] = load_avg[1]
            metrics['load_avg_15min'] = load_avg[2]
        
        # Temperature (if available)
        try:
            temps = psutil.sensors_temperatures()
            if temps:
                for name, entries in temps.items():
                    for entry in entries:
                        if entry.current:
                            metrics[f'temp_{name}'] = entry.current
                            break
        except Exception:
            pass  # Temperature monitoring not available
        
        # Process count
        metrics['process_count'] = len(psutil.pids())
        
        return metrics
        
    except Exception as e:
        logger.error(f"Error getting system metrics: {e}")
        return {
            'cpu_usage': 0.0,
            'ram_usage': 0.0,
            'disk_usage': 0.0,
            'network_bytes_sent': 0,
            'network_bytes_recv': 0,
            'process_count': 0
        }

def get_raspberry_pi_info() -> Dict:
    """
    Get Raspberry Pi specific information
    """
    pi_info = {}
    
    try:
        # Check if this is a Raspberry Pi
        with open('/proc/cpuinfo', 'r') as f:
            cpuinfo = f.read()
            if 'BCM' in cpuinfo or 'Raspberry Pi' in cpuinfo:
                pi_info['is_raspberry_pi'] = True
                
                # Get Pi model
                if 'Raspberry Pi 4' in cpuinfo:
                    pi_info['model'] = 'Raspberry Pi 4'
                elif 'Raspberry Pi 3' in cpuinfo:
                    pi_info['model'] = 'Raspberry Pi 3'
                elif 'Raspberry Pi 2' in cpuinfo:
                    pi_info['model'] = 'Raspberry Pi 2'
                elif 'Raspberry Pi' in cpuinfo:
                    pi_info['model'] = 'Raspberry Pi'
                else:
                    pi_info['model'] = 'Unknown Pi Model'
                    
                # Get revision
                for line in cpuinfo.split('\n'):
                    if line.startswith('Revision'):
                        pi_info['revision'] = line.split(':')[1].strip()
                        break
                        
                # Get serial
                for line in cpuinfo.split('\n'):
                    if line.startswith('Serial'):
                        pi_info['serial'] = line.split(':')[1].strip()
                        break
            else:
                pi_info['is_raspberry_pi'] = False
                
    except Exception as e:
        logger.error(f"Error getting Raspberry Pi info: {e}")
        pi_info['is_raspberry_pi'] = False
    
    # Get GPU memory split (Pi specific)
    if pi_info.get('is_raspberry_pi'):
        try:
            result = subprocess.run(
                ['vcgencmd', 'get_mem', 'gpu'],
                capture_output=True, text=True
            )
            if result.returncode == 0:
                gpu_mem = result.stdout.strip().split('=')[1].replace('M', '')
                pi_info['gpu_memory'] = int(gpu_mem)
        except Exception:
            pass
        
        # Get CPU temperature
        try:
            result = subprocess.run(
                ['vcgencmd', 'measure_temp'],
                capture_output=True, text=True
            )
            if result.returncode == 0:
                temp_str = result.stdout.strip().split('=')[1].replace("'C", '')
                pi_info['cpu_temperature'] = float(temp_str)
        except Exception:
            pass
    
    return pi_info

def check_cracking_tools() -> Dict:
    """
    Check if password cracking tools are installed
    """
    tools = {
        'hashcat': False,
        'john': False,
        'hashcat_path': None,
        'john_path': None
    }
    
    # Check for hashcat
    try:
        result = subprocess.run(['which', 'hashcat'], capture_output=True, text=True)
        if result.returncode == 0:
            tools['hashcat'] = True
            tools['hashcat_path'] = result.stdout.strip()
    except Exception:
        pass
    
    # Check for john
    try:
        result = subprocess.run(['which', 'john'], capture_output=True, text=True)
        if result.returncode == 0:
            tools['john'] = True
            tools['john_path'] = result.stdout.strip()
    except Exception:
        pass
    
    return tools
