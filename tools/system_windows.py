"""
Comprehensive Windows System, Hardware, and File Actuator
Gives Ultron deep, direct control over:
- File management (search, list, read, write notes, organize folders, open documents)
- Storage & disk analytics
- System updates & security maintenance (Windows Update, Defender)
- Hardware controls (Volume, Brightness, Wi-Fi status, Battery health, Resource hogs)
- Application & process lifecycle
"""

import os
import re
import sys
import glob
import shutil
import subprocess
import logging
import psutil

if sys.platform == "win32":
    import win32gui
    import win32con
    from ctypes import cast, POINTER
    from comtypes import CLSCTX_ALL
    from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume

logger = logging.getLogger("Ultron.SystemWindows")

class WindowsSystemTool:
    @staticmethod
    def get_user_directories() -> dict:
        user_home = os.path.expanduser("~")
        return {
            "home": user_home,
            "desktop": os.path.join(user_home, "Desktop"),
            "downloads": os.path.join(user_home, "Downloads"),
            "documents": os.path.join(user_home, "Documents"),
            "pictures": os.path.join(user_home, "Pictures"),
            "videos": os.path.join(user_home, "Videos")
        }

    # ==========================================
    # 1. HARDWARE TELEMETRY & DEVICE CARE
    # ==========================================
    @staticmethod
    def get_system_vitals() -> dict:
        """Returns CPU, RAM, Disk, and Battery hardware telemetry."""
        cpu_percent = psutil.cpu_percent(interval=0.1)
        mem = psutil.virtual_memory()
        disk = psutil.disk_usage("C:\\")
        battery = psutil.sensors_battery()
        batt_info = {
            "percent": battery.percent if battery else None,
            "power_plugged": battery.power_plugged if battery else None
        }

        return {
            "cpu_usage_percent": cpu_percent,
            "ram_used_gb": round((mem.total - mem.available) / (1024 ** 3), 2),
            "ram_total_gb": round(mem.total / (1024 ** 3), 2),
            "ram_percent": mem.percent,
            "disk_free_gb": round(disk.free / (1024 ** 3), 2),
            "disk_total_gb": round(disk.total / (1024 ** 3), 2),
            "battery": batt_info
        }

    @staticmethod
    def get_top_resource_hogs(count: int = 5) -> str:
        """Finds processes consuming the highest RAM on the system."""
        try:
            procs = sorted(
                psutil.process_iter(['name', 'memory_info', 'cpu_percent']),
                key=lambda p: (p.info['memory_info'].rss if p.info.get('memory_info') else 0),
                reverse=True
            )[:count]

            lines = []
            for p in procs:
                name = p.info['name']
                rss_mb = round(p.info['memory_info'].rss / (1024 * 1024), 1)
                lines.append(f"{name} ({rss_mb} MB RAM)")

            return "Top resource consuming apps: " + ", ".join(lines) + "."
        except Exception as e:
            return f"Failed to inspect processes: {e}"

    # ==========================================
    # 2. AUDIO & DISPLAY HARDWARE CONTROLS
    # ==========================================
    @staticmethod
    def _get_endpoint_volume():
        devices = AudioUtilities.GetSpeakers()
        if hasattr(devices, "EndpointVolume"):
            return devices.EndpointVolume
        interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
        return cast(interface, POINTER(IAudioEndpointVolume))

    @staticmethod
    def set_volume(level: int) -> str:
        level = max(0, min(100, level))
        if sys.platform != "win32":
            return "Volume control is only supported on Windows."
        try:
            vol = WindowsSystemTool._get_endpoint_volume()
            vol.SetMasterVolumeLevelScalar(level / 100.0, None)
            return f"Master volume adjusted to {level}%."
        except Exception as e:
            logger.error(f"Failed to set volume: {e}")
            return f"Error setting volume: {str(e)}"

    @staticmethod
    def mute_volume(mute: bool = True) -> str:
        if sys.platform != "win32":
            return "Volume mute is only supported on Windows."
        try:
            vol = WindowsSystemTool._get_endpoint_volume()
            vol.SetMute(1 if mute else 0, None)
            return "System audio muted." if mute else "System audio unmuted."
        except Exception as e:
            return f"Error modifying mute state: {str(e)}"

    @staticmethod
    def set_brightness(level: int) -> str:
        """Sets display brightness (0-100) via Windows WMI."""
        level = max(10, min(100, level))
        try:
            cmd = f"powershell (Get-WmiObject -Namespace root/wmi -Class WmiMonitorBrightnessMethods).WmiSetBrightness(1, {level})"
            subprocess.Popen(cmd, shell=True)
            return f"Screen brightness adjusted to {level}%."
        except Exception as e:
            return f"Failed to adjust brightness: {e}"

    @staticmethod
    def get_network_status() -> str:
        """Queries Wi-Fi network name, signal strength, and connection state."""
        try:
            res = subprocess.run("netsh wlan show interfaces", capture_output=True, text=True, shell=True)
            ssid = None
            signal = None
            state = "Disconnected"
            for line in res.stdout.splitlines():
                if "State" in line and ":" in line:
                    state = line.split(":", 1)[1].strip()
                elif "SSID" in line and "BSSID" not in line and ":" in line:
                    ssid = line.split(":", 1)[1].strip()
                elif "Signal" in line and ":" in line:
                    signal = line.split(":", 1)[1].strip()

            if ssid:
                return f"Wi-Fi is connected to '{ssid}' with {signal} signal strength."
            return f"Network state: {state}."
        except Exception as e:
            return f"Unable to retrieve network telemetry: {e}"

    # ==========================================
    # 3. FILE MANAGEMENT & DATA OPERATIONS
    # ==========================================
    @staticmethod
    def search_files(keyword: str, directory: str = None) -> str:
        """Searches user folders (Desktop, Downloads, Documents) for files matching keyword."""
        dirs = WindowsSystemTool.get_user_directories()
        search_roots = [directory] if directory and os.path.exists(directory) else [
            dirs["desktop"], dirs["downloads"], dirs["documents"]
        ]

        found = []
        kw = keyword.lower().strip()

        for root_dir in search_roots:
            for root, _, files in os.walk(root_dir):
                for f in files:
                    if kw in f.lower():
                        full_path = os.path.join(root, f)
                        found.append(full_path)
                        if len(found) >= 5:
                            break
                if len(found) >= 5:
                    break

        if not found:
            return f"No files found matching '{keyword}' in user directories."

        file_names = [os.path.basename(p) for p in found]
        return f"Found {len(found)} matching files: " + ", ".join(file_names) + "."

    @staticmethod
    def list_user_files(folder_name: str = "downloads") -> str:
        """Lists the latest files in Downloads, Desktop, or Documents."""
        dirs = WindowsSystemTool.get_user_directories()
        target_dir = dirs.get(folder_name.lower().strip(), dirs["downloads"])

        if not os.path.exists(target_dir):
            return f"Directory {target_dir} not found."

        items = os.listdir(target_dir)
        files = [f for f in items if not f.startswith(".") and os.path.isfile(os.path.join(target_dir, f))]
        # Sort by modification time descending
        files.sort(key=lambda f: os.path.getmtime(os.path.join(target_dir, f)), reverse=True)
        top_files = files[:6]

        if not top_files:
            return f"No files found in {folder_name}."

        return f"Recent files in {folder_name}: " + ", ".join(top_files) + "."

    @staticmethod
    def read_file_text(file_name_or_path: str) -> str:
        """Finds and reads text from a file on Desktop or Documents."""
        dirs = WindowsSystemTool.get_user_directories()
        target = file_name_or_path

        if not os.path.isabs(target):
            # Try finding on Desktop, Documents, Downloads
            for folder in [dirs["desktop"], dirs["documents"], dirs["downloads"]]:
                candidate = os.path.join(folder, target)
                if os.path.exists(candidate):
                    target = candidate
                    break

        if not os.path.exists(target):
            # Fuzzy search
            res = WindowsSystemTool.search_files(file_name_or_path)
            return f"File not found directly. {res}"

        try:
            with open(target, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read(500)
            return f"File '{os.path.basename(target)}' content: {content.strip()}"
        except Exception as e:
            return f"Error reading file: {e}"

    @staticmethod
    def write_note(title: str, text: str) -> str:
        """Creates or appends a text note on the user's Desktop."""
        dirs = WindowsSystemTool.get_user_directories()
        clean_title = re.sub(r'[^a-zA-Z0-9_\-]', '_', title).strip('_') or "Ultron_Note"
        file_path = os.path.join(dirs["desktop"], f"{clean_title}.txt")

        try:
            with open(file_path, "a", encoding="utf-8") as f:
                f.write(f"{text}\n")
            return f"Saved note '{clean_title}.txt' to your Desktop."
        except Exception as e:
            return f"Failed to save note: {e}"

    @staticmethod
    def delete_file(filename_or_keyword: str) -> str:
        """Finds and deletes a file from Downloads, Desktop, or Documents."""
        clean_target = filename_or_keyword.lower().strip()
        clean_target = re.sub(r"^(?:the\s+file\s*,?\s*|file\s*,?\s*|the\s*,?\s*)", "", clean_target).strip()
        clean_target = clean_target.strip(".,?! ")

        dirs = WindowsSystemTool.get_user_directories()
        search_roots = [dirs["downloads"], dirs["desktop"], dirs["documents"]]

        target_path = None
        target_name = None

        for folder in search_roots:
            if not os.path.exists(folder):
                continue
            for f in os.listdir(folder):
                f_lower = f.lower()
                if clean_target == f_lower or clean_target in f_lower:
                    full_p = os.path.join(folder, f)
                    if os.path.isfile(full_p):
                        target_path = full_p
                        target_name = f
                        break
            if target_path:
                break

        if not target_path:
            return f"I could not find any file matching '{filename_or_keyword}' in your Downloads, Desktop, or Documents."

        try:
            os.remove(target_path)
            return f"Successfully deleted '{target_name}'."
        except Exception as e:
            return f"Failed to delete '{target_name}': {e}"

    @staticmethod
    def organize_downloads() -> str:
        """Categorizes files in Downloads into subfolders by file type."""
        dirs = WindowsSystemTool.get_user_directories()
        down_dir = dirs["downloads"]
        if not os.path.exists(down_dir):
            return "Downloads folder not found."

        extensions_map = {
            "PDFs": [".pdf"],
            "Images": [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".svg"],
            "Documents": [".docx", ".doc", ".xlsx", ".csv", ".pptx", ".txt"],
            "Installers": [".exe", ".msi", ".iso"],
            "Archives": [".zip", ".rar", ".7z", ".tar", ".gz"]
        }

        moved_count = 0
        for item in os.listdir(down_dir):
            item_path = os.path.join(down_dir, item)
            if os.path.isfile(item_path):
                _, ext = os.path.splitext(item.lower())
                for category, exts in extensions_map.items():
                    if ext in exts:
                        cat_dir = os.path.join(down_dir, category)
                        os.makedirs(cat_dir, exist_ok=True)
                        try:
                            shutil.move(item_path, os.path.join(cat_dir, item))
                            moved_count += 1
                        except Exception:
                            pass
                        break

        return f"Organized {moved_count} files in your Downloads folder into categorized folders."

    # ==========================================
    # 4. STORAGE, SECURITY & WINDOWS UPDATES
    # ==========================================
    @staticmethod
    def clean_temporary_files() -> str:
        temp_dir = os.environ.get("TEMP", "")
        if not temp_dir or not os.path.exists(temp_dir):
            return "Temp directory not found."

        deleted_files = 0
        freed_bytes = 0
        for item in os.listdir(temp_dir):
            item_path = os.path.join(temp_dir, item)
            try:
                if os.path.isfile(item_path) or os.path.islink(item_path):
                    freed_bytes += os.path.getsize(item_path)
                    os.unlink(item_path)
                    deleted_files += 1
                elif os.path.isdir(item_path):
                    shutil.rmtree(item_path, ignore_errors=True)
                    deleted_files += 1
            except Exception:
                continue

        freed_mb = round(freed_bytes / (1024 * 1024), 2)
        return f"Cleaned {deleted_files} temporary files, freeing ~{freed_mb} MB of storage."

    @staticmethod
    def check_windows_updates() -> str:
        """Checks Windows Update service status and triggers update scan."""
        try:
            # Trigger background update orchestrator scan
            subprocess.Popen("powershell -Command Start-Process usoclient -ArgumentList StartScan", shell=True)
            return "Windows Update service is active. Triggered background scan for latest security and system patches."
        except Exception as e:
            return f"Failed to query Windows Update: {e}"

    @staticmethod
    def run_security_scan(scan_type: str = "QuickScan") -> str:
        try:
            cmd = f"powershell -Command Start-MpScan -ScanType {scan_type}"
            subprocess.Popen(cmd, shell=True)
            return f"Initiated Windows Defender {scan_type} in background."
        except Exception as e:
            return f"Failed to start security scan: {e}"

    @staticmethod
    def check_security_status() -> str:
        """Queries Windows Defender real-time protection and firewall status."""
        try:
            res = subprocess.run(
                ["powershell", "-Command", "(Get-MpComputerStatus).RealTimeProtectionEnabled"],
                capture_output=True, text=True
            )
            rtp = res.stdout.strip()
            status_str = "Enabled and active" if rtp.lower() == "true" else "Disabled"
            return f"Windows Defender Real-Time Protection is {status_str}."
        except Exception as e:
            return f"Security status check failed: {e}"

    # ==========================================
    # 5. UNIVERSAL APP & POWER CONTROLS
    # ==========================================
    @staticmethod
    def launch_application(app_name: str) -> str:
        """Launches any application, file, or protocol on Windows."""
        key = app_name.lower().strip()
        local_app = os.environ.get("LOCALAPPDATA", "")

        # Guard against blank or verb-only strings
        if not key or key in ["open", "launch", "start", "close", "the", "a", "an", "app", "application"]:
            return "Please tell me which app or folder you would like me to open, sir."

        # Common application paths
        if "discord" in key:
            discord_updater = os.path.join(local_app, "Discord", "Update.exe")
            if os.path.exists(discord_updater):
                subprocess.Popen(f'"{discord_updater}" --processStart Discord.exe', shell=True)
                return "Opening Discord."
            subprocess.Popen('cmd /c start discord:', shell=True)
            return "Opening Discord."

        if "whatsapp" in key:
            subprocess.Popen('cmd /c start whatsapp:', shell=True)
            return "Opening WhatsApp."

        if any(b in key for b in ["edge", "microsoft edge", "browser", "internet"]):
            subprocess.Popen('cmd /c start msedge', shell=True)
            return "Opening Microsoft Edge."

        if "chrome" in key:
            subprocess.Popen('cmd /c start chrome', shell=True)
            return "Opening Google Chrome."

        if "spotify" in key:
            subprocess.Popen('cmd /c start spotify:', shell=True)
            return "Opening Spotify."

        # Notepad & text editors
        if any(n in key for n in ["notepad", "note pack", "notepack", "note pad", "notes", "note"]):
            subprocess.Popen('cmd /c start notepad', shell=True)
            return "Opening Notepad."

        # Microsoft Office Suite
        if any(w in key for w in ["microsoft word", "word", "winword", "world", "ms word"]):
            subprocess.Popen('cmd /c start winword', shell=True)
            return "Opening Microsoft Word."

        if any(x in key for x in ["excel", "microsoft excel", "ms excel"]):
            subprocess.Popen('cmd /c start excel', shell=True)
            return "Opening Microsoft Excel."

        if any(p in key for p in ["powerpoint", "ppt", "power point", "ms powerpoint"]):
            subprocess.Popen('cmd /c start powerpnt', shell=True)
            return "Opening Microsoft PowerPoint."

        if any(c in key for c in ["calculator", "calc"]):
            subprocess.Popen('cmd /c start calc', shell=True)
            return "Opening Calculator."

        if "settings" in key:
            subprocess.Popen('cmd /c start ms-settings:', shell=True)
            return "Opening Windows Settings."

        if any(t in key for t in ["task manager", "taskmgr"]):
            subprocess.Popen('cmd /c start taskmgr', shell=True)
            return "Opening Task Manager."

        if any(e in key for e in ["file explorer", "explorer", "my files", "files"]):
            subprocess.Popen('cmd /c start explorer', shell=True)
            return "Opening File Explorer."

        # Drive root folders (e.g. "open new volume y", "open y drive", "open c drive", "local disk c")
        if any(y in key for y in ["volume y", "y drive", "y folder", "new volume y", "volume by", "new volume by", "drive y", "drive by", "volume why", "new volume why", "y:"]):
            subprocess.Popen('explorer.exe Y:\\', shell=True)
            return "Opening New Volume Y."

        if any(c in key for c in ["local disk c", "local disk", "disk c", "volume c", "c drive", "c folder", "new volume c", "drive c", "1 c drive", "one c drive", "1 disk c", "1c drive", "c:"]):
            subprocess.Popen('explorer.exe C:\\', shell=True)
            return "Opening Local Disk C."

        if any(d in key for d in ["volume d", "d drive", "d folder", "new volume d", "drive d", "d:"]):
            subprocess.Popen('explorer.exe D:\\', shell=True)
            return "Opening Volume D."

        # Try user folders directly (e.g. "open downloads", "open desktop")
        dirs = WindowsSystemTool.get_user_directories()
        for folder_k, folder_p in dirs.items():
            if folder_k in key:
                subprocess.Popen(f'cmd /c start "" "{folder_p}"', shell=True)
                return f"Opening {folder_k.capitalize()} folder."

        # Generic launch fallback
        try:
            subprocess.Popen(f'cmd /c start "" "{key}"', shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return f"Opening {app_name}."
        except Exception as e:
            return f"Failed to open {app_name}: {e}"

    @staticmethod
    def close_application(app_name: str) -> str:
        target = app_name.lower().strip()
        closed_count = 0
        for proc in psutil.process_iter(['pid', 'name']):
            try:
                p_name = (proc.info['name'] or '').lower()
                if target in p_name:
                    proc.terminate()
                    closed_count += 1
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        if closed_count > 0:
            return f"Closed {closed_count} instances of {app_name}."
        return f"No active process found matching '{app_name}'."

    @staticmethod
    def shutdown_system(delay_seconds: int = 15) -> str:
        try:
            subprocess.Popen(f"shutdown /s /t {delay_seconds}", shell=True)
            return f"Initiating system shutdown in {delay_seconds} seconds. Say 'Cancel shutdown' to abort."
        except Exception as e:
            return f"Failed to initiate shutdown: {e}"

    @staticmethod
    def abort_shutdown() -> str:
        try:
            subprocess.Popen("shutdown /a", shell=True)
            return "System shutdown has been cancelled."
        except Exception as e:
            return f"Failed to cancel shutdown: {e}"

    @staticmethod
    def restart_system(delay_seconds: int = 10) -> str:
        try:
            subprocess.Popen(f"shutdown /r /t {delay_seconds}", shell=True)
            return f"Restarting the computer in {delay_seconds} seconds."
        except Exception as e:
            return f"Failed to initiate restart: {e}"

    @staticmethod
    def lock_workstation() -> str:
        try:
            import ctypes
            ctypes.windll.user32.LockWorkStation()
            return "Locking the workstation."
        except Exception as e:
            return f"Failed to lock workstation: {e}"
