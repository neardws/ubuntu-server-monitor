import json
import subprocess
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
        skip_prefixes = ('/snap', '/boot/efi', '/run', '/dev', '/sys', '/proc')
        skip_fstypes = ('squashfs', 'tmpfs', 'devtmpfs', 'overlay')
        
        for partition in psutil.disk_partitions(all=False):
            if partition.mountpoint.startswith(skip_prefixes):
                continue
            if partition.fstype in skip_fstypes:
                continue
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

    def get_cpu_detailed(self) -> dict:
        freq = psutil.cpu_freq()
        return {
            'cores': psutil.cpu_count(logical=False),
            'threads': psutil.cpu_count(logical=True),
            'percent': psutil.cpu_percent(interval=1),
            'per_core_percent': psutil.cpu_percent(interval=0.1, percpu=True),
            'freq_current': freq.current if freq else None,
            'freq_min': freq.min if freq else None,
            'freq_max': freq.max if freq else None
        }

    def get_temperatures(self) -> dict:
        try:
            temps = psutil.sensors_temperatures()
            return temps if temps else {}
        except AttributeError:
            return {}

    def get_running_services(self, limit: int = 20) -> list:
        try:
            result = subprocess.run(
                ['systemctl', 'list-units', '--type=service', '--state=running', '--no-pager', '--plain'],
                capture_output=True, text=True, timeout=10
            )
            if result.returncode != 0:
                return []
            lines = result.stdout.strip().split('\n')
            services = []
            for line in lines[1:]:
                parts = line.split()
                if len(parts) >= 4 and parts[0].endswith('.service'):
                    services.append({
                        'name': parts[0].replace('.service', ''),
                        'status': parts[2],
                        'sub': parts[3]
                    })
            return services[:limit]
        except Exception:
            return []

    def get_docker_containers(self) -> list:
        try:
            result = subprocess.run(
                ['docker', 'ps', '--format', '{{json .}}'],
                capture_output=True, text=True, timeout=10
            )
            if result.returncode != 0:
                return []
            containers = []
            for line in result.stdout.strip().split('\n'):
                if line:
                    try:
                        container = json.loads(line)
                        containers.append({
                            'name': container.get('Names', ''),
                            'image': container.get('Image', ''),
                            'status': container.get('Status', ''),
                            'ports': container.get('Ports', '')
                        })
                    except json.JSONDecodeError:
                        continue
            return containers
        except Exception:
            return []

    @staticmethod
    def format_bytes(bytes_val: int) -> str:
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if bytes_val < 1024:
                return f"{bytes_val:.2f} {unit}"
            bytes_val /= 1024
        return f"{bytes_val:.2f} PB"
