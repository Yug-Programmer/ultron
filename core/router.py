"""
Multi-Model Fallback Router & Knowledge Grounding Engine
Routes conversation through Tier-1 Cloud (Groq, Gemini), Tier-2 Local (Ollama),
and injects real-time DuckDuckGo web search when current world facts are needed.
"""

import os
import re
import json
import random
import logging
import requests
from tools.web_search import WebSearchTool

logger = logging.getLogger("Ultron.ModelRouter")

class ModelRouter:
    def __init__(self, config: dict):
        self.config = config
        self.models_cfg = config.get("models", {})
        self.assistant_cfg = config.get("assistant", {})
        self.system_prompt = self.assistant_cfg.get(
            "system_prompt",
            "You are Ultron, a decisive, intelligent AI assistant. Keep responses natural, concise, and direct."
        )

    def _should_search_web(self, query: str) -> bool:
        """Heuristic check if query requires fresh real-time web facts."""
        q = query.lower().strip()
        search_patterns = [
            r"^what (?:is|are|was|were)\b",
            r"^who (?:is|was|are)\b",
            r"^where (?:is|are)\b",
            r"^why (?:is|are|does|did)\b",
            r"^how (?:to|does|do|can)\b",
            r"\bweather in\b",
            r"\bprice of\b",
            r"\blatest news\b",
            r"^search\b"
        ]
        return any(re.search(p, q) for p in search_patterns)

    def _get_api_key(self, provider: str, env_var: str) -> str:
        """Retrieves API key from config.yaml or environment variables."""
        cfg_key = self.models_cfg.get(provider, {}).get("api_key", "")
        if cfg_key and not cfg_key.startswith("your_"):
            return cfg_key
        return os.environ.get(env_var, "")

    def _query_groq(self, messages: list) -> str:
        api_key = self._get_api_key("groq", "GROQ_API_KEY")
        if not api_key:
            return None

        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": self.models_cfg.get("groq", {}).get("model", "llama-3.3-70b-versatile"),
            "messages": messages,
            "temperature": 0.6,
            "max_tokens": 400
        }

        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=12)
            if resp.status_code == 200:
                data = resp.json()
                raw = data["choices"][0]["message"]["content"].strip()
                raw = re.sub(r"<think>.*?</think>", "", raw, flags=re.DOTALL)
                raw = re.sub(r"\*\*Reasoning Summary\*\*.*?\n\n", "", raw, flags=re.DOTALL)
                raw = raw.replace("*", "").replace("#", "").strip()
                return raw
            logger.warning(f"Groq returned status {resp.status_code}: {resp.text}")
        except Exception as e:
            logger.warning(f"Groq API call failed: {e}")
        return None

    def _query_openrouter(self, messages: list) -> str:
        """Queries OpenRouter free tier models (:free)."""
        api_key = self._get_api_key("openrouter", "OPENROUTER_API_KEY")
        if not api_key:
            return None

        url = "https://openrouter.ai/api/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/ultron-ai",
            "X-Title": "Ultron Assistant"
        }
        model = self.models_cfg.get("openrouter", {}).get("model", "meta-llama/llama-3.3-70b-instruct:free")
        payload = {
            "model": model,
            "messages": messages,
            "temperature": 0.6,
            "max_tokens": 400
        }

        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=8)
            if resp.status_code == 200:
                data = resp.json()
                return data["choices"][0]["message"]["content"].strip()
            logger.warning(f"OpenRouter returned status {resp.status_code}: {resp.text}")
        except Exception as e:
            logger.warning(f"OpenRouter API call failed: {e}")
        return None

    def _query_gemini(self, messages: list) -> str:
        api_key = self._get_api_key("gemini", "GEMINI_API_KEY")
        if not api_key:
            return None

        model_name = self.models_cfg.get("gemini", {}).get("model", "gemini-2.5-flash")
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
        
        # Format messages for Gemini API
        contents = []
        for m in messages:
            role = "user" if m["role"] in ["user", "system"] else "model"
            contents.append({"role": role, "parts": [{"text": m["content"]}]})

        try:
            resp = requests.post(url, json={"contents": contents}, timeout=7)
            if resp.status_code == 200:
                data = resp.json()
                return data["candidates"][0]["content"]["parts"][0]["text"].strip()
            logger.warning(f"Gemini returned status {resp.status_code}: {resp.text}")
        except Exception as e:
            logger.warning(f"Gemini API call failed: {e}")
        return None

    def _query_ollama(self, messages: list) -> str:
        """Local offline LLM fallback via Ollama."""
        base_url = self.models_cfg.get("ollama", {}).get("base_url", "http://localhost:11434")
        model = self.models_cfg.get("ollama", {}).get("model", "qwen2.5:7b")

        url = f"{base_url}/api/chat"
        payload = {
            "model": model,
            "messages": messages,
            "stream": False
        }

        try:
            resp = requests.post(url, json=payload, timeout=8)
            if resp.status_code == 200:
                data = resp.json()
                return data.get("message", {}).get("content", "").strip()
        except Exception as e:
            logger.debug(f"Local Ollama call failed: {e}")
        return None

    def generate_response(self, user_prompt: str, screen_context: dict = None) -> str:
        """
        Processes prompt with web grounding, screen context injection, and tiered model failover.
        """
        context_additions = []

        # 1. Screen Context Injection
        if screen_context and screen_context.get("title"):
            title = screen_context.get("title")
            process = screen_context.get("process")
            context_additions.append(f"Active foreground application: '{title}' (Process: {process}).")

        # 2. Live Web Grounding
        if self._should_search_web(user_prompt):
            logger.info(f"[Router] Query requires live data. Executing web search...")
            search_results = WebSearchTool.search(user_prompt, max_results=2)
            if search_results:
                context_additions.append(f"Real-Time Web Search Context:\n{search_results[:800]}")

        # Assemble system instruction
        system_text = self.system_prompt
        if context_additions:
            system_text += "\n\n" + "\n\n".join(context_additions)

        messages = [
            {"role": "system", "content": system_text},
            {"role": "user", "content": user_prompt}
        ]

        # Tier 1: Fast Cloud LLM (Groq)
        ans = self._query_groq(messages)
        if ans:
            return ans

        # Tier 1 Fallback: OpenRouter Free Models
        ans = self._query_openrouter(messages)
        if ans:
            return ans

        # Tier 1 Fallback: Google Gemini
        ans = self._query_gemini(messages)
        if ans:
            return ans

        # Tier 2 Fallback: Local Offline Ollama
        ans = self._query_ollama(messages)
        if ans:
            return ans

        # Tier 3: Intelligent Grounded & Conversational Fallback
        if self._should_search_web(user_prompt):
            logger.info(f"[Router] Answering informational query via live web search...")
            search_res = WebSearchTool.search(user_prompt, max_results=2)
            if search_res and "No relevant web results" not in search_res:
                lines = [l for l in search_res.splitlines() if l.startswith("Summary:")]
                if lines:
                    summary = " ".join([l.replace("Summary:", "").strip() for l in lines])
                    # Clean ellipses and brackets
                    summary = re.sub(r"\[.*?\]", "", summary).strip()
                    return f"Based on live reports: {summary[:240]}."
                return f"Here is what I found: {search_res[:200]}."

        # Conversational small talk and banter
        chat_responses = [
            f"Understood, sir. I'm keeping all background systems tuned while you work.",
            f"I hear you, sir. Let me know if you need me to adjust your hardware or pull up files.",
            f"Acknowledged, sir. Standing by whenever you're ready for the next task.",
            f"Understood. All diagnostics are green and waiting on your command, sir.",
            f"Right with you, sir. Just say the word."
        ]
        return random.choice(chat_responses)
