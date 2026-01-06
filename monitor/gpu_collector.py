import logging

logger = logging.getLogger(__name__)

try:
    import pynvml
    NVML_AVAILABLE = True
except ImportError:
    NVML_AVAILABLE = False


class GPUCollector:
    """Collect NVIDIA GPU metrics using pynvml."""

    def __init__(self):
        self.initialized = False
        if NVML_AVAILABLE:
            try:
                pynvml.nvmlInit()
                self.initialized = True
                self.device_count = pynvml.nvmlDeviceGetCount()
            except pynvml.NVMLError as e:
                logger.warning(f"Failed to initialize NVML: {e}")
                self.device_count = 0
        else:
            self.device_count = 0

    def is_available(self) -> bool:
        return self.initialized and self.device_count > 0

    def get_gpu_info(self, index: int = 0) -> dict:
        if not self.is_available():
            return {}
        
        try:
            handle = pynvml.nvmlDeviceGetHandleByIndex(index)
            name = pynvml.nvmlDeviceGetName(handle)
            if isinstance(name, bytes):
                name = name.decode('utf-8')
            
            memory = pynvml.nvmlDeviceGetMemoryInfo(handle)
            utilization = pynvml.nvmlDeviceGetUtilizationRates(handle)
            temperature = pynvml.nvmlDeviceGetTemperature(handle, pynvml.NVML_TEMPERATURE_GPU)
            
            try:
                power = pynvml.nvmlDeviceGetPowerUsage(handle) / 1000  # mW to W
                power_limit = pynvml.nvmlDeviceGetPowerManagementLimit(handle) / 1000
            except pynvml.NVMLError:
                power = 0
                power_limit = 0

            return {
                'index': index,
                'name': name,
                'temperature': temperature,
                'gpu_utilization': utilization.gpu,
                'memory_utilization': utilization.memory,
                'memory_total': memory.total,
                'memory_used': memory.used,
                'memory_free': memory.free,
                'memory_percent': (memory.used / memory.total) * 100,
                'power_usage': power,
                'power_limit': power_limit
            }
        except pynvml.NVMLError as e:
            logger.error(f"Error getting GPU {index} info: {e}")
            return {}

    def get_all_gpus(self) -> list:
        if not self.is_available():
            return []
        return [self.get_gpu_info(i) for i in range(self.device_count)]

    def __del__(self):
        if self.initialized:
            try:
                pynvml.nvmlShutdown()
            except:
                pass

    @staticmethod
    def format_bytes(bytes_val: int) -> str:
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if bytes_val < 1024:
                return f"{bytes_val:.2f} {unit}"
            bytes_val /= 1024
        return f"{bytes_val:.2f} PB"
