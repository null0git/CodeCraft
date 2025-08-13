#!/usr/bin/env python3
"""
Advanced Password Cracking Techniques for CrackPi
Implements multiple cracking strategies and distribution algorithms
"""

import hashlib
import itertools
import threading
import time
import os
import subprocess
from typing import Dict, List, Optional, Callable, Tuple, Any
from concurrent.futures import ThreadPoolExecutor, as_completed
import logging

logger = logging.getLogger(__name__)

class AdvancedPasswordCracker:
    """Advanced password cracking with multiple techniques"""
    
    def __init__(self):
        self.supported_algorithms = {
            'md5': self._md5_hash,
            'sha1': self._sha1_hash,
            'sha256': self._sha256_hash,
            'sha512': self._sha512_hash,
            'ntlm': self._ntlm_hash,
            'bcrypt': self._bcrypt_hash,
            'sha3_256': self._sha3_256_hash,
            'blake2b': self._blake2b_hash,
            'argon2': self._argon2_hash
        }
        
        self.attack_modes = {
            'dictionary': self._dictionary_attack,
            'brute_force': self._brute_force_attack,
            'mask': self._mask_attack,
            'hybrid': self._hybrid_attack,
            'rule_based': self._rule_based_attack,
            'markov': self._markov_attack,
            'prince': self._prince_attack
        }
        
        # Common password patterns
        self.common_patterns = [
            '?d?d?d?d',  # 4 digits
            '?l?l?l?l?l?l',  # 6 lowercase
            '?u?l?l?l?l?l?d?d',  # Capital + lowercase + digits
            '?l?l?l?l?d?d?d?d',  # Word + year pattern
            '?l?l?l?l?l?l?s',  # Word + symbol
        ]
        
        # Character sets
        self.charsets = {
            'digits': '0123456789',
            'lowercase': 'abcdefghijklmnopqrstuvwxyz',
            'uppercase': 'ABCDEFGHIJKLMNOPQRSTUVWXYZ',
            'symbols': '!@#$%^&*()_+-=[]{}|;:,.<>?',
            'hex': '0123456789abcdef',
            'base64': 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/',
        }
        
    def _md5_hash(self, password: str) -> str:
        return hashlib.md5(password.encode()).hexdigest()
    
    def _sha1_hash(self, password: str) -> str:
        return hashlib.sha1(password.encode()).hexdigest()
    
    def _sha256_hash(self, password: str) -> str:
        return hashlib.sha256(password.encode()).hexdigest()
    
    def _sha512_hash(self, password: str) -> str:
        return hashlib.sha512(password.encode()).hexdigest()
    
    def _ntlm_hash(self, password: str) -> str:
        """NTLM hash implementation"""
        return hashlib.new('md4', password.encode('utf-16le')).hexdigest()
    
    def _bcrypt_hash(self, password: str) -> str:
        """BCrypt hash (requires bcrypt library)"""
        try:
            import bcrypt
            return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
        except ImportError:
            logger.warning("BCrypt library not available")
            return ""
    
    def _sha3_256_hash(self, password: str) -> str:
        return hashlib.sha3_256(password.encode()).hexdigest()
    
    def _blake2b_hash(self, password: str) -> str:
        return hashlib.blake2b(password.encode()).hexdigest()
    
    def _argon2_hash(self, password: str) -> str:
        """Argon2 hash (requires argon2 library)"""
        try:
            import argon2
            ph = argon2.PasswordHasher()
            return ph.hash(password)
        except ImportError:
            logger.warning("Argon2 library not available")
            return ""
    
    def crack_hash(self, target_hash: str, hash_type: str, attack_config: Dict, 
                   progress_callback: Optional[Callable] = None) -> Dict:
        """
        Advanced hash cracking with multiple attack modes
        """
        attack_mode = attack_config.get('mode', 'brute_force')
        
        if attack_mode not in self.attack_modes:
            return {'success': False, 'error': f'Unsupported attack mode: {attack_mode}'}
        
        if hash_type not in self.supported_algorithms:
            return {'success': False, 'error': f'Unsupported hash type: {hash_type}'}
        
        logger.info(f"Starting {attack_mode} attack on {hash_type} hash")
        
        try:
            result = self.attack_modes[attack_mode](
                target_hash, hash_type, attack_config, progress_callback
            )
            return result
        except Exception as e:
            logger.error(f"Cracking error: {e}")
            return {'success': False, 'error': str(e)}
    
    def _dictionary_attack(self, target_hash: str, hash_type: str, 
                          config: Dict, progress_callback: Optional[Callable] = None) -> Dict:
        """Dictionary-based attack using wordlists"""
        wordlist_path = config.get('wordlist', '/usr/share/wordlists/rockyou.txt')
        max_words = config.get('max_words', 100000)
        
        if not os.path.exists(wordlist_path):
            # Create basic wordlist if none exists
            wordlist_path = self._create_basic_wordlist()
        
        hash_func = self.supported_algorithms[hash_type]
        attempts = 0
        
        try:
            with open(wordlist_path, 'r', encoding='utf-8', errors='ignore') as f:
                for line in f:
                    if attempts >= max_words:
                        break
                    
                    password = line.strip()
                    if not password:
                        continue
                    
                    attempts += 1
                    
                    try:
                        if hash_func(password) == target_hash:
                            return {
                                'success': True,
                                'password': password,
                                'attempts': attempts,
                                'attack_mode': 'dictionary'
                            }
                    except:
                        continue
                    
                    if progress_callback and attempts % 1000 == 0:
                        progress = (attempts / max_words) * 100
                        if not progress_callback(progress, attempts, password):
                            break
                            
        except FileNotFoundError:
            logger.error(f"Wordlist not found: {wordlist_path}")
            return {'success': False, 'error': 'Wordlist not found'}
        
        return {'success': False, 'attempts': attempts, 'attack_mode': 'dictionary'}
    
    def _brute_force_attack(self, target_hash: str, hash_type: str, 
                           config: Dict, progress_callback: Optional[Callable] = None) -> Dict:
        """Enhanced brute force with optimized character sets"""
        charset = config.get('charset', 'digits')
        min_length = config.get('min_length', 4)
        max_length = config.get('max_length', 8)
        start_password = config.get('start_password', '')
        end_password = config.get('end_password', '')
        
        # Get character set
        if isinstance(charset, str) and charset in self.charsets:
            chars = self.charsets[charset]
        elif isinstance(charset, str):
            chars = charset
        else:
            chars = ''.join(charset) if isinstance(charset, list) else '0123456789'
        
        hash_func = self.supported_algorithms[hash_type]
        attempts = 0
        
        # Calculate range if specified
        if start_password and end_password:
            return self._brute_force_range(
                target_hash, hash_func, chars, start_password, end_password,
                progress_callback
            )
        
        # Standard brute force
        for length in range(min_length, max_length + 1):
            for password_tuple in itertools.product(chars, repeat=length):
                password = ''.join(password_tuple)
                attempts += 1
                
                try:
                    if hash_func(password) == target_hash:
                        return {
                            'success': True,
                            'password': password,
                            'attempts': attempts,
                            'attack_mode': 'brute_force'
                        }
                except:
                    continue
                
                if progress_callback and attempts % 1000 == 0:
                    total_combinations = sum(len(chars)**l for l in range(min_length, max_length + 1))
                    progress = (attempts / total_combinations) * 100
                    if not progress_callback(progress, attempts, password):
                        break
        
        return {'success': False, 'attempts': attempts, 'attack_mode': 'brute_force'}
    
    def _brute_force_range(self, target_hash: str, hash_func: Callable, 
                          chars: str, start_password: str, end_password: str,
                          progress_callback: Optional[Callable] = None) -> Dict:
        """Brute force within a specific range"""
        attempts = 0
        current = start_password
        
        while current <= end_password:
            attempts += 1
            
            try:
                if hash_func(current) == target_hash:
                    return {
                        'success': True,
                        'password': current,
                        'attempts': attempts,
                        'attack_mode': 'brute_force_range'
                    }
            except:
                pass
            
            if progress_callback and attempts % 1000 == 0:
                progress = self._calculate_range_progress(current, start_password, end_password)
                if not progress_callback(progress, attempts, current):
                    break
            
            current = self._next_password(current, chars)
            if not current:
                break
        
        return {'success': False, 'attempts': attempts, 'attack_mode': 'brute_force_range'}
    
    def _mask_attack(self, target_hash: str, hash_type: str, 
                    config: Dict, progress_callback: Optional[Callable] = None) -> Dict:
        """Mask-based attack (e.g., ?d?d?d?d for 4 digits)"""
        mask = config.get('mask', '?d?d?d?d')
        custom_charsets = config.get('custom_charsets', {})
        
        # Parse mask
        mask_chars = []
        i = 0
        while i < len(mask):
            if mask[i] == '?' and i + 1 < len(mask):
                char_type = mask[i + 1]
                if char_type == 'd':
                    mask_chars.append(self.charsets['digits'])
                elif char_type == 'l':
                    mask_chars.append(self.charsets['lowercase'])
                elif char_type == 'u':
                    mask_chars.append(self.charsets['uppercase'])
                elif char_type == 's':
                    mask_chars.append(self.charsets['symbols'])
                elif char_type in custom_charsets:
                    mask_chars.append(custom_charsets[char_type])
                else:
                    mask_chars.append('?')
                i += 2
            else:
                mask_chars.append(mask[i])
                i += 1
        
        hash_func = self.supported_algorithms[hash_type]
        attempts = 0
        
        # Generate passwords based on mask
        for password_parts in itertools.product(*mask_chars):
            password = ''.join(password_parts)
            attempts += 1
            
            try:
                if hash_func(password) == target_hash:
                    return {
                        'success': True,
                        'password': password,
                        'attempts': attempts,
                        'attack_mode': 'mask'
                    }
            except:
                continue
            
            if progress_callback and attempts % 1000 == 0:
                total_combinations = 1
                for chars in mask_chars:
                    if isinstance(chars, str) and len(chars) > 1:
                        total_combinations *= len(chars)
                progress = (attempts / total_combinations) * 100
                if not progress_callback(progress, attempts, password):
                    break
        
        return {'success': False, 'attempts': attempts, 'attack_mode': 'mask'}
    
    def _hybrid_attack(self, target_hash: str, hash_type: str, 
                      config: Dict, progress_callback: Optional[Callable] = None) -> Dict:
        """Hybrid attack combining dictionary + brute force"""
        wordlist_path = config.get('wordlist', '/usr/share/wordlists/rockyou.txt')
        append_chars = config.get('append_chars', '0123456789')
        prepend_chars = config.get('prepend_chars', '')
        max_append = config.get('max_append', 3)
        max_prepend = config.get('max_prepend', 0)
        
        if not os.path.exists(wordlist_path):
            wordlist_path = self._create_basic_wordlist()
        
        hash_func = self.supported_algorithms[hash_type]
        attempts = 0
        
        try:
            with open(wordlist_path, 'r', encoding='utf-8', errors='ignore') as f:
                for line in f:
                    base_word = line.strip()
                    if not base_word:
                        continue
                    
                    # Try base word
                    attempts += 1
                    try:
                        if hash_func(base_word) == target_hash:
                            return {
                                'success': True,
                                'password': base_word,
                                'attempts': attempts,
                                'attack_mode': 'hybrid'
                            }
                    except:
                        pass
                    
                    # Try with appended characters
                    for append_len in range(1, max_append + 1):
                        for append_combo in itertools.product(append_chars, repeat=append_len):
                            password = base_word + ''.join(append_combo)
                            attempts += 1
                            
                            try:
                                if hash_func(password) == target_hash:
                                    return {
                                        'success': True,
                                        'password': password,
                                        'attempts': attempts,
                                        'attack_mode': 'hybrid'
                                    }
                            except:
                                continue
                    
                    # Try with prepended characters
                    for prepend_len in range(1, max_prepend + 1):
                        for prepend_combo in itertools.product(prepend_chars, repeat=prepend_len):
                            password = ''.join(prepend_combo) + base_word
                            attempts += 1
                            
                            try:
                                if hash_func(password) == target_hash:
                                    return {
                                        'success': True,
                                        'password': password,
                                        'attempts': attempts,
                                        'attack_mode': 'hybrid'
                                    }
                            except:
                                continue
                    
                    if progress_callback and attempts % 1000 == 0:
                        if not progress_callback(50, attempts, password):
                            break
                            
        except FileNotFoundError:
            logger.error(f"Wordlist not found: {wordlist_path}")
            return {'success': False, 'error': 'Wordlist not found'}
        
        return {'success': False, 'attempts': attempts, 'attack_mode': 'hybrid'}
    
    def _rule_based_attack(self, target_hash: str, hash_type: str, 
                          config: Dict, progress_callback: Optional[Callable] = None) -> Dict:
        """Rule-based attack with common password transformations"""
        wordlist_path = config.get('wordlist', '/usr/share/wordlists/rockyou.txt')
        
        # Common password rules
        rules = [
            lambda w: w,  # No change
            lambda w: w.capitalize(),  # Capitalize first letter
            lambda w: w.upper(),  # All uppercase
            lambda w: w.lower(),  # All lowercase
            lambda w: w + '1',  # Append 1
            lambda w: w + '123',  # Append 123
            lambda w: w + '!',  # Append !
            lambda w: w[::-1],  # Reverse
            lambda w: w.replace('a', '@'),  # a -> @
            lambda w: w.replace('e', '3'),  # e -> 3
            lambda w: w.replace('i', '1'),  # i -> 1
            lambda w: w.replace('o', '0'),  # o -> 0
            lambda w: w.replace('s', '$'),  # s -> $
        ]
        
        if not os.path.exists(wordlist_path):
            wordlist_path = self._create_basic_wordlist()
        
        hash_func = self.supported_algorithms[hash_type]
        attempts = 0
        
        try:
            with open(wordlist_path, 'r', encoding='utf-8', errors='ignore') as f:
                for line in f:
                    base_word = line.strip()
                    if not base_word:
                        continue
                    
                    # Apply each rule
                    for rule in rules:
                        try:
                            password = rule(base_word)
                            attempts += 1
                            
                            if hash_func(password) == target_hash:
                                return {
                                    'success': True,
                                    'password': password,
                                    'attempts': attempts,
                                    'attack_mode': 'rule_based'
                                }
                        except:
                            continue
                    
                    if progress_callback and attempts % 1000 == 0:
                        if not progress_callback(50, attempts, password):
                            break
                            
        except FileNotFoundError:
            logger.error(f"Wordlist not found: {wordlist_path}")
            return {'success': False, 'error': 'Wordlist not found'}
        
        return {'success': False, 'attempts': attempts, 'attack_mode': 'rule_based'}
    
    def _markov_attack(self, target_hash: str, hash_type: str, 
                      config: Dict, progress_callback: Optional[Callable] = None) -> Dict:
        """Simple Markov chain-based attack"""
        # This is a simplified version - full Markov would require training data
        max_length = config.get('max_length', 8)
        samples = config.get('samples', 10000)
        
        # Simple character frequency for English
        char_freq = {
            'a': 0.08167, 'b': 0.01492, 'c': 0.02782, 'd': 0.04253,
            'e': 0.12702, 'f': 0.02228, 'g': 0.02015, 'h': 0.06094,
            'i': 0.06966, 'j': 0.00153, 'k': 0.00772, 'l': 0.04025,
            'm': 0.02406, 'n': 0.06749, 'o': 0.07507, 'p': 0.01929,
            'q': 0.00095, 'r': 0.05987, 's': 0.06327, 't': 0.09056,
            'u': 0.02758, 'v': 0.00978, 'w': 0.02360, 'x': 0.00150,
            'y': 0.01974, 'z': 0.00074
        }
        
        hash_func = self.supported_algorithms[hash_type]
        attempts = 0
        
        import random
        random.seed(42)  # Reproducible results
        
        for _ in range(samples):
            # Generate password based on character frequency
            password = ''
            for _ in range(random.randint(4, max_length)):
                char = random.choices(
                    list(char_freq.keys()),
                    weights=list(char_freq.values())
                )[0]
                password += char
            
            attempts += 1
            
            try:
                if hash_func(password) == target_hash:
                    return {
                        'success': True,
                        'password': password,
                        'attempts': attempts,
                        'attack_mode': 'markov'
                    }
            except:
                continue
            
            if progress_callback and attempts % 1000 == 0:
                progress = (attempts / samples) * 100
                if not progress_callback(progress, attempts, password):
                    break
        
        return {'success': False, 'attempts': attempts, 'attack_mode': 'markov'}
    
    def _prince_attack(self, target_hash: str, hash_type: str, 
                      config: Dict, progress_callback: Optional[Callable] = None) -> Dict:
        """PRINCE algorithm (simplified version)"""
        wordlist_path = config.get('wordlist', '/usr/share/wordlists/rockyou.txt')
        max_combinations = config.get('max_combinations', 10000)
        
        if not os.path.exists(wordlist_path):
            wordlist_path = self._create_basic_wordlist()
        
        # Load words
        words = []
        try:
            with open(wordlist_path, 'r', encoding='utf-8', errors='ignore') as f:
                for line in f:
                    word = line.strip()
                    if word and len(word) <= 8:  # Reasonable length
                        words.append(word)
                    if len(words) >= 1000:  # Limit for performance
                        break
        except FileNotFoundError:
            words = ['password', 'admin', 'root', 'user', 'test']
        
        hash_func = self.supported_algorithms[hash_type]
        attempts = 0
        
        # Combine words (simplified PRINCE)
        for i, word1 in enumerate(words):
            for j, word2 in enumerate(words):
                if i != j and attempts < max_combinations:
                    password = word1 + word2
                    attempts += 1
                    
                    try:
                        if hash_func(password) == target_hash:
                            return {
                                'success': True,
                                'password': password,
                                'attempts': attempts,
                                'attack_mode': 'prince'
                            }
                    except:
                        continue
                    
                    if progress_callback and attempts % 1000 == 0:
                        progress = (attempts / max_combinations) * 100
                        if not progress_callback(progress, attempts, password):
                            break
        
        return {'success': False, 'attempts': attempts, 'attack_mode': 'prince'}
    
    def _create_basic_wordlist(self) -> str:
        """Create a basic wordlist if none exists"""
        wordlist_path = '/tmp/basic_wordlist.txt'
        
        basic_passwords = [
            'password', 'admin', 'root', 'user', 'test', 'guest', 'qwerty',
            'password123', 'admin123', 'root123', 'user123', 'test123',
            '123456', '1234567890', 'abcdef', 'letmein', 'welcome',
            'password1', 'admin1', 'root1', 'user1', 'test1',
            'pass', 'administrator', 'login', 'secret', 'default'
        ]
        
        with open(wordlist_path, 'w') as f:
            for password in basic_passwords:
                f.write(password + '\n')
        
        return wordlist_path
    
    def _next_password(self, current: str, charset: str) -> Optional[str]:
        """Generate next password in sequence"""
        if not current:
            return charset[0] if charset else None
        
        # Convert to list for manipulation
        chars = list(current)
        charset_len = len(charset)
        
        # Increment from right to left
        for i in range(len(chars) - 1, -1, -1):
            char_index = charset.index(chars[i])
            if char_index < charset_len - 1:
                chars[i] = charset[char_index + 1]
                return ''.join(chars)
            else:
                chars[i] = charset[0]
        
        # All positions wrapped, need to increase length
        return charset[0] * (len(current) + 1)
    
    def _calculate_range_progress(self, current: str, start: str, end: str) -> float:
        """Calculate progress percentage for range-based cracking"""
        if start == end:
            return 100.0
        
        try:
            # Simple numeric comparison for now
            curr_num = int(current) if current.isdigit() else ord(current[0])
            start_num = int(start) if start.isdigit() else ord(start[0])
            end_num = int(end) if end.isdigit() else ord(end[0])
            
            return ((curr_num - start_num) / (end_num - start_num)) * 100
        except:
            return 50.0  # Fallback

