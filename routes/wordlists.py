"""
Wordlist and Rule Set Management
Upload, manage, preview custom wordlists and hashcat rule files
"""

from flask import Blueprint, render_template, request, jsonify, send_file, flash, redirect, url_for
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from config import Config
import os
import io
import math
import logging

logger = logging.getLogger(__name__)
wordlists_bp = Blueprint('wordlists', __name__, url_prefix='/wordlists')

WORDLIST_EXTENSIONS = {'txt', 'lst', 'dic', 'wl'}
RULES_EXTENSIONS = {'rule', 'rules', 'txt'}


def ensure_dirs():
    os.makedirs(Config.LOCAL_WORDLISTS_DIR, exist_ok=True)
    os.makedirs(Config.LOCAL_RULES_DIR, exist_ok=True)


def human_size(size_bytes: int) -> str:
    if size_bytes == 0:
        return '0 B'
    units = ('B', 'KB', 'MB', 'GB')
    i = int(math.floor(math.log(size_bytes, 1024)))
    i = min(i, len(units) - 1)
    p = math.pow(1024, i)
    return f"{size_bytes / p:.1f} {units[i]}"


def count_lines(filepath: str) -> int:
    try:
        with open(filepath, 'rb') as f:
            return sum(1 for _ in f)
    except Exception:
        return 0


def get_wordlist_info(filepath: str) -> dict:
    try:
        stat = os.stat(filepath)
        lines = count_lines(filepath)
        return {
            'name': os.path.basename(filepath),
            'path': filepath,
            'size': human_size(stat.st_size),
            'size_bytes': stat.st_size,
            'lines': lines,
            'modified': stat.st_mtime,
            'type': 'wordlist',
            'local': filepath.startswith(Config.LOCAL_WORDLISTS_DIR),
        }
    except Exception as e:
        return {
            'name': os.path.basename(filepath),
            'path': filepath,
            'size': 'N/A',
            'size_bytes': 0,
            'lines': 0,
            'modified': 0,
            'type': 'wordlist',
            'local': False,
        }


def get_rule_info(filepath: str) -> dict:
    try:
        stat = os.stat(filepath)
        lines = count_lines(filepath)
        return {
            'name': os.path.basename(filepath),
            'path': filepath,
            'size': human_size(stat.st_size),
            'size_bytes': stat.st_size,
            'lines': lines,
            'modified': stat.st_mtime,
            'type': 'rule',
            'local': filepath.startswith(Config.LOCAL_RULES_DIR),
        }
    except Exception:
        return {
            'name': os.path.basename(filepath),
            'path': filepath,
            'size': 'N/A',
            'size_bytes': 0,
            'lines': 0,
            'modified': 0,
            'type': 'rule',
            'local': False,
        }


def list_wordlists():
    ensure_dirs()
    wordlists = []

    # System wordlists
    if os.path.isdir(Config.WORDLISTS_DIR):
        for f in sorted(os.listdir(Config.WORDLISTS_DIR)):
            if f.endswith(tuple('.' + e for e in WORDLIST_EXTENSIONS)):
                fp = os.path.join(Config.WORDLISTS_DIR, f)
                if os.path.isfile(fp):
                    wordlists.append(get_wordlist_info(fp))

    # User-uploaded wordlists
    for f in sorted(os.listdir(Config.LOCAL_WORDLISTS_DIR)):
        fp = os.path.join(Config.LOCAL_WORDLISTS_DIR, f)
        if os.path.isfile(fp):
            wordlists.append(get_wordlist_info(fp))

    return wordlists


def list_rules():
    ensure_dirs()
    rules = []

    # System rules
    if os.path.isdir(Config.RULES_DIR):
        for f in sorted(os.listdir(Config.RULES_DIR)):
            if f.endswith(('.rule', '.rules')):
                fp = os.path.join(Config.RULES_DIR, f)
                if os.path.isfile(fp):
                    rules.append(get_rule_info(fp))

    # User-uploaded rules
    for f in sorted(os.listdir(Config.LOCAL_RULES_DIR)):
        fp = os.path.join(Config.LOCAL_RULES_DIR, f)
        if os.path.isfile(fp):
            rules.append(get_rule_info(fp))

    return rules


@wordlists_bp.route('/')
@login_required
def index():
    wordlists = list_wordlists()
    rules = list_rules()
    total_wordlist_size = sum(w['size_bytes'] for w in wordlists)
    total_rules_size = sum(r['size_bytes'] for r in rules)
    return render_template('wordlists.html',
        wordlists=wordlists,
        rules=rules,
        total_wordlist_size=human_size(total_wordlist_size),
        total_rules_size=human_size(total_rules_size),
    )


