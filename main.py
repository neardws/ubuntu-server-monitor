#!/usr/bin/env python3
import asyncio
import logging
import signal
import sys
import threading
from pathlib import Path

import schedule
import yaml

from monitor import SystemCollector, GPUCollector, TelegramBot, Alerter

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def load_config(config_path: str = "config.yaml") -> dict:
    path = Path(config_path)
    if not path.exists():
        logger.error(f"Config file not found: {config_path}")
        logger.info("Please copy config.example.yaml to config.yaml and configure it.")
        sys.exit(1)
    
    with open(path, 'r') as f:
        return yaml.safe_load(f)


class ServerMonitor:
    def __init__(self, config: dict):
        self.config = config
        self.server_name = config.get('server', {}).get('name', 'Server')
        self.interval = config.get('monitor', {}).get('interval', 60)
        
        self.system_collector = SystemCollector()
        self.gpu_collector = GPUCollector()
        
        telegram_config = config['telegram']
        self.bot = TelegramBot(
            token=telegram_config['bot_token'],
            chat_id=telegram_config['chat_id'],
            server_name=self.server_name
        )
        
        self.alerter = Alerter(config, self.bot.send_message)
        self.running = False

    async def check_and_alert(self):
        try:
            system_metrics = self.system_collector.get_all_metrics()
            gpu_metrics = self.gpu_collector.get_all_gpus()
            await self.alerter.check_all(system_metrics, gpu_metrics, self.server_name)
        except Exception as e:
            logger.error(f"Error during monitoring check: {e}")

    async def send_daily_report(self):
        try:
            metrics = self.system_collector.get_all_metrics()
            mem = metrics['memory']
            load = metrics['load_average']
            
            text = f"""<b>📊 Daily Report - {self.server_name}</b>

<b>Uptime:</b> {metrics['uptime']}
<b>CPU:</b> {metrics['cpu_percent']:.1f}%
<b>Memory:</b> {mem['percent']:.1f}% ({self.system_collector.format_bytes(mem['used'])} / {self.system_collector.format_bytes(mem['total'])})
<b>Load:</b> {load[0]:.2f}, {load[1]:.2f}, {load[2]:.2f}

<b>Disk Usage:</b>"""
            
            for disk in metrics['disks']:
                text += f"\n  {disk['mountpoint']}: {disk['percent']:.1f}%"
            
            if self.gpu_collector.is_available():
                gpus = self.gpu_collector.get_all_gpus()
                text += "\n\n<b>GPU Status:</b>"
                for gpu in gpus:
                    text += f"\n  GPU {gpu['index']}: {gpu['gpu_utilization']}% | {gpu['temperature']}°C | {gpu['memory_percent']:.1f}% VRAM"
            
            await self.bot.send_message(text)
            logger.info("Daily report sent")
        except Exception as e:
            logger.error(f"Error sending daily report: {e}")

    def schedule_jobs(self):
        daily_config = self.config.get('daily_report', {})
        if daily_config.get('enabled', False):
            report_time = daily_config.get('time', '09:00')
            schedule.every().day.at(report_time).do(
                lambda: asyncio.run(self.send_daily_report())
            )
            logger.info(f"Daily report scheduled at {report_time}")

    def run_schedule(self):
        import time
        while self.running:
            schedule.run_pending()
            asyncio.run(self.check_and_alert())
            for _ in range(self.interval):
                if not self.running:
                    break
                schedule.run_pending()
                time.sleep(1)

    def start(self):
        self.running = True
        self.schedule_jobs()
        
        monitor_thread = threading.Thread(target=self.run_schedule, daemon=True)
        monitor_thread.start()
        
        logger.info(f"Starting {self.server_name} monitor...")
        logger.info(f"Monitoring interval: {self.interval}s")
        
        self.bot.run_polling()

    def stop(self):
        self.running = False
        logger.info("Monitor stopped")


def main():
    config = load_config()
    monitor = ServerMonitor(config)
    
    def signal_handler(signum, frame):
        logger.info("Received shutdown signal")
        monitor.stop()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        monitor.start()
    except KeyboardInterrupt:
        monitor.stop()


if __name__ == "__main__":
    main()
