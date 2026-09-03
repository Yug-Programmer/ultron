"""
Comprehensive Fast Intent & System Actuator Filter
Translates natural spoken user requests directly into OS actions for:
- File searching, reading, note taking, listing, and folder organization
- Windows Update check and triggers
- Security & Antivirus diagnostics
- Device Care & resource hog detection (CPU, RAM, Battery)
- Display brightness, Wi-Fi networking, Audio volume
- App and folder opening/closing
- System shutdown, abort, restart, lock
"""

import re
import random
import logging
from tools.system_windows import WindowsSystemTool
from tools.gui_automation import GUIAutomationTool
from tools.file_assistant import FileAssistantTool

logger = logging.getLogger("Ultron.IntentFilter")

class FastIntentFilter:
    @staticmethod
    def evaluate(user_text: str) -> str:
        text = user_text.lower().strip()

        # ----------------------------------------------------
        # 1. Conversational Greetings & Human-like Small Talk
        # ----------------------------------------------------
        if text in ["hello", "hi", "hey", "hello ultron", "hi ultron", "hey ultron"]:
            return random.choice([
                "Good day, sir. All systems running smoothly. What's on your mind?",
                "Hello sir. Always at your disposal. What can I do for you?",
                "Right here, sir. Standing by for your instructions.",
                "Greetings, sir. Ready when you are."
            ])
        if any(k in text for k in ["how are you", "how're you", "how are you doing", "how do you feel"]):
            v = WindowsSystemTool.get_system_vitals()
            return random.choice([
                f"Operating smoothly at {v['cpu_usage_percent']}% CPU with zero issues to report, sir. How are things on your end?",
                "Feeling quite sharp today, sir. All hardware systems are running at peak efficiency.",
                "Never better, sir. Ready to assist with whatever you need.",
                f"Diagnostics look pristine—RAM is at {v['ram_percent']}% and storage is healthy. What are we tackling today?"
            ])
        if any(k in text for k in ["who are you", "what are you", "introduce yourself"]):
            return "I am Ultron, your autonomous OS assistant. Think of me as your personal Jarvis—I have direct control over your hardware, screen, files, and daily tasks."
        if any(k in text for k in ["what can you do", "help me with commands", "your features", "what are your capabilities"]):
            return ("I can search and delete files, organize your downloads, take notes, check Windows updates, "
                    "detect RAM hogs, adjust volume and brightness, check Wi-Fi, open any app, clean temporary storage, and manage your workstation.")
        if any(k in text for k in ["thank you", "thanks ultron", "thanks"]):
            return random.choice([
                "Always at your service, sir.",
                "Glad to be of assistance, sir.",
                "Anytime, sir. Let me know if you need anything else.",
                "Don't mention it, sir. That's what I'm here for."
            ])

        # ----------------------------------------------------
        # 2. Power & Workstation Controls
        # ----------------------------------------------------
        if any(k in text for k in ["don't shut", "dont shut", "cancel shut", "stop shut", "abort shut", "do not shut"]):
            return WindowsSystemTool.abort_shutdown()

        if any(k in text for k in ["shut down", "shutdown", "turn off my pc", "turn off pc", "turn off the pc", "power off"]):
            return WindowsSystemTool.shutdown_system(15)
        if any(k in text for k in ["restart my pc", "restart pc", "reboot", "reboot pc"]):
            return WindowsSystemTool.restart_system(10)
        if any(k in text for k in ["lock pc", "lock screen", "lock workstation", "sleep pc"]):
            return WindowsSystemTool.lock_workstation()

        # ----------------------------------------------------
        # 3. Hardware: Display Brightness & Network Telemetry
        # ----------------------------------------------------
        if "brightness" in text:
            digits = re.findall(r"\d+", text)
            if digits:
                return WindowsSystemTool.set_brightness(int(digits[0]))
            if any(u in text for u in ["up", "raise", "increase", "higher"]):
                return WindowsSystemTool.set_brightness(90)
            if any(d in text for d in ["down", "lower", "decrease", "dim"]):
                return WindowsSystemTool.set_brightness(40)

        if any(k in text for k in ["wifi", "wi-fi", "network status", "internet connection", "am i connected"]):
            return WindowsSystemTool.get_network_status()

        if "nightlight" in text or "night light" in text:
            import subprocess
            subprocess.Popen("cmd /c start ms-settings:nightlight", shell=True)
            return "Opening Night Light settings for you."

        if "hotspot" in text:
            import subprocess
            subprocess.Popen("cmd /c start ms-settings:network-mobilehotspot", shell=True)
            return "Opening Mobile Hotspot settings for you."

        # ----------------------------------------------------
        # 4. Hardware: Audio & Volume
        # ----------------------------------------------------
        if "mute" in text and "unmute" not in text:
            return WindowsSystemTool.mute_volume(True)
        if "unmute" in text:
            return WindowsSystemTool.mute_volume(False)

        if "volume" in text or "sound" in text:
            digits = re.findall(r"\d+", text)
            if digits:
                val = int(digits[0])
                if val == 250:  # Whisper mis-transcription of 'to 50'
                    val = 50
                elif val > 100:
                    val = 100
                return WindowsSystemTool.set_volume(val)
            if any(u in text for u in ["up", "raise", "increase", "higher"]):
                return WindowsSystemTool.set_volume(80)
            if any(d in text for d in ["down", "lower", "decrease", "softer"]):
                return WindowsSystemTool.set_volume(30)

        # ----------------------------------------------------
        # 5. Device Care & Resource Hogs
        # ----------------------------------------------------
        if any(k in text for k in ["most ram", "ram hogs", "resource hogs", "using most memory", "cpu hogs", "consuming ram"]):
            return WindowsSystemTool.get_top_resource_hogs(count=4)

        if any(k in text for k in ["battery", "charge", "percentage", "storage space", "free disk", "free storage", "ram usage", "cpu usage", "system vitals", "system status", "hardware specs"]):
            v = WindowsSystemTool.get_system_vitals()
            batt_str = f"Battery is at {v['battery']['percent']}%" if v['battery']['percent'] is not None else "Running on AC power"
            return (f"CPU load is at {v['cpu_usage_percent']}%. "
                    f"RAM usage is {v['ram_percent']}%. "
                    f"C drive has {v['disk_free_gb']} GB free. {batt_str}.")

        # ----------------------------------------------------
        # 6. Windows Updates & Security Management
        # ----------------------------------------------------
        if any(k in text for k in ["windows update", "system update", "check for update", "check updates", "install update"]):
            return WindowsSystemTool.check_windows_updates()

        if any(k in text for k in ["security status", "antivirus status", "is antivirus active", "protection status"]):
            return WindowsSystemTool.check_security_status()

        if any(k in text for k in ["security scan", "antivirus scan", "scan pc", "scan virus"]):
            return WindowsSystemTool.run_security_scan()

        if any(k in text for k in ["clean temp", "clean storage", "clean disk", "free up space", "free storage", "clean cache"]):
            return WindowsSystemTool.clean_temporary_files()

        # ----------------------------------------------------
        # 7. File Management & Data Operations
        # ----------------------------------------------------
        if any(k in text for k in ["organize downloads", "organize my downloads", "sort downloads"]):
            return WindowsSystemTool.organize_downloads()

        if any(k in text for k in ["search for file", "search file", "find file", "search for", "find my"]):
            kw = re.sub(r".*?(?:search for file|search file|find file|search for|find my)\s+", "", text).strip()
            kw = kw.strip(".,?! ")
            if kw:
                return WindowsSystemTool.search_files(kw)

        if any(k in text for k in ["list files", "what files", "show files", "recent files"]):
            folder = "downloads"
            if "desktop" in text:
                folder = "desktop"
            elif "document" in text:
                folder = "documents"
            return WindowsSystemTool.list_user_files(folder)

        # ----------------------------------------------------
        # 7. File & Folder Operations, Reading, and Editing
        # ----------------------------------------------------
        # Natural Folder Opening (e.g. "open program files in local disk c", "open program files", "open ultron folder")
        if re.search(r"^(?:open|explore|show)\s+", text):
            folder_res = FileAssistantTool.open_folder(text)
            if folder_res:
                return folder_res

        # Specific File Opening (e.g. "open file main.py", "open notes.txt", "open download file.pdf")
        if any(k in text for k in ["open file", "open the file", "launch file"]):
            f_target = re.sub(r".*?(?:open file|open the file|launch file)\s*", "", text).strip()
            f_res = FileAssistantTool.open_file(f_target)
            if f_res:
                return f_res

        # Reading File Content
        if any(k in text for k in ["read file", "read the file", "what is in file", "read contents of"]):
            f_target = re.sub(r".*?(?:read file|read the file|what is in file|read contents of)\s*", "", text).strip()
            return FileAssistantTool.read_file(f_target)

        # Appending / Writing to File by Voice (e.g. "append to notes.txt saying meeting at 5pm", "in notes.txt add buy groceries")
        m_app = re.search(r"(?:append to|add to|write into)\s+(?:file\s+)?([a-zA-Z0-9_\-\.]+)\s+(?:saying\s+|that\s+)?(.*)", text)
        if m_app:
            target_fn, target_txt = m_app.group(1), m_app.group(2)
            return FileAssistantTool.append_to_file(target_fn, target_txt)

        m_in = re.search(r"in\s+(?:file\s+)?([a-zA-Z0-9_\-\.]+)\s+(?:add|write|append)\s+(.*)", text)
        if m_in:
            target_fn, target_txt = m_in.group(1), m_in.group(2)
            return FileAssistantTool.append_to_file(target_fn, target_txt)

        # In-Editor Live Voice Typing & Document Saving
        # Handles: "write hello in this", "write hello in this note", "write hello", "type this text"
        if re.search(r"^(?:type|write)\s+", text):
            if not re.search(r"^(?:write\s+a\s+note|write\s+note\b|write\s+into\s+file\s+[a-zA-Z0-9_\-\.]+)", text):
                clean_text = re.sub(r"^(?:type|write)\s+", "", text).strip()
                clean_text = re.sub(r"\s+(?:in\s+this\s*(?:note|document|file)?|in\s+notepad|in\s+editor|into\s+this)$", "", clean_text).strip()
                clean_text = re.sub(r"^(?:into\s+(?:file|document|editor)\s+|saying\s+|that\s+|text\s+)", "", clean_text).strip()
                if clean_text:
                    return FileAssistantTool.type_into_active_editor(clean_text)

        # Disk File Modifications (e.g. "in notes.txt replace meeting with workshop", "in notes.txt delete line error")
        m_disk_rep = re.search(r"in\s+(?:file\s+)?([a-zA-Z0-9_\-\.]+)\s+(?:replace|change)\s+(.*?)\s+(?:with|to)\s+(.*)", text)
        if m_disk_rep:
            return FileAssistantTool.replace_in_file_on_disk(m_disk_rep.group(1), m_disk_rep.group(2), m_disk_rep.group(3))

        m_disk_del = re.search(r"in\s+(?:file\s+)?([a-zA-Z0-9_\-\.]+)\s+(?:delete|remove)\s+(?:lines?\s*(?:containing|with)?|all\s+data|all)\s*(.*)", text)
        if m_disk_del:
            kw = m_disk_del.group(2).strip() or "all"
            return FileAssistantTool.delete_from_file_on_disk(m_disk_del.group(1), kw)

        # Active Application Find & Replace (e.g. "replace hello with goodbye in this", "change apple to orange in note")
        m_active_rep = re.search(r"^(?:replace|change)\s+(.*?)\s+(?:with|to)\s+(.*?)(?:\s+in\s+this.*|\s+in\s+note.*|\s+in\s+document.*)?$", text)
        if m_active_rep:
            return FileAssistantTool.replace_in_active_editor(m_active_rep.group(1), m_active_rep.group(2))

        # Active Application Clear, Delete Text, Undo, and Redo
        if any(k in text for k in ["clear this", "clear document", "clear all text", "delete all text", "clear note"]):
            return FileAssistantTool.clear_active_editor()

        if any(k in text for k in ["delete line", "delete this line", "clear line"]):
            return FileAssistantTool.delete_in_active_editor("line")

        if any(k in text for k in ["delete last word", "delete word"]):
            return FileAssistantTool.delete_in_active_editor("word")

        if any(k in text for k in ["undo that", "undo"]):
            return FileAssistantTool.undo_in_active_editor()

        if any(k in text for k in ["redo that", "redo"]):
            return FileAssistantTool.redo_in_active_editor()

        if text in ["save file", "save the file", "save document", "save this document", "save this file", "save"]:
            return FileAssistantTool.save_active_document()

        if any(k in text for k in ["delete file", "delete the file", "remove file", "delete"]):
            target = re.sub(r".*?(?:delete file|delete the file|remove file|delete)\s+", "", text).strip()
            target = re.sub(r"^(?:the\s+file\s*,?\s*|file\s*,?\s*|the\s*,?\s*)", "", target).strip(".,?! ")
            if target and not any(p in target for p in ["shutdown", "window", "note", "app", "line", "word", "text"]):
                # Try FileAssistantTool first, then WindowsSystemTool
                del_res = FileAssistantTool.delete_file_on_disk(target)
                if del_res and "could not locate" not in del_res:
                    return del_res
                return WindowsSystemTool.delete_file(target)

        if any(k in text for k in ["write a note", "take a note", "save note", "create note"]):
            note_content = re.sub(r".*?(?:write a note|take a note|save note|create note)\s*(?:saying|that)?\s*", "", text).strip()
            if note_content:
                return WindowsSystemTool.write_note("Ultron_Note", note_content)

        # ----------------------------------------------------
        # 8. Universal App & Window Control
        # ----------------------------------------------------
        if re.search(r"^(?:open|launch|start)\s+", text):
            clean = re.sub(r"^(?:open|launch|start)\s+", "", text).strip()
            clean = re.sub(r"^(?:an\s+|the\s+|app\s+|application\s+|my\s+)", "", clean).strip()
            clean = clean.strip(".,?! ")
            if clean:
                return WindowsSystemTool.launch_application(clean)

        # Direct app names without 'open'
        if text in ["task manager", "calculator", "notepad", "settings", "file explorer"]:
            return WindowsSystemTool.launch_application(text)

        if re.search(r"^(?:close|kill|terminate|exit)\s+", text):
            clean = re.sub(r"^(?:close|kill|terminate|exit)\s+", "", text).strip()
            clean = re.sub(r"^(?:an\s+|the\s+|app\s+|application\s+|my\s+)", "", clean).strip()
            clean = clean.strip(".,?! ")
            if clean and len(clean.split()) <= 4:
                return WindowsSystemTool.close_application(clean)

        # ----------------------------------------------------
        # 9. GUI & Desktop Operations
        # ----------------------------------------------------
        if any(k in text for k in ["show desktop", "minimize all", "go to desktop"]):
            return GUIAutomationTool.show_desktop()
        if any(k in text for k in ["dismiss", "close dialog", "click ok", "dismiss error"]):
            return GUIAutomationTool.dismiss_active_dialog()
        if any(k in text for k in ["close window", "close this window"]):
            return GUIAutomationTool.force_close_active_window()

        return None

    @staticmethod
    def is_direct_system_command(user_text: str) -> bool:
        """
        Determines whether the spoken phrase is an explicit, unambiguous system command
        that should be executed immediately even in Standby mode without saying 'Ultron'.
        Filters out casual conversation, room talk, and non-system chatter.
        """
        text = user_text.lower().strip()
        valid_patterns = [
            r'^(?:open|launch|start)\s+(?:task\s*manager|calculator|notepad|settings|chrome|edge|discord|whatsapp|spotify|explorer|file\s*explorer|files?|downloads|desktop|documents|new\s+volume(?:\s+[a-z])?|[a-z]\s+drive|drive\s+[a-z])\b',
            r'^(?:task\s*manager|calculator|notepad|settings|file\s*explorer)$',
            r'^(?:set|turn|change|increase|decrease)\s+(?:the\s+)?(?:volume|brightness)\b',
            r'^(?:mute|unmute)(?:\s+(?:volume|audio|sound|pc|system))?$',
            r'^(?:turn\s+on|turn\s+off|enable|disable)\s+(?:night\s*light|hotspot|mobile\s*hotspot|wifi|wi-fi)\b',
            r'^(?:what\s+is|check|show|get)\s+(?:my|the)?\s*(?:battery|ram|cpu|storage|disk|specs|vitals|wifi|wi-fi)\b',
            r'^(?:battery|system\s+vitals|ram\s+usage|cpu\s+usage)$',
            r'^(?:open|explore)\s+(?:folder\s+)?(?:program\s*files|windows|users|downloads|desktop|documents|ultron)\b',
            r'^(?:open|read)\s+file\b',
            r'^(?:append\s+to|add\s+to|write\s+into)\s+(?:file\s+)?[a-zA-Z0-9_\-\.]+\b',
            r'^(?:save|save\s+file|save\s+document)$',
            r'^(?:replace|change)\s+.*?\s+(?:with|to)\b',
            r'^(?:clear|delete)\s+(?:this|document|all\s+text|last\s+word|word|line)\b',
            r'^(?:undo|redo)(?:\s+that)?$',
            r'^in\s+(?:file\s+)?[a-zA-Z0-9_\-\.]+\s+(?:replace|change|delete|remove|clear)\b',
            r'^(?:delete|remove)\s+(?:the\s+)?(?:file|download)\b',
            r'^(?:organize|clean\s+up)\s+(?:my\s+)?(?:downloads|temp|temporary\s+files)\b',
            r'^(?:lock|shutdown|shut\s+down|restart|reboot)\s+(?:pc|computer|workstation|screen)?$',
        ]
        return any(re.search(p, text) for p in valid_patterns)
