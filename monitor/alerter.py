import logging
import time
from typing import Optional

logger = logging.getLogger(__name__)


class Alerter:
    """Handle alert logic with cooldown to prevent spam."""

    def __init__(self, config: dict, send_func):
        self.config = config.get('alerts', {})
        self.send_func = send_func
        self.cooldown = self.config.get('cooldown', 300)
        self.last_alerts = {}

    def _can_alert(self, alert_key: str) -> bool:
        now = time.time()
        last_time = self.last_alerts.get(alert_key, 0)
        if now - last_time >= self.cooldown:
            self.last_alerts[alert_key] = now
            return True
        return False

    def _get_level(self, value: float, warning: float, critical: float) -> Optional[str]:
        if value >= critical:
            return 'CRITICAL'
        elif value >= warning:
            return 'WARNING'
        return None

    async def check_cpu(self, cpu_percent: float, server_name: str):
        warning = self.config.get('cpu_warning', 70)
        critical = self.config.get('cpu_critical', 90)
        level = self._get_level(cpu_percent, warning, critical)
        
        if level and self._can_alert(f'cpu_{level}'):
            emoji = "🔴" if level == 'CRITICAL' else "🟡"
            await self.send_func(
                f"{emoji} <b>[{level}] {server_name}</b>\n"
                f"CPU usage: <b>{cpu_percent:.1f}%</b>"
            )

    async def check_memory(self, memory_percent: float, server_name: str):
        warning = self.config.get('memory_warning', 80)
        critical = self.config.get('memory_critical', 95)
        level = self._get_level(memory_percent, warning, critical)
        
        if level and self._can_alert(f'memory_{level}'):
            emoji = "🔴" if level == 'CRITICAL' else "🟡"
            await self.send_func(
                f"{emoji} <b>[{level}] {server_name}</b>\n"
                f"Memory usage: <b>{memory_percent:.1f}%</b>"
            )

    async def check_disk(self, disk_info: dict, server_name: str):
        warning = self.config.get('disk_warning', 80)
        critical = self.config.get('disk_critical', 95)
        
        for disk in disk_info:
            level = self._get_level(disk['percent'], warning, critical)
            if level and self._can_alert(f"disk_{disk['mountpoint']}_{level}"):
                emoji = "🔴" if level == 'CRITICAL' else "🟡"
                await self.send_func(
                    f"{emoji} <b>[{level}] {server_name}</b>\n"
                    f"Disk {disk['mountpoint']}: <b>{disk['percent']:.1f}%</b>"
                )

    async def check_gpu_temp(self, gpu_info: list, server_name: str):
        warning = self.config.get('gpu_temp_warning', 75)
        critical = self.config.get('gpu_temp_critical', 85)
        
        for gpu in gpu_info:
            temp = gpu.get('temperature', 0)
            level = self._get_level(temp, warning, critical)
            if level and self._can_alert(f"gpu_temp_{gpu['index']}_{level}"):
                emoji = "🔴" if level == 'CRITICAL' else "🟡"
                await self.send_func(
                    f"{emoji} <b>[{level}] {server_name}</b>\n"
                    f"GPU {gpu['index']} ({gpu['name']}) temperature: <b>{temp}°C</b>"
                )

    async def check_gpu_memory(self, gpu_info: list, server_name: str):
        warning = self.config.get('gpu_memory_warning', 80)
        critical = self.config.get('gpu_memory_critical', 95)
        
        for gpu in gpu_info:
            mem_percent = gpu.get('memory_percent', 0)
            level = self._get_level(mem_percent, warning, critical)
            if level and self._can_alert(f"gpu_mem_{gpu['index']}_{level}"):
                emoji = "🔴" if level == 'CRITICAL' else "🟡"
                await self.send_func(
                    f"{emoji} <b>[{level}] {server_name}</b>\n"
                    f"GPU {gpu['index']} ({gpu['name']}) memory: <b>{mem_percent:.1f}%</b>"
                )

    async def check_all(self, system_metrics: dict, gpu_metrics: list, server_name: str):
        await self.check_cpu(system_metrics['cpu_percent'], server_name)
        await self.check_memory(system_metrics['memory']['percent'], server_name)
        await self.check_disk(system_metrics['disks'], server_name)
        if gpu_metrics:
            await self.check_gpu_temp(gpu_metrics, server_name)
            await self.check_gpu_memory(gpu_metrics, server_name)
