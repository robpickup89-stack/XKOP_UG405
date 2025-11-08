#!/bin/bash
# COMPLETE INSTALLATION SCRIPT

echo "=========================================="
echo "XKOP Tool - Complete Installation"
echo "=========================================="

# Stop current app if running
echo "Stopping any running processes..."
sudo pkill -f app.py 2>/dev/null

# Install to correct location
cd ~/Desktop/Raspberry\ Pi\ KXOP\ UG405 || exit 1

echo ""
echo "Step 1: Installing Flask app..."
cp COMPLETE_app.py app.py
echo "✅ app.py installed"

echo ""
echo "Step 2: Installing SNMP pass script..."
sudo cp COMPLETE_utmc_snmp_pass.sh /usr/local/bin/utmc_snmp_pass.sh
sudo chmod +x /usr/local/bin/utmc_snmp_pass.sh
echo "✅ SNMP pass script installed"

echo ""
echo "Step 3: Installing snmpd configuration..."
sudo cp COMPLETE_snmpd.conf /etc/snmp/snmpd.conf
echo "✅ snmpd.conf installed"

echo ""
echo "Step 4: Restarting snmpd..."
sudo systemctl restart snmpd
sleep 2
sudo systemctl status snmpd --no-pager | head -5
echo "✅ snmpd restarted"

echo ""
echo "=========================================="
echo "Installation Complete!"
echo "=========================================="
echo ""
echo "To start the Flask app:"
echo "  cd ~/Desktop/Raspberry\ Pi\ KXOP\ UG405"
echo "  source venv/bin/activate"
echo "  python app.py"
echo ""
echo "Then test with:"
echo "  snmpset -v2c -c UTMC 10.164.95.201 .1.3.6.1.4.1.13267.3.2.4.2.1.5.1.5.49.49.48.49.49 i 5"
echo ""

