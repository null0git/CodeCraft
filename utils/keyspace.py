"""
CrackPi Keyspace Engine
=======================
Implements the coordinator-side keyspace math for distributed brute-force:

  Step 1  Build the keyspace  (charset + length rules)
  Step 2  Represent passwords as numeric indexes
  Step 3  Calculate total combination count
  Step 4  Divide work between workers with no overlap
  Step 5  Handle uneven division (remainder distributed among first N workers)

All functions are pure-Python, dependency-free, and safe for large numbers
(Python integers have arbitrary precision).
"""

from __future__ import annotations
from typing import List, Tuple

# ── Built-in charsets ─────────────────────────────────────────────────────────
CHARSETS: dict[str, str] = {
    'digits':       '0123456789',
    'lowercase':    'abcdefghijklmnopqrstuvwxyz',
    'uppercase':    'ABCDEFGHIJKLMNOPQRSTUVWXYZ',
    'mixedcase':    'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ',
    'alphanumeric': '0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ',
    'lowercase+digits': '0123456789abcdefghijklmnopqrstuvwxyz',
    'uppercase+digits': '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ',
    'full':         (
        '0123456789'
        'abcdefghijklmnopqrstuvwxyz'
        'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
        r"""!"#$%&'()*+,-./:;<=>?@[\]^_`{|}~"""
    ),
}

CHARSET_LABELS: dict[str, str] = {
    'digits':           'Digits only  [0-9]  — 10 chars',
    'lowercase':        'Lowercase letters  [a-z]  — 26 chars',
    'uppercase':        'Uppercase letters  [A-Z]  — 26 chars',
    'mixedcase':        'Mixed case  [a-zA-Z]  — 52 chars',
    'lowercase+digits': 'Lowercase + digits  [a-z0-9]  — 36 chars',
    'uppercase+digits': 'Uppercase + digits  [A-Z0-9]  — 36 chars',
    'alphanumeric':     'Alphanumeric  [a-zA-Z0-9]  — 62 chars',
    'full':             'Full printable ASCII  — 94 chars',
    'custom':           'Custom charset (specify below)',
}


def resolve_charset(charset_name: str, custom: str = '') -> str:
    """Return the actual charset string for a given preset name or custom value."""
    if charset_name == 'custom':
        if not custom:
            raise ValueError("Custom charset is empty")
        # Deduplicate while preserving order
        seen = set()
        deduped = ''
        for ch in custom:
            if ch not in seen:
                seen.add(ch)
                deduped += ch
        return deduped
    return CHARSETS.get(charset_name, CHARSETS['digits'])


# ── Step 3: Total combination count ──────────────────────────────────────────

def keyspace_at_length(charset_size: int, length: int) -> int:
    """Number of passwords of exactly `length` characters."""
    return charset_size ** length


def total_keyspace(charset: str, min_len: int, max_len: int) -> int:
    """
    Total number of passwords from min_len to max_len characters.

    Formula:  Σ  c^i   for i in [min_len, max_len]
    """
    c = len(charset)
    return sum(c ** i for i in range(min_len, max_len + 1))


def keyspace_summary(charset: str, min_len: int, max_len: int) -> dict:
    """Return a human-readable breakdown of the keyspace."""
    c = len(charset)
    rows = []
    total = 0
    for length in range(min_len, max_len + 1):
        count = c ** length
        total += count
        rows.append({'length': length, 'count': count})
    return {
        'charset_size': c,
        'min_len':  min_len,
        'max_len':  max_len,
        'total':    total,
        'by_length': rows,
    }


# ── Step 2: Index ↔ Password conversion ──────────────────────────────────────