@wordlists_bp.route('/upload_wordlist', methods=['POST'])
@login_required
def upload_wordlist():
    ensure_dirs()
    if 'file' not in request.files:
        flash('No file selected.', 'error')
        return redirect(url_for('wordlists.index'))

    file = request.files['file']
    if not file.filename:
        flash('No file selected.', 'error')
        return redirect(url_for('wordlists.index'))

    ext = file.filename.rsplit('.', 1)[-1].lower() if '.' in file.filename else ''
    if ext not in WORDLIST_EXTENSIONS:
        flash(f'Invalid file type. Allowed: {", ".join(WORDLIST_EXTENSIONS)}', 'error')
        return redirect(url_for('wordlists.index'))

    filename = secure_filename(file.filename)
    dest = os.path.join(Config.LOCAL_WORDLISTS_DIR, filename)
    file.save(dest)
    size = os.path.getsize(dest)
    lines = count_lines(dest)
    flash(f'Wordlist "{filename}" uploaded ({human_size(size)}, {lines:,} words).', 'success')
    return redirect(url_for('wordlists.index'))


@wordlists_bp.route('/upload_rules', methods=['POST'])
@login_required
def upload_rules():
    ensure_dirs()
    if 'file' not in request.files:
        flash('No file selected.', 'error')
        return redirect(url_for('wordlists.index'))

    file = request.files['file']
    if not file.filename:
        flash('No file selected.', 'error')
        return redirect(url_for('wordlists.index'))

    filename = secure_filename(file.filename)
    dest = os.path.join(Config.LOCAL_RULES_DIR, filename)
    file.save(dest)
    size = os.path.getsize(dest)
    lines = count_lines(dest)
    flash(f'Rule set "{filename}" uploaded ({human_size(size)}, {lines:,} rules).', 'success')
    return redirect(url_for('wordlists.index'))


@wordlists_bp.route('/delete_wordlist', methods=['POST'])
@login_required
def delete_wordlist():
    if not current_user.is_admin:
        return jsonify({'error': 'Admin required'}), 403
    filepath = request.form.get('path', '')
    if not filepath.startswith(Config.LOCAL_WORDLISTS_DIR):
        return jsonify({'error': 'Can only delete locally uploaded wordlists'}), 403
    try:
        os.remove(filepath)
        flash(f'Wordlist "{os.path.basename(filepath)}" deleted.', 'success')
    except Exception as e:
        flash(f'Error deleting wordlist: {e}', 'error')
    return redirect(url_for('wordlists.index'))


@wordlists_bp.route('/delete_rules', methods=['POST'])
@login_required
def delete_rules():
    if not current_user.is_admin:
        return jsonify({'error': 'Admin required'}), 403
    filepath = request.form.get('path', '')
    if not filepath.startswith(Config.LOCAL_RULES_DIR):
        return jsonify({'error': 'Can only delete locally uploaded rule files'}), 403
    try:
        os.remove(filepath)
        flash(f'Rule set "{os.path.basename(filepath)}" deleted.', 'success')
    except Exception as e:
        flash(f'Error deleting rule set: {e}', 'error')
    return redirect(url_for('wordlists.index'))


@wordlists_bp.route('/preview')
@login_required
def preview():
    filepath = request.args.get('path', '')
    limit = int(request.args.get('limit', 50))
    offset = int(request.args.get('offset', 0))

    # Security: only allow paths within known dirs
    allowed_prefixes = (
        Config.LOCAL_WORDLISTS_DIR,
        Config.LOCAL_RULES_DIR,
        Config.WORDLISTS_DIR,
        Config.RULES_DIR,
    )
    if not any(filepath.startswith(p) for p in allowed_prefixes):
        return jsonify({'error': 'Access denied'}), 403

    try:
        lines = []
        total = 0
        with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
            for i, line in enumerate(f):
                total += 1
                if offset <= i < offset + limit:
                    lines.append(line.rstrip('\n'))
        return jsonify({
            'lines': lines,
            'total': total,
            'offset': offset,
            'limit': limit,
            'filename': os.path.basename(filepath),
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@wordlists_bp.route('/api/list')
@login_required
def api_list():
    return jsonify({
        'wordlists': list_wordlists(),
        'rules': list_rules(),
    })


@wordlists_bp.route('/create_wordlist', methods=['POST'])
@login_required
def create_wordlist():
    """Create a wordlist from text input"""
    ensure_dirs()
    name = request.form.get('name', '').strip()
    content = request.form.get('content', '')

    if not name:
        flash('Wordlist name is required.', 'error')
        return redirect(url_for('wordlists.index'))

    if not name.endswith('.txt'):
        name += '.txt'
    filename = secure_filename(name)
    dest = os.path.join(Config.LOCAL_WORDLISTS_DIR, filename)

    words = [w.strip() for w in content.splitlines() if w.strip()]
    with open(dest, 'w', encoding='utf-8') as f:
        f.write('\n'.join(words) + '\n')

    flash(f'Wordlist "{filename}" created with {len(words):,} words.', 'success')
    return redirect(url_for('wordlists.index'))
