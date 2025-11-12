// API Configuration
const API_URL = window.location.origin;

// Session management
let adminPassword = '';

// Login
async function login() {
    const password = document.getElementById('loginPassword').value;
    const errorDiv = document.getElementById('loginError');
    
    if (!password) {
        errorDiv.textContent = '⚠️ Please enter admin password';
        return;
    }
    
    errorDiv.textContent = '';
    
    try {
        // Verify password by trying to load keys
        const response = await fetch(`${API_URL}/api/keys`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ password })
        });
        
        const data = await response.json();
        
        if (data.success) {
            adminPassword = password;
            document.getElementById('loginSection').style.display = 'none';
            document.getElementById('mainPanel').style.display = 'block';
            loadKeys();
        } else {
            errorDiv.textContent = '❌ Invalid admin password';
        }
    } catch (error) {
        errorDiv.textContent = '❌ Connection error. Make sure the server is running.';
    }
}

// Logout
function logout() {
    adminPassword = '';
    document.getElementById('loginSection').style.display = 'block';
    document.getElementById('mainPanel').style.display = 'none';
    document.getElementById('loginPassword').value = '';
}

// Generate Key
async function generateKey() {
    const note = document.getElementById('keyNote').value;
    const resultDiv = document.getElementById('generateResult');
    
    resultDiv.textContent = '';
    
    try {
        const response = await fetch(`${API_URL}/api/generate`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ password: adminPassword, note })
        });
        
        const data = await response.json();
        
        if (data.success) {
            resultDiv.textContent = `✅ Generated: ${data.key}`;
            document.getElementById('keyNote').value = '';
            
            // Copy to clipboard
            navigator.clipboard.writeText(data.key).then(() => {
                resultDiv.textContent += ' (Copied to clipboard!)';
            });
            
            // Reload keys list
            setTimeout(() => {
                loadKeys();
                resultDiv.textContent = '';
            }, 3000);
        } else {
            resultDiv.className = 'error-message';
            resultDiv.textContent = '❌ ' + data.message;
        }
    } catch (error) {
        resultDiv.className = 'error-message';
        resultDiv.textContent = '❌ Connection error';
    }
}

// Load Keys
async function loadKeys() {
    const keysDiv = document.getElementById('keysList');
    keysDiv.innerHTML = '<div class="loading">Loading keys...</div>';
    
    try {
        const response = await fetch(`${API_URL}/api/keys`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ password: adminPassword })
        });
        
        const data = await response.json();
        
        if (data.success) {
            const keys = data.keys;
            
            // Update stats
            document.getElementById('totalKeys').textContent = keys.length;
            document.getElementById('activeKeys').textContent = keys.filter(k => k.active).length;
            
            if (keys.length === 0) {
                keysDiv.innerHTML = '<div class="loading">No license keys yet. Generate one to get started!</div>';
                return;
            }
            
            // Display keys
            keysDiv.innerHTML = keys.map(key => `
                <div class="key-item">
                    <div class="key-header">
                        <div class="key-code" onclick="copyToClipboard('${key.key}')" title="Click to copy">
                            ${key.key}
                        </div>
                        <div class="key-status ${key.active ? 'status-active' : 'status-inactive'}">
                            ${key.active ? '✅ Active' : '❌ Revoked'}
                        </div>
                    </div>
                    
                    <div class="key-info">
                        <div class="info-item">
                            <div class="info-label">Created</div>
                            <div class="info-value">${formatDate(key.created_at)}</div>
                        </div>
                        <div class="info-item">
                            <div class="info-label">HWID</div>
                            <div class="info-value">${key.hwid}</div>
                        </div>
                        <div class="info-item">
                            <div class="info-label">Note</div>
                            <div class="info-value">${key.note || 'No note'}</div>
                        </div>
                    </div>
                    
                    <div class="key-actions">
                        ${key.active ? 
                            `<button class="btn btn-danger btn-sm" onclick="revokeKey('${key.key}')">
                                <svg width="16" height="16" viewBox="0 0 20 20" fill="none">
                                    <path d="M6 10L14 10" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
                                </svg>
                                Revoke
                            </button>` :
                            `<button class="btn btn-warning btn-sm" onclick="activateKey('${key.key}')">
                                <svg width="16" height="16" viewBox="0 0 20 20" fill="none">
                                    <path d="M10 4V16M4 10H16" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
                                </svg>
                                Activate
                            </button>`
                        }
                        <button class="btn btn-danger btn-sm" onclick="deleteKey('${key.key}')">
                            <svg width="16" height="16" viewBox="0 0 20 20" fill="none">
                                <path d="M6 6L14 14M6 14L14 6" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
                            </svg>
                            Delete
                        </button>
                    </div>
                </div>
            `).join('');
        }
    } catch (error) {
        keysDiv.innerHTML = '<div class="loading">❌ Failed to load keys</div>';
    }
}

// Revoke Key
async function revokeKey(key) {
    if (!confirm(`Revoke license key: ${key}?`)) return;
    
    try {
        const response = await fetch(`${API_URL}/api/revoke`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ password: adminPassword, key })
        });
        
        const data = await response.json();
        if (data.success) {
            loadKeys();
        }
    } catch (error) {
        alert('Failed to revoke key');
    }
}

// Activate Key
async function activateKey(key) {
    if (!confirm(`Activate license key: ${key}?`)) return;
    
    try {
        const response = await fetch(`${API_URL}/api/activate`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ password: adminPassword, key })
        });
        
        const data = await response.json();
        if (data.success) {
            loadKeys();
        }
    } catch (error) {
        alert('Failed to activate key');
    }
}

// Delete Key
async function deleteKey(key) {
    if (!confirm(`Permanently delete license key: ${key}?\n\nThis action cannot be undone!`)) return;
    
    try {
        const response = await fetch(`${API_URL}/api/delete`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ password: adminPassword, key })
        });
        
        const data = await response.json();
        if (data.success) {
            loadKeys();
        }
    } catch (error) {
        alert('Failed to delete key');
    }
}

// Utility: Copy to clipboard
function copyToClipboard(text) {
    navigator.clipboard.writeText(text).then(() => {
        // Visual feedback
        const tempMsg = document.createElement('div');
        tempMsg.textContent = '✅ Copied to clipboard!';
        tempMsg.style.cssText = 'position: fixed; top: 20px; right: 20px; background: #48bb78; color: white; padding: 1rem 2rem; border-radius: 8px; font-weight: 600; z-index: 9999; animation: slideIn 0.3s;';
        document.body.appendChild(tempMsg);
        setTimeout(() => tempMsg.remove(), 2000);
    });
}

// Utility: Format date
function formatDate(isoString) {
    const date = new Date(isoString);
    return date.toLocaleString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
}

// Handle Enter key on login
document.addEventListener('DOMContentLoaded', () => {
    document.getElementById('loginPassword').addEventListener('keypress', (e) => {
        if (e.key === 'Enter') login();
    });
});
