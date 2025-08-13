#!/usr/bin/env python3
"""
Advanced Cracking Demo for CrackPi System
Demonstrates all the enhanced features and capabilities
"""

import hashlib
import time
import requests
import json
from utils.advanced_cracker import AdvancedPasswordCracker, DistributedHashManager

def demo_hash_generation():
    """Generate demo hashes for testing"""
    passwords = [
        "admin123",
        "password1", 
        "test456",
        "qwerty",
        "123456789",
        "welcome1",
        "admin",
        "root123"
    ]
    
    hashes = {}
    for password in passwords:
        hashes[password] = {
            'md5': hashlib.md5(password.encode()).hexdigest(),
            'sha1': hashlib.sha1(password.encode()).hexdigest(),
            'sha256': hashlib.sha256(password.encode()).hexdigest(),
            'sha512': hashlib.sha512(password.encode()).hexdigest()
        }
    
    return hashes

def demo_advanced_attacks():
    """Demonstrate advanced attack modes"""
    print("🔥 Advanced CrackPi Attack Modes Demo")
    print("=" * 50)
    
    cracker = AdvancedPasswordCracker()
    demo_hashes = demo_hash_generation()
    
    # Demo 1: Dictionary Attack
    print("\n1. Dictionary Attack Demo")
    target_password = "admin123"
    target_hash = demo_hashes[target_password]['md5']
    
    config = {
        'mode': 'dictionary',
        'max_words': 1000
    }
    
    result = cracker.crack_hash(target_hash, 'md5', config)
    print(f"Target: {target_password} -> {target_hash}")
    print(f"Result: {result}")
    
    # Demo 2: Mask Attack
    print("\n2. Mask Attack Demo")
    target_password = "test456"
    target_hash = demo_hashes[target_password]['md5']
    
    config = {
        'mode': 'mask',
        'mask': '?l?l?l?l?d?d?d'  # 4 lowercase + 3 digits
    }
    
    result = cracker.crack_hash(target_hash, 'md5', config)
    print(f"Target: {target_password} -> {target_hash}")
    print(f"Mask: {config['mask']}")
    print(f"Result: {result}")
    
    # Demo 3: Hybrid Attack
    print("\n3. Hybrid Attack Demo")
    target_password = "admin1"
    target_hash = hashlib.md5(target_password.encode()).hexdigest()
    
    config = {
        'mode': 'hybrid',
        'append_chars': '0123456789',
        'max_append': 2
    }
    
    result = cracker.crack_hash(target_hash, 'md5', config)
    print(f"Target: {target_password} -> {target_hash}")
    print(f"Result: {result}")

def demo_hash_distribution():
    """Demonstrate hash distribution strategies"""
    print("\n🌐 Hash Distribution Strategies Demo")
    print("=" * 50)
    
    manager = DistributedHashManager()
    
    # Sample hashes and clients
    hashes = [f"hash_{i:03d}" for i in range(20)]
    clients = [
        {'client_id': 'client_001', 'cpu_cores': 4, 'ram_total': 8000000, 'cpu_usage': 20},
        {'client_id': 'client_002', 'cpu_cores': 8, 'ram_total': 16000000, 'cpu_usage': 10},
        {'client_id': 'client_003', 'cpu_cores': 2, 'ram_total': 4000000, 'cpu_usage': 60},
        {'client_id': 'client_004', 'cpu_cores': 16, 'ram_total': 32000000, 'cpu_usage': 5}
    ]
    
    # Test different distribution strategies
    strategies = ['equal_split', 'capability_based', 'dynamic_load', 'hash_based']
    
    for strategy in strategies:
        print(f"\n--- {strategy.upper()} Strategy ---")
        distribution = manager.distribute_work(hashes, clients, strategy)
        
        for client_id, assignment in distribution.items():
            print(f"{client_id}: {assignment['hash_count']} hashes, "
                  f"priority: {assignment['priority']}, "
                  f"estimated: {assignment['estimated_time']:.0f}s")

def demo_server_integration():
    """Test server integration with advanced features"""
    print("\n🚀 Server Integration Demo")
    print("=" * 30)
    
    server_url = "http://localhost:5000"
    
    try:
        # Test server ping
        response = requests.get(f"{server_url}/api/ping", timeout=5)
        if response.status_code == 200:
            print("✅ Server is running and responding")
            print(f"Response: {response.json()}")
        else:
            print("❌ Server not responding properly")
            return
    except Exception as e:
        print(f"❌ Cannot connect to server: {e}")
        return
    
    # Test client registration
    try:
        registration_data = {
            'client_id': 'demo_client_001',
            'client_mode': 'enhanced',
            'system_info': {
                'cpu': {'cores': 8, 'model': 'Demo CPU'},
                'memory': {'total': 16000000000},
                'network': {'hostname': 'demo-host', 'ip_address': '192.168.1.100'}
            },
            'capabilities': {
                'cpu_cores': 8,
                'memory_gb': 16,
                'has_gpu': True,
                'recommended_mode': 'enhanced'
            }
        }
        
        response = requests.post(
            f"{server_url}/api/clients/register",
            json=registration_data,
            timeout=5
        )
        
        if response.status_code == 200:
            print("✅ Client registration successful")
            print(f"Response: {response.json()}")
        else:
            print(f"❌ Client registration failed: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Registration error: {e}")

def main():
    """Main demo function"""
    print("🎯 CrackPi Advanced Features Demonstration")
    print("=" * 60)
    
    # Demo advanced attacks
    demo_advanced_attacks()
    
    # Demo hash distribution
    demo_hash_distribution()
    
    # Demo server integration
    demo_server_integration()
    
    print("\n🎉 Demo Complete!")
    print("\nAdvanced Features Available:")
    print("- Multiple attack modes (dictionary, mask, hybrid, rule-based)")
    print("- Intelligent hash distribution across clients")
    print("- Automatic capability detection and optimization")
    print("- Concurrent multi-hash cracking")
    print("- Universal client with auto-configuration")
    print("- Production-ready deployment scripts")

if __name__ == '__main__':
    main()