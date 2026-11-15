import tkinter as tk
import psutil
import threading
import time
import subprocess

# Inicialização segura da NVML da NVIDIA
NVML_AVAILABLE = False
NVML_HANDLE = None

try:
    import pynvml
    pynvml.nvmlInit()
    NVML_HANDLE = pynvml.nvmlDeviceGetHandleByIndex(0)
    NVML_AVAILABLE = True
except Exception:
    NVML_AVAILABLE = False

class SystemMonitorOverlay:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("SysMonitor Pro")
        
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        self.root.attributes("-alpha", 0.88)
        self.root.configure(bg="#18181b")

        screen_w = self.root.winfo_screenwidth()
        # Altura reduzida para eliminar o espaço vazio inferior
        self.root.geometry(f"230x125+{screen_w - 250}+20")

        self.root.bind("<Button-1>", self.start_move)
        self.root.bind("<B1-Motion>", self.do_move)
        self.root.bind("<Button-3>", lambda e: self.root.destroy())

        self.gpu_usage = 0.0
        self.gpu_temp = 0.0
        self.vram_used_gb = 0.0
        self.vram_total_gb = self.get_total_vram_gb()
        self.running = True

        self.setup_ui()

        if NVML_AVAILABLE:
            threading.Thread(target=self.poll_nvidia, daemon=True).start()

        self.update_ui()

    def get_total_vram_gb(self):
        if NVML_AVAILABLE and NVML_HANDLE:
            try:
                mem_info = pynvml.nvmlDeviceGetMemoryInfo(NVML_HANDLE)
                return mem_info.total / (1024**3)
            except Exception:
                pass
        try:
            cmd = 'powershell -NoProfile -Command "(Get-CimInstance Win32_VideoController | Measure-Object -Property AdapterRAM -Maximum).Maximum"'
            out = subprocess.check_output(cmd, shell=True, creationflags=subprocess.CREATE_NO_WINDOW).decode().strip()
            return int(out) / (1024**3)
        except Exception:
            return 8.0

    def poll_nvidia(self):
        while self.running:
            try:
                util = pynvml.nvmlDeviceGetUtilizationRates(NVML_HANDLE)
                self.gpu_usage = float(util.gpu)
                
                mem_info = pynvml.nvmlDeviceGetMemoryInfo(NVML_HANDLE)
                self.vram_used_gb = mem_info.used / (1024**3)

                self.gpu_temp = float(pynvml.nvmlDeviceGetTemperature(NVML_HANDLE, pynvml.NVML_TEMPERATURE_GPU))
            except Exception:
                pass
            time.sleep(1)

    def setup_ui(self):
        frame = tk.Frame(self.root, bg="#18181b", highlightbackground="#3f3f46", highlightthickness=1, padx=12, pady=8)
        frame.pack(fill="both", expand=True)

        self.bars = {}
        metrics = [
            ("CPU", "#38bdf8"),
            ("RAM", "#a78bfa"),
            ("GPU", "#34d399"),
            ("VRAM", "#fb923c")
        ]

        for name, color in metrics:
            row = tk.Frame(frame, bg="#18181b")
            row.pack(fill="x", pady=2)

            lbl_name = tk.Label(row, text=name, font=("Segoe UI", 8, "bold"), fg="#a1a1aa", bg="#18181b", width=5, anchor="w")
            lbl_name.pack(side="left")

            lbl_val = tk.Label(row, text="0%", font=("Segoe UI", 8, "bold"), fg="#f4f4f5", bg="#18181b", anchor="e")
            lbl_val.pack(side="right")

            canvas = tk.Canvas(row, height=5, bg="#27272a", highlightthickness=0)
            canvas.pack(side="left", fill="x", expand=True, padx=(4, 6))
            bar = canvas.create_rectangle(0, 0, 0, 5, fill=color, width=0)

            self.bars[name] = (canvas, bar, lbl_val)

    def update_bar(self, name, pct, text_override=None):
        canvas, bar, lbl_val = self.bars[name]
        pct = max(0.0, min(100.0, pct))
        width = canvas.winfo_width()
        if width <= 1:
            width = 100
        canvas.coords(bar, 0, 0, (pct / 100.0) * width, 5)
        lbl_val.config(text=text_override if text_override else f"{pct:.0f}%")

    def update_ui(self):
        cpu_pct = psutil.cpu_percent(interval=None)
        
        ram = psutil.virtual_memory()
        ram_pct = ram.percent
        ram_used_gb = ram.used / (1024**3)
        ram_total_gb = ram.total / (1024**3)

        gpu_text = f"{self.gpu_usage:.0f}% | {self.gpu_temp:.0f}°C" if self.gpu_temp > 0 else f"{self.gpu_usage:.0f}%"

        self.update_bar("CPU", cpu_pct, f"{cpu_pct:.0f}%")
        self.update_bar("RAM", ram_pct, f"{ram_used_gb:.1f}/{ram_total_gb:.0f}G")
        self.update_bar("GPU", self.gpu_usage, gpu_text)

        if self.vram_total_gb > 0:
            vram_pct = (self.vram_used_gb / self.vram_total_gb) * 100
            self.update_bar("VRAM", vram_pct, f"{self.vram_used_gb:.1f}/{self.vram_total_gb:.0f}G")
        else:
            self.update_bar("VRAM", 0, f"{self.vram_used_gb:.1f} GB")

        self.root.after(1000, self.update_ui)

    def start_move(self, event):
        self.x = event.x
        self.y = event.y

    def do_move(self, event):
        x = self.root.winfo_x() + (event.x - self.x)
        y = self.root.winfo_y() + (event.y - self.y)
        self.root.geometry(f"+{x}+{y}")

if __name__ == "__main__":
    app = SystemMonitorOverlay()
    app.root.mainloop()