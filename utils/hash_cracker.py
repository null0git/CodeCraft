"""
Enhanced hash cracking utilities for distributed password cracking
"""
import hashlib
import itertools
import string
import math
from typing import List, Dict, Tuple, Generator
import logging

logger = logging.getLogger(__name__)

class RangeDistributor:
    """Distributes password ranges among multiple clients"""
    
    @staticmethod
    def calculate_total_combinations(charset: str, length: int) -> int:
        """Calculate total number of combinations for given charset and length"""
        return len(charset) ** length
    
    @staticmethod
    def calculate_range_combinations(start_range: str, end_range: str, charset: str) -> int:
        """Calculate combinations in a custom range"""
        if len(start_range) != len(end_range):
            raise ValueError("Start and end range must have same length")
        
        # Convert range strings to numbers in base len(charset)
        start_num = RangeDistributor._string_to_number(start_range, charset)
        end_num = RangeDistributor._string_to_number(end_range, charset)
        
        return end_num - start_num + 1
    
    @staticmethod
    def _string_to_number(s: str, charset: str) -> int:
        """Convert string to number using charset as base"""
        result = 0
        base = len(charset)
        for char in s:
            if char not in charset:
                raise ValueError(f"Character '{char}' not in charset")
            result = result * base + charset.index(char)
        return result
    
    @staticmethod
    def _number_to_string(num: int, length: int, charset: str) -> str:
        """Convert number to string using charset as base"""
        if num < 0:
            raise ValueError("Number must be non-negative")
        
        result = []
        base = len(charset)
        
        for _ in range(length):
            result.append(charset[num % base])
            num //= base
        
        return ''.join(reversed(result))
    
    @staticmethod
    def distribute_range(total_combinations: int, num_clients: int) -> List[Tuple[int, int]]:
        """Distribute total combinations among clients"""
        if num_clients <= 0:
            raise ValueError("Number of clients must be positive")
        
        combinations_per_client = total_combinations // num_clients
        remainder = total_combinations % num_clients
        
        ranges = []
        start = 0
        
        for i in range(num_clients):
            # Add one extra combination to first 'remainder' clients
            client_combinations = combinations_per_client + (1 if i < remainder else 0)
            end = start + client_combinations - 1
            ranges.append((start, end))
            start = end + 1
        
        return ranges
    
    @staticmethod
    def distribute_charset_range(charset: str, length: int, num_clients: int) -> List[Dict]:
        """Distribute charset combinations among clients"""
        total_combinations = RangeDistributor.calculate_total_combinations(charset, length)
        ranges = RangeDistributor.distribute_range(total_combinations, num_clients)
        
        client_ranges = []
        for i, (start_num, end_num) in enumerate(ranges):
            start_password = RangeDistributor._number_to_string(start_num, length, charset)
            end_password = RangeDistributor._number_to_string(end_num, length, charset)
            
            client_ranges.append({
                'client_id': i + 1,
                'start_password': start_password,
                'end_password': end_password,
                'start_number': start_num,
                'end_number': end_num,
                'total_combinations': end_num - start_num + 1
            })
        
        return client_ranges
    
    @staticmethod
    def distribute_custom_range(start_range: str, end_range: str, charset: str, num_clients: int) -> List[Dict]:
        """Distribute custom range among clients"""
        start_num = RangeDistributor._string_to_number(start_range, charset)
        end_num = RangeDistributor._string_to_number(end_range, charset)
        total_combinations = end_num - start_num + 1
        
        ranges = RangeDistributor.distribute_range(total_combinations, num_clients)
        
        client_ranges = []
        for i, (relative_start, relative_end) in enumerate(ranges):
            absolute_start = start_num + relative_start
            absolute_end = start_num + relative_end
            
            start_password = RangeDistributor._number_to_string(
                absolute_start, len(start_range), charset
            )
            end_password = RangeDistributor._number_to_string(
                absolute_end, len(end_range), charset
            )
            
            client_ranges.append({
                'client_id': i + 1,
                'start_password': start_password,
                'end_password': end_password,
                'start_number': absolute_start,
                'end_number': absolute_end,
                'total_combinations': relative_end - relative_start + 1
            })
        
        return client_ranges

