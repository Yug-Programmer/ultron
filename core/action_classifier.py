"""
Ultron Neural Action Classifier
Uses Groq LPU LLM to classify arbitrary human speech into structured OS actions,
enabling Siri-grade conversational control without rigid regex rules.
"""

import json
import logging
import requests
from tools.file_assistant import FileAssistantTool
from tools.system_windows import WindowsSystemTool

logger = logging.getLogger("Ultron.ActionClassifier")

SYSTEM_PROMPT = (
    "You are Ultron's Neural Action Classifier. Your job is to convert natural spoken commands "
    "into an executable JSON action object.\n\n"
    "Supported actions:\n"
    "1. {\"action\": \"type\", \"text\": \"<text_to_type>\"}\n"
    "   - When user wants to write, type, or dictate text into whatever app/note is open\n"
    "2. {\"action\": \"replace_in_app\", \"find\": \"<find_text>\", \"replace\": \"<replace_text>\"}\n"
    "   - When user wants to replace/change text in the active open document or note\n"
    "3. {\"action\": \"clear_in_app\"}\n"
    "   - When user wants to clear, wipe, or delete all text in the active window\n"
    "4. {\"action\": \"delete_in_app\", \"scope\": \"word\" | \"line\"}\n"
    "   - When user wants to delete the last word or the line\n"
    "5. {\"action\": \"undo\"} / {\"action\": \"redo\"}\n"
    "6. {\"action\": \"save\"}\n"
    "7. {\"action\": \"open_app\", \"app\": \"<app_name>\"}\n"
    "   - When user wants to launch an application (e.g., notepad, word, excel, chrome, calculator)\n"
    "8. {\"action\": \"open_folder\", \"folder\": \"<folder_or_path>\"}\n"
    "   - When user wants to open a folder or drive (e.g., program files, C drive, Y drive, downloads)\n"
    "9. {\"action\": \"modify_file\", \"file\": \"<filename>\", \"instruction\": \"<instruction>\"}\n"
    "   - When user wants to edit, update, or change a specific file on disk\n"
    "10. {\"action\": \"delete_file\", \"file\": \"<filename>\"}\n"
    "   - When user wants to delete a specific file from disk\n"
    "11. {\"action\": \"chat\", \"query\": \"<user_query>\"}\n"
    "   - For general conversation, questions, weather, news, explanations, or facts\n\n"
    "Rules:\n"
    "- Return ONLY the raw JSON object.\n"
    "- Do NOT include any markdown code blocks, backticks, or explanation."
)

class NeuralActionClassifier:
    def __init__(self, api_key: str, model: str = "qwen/qwen3.8-27b"):
        self.api_key = api_key
        self.model = model

    def classify_and_execute(self, user_command: str, router=None) -> str:
        """
        Interprets natural language using the AI model and executes the corresponding action.
        Returns a human-readable confirmation string, or None if action is 'chat'.
        """
        if not self.api_key:
            return None

        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_command}
            ],
            "temperature": 0.0,
            "max_tokens": 120
        }

        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=4)
            if resp.status_code != 200:
                logger.debug(f"Action classifier HTTP {resp.status_code}")
                return None

            raw_text = resp.json()["choices"][0]["message"]["content"].strip()
            # Clean any backticks if present
            clean_json = raw_text.replace("```json", "").replace("```", "").strip()
            data = json.loads(clean_json)

            action = data.get("action")
            logger.info(f"[NeuralAction] Classified '{user_command}' -> {data}")

            if action == "type":
                text = data.get("text", "")
                if text:
                    return FileAssistantTool.type_into_active_editor(text)

            elif action == "replace_in_app":
                find = data.get("find", "")
                rep = data.get("replace", "")
                if find:
                    return FileAssistantTool.replace_in_active_editor(find, rep)

            elif action == "clear_in_app":
                return FileAssistantTool.clear_active_editor()

            elif action == "delete_in_app":
                scope = data.get("scope", "word")
                return FileAssistantTool.delete_in_active_editor(scope)

            elif action == "undo":
                return FileAssistantTool.undo_in_active_editor()

            elif action == "redo":
                return FileAssistantTool.redo_in_active_editor()

            elif action == "save":
                return FileAssistantTool.save_active_document()

            elif action == "open_app":
                app = data.get("app", "")
                if app:
                    return WindowsSystemTool.launch_application(app)

            elif action == "open_folder":
                folder = data.get("folder", "")
                if folder:
                    return FileAssistantTool.open_folder(folder) or WindowsSystemTool.launch_application(folder)

            elif action == "modify_file":
                fname = data.get("file", "")
                instr = data.get("instruction", "")
                if fname and instr:
                    return FileAssistantTool.edit_file_with_ai(fname, instr, router)

            elif action == "delete_file":
                fname = data.get("file", "")
                if fname:
                    return FileAssistantTool.delete_file_on_disk(fname)

            elif action == "chat":
                # Let ModelRouter generate a rich conversational answer
                return None

        except Exception as e:
            logger.debug(f"Action classification notice: {e}")

        return None
