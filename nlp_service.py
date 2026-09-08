"""
Ultron Local Python NLP Companion Service
Provides ultra-fast (<5ms) local linguistic parsing, multilingual tokenization,
and entity/slot extraction for Windows and Android clients.
"""

import json
import re
from http.server import HTTPServer, BaseHTTPRequestHandler

PORT = 8766

class NlpHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path != "/nlp/analyze":
            self.send_response(404)
            self.end_headers()
            return

        content_length = int(self.headers.get("Content-Length", 0))
        post_data = self.rfile.read(content_length)
        
        try:
            req = json.loads(post_data.decode("utf-8"))
            raw_text = req.get("text", "").strip()
            last_app = req.get("last_app")
            last_file = req.get("last_file")

            result = self.analyze_nlp(raw_text, last_app, last_file)
            
            if result:
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps(result).encode("utf-8"))
            else:
                self.send_response(204)  # No content; defer to cloud neural NLP
                self.end_headers()

        except Exception as e:
            self.send_response(500)
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(e)}).encode("utf-8"))

    def analyze_nlp(self, text: str, last_app: str = None, last_file: str = None):
        t = text.lower().strip()
        
        # Multilingual Language Detection
        hindi_keywords = ["kholo", "likho", "badal", "karo", "kitni", "hai", "batao", "isko", "usme", "isme", "se"]
        is_hindi = any(re.search(rf"\b{k}\b", t) for k in hindi_keywords)
        lang = "hinglish" if is_hindi else "en"

        # 1. Hindi / Hinglish: "isme <text> likho" / "write <text> in this"
        m_hi_write = re.search(r"(?:isme|usme|is me)?\s*(.*?)\s*(?:likho|type karo)", t)
        if is_hindi and m_hi_write and m_hi_write.group(1):
            return {"action": "type", "text": m_hi_write.group(1).strip(), "language": lang, "reply_language": lang}

        # 2. Hindi / Hinglish: "<find> ko <replace> se badlo / replace karo / change karo"
        m_hi_replace = re.search(r"(.*?)\s+ko\s+(.*?)\s+se\s+(?:badal\s+do|badlo|replace\s+karo|change\s+karo)", t)
        if is_hindi and m_hi_replace:
            return {"action": "replace_in_app", "find": m_hi_replace.group(1).strip(), "replace": m_hi_replace.group(2).strip(), "language": lang, "reply_language": lang}

        # 3. Hindi / Hinglish: "<app> kholo / open karo"
        m_hi_open = re.search(r"(.*?)\s+(?:kholo|open\s+karo|start\s+karo)", t)
        if is_hindi and m_hi_open:
            app_target = m_hi_open.group(1).strip()
            if any(d in app_target for d in ["disk", "drive", "c", "y", "folder"]):
                return {"action": "open_folder", "folder": app_target, "language": lang, "reply_language": lang}
            return {"action": "open_app", "app": app_target, "language": lang, "reply_language": lang}

        # 4. Hindi / Hinglish: "isko save karo / save kar do"
        if is_hindi and re.search(r"(?:isko|file|ise)?\s*save\s*(?:karo|kar do)", t):
            return {"action": "save", "language": lang, "reply_language": lang}

        # 5. Hindi / Hinglish: "battery kitni hai / battery check karo"
        if is_hindi and ("battery" in t or "vitals" in t):
            return {"action": "vitals", "language": lang, "reply_language": lang}

        # 6. English Quick Patterns
        if re.search(r"^(?:type|write)\s+(.*)", t):
            clean = re.sub(r"^(?:type|write)\s+", "", t)
            clean = re.sub(r"\s+(?:in\s+this.*|into\s+this.*|in\s+note.*)$", "", clean)
            return {"action": "type", "text": clean.strip(), "language": "en", "reply_language": "en"}

        m_en_rep = re.search(r"replace\s+(.*?)\s+with\s+(.*?)(?:\s+in\s+this.*)?$", t)
        if m_en_rep:
            return {"action": "replace_in_app", "find": m_en_rep.group(1).strip(), "replace": m_en_rep.group(2).strip(), "language": "en", "reply_language": "en"}

        if t in ["clear this", "clear document", "delete all text"]:
            return {"action": "clear_in_app", "language": "en", "reply_language": "en"}

        if t in ["undo", "undo that"]:
            return {"action": "undo", "language": "en", "reply_language": "en"}

        if t in ["save", "save file", "save document"]:
            return {"action": "save", "language": "en", "reply_language": "en"}

        if "battery" in t or "vitals" in t:
            return {"action": "vitals", "language": "en", "reply_language": "en"}

        # Pronoun resolution: e.g. "add hello to it" -> resolves 'it' to last_file
        if last_file and re.search(r"\b(it|that file|isko|usme)\b", t):
            instruction = re.sub(r"\b(it|that file|isko|usme)\b", "", t).strip()
            return {"action": "modify_file", "file": last_file, "instruction": instruction, "language": lang, "reply_language": lang}

        return None

    def log_message(self, format, *args):
        pass  # Quiet logs for high performance

def run_server():
    server = HTTPServer(("127.0.0.1", PORT), NlpHandler)
    print(f"[Ultron NLP] Local Python NLP Microservice active on http://127.0.0.1:{PORT}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.server_close()

if __name__ == "__main__":
    run_server()
