# Ubuntu Server Monitor

A lightweight Ubuntu server monitoring tool that sends alerts and status updates via Telegram.

## Features

- **System Monitoring**: CPU, memory, disk, network, load average
- **GPU Monitoring**: NVIDIA GPU temperature, utilization, memory (via pynvml)
- **Telegram Bot Commands**: Interactive commands to check server status
- **Alerting**: Configurable thresholds with warning/critical levels
- **Daily Reports**: Scheduled daily health summaries

## Telegram Commands

| Command | Description |
|---------|-------------|
| `/status` | Server overview |
| `/cpu` | CPU detailed information (cores, frequency, per-core usage) |
| `/memory` | Memory usage |
| `/disk` | Disk usage |
| `/gpu` | GPU information |
| `/temps` | Sensor temperatures |
| `/services` | Running systemd services |
| `/containers` | Docker containers status |
| `/tmux` | Tmux sessions |
| `/top` | Top processes |
| `/help` | Show help |

## Installation

### Prerequisites

- Python 3.8+
- Telegram Bot Token (create via [@BotFather](https://t.me/BotFather))
- Your Telegram Chat ID (get via [@userinfobot](https://t.me/userinfobot))

### Quick Start

```bash
# Clone the repository
git clone https://github.com/YOUR_USERNAME/ubuntu-server-monitor.git
cd ubuntu-server-monitor

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure
cp config.example.yaml config.yaml
nano config.yaml  # Edit with your Telegram credentials

# Run
python main.py
```

### Install as System Service

```bash
sudo ./install.sh
sudo nano /opt/ubuntu-server-monitor/config.yaml  # Configure
sudo systemctl start ubuntu-server-monitor
```

## Configuration

Edit `config.yaml`:

```yaml
telegram:
  bot_token: "YOUR_BOT_TOKEN"
  chat_id: "YOUR_CHAT_ID"

server:
  name: "My Server"

monitor:
  interval: 60  # Check interval in seconds

alerts:
  cpu_warning: 70
  cpu_critical: 90
  memory_warning: 80
  memory_critical: 95
  disk_warning: 80
  disk_critical: 95
  gpu_temp_warning: 75
  gpu_temp_critical: 85
  gpu_memory_warning: 80
  gpu_memory_critical: 95
  cooldown: 300  # Seconds between same alerts

daily_report:
  enabled: true
  time: "09:00"
```

## Service Management

```bash
# Start/Stop/Restart
sudo systemctl start ubuntu-server-monitor
sudo systemctl stop ubuntu-server-monitor
sudo systemctl restart ubuntu-server-monitor

# View logs
sudo journalctl -u ubuntu-server-monitor -f

# Check status
sudo systemctl status ubuntu-server-monitor
```

## License

MIT
