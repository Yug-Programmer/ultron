"""
Ultron File & Folder Assistant
Handles natural language folder navigation, file opening, file reading,
in-editor voice typing/saving, and AI-powered voice editing of editable files.
"""

import os
import re
import shutil
import logging
import subprocess
import pyautogui
import pyperclip

pyautogui.FAILSAFE = False
logger = logging.getLogger("Ultron.FileAssistant")

EDITABLE_EXTENSIONS = {
    ".txt", ".py", ".md", ".json", ".csv", ".log",
    ".yaml", ".yml", ".html", ".css", ".js", ".bat",
    ".ps1", ".ini", ".xml", ".sh", ".env", ".cfg"
}

class FileAssistantTool:
    @staticmethod
    def get_search_roots() -> list:
        user_home = os.path.expanduser("~")
        roots = [
            r"Y:\Ultron",
            os.path.join(user_home, "Desktop"),
            os.path.join(user_home, "Documents"),
            os.path.join(user_home, "Downloads"),
            r"Y:\\",
            r"C:\\"
        ]
        return [r for r in roots if os.path.exists(r)]

    @staticmethod
    def resolve_natural_folder(query: str) -> str:
        """
        Resolves spoken natural language folder requests like:
        - 'open program files in local disk c'
        - 'open program files'
        - 'open windows folder'
        - 'open users folder'
        - 'open ultron folder'
        """
        q = query.lower().strip()
        q = re.sub(r"^(?:open|show|explore|launch)\s+", "", q).strip()
        q = re.sub(r"^(?:the\s+|folder\s+|directory\s+)", "", q).strip()
        q = q.strip(".,?! ")

        # Direct well-known Windows system directories
        well_known = {
            "program files in local disk c": r"C:\Program Files",
            "program files in c drive": r"C:\Program Files",
            "program files in c": r"C:\Program Files",
            "program files (x86)": r"C:\Program Files (x86)",
            "program files x86": r"C:\Program Files (x86)",
            "program files": r"C:\Program Files",
            "windows in c": r"C:\Windows",
            "windows": r"C:\Windows",
            "system32": r"C:\Windows\System32",
            "users in c": r"C:\Users",
            "users": r"C:\Users",
            "ultron": r"Y:\Ultron",
        }
        for alias, path in well_known.items():
            if alias in q:
                if os.path.exists(path):
                    return path

        # Check for pattern: "<subfolder> in <drive_or_parent>"
        # e.g. "program files in local disk c" or "tools in ultron"
        m = re.search(r"^(.*?)\s+in\s+(local\s+disk\s+[a-z]|[a-z]\s+drive|new\s+volume\s+[a-z]|drive\s+[a-z]|ultron|[a-z]:?)$", q)
        if m:
            sub = m.group(1).strip()
            parent_key = m.group(2).strip()

            parent_path = None
            if any(c in parent_key for c in ["c drive", "local disk c", "drive c", "c:"]):
                parent_path = r"C:\\"
            elif any(y in parent_key for y in ["y drive", "new volume y", "drive y", "y:", "ultron"]):
                parent_path = r"Y:\\" if "y" in parent_key else r"Y:\Ultron"

            if parent_path and os.path.exists(parent_path):
                # Search directly in parent
                for item in os.listdir(parent_path):
                    if sub == item.lower() or sub in item.lower():
                        full = os.path.join(parent_path, item)
                        if os.path.isdir(full):
                            return full

        # Check standard user folders
        user_home = os.path.expanduser("~")
        std_folders = {
            "downloads": os.path.join(user_home, "Downloads"),
            "desktop": os.path.join(user_home, "Desktop"),
            "documents": os.path.join(user_home, "Documents"),
            "pictures": os.path.join(user_home, "Pictures"),
            "music": os.path.join(user_home, "Music"),
            "videos": os.path.join(user_home, "Videos"),
        }
        for name, p in std_folders.items():
            if name in q and os.path.exists(p):
                return p

        return None

    @staticmethod
    def open_folder(query: str) -> str:
        """Opens a folder in File Explorer matching query."""
        path = FileAssistantTool.resolve_natural_folder(query)
        if path and os.path.exists(path):
            subprocess.Popen(f'explorer.exe "{path}"', shell=True)
            folder_name = os.path.basename(path) or path
            return f"Opening {folder_name}."
        return None

    @staticmethod
    def find_file(filename_or_keyword: str) -> str:
        """Fast searches for a file across user directories and workspace."""
        clean = filename_or_keyword.lower().strip()
        clean = re.sub(r"^(?:the\s+file\s+|file\s+|open\s+file\s+|open\s+)", "", clean).strip()
        clean = clean.strip(".,?! '\"")

        if not clean:
            return None

        roots = FileAssistantTool.get_search_roots()
        for r in roots:
            direct = os.path.join(r, clean)
            if os.path.isfile(direct):
                return direct

            # Search top 2 levels
            for dirpath, dirnames, filenames in os.walk(r):
                rel = os.path.relpath(dirpath, r)
                if rel != "." and rel.count(os.sep) >= 2:
                    dirnames.clear()
                    continue
                for f in filenames:
                    f_lower = f.lower()
                    if clean == f_lower or clean in f_lower:
                        return os.path.join(dirpath, f)
        return None

    @staticmethod
    def open_file(query: str) -> str:
        """Finds and launches a file with its default Windows application."""
        file_path = FileAssistantTool.find_file(query)
        if file_path and os.path.exists(file_path):
            try:
                os.startfile(file_path)
                return f"Opening {os.path.basename(file_path)}."
            except Exception as e:
                return f"Failed to open {os.path.basename(file_path)}: {e}"
        return None

    @staticmethod
    def read_file(query: str) -> str:
        """Reads content from an editable file."""
        file_path = FileAssistantTool.find_file(query)
        if not file_path:
            return "I could not locate that file on your system, sir."

        _, ext = os.path.splitext(file_path.lower())
        if ext not in EDITABLE_EXTENSIONS:
            return f"The file {os.path.basename(file_path)} is a binary format and cannot be read as plain text."

        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                lines = [line.strip() for line in f.readlines() if line.strip()]
            if not lines:
                return f"{os.path.basename(file_path)} is currently empty."
            preview = " ".join(lines[:4])
            if len(preview) > 200:
                preview = preview[:200] + "..."
            return f"{os.path.basename(file_path)} contains {len(lines)} lines. Here is the beginning: {preview}"
        except Exception as e:
            return f"Failed to read file: {e}"

    @staticmethod
    def append_to_file(filename_or_query: str, text_to_add: str) -> str:
        """Appends text to a file, creating it in Documents or Ultron if missing."""
        file_path = FileAssistantTool.find_file(filename_or_query)
        if not file_path:
            # Create in Ultron workspace by default
            target_name = re.sub(r"[^\w\.\-]", "_", filename_or_query.strip())
            if not any(target_name.endswith(e) for e in EDITABLE_EXTENSIONS):
                target_name += ".txt"
            file_path = os.path.join(r"Y:\Ultron", target_name)

        try:
            with open(file_path, "a", encoding="utf-8") as f:
                f.write("\n" + text_to_add.strip() + "\n")
            return f"Successfully added to {os.path.basename(file_path)}: '{text_to_add[:40]}'."
        except Exception as e:
            return f"Failed to update file: {e}"

    @staticmethod
    def edit_file_with_ai(filename: str, instruction: str, router=None) -> str:
        """
        Uses ModelRouter / Groq to edit an editable file based on spoken instructions.
        """
        file_path = FileAssistantTool.find_file(filename)
        if not file_path:
            return f"I could not locate '{filename}' to edit, sir."

        _, ext = os.path.splitext(file_path.lower())
        if ext not in EDITABLE_EXTENSIONS:
            return f"File '{os.path.basename(file_path)}' is not an editable text file."

        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                current_content = f.read()

            if router and hasattr(router, "_query_groq"):
                system_prompt = (
                    "You are Ultron's automated file editing engine. "
                    "The user wants to edit a file with natural language instructions. "
                    "Return ONLY the updated file content. Do NOT include markdown code blocks, backticks, or explanations."
                )
                prompt = (
                    f"File: {os.path.basename(file_path)}\n"
                    f"Instruction: {instruction}\n\n"
                    f"Current File Content:\n{current_content[:3000]}"
                )
                messages = [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ]
                updated_content = router._query_groq(messages)
                if updated_content:
                    # Clean any residual backticks
                    updated_content = re.sub(r"^```[a-zA-Z]*\n?", "", updated_content)
                    updated_content = re.sub(r"\n?```$", "", updated_content).strip()

                    with open(file_path, "w", encoding="utf-8") as f:
                        f.write(updated_content)
                    return f"Successfully edited {os.path.basename(file_path)} according to your instructions, sir."

            # Fallback if no LLM: simple append
            with open(file_path, "a", encoding="utf-8") as f:
                f.write(f"\n# Added by Ultron:\n{instruction}\n")
            return f"Updated {os.path.basename(file_path)} with: '{instruction}'."
        except Exception as e:
            return f"Failed to edit file: {e}"

    @staticmethod
    def type_into_active_editor(text: str) -> str:
        """Types text directly into whatever editor window is currently focused."""
        try:
            clean = text.strip()
            pyperclip.copy(clean)
            pyautogui.hotkey("ctrl", "v")
            return f"Typed: '{clean[:40]}'."
        except Exception as e:
            return f"Failed to type: {e}"

    @staticmethod
    def save_active_document() -> str:
        """Triggers Ctrl+S in the currently focused window."""
        try:
            pyautogui.hotkey("ctrl", "s")
            return "Document saved, sir."
        except Exception as e:
            return f"Failed to save document: {e}"

    @staticmethod
    def clear_active_editor() -> str:
        """Selects all content and deletes it in whatever active editor or input is focused."""
        try:
            pyautogui.hotkey("ctrl", "a")
            pyautogui.press("backspace")
            return "Cleared content in active window, sir."
        except Exception as e:
            return f"Failed to clear content: {e}"

    @staticmethod
    def delete_in_active_editor(target: str = "word") -> str:
        """Deletes last word, last line, or triggers backspace."""
        try:
            if "line" in target:
                pyautogui.hotkey("shift", "home")
                pyautogui.press("backspace")
                return "Deleted line, sir."
            elif "all" in target or "everything" in target:
                return FileAssistantTool.clear_active_editor()
            else:
                pyautogui.hotkey("ctrl", "backspace")
                return "Deleted word, sir."
        except Exception as e:
            return f"Failed to delete text: {e}"

    @staticmethod
    def undo_in_active_editor() -> str:
        try:
            pyautogui.hotkey("ctrl", "z")
            return "Undone, sir."
        except Exception as e:
            return f"Failed to undo: {e}"

    @staticmethod
    def redo_in_active_editor() -> str:
        try:
            pyautogui.hotkey("ctrl", "y")
            return "Redone, sir."
        except Exception as e:
            return f"Failed to redo: {e}"

    @staticmethod
    def replace_in_active_editor(find_text: str, replace_text: str) -> str:
        """
        Replaces text in any active open application by selecting all, reading clipboard,
        substituting text, and pasting back.
        """
        try:
            import time
            pyautogui.hotkey("ctrl", "a")
            pyautogui.hotkey("ctrl", "c")
            time.sleep(0.08)
            content = pyperclip.paste()
            if not content:
                return "No text was detected in the active window, sir."

            pattern = re.compile(re.escape(find_text.strip()), re.IGNORECASE)
            if not pattern.search(content):
                return f"Could not find '{find_text}' in the active document, sir."

            new_content = pattern.sub(replace_text.strip(), content)
            pyperclip.copy(new_content)
            pyautogui.hotkey("ctrl", "v")
            return f"Replaced '{find_text}' with '{replace_text}', sir."
        except Exception as e:
            return f"Failed to replace text: {e}"

    @staticmethod
    def replace_in_file_on_disk(filename: str, find_text: str, replace_text: str) -> str:
        """Finds and replaces text in a file saved on disk."""
        file_path = FileAssistantTool.find_file(filename)
        if not file_path:
            return f"I could not locate '{filename}' on your system, sir."

        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()

            pattern = re.compile(re.escape(find_text.strip()), re.IGNORECASE)
            if not pattern.search(content):
                return f"Text '{find_text}' was not found in {os.path.basename(file_path)}, sir."

            new_content = pattern.sub(replace_text.strip(), content)
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(new_content)
            return f"Replaced '{find_text}' with '{replace_text}' in {os.path.basename(file_path)}, sir."
        except Exception as e:
            return f"Failed to replace text in file: {e}"

    @staticmethod
    def delete_from_file_on_disk(filename: str, keyword: str) -> str:
        """Deletes lines containing a keyword or deletes file completely if keyword is 'all'."""
        file_path = FileAssistantTool.find_file(filename)
        if not file_path:
            return f"I could not locate '{filename}' on your system, sir."

        if keyword.strip().lower() in ["all", "everything", "all content", "all data"]:
            try:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write("")
                return f"Cleared all data inside {os.path.basename(file_path)}, sir."
            except Exception as e:
                return f"Failed to clear file: {e}"

        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                lines = f.readlines()

            initial_count = len(lines)
            remaining_lines = [l for l in lines if keyword.lower() not in l.lower()]
            deleted_count = initial_count - len(remaining_lines)

            with open(file_path, "w", encoding="utf-8") as f:
                f.writelines(remaining_lines)

            return f"Deleted {deleted_count} lines matching '{keyword}' from {os.path.basename(file_path)}, sir."
        except Exception as e:
            return f"Failed to delete lines from file: {e}"

    @staticmethod
    def delete_file_on_disk(filename: str) -> str:
        """Deletes a file from disk."""
        file_path = FileAssistantTool.find_file(filename)
        if not file_path:
            return f"I could not locate '{filename}' on your system to delete, sir."
        try:
            os.remove(file_path)
            return f"Successfully deleted {os.path.basename(file_path)}, sir."
        except Exception as e:
            return f"Failed to delete file: {e}"