class DistributedHashManager:
    """Advanced hash and range distribution for multiple clients"""
    
    def __init__(self):
        self.distribution_strategies = {
            'equal_split': self._equal_split_strategy,
            'capability_based': self._capability_based_strategy,
            'dynamic_load': self._dynamic_load_strategy,
            'hash_based': self._hash_based_strategy
        }
    
    def distribute_work(self, hashes: List[str], clients: List[Dict], 
                       strategy: str = 'equal_split') -> Dict:
        """Distribute hashes and ranges across multiple clients"""
        
        if strategy not in self.distribution_strategies:
            strategy = 'equal_split'
        
        return self.distribution_strategies[strategy](hashes, clients)
    
    def _equal_split_strategy(self, hashes: List[str], clients: List[Dict]) -> Dict:
        """Split hashes equally among clients"""
        if not clients:
            return {}
        
        client_count = len(clients)
        hash_count = len(hashes)
        
        distributions = {}
        
        for i, client in enumerate(clients):
            client_id = client['client_id']
            
            # Calculate hash range for this client
            start_idx = (i * hash_count) // client_count
            end_idx = ((i + 1) * hash_count) // client_count
            
            client_hashes = hashes[start_idx:end_idx]
            
            distributions[client_id] = {
                'hashes': client_hashes,
                'hash_count': len(client_hashes),
                'priority': 'normal',
                'estimated_time': len(client_hashes) * 60  # 1 minute per hash estimate
            }
        
        return distributions
    
    def _capability_based_strategy(self, hashes: List[str], clients: List[Dict]) -> Dict:
        """Distribute based on client capabilities (CPU, RAM, etc.)"""
        if not clients:
            return {}
        
        # Calculate client weights based on capabilities
        total_weight = 0
        client_weights = {}
        
        for client in clients:
            # Weight based on CPU cores, RAM, and current load
            cpu_weight = client.get('cpu_cores', 1)
            ram_weight = client.get('ram_total', 1000000) / 1000000  # MB to GB
            load_penalty = 1 - (client.get('cpu_usage', 0) / 100)
            
            weight = cpu_weight * ram_weight * load_penalty
            client_weights[client['client_id']] = max(weight, 0.1)  # Minimum weight
            total_weight += weight
        
        # Distribute hashes based on weights
        distributions = {}
        hash_count = len(hashes)
        allocated_hashes = 0
        
        for i, client in enumerate(clients):
            client_id = client['client_id']
            
            if i == len(clients) - 1:  # Last client gets remaining hashes
                client_hash_count = hash_count - allocated_hashes
            else:
                weight_ratio = client_weights[client_id] / total_weight
                client_hash_count = int(hash_count * weight_ratio)
            
            start_idx = allocated_hashes
            end_idx = allocated_hashes + client_hash_count
            
            client_hashes = hashes[start_idx:end_idx]
            allocated_hashes += client_hash_count
            
            distributions[client_id] = {
                'hashes': client_hashes,
                'hash_count': len(client_hashes),
                'priority': 'high' if client_weights[client_id] > 1.0 else 'normal',
                'estimated_time': len(client_hashes) * (60 / client_weights[client_id])
            }
        
        return distributions
    
    def _dynamic_load_strategy(self, hashes: List[str], clients: List[Dict]) -> Dict:
        """Dynamic distribution based on current client load"""
        if not clients:
            return {}
        
        # Sort clients by current load (ascending)
        sorted_clients = sorted(clients, 
                              key=lambda c: c.get('cpu_usage', 0) + c.get('ram_usage', 0))
        
        distributions = {}
        remaining_hashes = hashes.copy()
        
        # Give more work to less loaded clients
        for i, client in enumerate(sorted_clients):
            client_id = client['client_id']
            
            # Calculate load factor (lower load = more hashes)
            load_factor = 1 - ((client.get('cpu_usage', 0) + client.get('ram_usage', 0)) / 200)
            load_factor = max(load_factor, 0.1)  # Minimum 10% allocation
            
            if i == len(sorted_clients) - 1:  # Last client gets all remaining
                client_hashes = remaining_hashes
            else:
                hash_count = int(len(remaining_hashes) * load_factor)
                client_hashes = remaining_hashes[:hash_count]
                remaining_hashes = remaining_hashes[hash_count:]
            
            distributions[client_id] = {
                'hashes': client_hashes,
                'hash_count': len(client_hashes),
                'priority': 'high' if load_factor > 0.7 else 'normal',
                'estimated_time': len(client_hashes) * (60 / load_factor)
            }
        
        return distributions
    
    def _hash_based_strategy(self, hashes: List[str], clients: List[Dict]) -> Dict:
        """Distribute hashes based on hash characteristics"""
        if not clients:
            return {}
        
        # Group hashes by type/complexity
        hash_groups = {
            'simple': [],  # Short hashes, likely simple passwords
            'complex': [],  # Longer hashes, likely complex passwords
            'unknown': []
        }
        
        for hash_val in hashes:
            # Simple heuristic based on hash length and patterns
            if len(hash_val) <= 32:  # MD5-like
                hash_groups['simple'].append(hash_val)
            elif len(hash_val) <= 64:  # SHA256-like
                hash_groups['complex'].append(hash_val)
            else:
                hash_groups['unknown'].append(hash_val)
        
        # Assign based on client capabilities
        distributions = {}
        client_count = len(clients)
        
        # Assign simple hashes to all clients
        simple_per_client = len(hash_groups['simple']) // client_count
        complex_per_client = len(hash_groups['complex']) // client_count
        
        for i, client in enumerate(clients):
            client_id = client['client_id']
            client_hashes = []
            
            # Distribute simple hashes
            start_simple = i * simple_per_client
            end_simple = (i + 1) * simple_per_client if i < client_count - 1 else len(hash_groups['simple'])
            client_hashes.extend(hash_groups['simple'][start_simple:end_simple])
            
            # Distribute complex hashes to more capable clients
            cpu_cores = client.get('cpu_cores', 1)
            if cpu_cores >= 4:  # High-end clients get complex hashes
                start_complex = i * complex_per_client
                end_complex = (i + 1) * complex_per_client if i < client_count - 1 else len(hash_groups['complex'])
                client_hashes.extend(hash_groups['complex'][start_complex:end_complex])
            
            distributions[client_id] = {
                'hashes': client_hashes,
                'hash_count': len(client_hashes),
                'priority': 'high' if cpu_cores >= 4 else 'normal',
                'estimated_time': len(client_hashes) * (30 if cpu_cores >= 4 else 90)
            }
        
        return distributions