class PasswordGenerator:
    """Generate passwords for brute force attacks"""
    
    # Common character sets
    CHARSET_DIGITS = string.digits
    CHARSET_LOWERCASE = string.ascii_lowercase
    CHARSET_UPPERCASE = string.ascii_uppercase
    CHARSET_LETTERS = string.ascii_letters
    CHARSET_ALPHANUMERIC = string.ascii_letters + string.digits
    CHARSET_SYMBOLS = "!@#$%^&*()_+-=[]{}|;:,.<>?"
    CHARSET_ALL = string.ascii_letters + string.digits + CHARSET_SYMBOLS
    
    @staticmethod
    def get_charset_by_name(name: str) -> str:
        """Get charset by name"""
        charsets = {
            'digits': PasswordGenerator.CHARSET_DIGITS,
            'lowercase': PasswordGenerator.CHARSET_LOWERCASE,
            'uppercase': PasswordGenerator.CHARSET_UPPERCASE,
            'letters': PasswordGenerator.CHARSET_LETTERS,
            'alphanumeric': PasswordGenerator.CHARSET_ALPHANUMERIC,
            'symbols': PasswordGenerator.CHARSET_SYMBOLS,
            'all': PasswordGenerator.CHARSET_ALL
        }
        return charsets.get(name, name)  # Return name if not found (custom charset)
    
    @staticmethod
    def generate_range(start_password: str, end_password: str, charset: str) -> Generator[str, None, None]:
        """Generate passwords in a specific range"""
        if len(start_password) != len(end_password):
            raise ValueError("Start and end passwords must have same length")
        
        length = len(start_password)
        start_num = RangeDistributor._string_to_number(start_password, charset)
        end_num = RangeDistributor._string_to_number(end_password, charset)
        
        for num in range(start_num, end_num + 1):
            yield RangeDistributor._number_to_string(num, length, charset)

class HashCracker:
    """Hash cracking functionality"""
    
    HASH_ALGORITHMS = {
        'md5': hashlib.md5,
        'sha1': hashlib.sha1,
        'sha256': hashlib.sha256,
        'sha512': hashlib.sha512,
    }
    
    @staticmethod
    def detect_hash_type(hash_value: str) -> str:
        """Detect hash type based on length and format"""
        hash_value = hash_value.strip().lower()
        
        # Remove common prefixes
        if hash_value.startswith('$'):
            if hash_value.startswith('$2a$') or hash_value.startswith('$2b$'):
                return 'bcrypt'
            elif hash_value.startswith('$1$'):
                return 'md5crypt'
            elif hash_value.startswith('$6$'):
                return 'sha512crypt'
        
        # Detect by length
        length = len(hash_value)
        if length == 32:
            return 'md5'
        elif length == 40:
            return 'sha1'
        elif length == 64:
            return 'sha256'
        elif length == 128:
            return 'sha512'
        elif length == 32 and ':' in hash_value:
            return 'ntlm'
        
        return 'unknown'
    
    @staticmethod
    def crack_hash(target_hash: str, hash_type: str, start_password: str, 
                  end_password: str, charset: str, progress_callback=None) -> Dict:
        """
        Crack a hash within a specific password range
        
        Args:
            target_hash: The hash to crack
            hash_type: Type of hash (md5, sha1, etc.)
            start_password: Starting password in range
            end_password: Ending password in range
            charset: Character set used
            progress_callback: Function to call for progress updates
        
        Returns:
            Dictionary with result information
        """
        if hash_type not in HashCracker.HASH_ALGORITHMS:
            return {
                'success': False,
                'error': f'Unsupported hash type: {hash_type}',
                'attempts': 0
            }
        
        hasher = HashCracker.HASH_ALGORITHMS[hash_type]
        target_hash = target_hash.strip().lower()
        
        attempts = 0
        total_combinations = RangeDistributor.calculate_range_combinations(
            start_password, end_password, charset
        )
        
        try:
            for password in PasswordGenerator.generate_range(start_password, end_password, charset):
                attempts += 1
                
                # Calculate hash
                calculated_hash = hasher(password.encode()).hexdigest()
                
                # Check if matches
                if calculated_hash == target_hash:
                    return {
                        'success': True,
                        'password': password,
                        'attempts': attempts,
                        'total_combinations': total_combinations
                    }
                
                # Progress callback
                if progress_callback and attempts % 1000 == 0:
                    progress = (attempts / total_combinations) * 100
                    progress_callback(progress, attempts, password)
                
        except Exception as e:
            logger.error(f"Error during hash cracking: {e}")
            return {
                'success': False,
                'error': str(e),
                'attempts': attempts
            }
        
        return {
            'success': False,
            'attempts': attempts,
            'total_combinations': total_combinations,
            'message': 'Password not found in range'
        }