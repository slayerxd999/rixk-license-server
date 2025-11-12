# License Key Management Server
# Run with: python server.py

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import sqlite3
import secrets
import hashlib
from datetime import datetime
import os

app = Flask(__name__, static_folder='public')
CORS(app)

# Admin password (change this!)
ADMIN_PASSWORD = "admin123"  # TODO: Change this to a secure password

# Database initialization
def init_db():
    conn = sqlite3.connect('licenses.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS licenses
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  license_key TEXT UNIQUE NOT NULL,
                  active INTEGER DEFAULT 1,
                  created_at TEXT NOT NULL,
                  hwid TEXT,
                  note TEXT)''')
    conn.commit()
    conn.close()

init_db()

def verify_admin(password):
    """Verify admin password"""
    return password == ADMIN_PASSWORD

@app.route('/')
def index():
    """Serve admin panel"""
    return send_from_directory('public', 'index.html')

@app.route('/<path:path>')
def serve_static(path):
    """Serve static files"""
    return send_from_directory('public', path)

@app.route('/api/validate', methods=['POST'])
def validate_key():
    """Validate a license key (PUBLIC - used by run.py)"""
    data = request.json
    license_key = data.get('key', '').strip()
    hwid = data.get('hwid', '')
    
    if not license_key:
        return jsonify({'valid': False, 'message': 'License key required'})
    
    conn = sqlite3.connect('licenses.db')
    c = conn.cursor()
    c.execute('SELECT active, hwid FROM licenses WHERE license_key = ?', (license_key,))
    result = c.fetchone()
    
    if not result:
        conn.close()
        return jsonify({'valid': False, 'message': 'Invalid license key'})
    
    active, stored_hwid = result
    
    if not active:
        conn.close()
        return jsonify({'valid': False, 'message': 'License key has been revoked'})
    
    # HWID binding (optional - first activation binds HWID)
    if hwid:
        if stored_hwid is None:
            # First activation - bind HWID
            c.execute('UPDATE licenses SET hwid = ? WHERE license_key = ?', (hwid, license_key))
            conn.commit()
        elif stored_hwid != hwid:
            conn.close()
            return jsonify({'valid': False, 'message': 'License key is bound to another device'})
    
    conn.close()
    return jsonify({'valid': True, 'message': 'License key is valid'})

@app.route('/api/generate', methods=['POST'])
def generate_key():
    """Generate a new license key (ADMIN only)"""
    data = request.json
    password = data.get('password', '')
    note = data.get('note', '')
    
    if not verify_admin(password):
        return jsonify({'success': False, 'message': 'Invalid admin password'}), 401
    
    # Generate secure random key (format: RIXK-XXXX-XXXX-XXXX)
    raw_key = secrets.token_hex(6).upper()  # 12 hex chars
    license_key = f"RIXK-{raw_key[0:4]}-{raw_key[4:8]}-{raw_key[8:12]}"
    
    try:
        conn = sqlite3.connect('licenses.db')
        c = conn.cursor()
        c.execute('INSERT INTO licenses (license_key, created_at, note) VALUES (?, ?, ?)',
                  (license_key, datetime.now().isoformat(), note))
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'key': license_key})
    except sqlite3.IntegrityError:
        return jsonify({'success': False, 'message': 'Key generation failed, try again'})

@app.route('/api/keys', methods=['POST'])
def list_keys():
    """List all license keys (ADMIN only)"""
    data = request.json
    password = data.get('password', '')
    
    if not verify_admin(password):
        return jsonify({'success': False, 'message': 'Invalid admin password'}), 401
    
    conn = sqlite3.connect('licenses.db')
    c = conn.cursor()
    c.execute('SELECT id, license_key, active, created_at, hwid, note FROM licenses ORDER BY id DESC')
    rows = c.fetchall()
    conn.close()
    
    keys = [{
        'id': row[0],
        'key': row[1],
        'active': bool(row[2]),
        'created_at': row[3],
        'hwid': row[4] or 'Not activated',
        'note': row[5] or ''
    } for row in rows]
    
    return jsonify({'success': True, 'keys': keys})

@app.route('/api/revoke', methods=['POST'])
def revoke_key():
    """Revoke a license key (ADMIN only)"""
    data = request.json
    password = data.get('password', '')
    license_key = data.get('key', '')
    
    if not verify_admin(password):
        return jsonify({'success': False, 'message': 'Invalid admin password'}), 401
    
    conn = sqlite3.connect('licenses.db')
    c = conn.cursor()
    c.execute('UPDATE licenses SET active = 0 WHERE license_key = ?', (license_key,))
    conn.commit()
    conn.close()
    
    return jsonify({'success': True, 'message': 'License key revoked'})

@app.route('/api/activate', methods=['POST'])
def activate_key():
    """Reactivate a license key (ADMIN only)"""
    data = request.json
    password = data.get('password', '')
    license_key = data.get('key', '')
    
    if not verify_admin(password):
        return jsonify({'success': False, 'message': 'Invalid admin password'}), 401
    
    conn = sqlite3.connect('licenses.db')
    c = conn.cursor()
    c.execute('UPDATE licenses SET active = 1 WHERE license_key = ?', (license_key,))
    conn.commit()
    conn.close()
    
    return jsonify({'success': True, 'message': 'License key activated'})

@app.route('/api/delete', methods=['POST'])
def delete_key():
    """Delete a license key (ADMIN only)"""
    data = request.json
    password = data.get('password', '')
    license_key = data.get('key', '')
    
    if not verify_admin(password):
        return jsonify({'success': False, 'message': 'Invalid admin password'}), 401
    
    conn = sqlite3.connect('licenses.db')
    c = conn.cursor()
    c.execute('DELETE FROM licenses WHERE license_key = ?', (license_key,))
    conn.commit()
    conn.close()
    
    return jsonify({'success': True, 'message': 'License key deleted'})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))  # Use PORT from environment or default to 5000
    print("=" * 60)
    print("🔐 License Key Management Server")
    print("=" * 60)
    print(f"🌐 Admin Panel: http://0.0.0.0:{port}")
    print("🔑 Default Admin Password: admin123")
    print("⚠️  CHANGE THE PASSWORD IN server.py BEFORE DEPLOYMENT!")
    print("=" * 60)
    app.run(host='0.0.0.0', port=port, debug=False)
