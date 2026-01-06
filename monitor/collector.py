import psutil
from datetime import datetime


class SystemCollector:
    """Collect system metrics: CPU, memory, disk, network, load."""

    def get_cpu_percent(self) -> float:
        return psutil.cpu_percent(interval=1)

    def get_memory_info(self) -> dict:
        mem = psutil.virtual_memory()
        return {
            'total': mem.total,
            'used': mem.used,
            'available': mem.available,
            'percent': mem.percent
        }

    def get_disk_info(self) -> list:
        disks = []
        for partition in psutil.disk_partitions():
            try:
                usage = psutil.disk_usage(partition.mountpoint)
                disks.append({
                    'device': partition.device,
                    'mountpoint': partition.mountpoint,
                    'total': usage.total,
                    'used': usage.used,
                    'free': usage.free,
                    'percent': usage.percent
                })
            except PermissionError:
                continue
        return disks

    def get_network_io(self) -> dict:
        net = psutil.net_io_counters()
        return {
            'bytes_sent': net.bytes_sent,
            'bytes_recv': net.bytes_recv
        }

    def get_load_average(self) -> tuple:
        return psutil.getloadavg()

    def get_uptime(self) -> str:
        boot_time = datetime.fromtimestamp(psutil.boot_time())
        uptime = datetime.now() - boot_time
        days = uptime.days
        hours, remainder = divmod(uptime.seconds, 3600)
        minutes, _ = divmod(remainder, 60)
        return f"{days}d {hours}h {minutes}m"

    def get_top_processes(self, n: int = 5) -> list:
        processes = []
        for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
            try:
                processes.append(proc.info)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        processes.sort(key=lambda x: x['cpu_percent'] or 0, reverse=True)
        return processes[:n]

    def get_all_metrics(self) -> dict:
        return {
            'timestamp': datetime.now().isoformat(),
            'cpu_percent': self.get_cpu_percent(),
            'memory': self.get_memory_info(),
            'disks': self.get_disk_info(),
            'network': self.get_network_io(),
            'load_average': self.get_load_average(),
            'uptime': self.get_uptime()
        }

    @staticmethod
    def format_bytes(bytes_val: int) -> str:
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if bytes_val < 1024:
                return f"{bytes_val:.2f} {unit}"
            bytes_val /= 1024
        return f"{bytes_val:.2f} PB"