def index_to_password(index: int, charset: str, min_len: int, max_len: int) -> str | None:
    """
    Convert a 0-based global index to the corresponding password.

    Indexes are assigned in ascending length order:
      [min_len passwords]  then  [min_len+1 passwords]  ...  [max_len passwords]

    Within each length group, passwords are enumerated in lexicographic order
    of the charset (index 0 → charset[0] repeated min_len times, etc.).

    Returns None if index is outside the keyspace.
    """
    c = len(charset)
    offset = 0
    for length in range(min_len, max_len + 1):
        group_size = c ** length
        if index < offset + group_size:
            local_idx = index - offset
            chars = []
            for _ in range(length):
                chars.append(charset[local_idx % c])
                local_idx //= c
            return ''.join(reversed(chars))
        offset += group_size
    return None  # index beyond keyspace


def password_to_index(password: str, charset: str, min_len: int) -> int:
    """
    Convert a password back to its global 0-based index.
    Raises ValueError if any character is not in charset.
    """
    c = len(charset)
    char_map = {ch: i for i, ch in enumerate(charset)}
    length = len(password)

    # Offset: all passwords shorter than this length
    offset = sum(c ** i for i in range(min_len, length))

    # Local index within this length group
    local_idx = 0
    for ch in password:
        if ch not in char_map:
            raise ValueError(f"Character {ch!r} not in charset")
        local_idx = local_idx * c + char_map[ch]

    return offset + local_idx


# ── Step 4 & 5: Divide keyspace among workers ─────────────────────────────────

def divide_keyspace(total: int, num_workers: int) -> List[Tuple[int, int]]:
    """
    Split [0, total) into `num_workers` non-overlapping ranges.

    Returns a list of (start_index, end_index_inclusive) tuples.

    The remainder (total % num_workers) is distributed one extra combination
    to the first `remainder` workers, keeping workloads as equal as possible.

    Example:
        divide_keyspace(10, 3)  →  [(0,3), (4,7), (8,9)]
        divide_keyspace(9,  3)  →  [(0,2), (3,5), (6,8)]
    """
    if num_workers <= 0:
        raise ValueError("num_workers must be >= 1")
    if total <= 0:
        return [(0, 0)] * num_workers

    base      = total // num_workers
    remainder = total % num_workers

    ranges: List[Tuple[int, int]] = []
    start = 0
    for i in range(num_workers):
        size = base + (1 if i < remainder else 0)
        if size == 0:
            # More workers than combinations — give them an empty range
            ranges.append((start, start))
        else:
            ranges.append((start, start + size - 1))
        start += size
    return ranges


def distribute_job(
    charset: str,
    min_len: int,
    max_len: int,
    num_workers: int,
) -> dict:
    """
    High-level function used by the coordinator.

    Returns a dict with:
      - total_combinations
      - ranges: list of {worker_index, start_index, end_index, count}
      - charset_size
      - keyspace_summary
    """
    total  = total_keyspace(charset, min_len, max_len)
    ranges = divide_keyspace(total, num_workers)
    summary = keyspace_summary(charset, min_len, max_len)

    return {
        'total_combinations': total,
        'charset_size':       len(charset),
        'num_workers':        num_workers,
        'keyspace_summary':   summary,
        'ranges': [
            {
                'worker_index': i,
                'start_index':  start,
                'end_index':    end,
                'count':        end - start + 1,
            }
            for i, (start, end) in enumerate(ranges)
        ],
    }


# ── Brute-force time estimator ─────────────────────────────────────────────────

def estimate_time(total: int, hashes_per_second: float) -> dict:
    """Estimate crack time given a hash rate in H/s."""
    if hashes_per_second <= 0:
        return {'seconds': None, 'human': 'unknown'}

    seconds = total / hashes_per_second
    if seconds < 60:
        human = f"{seconds:.1f} seconds"
    elif seconds < 3600:
        human = f"{seconds/60:.1f} minutes"
    elif seconds < 86400:
        human = f"{seconds/3600:.1f} hours"
    elif seconds < 86400 * 365:
        human = f"{seconds/86400:.1f} days"
    else:
        human = f"{seconds/86400/365:.1f} years"
    return {'seconds': seconds, 'human': human}
