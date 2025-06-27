import re
import os
import subprocess
import time
import logging
from typing import Dict, List, Optional, Callable

logger = logging.getLogger(__name__)

def identify_hash_type(hash_value: str) -> str:
    """
    Identify hash type based on hash characteristics
    """
    hash_value = hash_value.strip()
    
    # Remove common prefixes
    if hash_value.startswith('$'):
        if hash_value.startswith('$1$'):
            return 'md5crypt'
        elif hash_value.startswith('$2a$') or hash_value.startswith('$2b$') or hash_value.startswith('$2y$'):
            return 'bcrypt'
        elif hash_value.startswith('$5$'):
            return 'sha256crypt'
        elif hash_value.startswith('$6$'):
            return 'sha512crypt'
        elif hash_value.startswith('$7$'):
            return 'scrypt'
    
    # Check by length and character set
    if re.match(r'^[a-fA-F0-9]{32}$', hash_value):
        return 'md5'
    elif re.match(r'^[a-fA-F0-9]{40}$', hash_value):
        return 'sha1'
    elif re.match(r'^[a-fA-F0-9]{64}$', hash_value):
        return 'sha256'
    elif re.match(r'^[a-fA-F0-9]{128}$', hash_value):
        return 'sha512'
    elif re.match(r'^[a-fA-F0-9]{32}:[a-fA-F0-9]{32}$', hash_value):
        return 'ntlm'  # Often stored as LM:NTLM
    elif re.match(r'^[a-fA-F0-9]{56}$', hash_value):
        return 'sha224'
    elif len(hash_value) == 60 and hash_value.startswith('$2'):
        return 'bcrypt'
    
    return 'unknown'

def detect_hash_types_from_file(file_path: str) -> Dict[str, int]:
    """
    Analyze a file of hashes and return detected hash types with counts
    """
    hash_types = {}
    
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                
                # Handle different formats: hash, username:hash, hash:salt
                parts = line.split(':')
                if len(parts) >= 2:
                    # Try to identify which part is the hash
                    for part in parts:
                        hash_type = identify_hash_type(part)
                        if hash_type != 'unknown':
                            hash_types[hash_type] = hash_types.get(hash_type, 0) + 1
                            break
                else:
                    hash_type = identify_hash_type(line)
                    if hash_type != 'unknown':
                        hash_types[hash_type] = hash_types.get(hash_type, 0) + 1
                
                # Limit analysis to first 1000 lines for performance
                if line_num >= 1000:
                    break
                    
    except Exception as e:
        logger.error(f"Error analyzing hash file {file_path}: {e}")
    
    return hash_types

def run_hashcat(hash_file: str, hash_type: str, attack_mode: str = 'dictionary',
               wordlist_path: str = None, rules_path: str = None, mask: str = None,
               progress_callback: Callable = None, password_found_callback: Callable = None) -> Dict:
    """
    Run hashcat with the specified parameters
    """
    try:
        from config import Config
        
        hashcat_path = Config.HASHCAT_PATH
        if not os.path.exists(hashcat_path):
            return {'success': False, 'error': 'Hashcat not found'}
        
        # Get hashcat mode for hash type
        hash_modes = Config.HASH_TYPES
        if hash_type not in hash_modes:
            return {'success': False, 'error': f'Unsupported hash type: {hash_type}'}
        
        mode = hash_modes[hash_type]['hashcat_mode']
        
        # Prepare command
        cmd = [hashcat_path, '-m', str(mode), hash_file]
        
        # Add attack mode specific parameters
        if attack_mode == 'dictionary':
            if not wordlist_path or not os.path.exists(wordlist_path):
                # Use default wordlist
                wordlist_path = Config.DEFAULT_WORDLISTS[0]
                if not os.path.exists(wordlist_path):
                    return {'success': False, 'error': 'No wordlist found'}
            
            cmd.append(wordlist_path)
            
            if rules_path and os.path.exists(rules_path):
                cmd.extend(['-r', rules_path])
                
        elif attack_mode == 'bruteforce':
            if mask:
                cmd.extend(['-a', '3', mask])
            else:
                cmd.extend(['-a', '3', '?a?a?a?a?a?a?a?a'])  # Default 8-char mask
                
        elif attack_mode == 'hybrid':
            if wordlist_path and os.path.exists(wordlist_path):
                cmd.extend(['-a', '6', wordlist_path, '?d?d?d?d'])
            else:
                return {'success': False, 'error': 'Wordlist required for hybrid attack'}
        
        # Add additional options
        cmd.extend([
            '--status',
            '--status-timer=10',
            '--quiet',
            '--potfile-disable',
            '--outfile-format=2',
            '--outfile=/tmp/hashcat_output.txt'
        ])
        
        logger.info(f"Running hashcat command: {' '.join(cmd)}")
        
        # Run hashcat
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
            bufsize=1
        )
        
        cracked_count = 0
        start_time = time.time()
        
        while True:
            output = process.stdout.readline()
            if output == '' and process.poll() is not None:
                break
                
            if output:
                line = output.strip()
                
                # Parse progress information
                if 'Progress' in line and progress_callback:
                    try:
                        # Extract progress percentage
                        progress_match = re.search(r'(\d+\.\d+)%', line)
                        if progress_match:
                            progress = float(progress_match.group(1))
                            
                            # Estimate time remaining
                            elapsed = time.time() - start_time
                            if progress > 0:
                                estimated_total = elapsed * (100 / progress)
                                estimated_remaining = estimated_total - elapsed
                            else:
                                estimated_remaining = 0
                            
                            progress_callback(progress, int(estimated_remaining))
                    except Exception as e:
                        logger.error(f"Error parsing progress: {e}")
        
        # Wait for process to complete
        process.wait()
        
        # Check for cracked passwords
        if os.path.exists('/tmp/hashcat_output.txt'):
            with open('/tmp/hashcat_output.txt', 'r') as f:
                for line in f:
                    if ':' in line:
                        hash_value, password = line.strip().split(':', 1)
                        if password_found_callback:
                            password_found_callback(hash_value, password)
                        cracked_count += 1
            
            # Clean up output file
            os.remove('/tmp/hashcat_output.txt')
        
        if process.returncode == 0:
            return {'success': True, 'cracked_count': cracked_count}
        else:
            stderr = process.stderr.read()
            return {'success': False, 'error': f'Hashcat failed: {stderr}'}
            
    except Exception as e:
        logger.error(f"Error running hashcat: {e}")
        return {'success': False, 'error': str(e)}

