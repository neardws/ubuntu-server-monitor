import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

from .collector import SystemCollector
from .gpu_collector import GPUCollector

logger = logging.getLogger(__name__)


class TelegramBot:
    """Telegram bot for server monitoring commands and notifications."""

    def __init__(self, token: str, chat_id: str, server_name: str = "Server"):
        self.token = token
        self.chat_id = chat_id
        self.server_name = server_name
        self.app = None
        self.system_collector = SystemCollector()
        self.gpu_collector = GPUCollector()

    async def send_message(self, text: str, parse_mode: str = "HTML"):
        """Send a message to the configured chat."""
        if self.app is None:
            self.app = Application.builder().token(self.token).build()
            await self.app.initialize()
        await self.app.bot.send_message(
            chat_id=self.chat_id,
            text=text,
            parse_mode=parse_mode
        )

    async def cmd_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text(
            f"Welcome to {self.server_name} Monitor Bot!\n"
            "Use /help to see available commands."
        )

    async def cmd_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        help_text = """<b>Available Commands:</b>
/status - Server overview
/cpu - CPU detailed information
/memory - Memory usage
/disk - Disk usage
/gpu - GPU information
/temps - Sensor temperatures
/services - Running services
/containers - Docker containers
/tmux - Tmux sessions
/top - Top processes
/help - Show this help"""
        await update.message.reply_html(help_text)

    async def cmd_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        metrics = self.system_collector.get_all_metrics()
        mem = metrics['memory']
        load = metrics['load_average']
        
        text = f"""<b>{self.server_name} Status</b>

<b>Uptime:</b> {metrics['uptime']}
<b>CPU:</b> {metrics['cpu_percent']:.1f}%
<b>Memory:</b> {mem['percent']:.1f}% ({self.system_collector.format_bytes(mem['used'])} / {self.system_collector.format_bytes(mem['total'])})
<b>Load:</b> {load[0]:.2f}, {load[1]:.2f}, {load[2]:.2f}"""

        if self.gpu_collector.is_available():
            gpus = self.gpu_collector.get_all_gpus()
            for gpu in gpus:
                text += f"\n<b>GPU {gpu['index']}:</b> {gpu['gpu_utilization']}% | {gpu['temperature']}°C | {gpu['memory_percent']:.1f}% VRAM"

        await update.message.reply_html(text)

    async def cmd_cpu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        cpu = self.system_collector.get_cpu_detailed()
        load = self.system_collector.get_load_average()
        text = f"""<b>CPU Information</b>

<b>Usage:</b> {cpu['percent']:.1f}%
<b>Cores:</b> {cpu['cores']} physical, {cpu['threads']} logical
<b>Load Average:</b> {load[0]:.2f}, {load[1]:.2f}, {load[2]:.2f}"""
        
        if cpu['freq_current']:
            text += f"\n<b>Frequency:</b> {cpu['freq_current']:.0f} MHz"
            if cpu['freq_max']:
                text += f" (max: {cpu['freq_max']:.0f} MHz)"
        
        text += "\n\n<b>Per Core Usage:</b>"
        for i, pct in enumerate(cpu['per_core_percent']):
            text += f"\n  Core {i}: {pct:.1f}%"
        
        await update.message.reply_html(text)

    async def cmd_memory(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        mem = self.system_collector.get_memory_info()
        text = f"""<b>Memory Information</b>

<b>Total:</b> {self.system_collector.format_bytes(mem['total'])}
<b>Used:</b> {self.system_collector.format_bytes(mem['used'])} ({mem['percent']:.1f}%)
<b>Available:</b> {self.system_collector.format_bytes(mem['available'])}"""
        await update.message.reply_html(text)

    async def cmd_disk(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        disks = self.system_collector.get_disk_info()
        text = f"<b>Disk Usage</b>\n"
        for disk in disks:
            text += f"\n<b>{disk['mountpoint']}</b>\n"
            text += f"  {self.system_collector.format_bytes(disk['used'])} / {self.system_collector.format_bytes(disk['total'])} ({disk['percent']:.1f}%)\n"
        await update.message.reply_html(text)

    async def cmd_gpu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self.gpu_collector.is_available():
            await update.message.reply_text("No NVIDIA GPU detected.")
            return
        
        gpus = self.gpu_collector.get_all_gpus()
        text = "<b>GPU Information</b>\n"
        for gpu in gpus:
            text += f"""
<b>GPU {gpu['index']}: {gpu['name']}</b>
  Temperature: {gpu['temperature']}°C
  GPU Usage: {gpu['gpu_utilization']}%
  Memory: {self.gpu_collector.format_bytes(gpu['memory_used'])} / {self.gpu_collector.format_bytes(gpu['memory_total'])} ({gpu['memory_percent']:.1f}%)
  Power: {gpu['power_usage']:.1f}W / {gpu['power_limit']:.1f}W
"""
        await update.message.reply_html(text)

    async def cmd_top(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        processes = self.system_collector.get_top_processes(5)
        text = "<b>Top Processes (by CPU)</b>\n\n"
        for proc in processes:
            text += f"<code>{proc['name'][:20]:20}</code> CPU: {proc['cpu_percent']:.1f}% MEM: {proc['memory_percent']:.1f}%\n"
        await update.message.reply_html(text)

    async def cmd_temps(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        temps = self.system_collector.get_temperatures()
        if not temps:
            await update.message.reply_text("No temperature sensors detected.")
            return
        
        text = "<b>Sensor Temperatures</b>\n"
        for sensor_name, entries in temps.items():
            text += f"\n<b>{sensor_name}:</b>"
            for entry in entries:
                label = entry.label or "temp"
                text += f"\n  {label}: {entry.current:.1f}°C"
                if entry.high:
                    text += f" (high: {entry.high:.0f}°C)"
        await update.message.reply_html(text)

    async def cmd_services(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        services = self.system_collector.get_running_services(20)
        if not services:
            await update.message.reply_text("No running services found or systemctl not available.")
            return
        
        text = f"<b>Running Services ({len(services)})</b>\n\n"
        for svc in services:
            text += f"<code>{svc['name'][:30]}</code>\n"
        await update.message.reply_html(text)

    async def cmd_containers(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        containers = self.system_collector.get_docker_containers()
        if not containers:
            await update.message.reply_text("No running containers or Docker not available.")
            return
        
        text = f"<b>Docker Containers ({len(containers)})</b>\n"
        for c in containers:
            text += f"\n<b>{c['name']}</b>\n"
            text += f"  Image: <code>{c['image'][:30]}</code>\n"
            text += f"  Status: {c['status']}\n"
        await update.message.reply_html(text)

    async def cmd_tmux(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        sessions = self.system_collector.get_tmux_sessions()
        if not sessions:
            await update.message.reply_text("No tmux sessions or tmux not available.")
            return
        
        text = f"<b>Tmux Sessions ({len(sessions)})</b>\n"
        for s in sessions:
            attached = "attached" if s['attached'] else "detached"
            text += f"\n<b>{s['name']}</b> ({attached})\n"
            text += f"  Windows: {s['windows']}\n"
            text += f"  Created: {s['created']}\n"
        await update.message.reply_html(text)

    def setup_handlers(self, app: Application):
        app.add_handler(CommandHandler("start", self.cmd_start))
        app.add_handler(CommandHandler("help", self.cmd_help))
        app.add_handler(CommandHandler("status", self.cmd_status))
        app.add_handler(CommandHandler("cpu", self.cmd_cpu))
        app.add_handler(CommandHandler("memory", self.cmd_memory))
        app.add_handler(CommandHandler("disk", self.cmd_disk))
        app.add_handler(CommandHandler("gpu", self.cmd_gpu))
        app.add_handler(CommandHandler("temps", self.cmd_temps))
        app.add_handler(CommandHandler("services", self.cmd_services))
        app.add_handler(CommandHandler("containers", self.cmd_containers))
        app.add_handler(CommandHandler("tmux", self.cmd_tmux))
        app.add_handler(CommandHandler("top", self.cmd_top))

    def run_polling(self):
        """Run the bot in polling mode."""
        app = Application.builder().token(self.token).build()
        self.app = app
        self.setup_handlers(app)
        logger.info("Starting Telegram bot...")
        app.run_polling()
