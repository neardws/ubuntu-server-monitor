#!/bin/bash
set -e

SERVICE_NAME="ubuntu-server-monitor"
INSTALL_DIR="/opt/$SERVICE_NAME"
CURRENT_DIR="$(cd "$(dirname "$0")" && pwd)"

if [ "$EUID" -ne 0 ]; then
    echo "Please run as root (sudo ./install.sh)"
    exit 1
fi

echo "Installing $SERVICE_NAME..."

mkdir -p "$INSTALL_DIR"
cp -r "$CURRENT_DIR"/* "$INSTALL_DIR/"

if [ ! -f "$INSTALL_DIR/config.yaml" ]; then
    cp "$INSTALL_DIR/config.example.yaml" "$INSTALL_DIR/config.yaml"
    echo "Created config.yaml from template. Please edit it with your settings."
fi

cd "$INSTALL_DIR"
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
deactivate

cat > /etc/systemd/system/$SERVICE_NAME.service << EOF
[Unit]
Description=Ubuntu Server Monitor with Telegram
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=$INSTALL_DIR
ExecStart=$INSTALL_DIR/venv/bin/python main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable $SERVICE_NAME

echo ""
echo "Installation complete!"
echo ""
echo "Next steps:"
echo "1. Edit the config file: sudo nano $INSTALL_DIR/config.yaml"
echo "2. Start the service: sudo systemctl start $SERVICE_NAME"
echo "3. Check status: sudo systemctl status $SERVICE_NAME"
echo "4. View logs: sudo journalctl -u $SERVICE_NAME -f"