def run_john(hash_file: str, hash_type: str, attack_mode: str = 'dictionary',
            wordlist_path: str = None, rules_path: str = None,
            progress_callback: Callable = None, password_found_callback: Callable = None) -> Dict:
    """
    Run John the Ripper with the specified parameters
    """
    try:
        from config import Config
        
        john_path = Config.JOHN_PATH
        if not os.path.exists(john_path):
            return {'success': False, 'error': 'John the Ripper not found'}
        
        # Get john format for hash type
        hash_formats = Config.HASH_TYPES
        if hash_type not in hash_formats:
            return {'success': False, 'error': f'Unsupported hash type: {hash_type}'}
        
        format_name = hash_formats[hash_type]['john_format']
        
        # Prepare command
        cmd = [john_path, '--format=' + format_name, hash_file]
        
        # Add attack mode specific parameters
        if attack_mode == 'dictionary':
            if wordlist_path and os.path.exists(wordlist_path):
                cmd.extend(['--wordlist=' + wordlist_path])
            
            if rules_path and os.path.exists(rules_path):
                cmd.extend(['--rules=' + rules_path])
        elif attack_mode == 'bruteforce':
            cmd.extend(['--incremental'])
        
        logger.info(f"Running john command: {' '.join(cmd)}")
        
        # Run john
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
            bufsize=1
        )
        
        cracked_count = 0
        
        while True:
            output = process.stdout.readline()
            if output == '' and process.poll() is not None:
                break
                
            if output:
                line = output.strip()
                
                # Check for cracked passwords
                if '(' in line and ')' in line:
                    # John output format: password (hash)
                    try:
                        password = line.split('(')[0].strip()
                        hash_value = line.split('(')[1].split(')')[0].strip()
                        
                        if password_found_callback:
                            password_found_callback(hash_value, password)
                        cracked_count += 1
                    except Exception as e:
                        logger.error(f"Error parsing john output: {e}")
        
        # Wait for process to complete
        process.wait()
        
        if process.returncode == 0:
            return {'success': True, 'cracked_count': cracked_count}
        else:
            stderr = process.stderr.read()
            return {'success': False, 'error': f'John failed: {stderr}'}
            
    except Exception as e:
        logger.error(f"Error running john: {e}")
        return {'success': False, 'error': str(e)}

def run_cracking_job(hash_file: str, hash_type: str, attack_mode: str = 'dictionary',
                    wordlist_path: str = None, rules_path: str = None, mask: str = None,
                    progress_callback: Callable = None, password_found_callback: Callable = None,
                    tool: str = 'hashcat') -> Dict:
    """
    Run a cracking job using the specified tool and parameters
    """
    if tool == 'hashcat':
        return run_hashcat(
            hash_file, hash_type, attack_mode, wordlist_path, rules_path, mask,
            progress_callback, password_found_callback
        )
    elif tool == 'john':
        return run_john(
            hash_file, hash_type, attack_mode, wordlist_path, rules_path,
            progress_callback, password_found_callback
        )
    else:
        return {'success': False, 'error': f'Unknown cracking tool: {tool}'}

def prepare_cracking_job(job_id: int, hashes: List[str], hash_type: str) -> str:
    """
    Prepare a hash file for cracking and return the file path
    """
    hash_file = f"/tmp/job_{job_id}_hashes.txt"
    
    try:
        with open(hash_file, 'w') as f:
            for hash_value in hashes:
                f.write(f"{hash_value}\n")
        
        return hash_file
    except Exception as e:
        logger.error(f"Error preparing hash file: {e}")
        return None
