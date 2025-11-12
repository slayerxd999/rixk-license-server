===============================================
LICENSE KEY MANAGEMENT SYSTEM
===============================================

📋 SETUP INSTRUCTIONS
===============================================

1. Install Dependencies:
   pip install -r requirements.txt

2. Configure Admin Password:
   Open server.py and change this line:
   ADMIN_PASSWORD = "admin123"  # Change to your secure password

3. Run the Server:
   python server.py

4. Access the Panel:
   Open your browser: http://localhost:5000

===============================================

🚀 HOW TO USE
===============================================

STEP 1: Start the Server
   - Run: python server.py
   - Server will start on http://localhost:5000

STEP 2: Login to Admin Panel
   - Open: http://localhost:5000
   - Enter your admin password (default: admin123)

STEP 3: Generate License Keys
   - Click "Generate Key" button
   - Add optional note (customer name, order ID, etc.)
   - Key is automatically copied to clipboard
   - Give this key to your customer

STEP 4: Customer Uses the Key
   - Customer runs: run.py
   - Enters the license key you generated
   - Key is validated against your server
   - If valid, tool continues running
   - If invalid, customer sees error message

===============================================

🔐 KEY FEATURES
===============================================

✅ License Key Validation
   - Validates keys via API
   - HWID (Hardware ID) binding
   - First activation binds to device

✅ Key Management
   - Generate unlimited keys
   - Revoke/Activate keys
   - Delete keys permanently
   - Add notes to each key

✅ HWID Binding
   - First activation binds key to device
   - Prevents key sharing
   - Shows "bound to another device" if used elsewhere

===============================================

⚙️ DEPLOYMENT (For Production)
===============================================

1. Deploy to a Cloud Server:
   - Heroku, DigitalOcean, AWS, etc.
   - Make sure Python is installed

2. Update run.py:
   Open run.py and change this line:
   LICENSE_SERVER = "http://your-server-url.com"
   
   Example:
   LICENSE_SERVER = "https://mykeypanel.herokuapp.com"

3. Keep server.py running 24/7
   Use process managers like:
   - PM2 (with pm2-runtime)
   - Supervisor
   - systemd

4. Use HTTPS in production
   - Get SSL certificate (Let's Encrypt)
   - Use reverse proxy (Nginx)

===============================================

📊 DATABASE
===============================================

- Database: SQLite (licenses.db)
- Automatically created on first run
- Location: keypanel/licenses.db
- Backup regularly!

===============================================

🔧 IMPORTANT CONFIGURATION
===============================================

In run.py (line 16):
   LICENSE_SERVER = "http://localhost:5000"
   
   For production, change to your deployed URL:
   LICENSE_SERVER = "https://your-domain.com"

In server.py (line 11):
   ADMIN_PASSWORD = "admin123"
   
   IMPORTANT: Change this before deployment!

===============================================

💡 WORKFLOW SUMMARY
===============================================

You (Admin):
1. Run the license server (server.py)
2. Generate license keys from admin panel
3. Give keys to customers

Customer:
1. Receives run.py from you
2. Runs run.py
3. Enters license key when prompted
4. If valid → Tool runs
5. If invalid → Error message shown

===============================================

🛡️ SECURITY NOTES
===============================================

✓ HWID binding prevents key sharing
✓ Keys are validated server-side
✓ Admin password protects key management
✓ Server must be running for validation
✓ Customer only needs run.py file

⚠️ CHANGE DEFAULT ADMIN PASSWORD!
⚠️ BACKUP licenses.db regularly!
⚠️ Use HTTPS in production!

===============================================
