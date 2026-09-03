# ⚡ Ultron: Autonomous AI Assistant for Windows & Android

> **"Ultron online and operational."**

An autonomous, Jarvis-like AI assistant tailored for Windows and Android. Features a minimalist Siri-style border glow UI, ultra-low-latency local voice detection, dynamic microphone auto-yielding, screen context awareness with proactive assistance, tiered model failover, and hardware/OS automation.

---

## 🌟 Key Features

1. **Siri-Style Border Glow Overlay**:
   - Zero bulky windows. An animated neon gradient border pulses along your screen edges.
   - Built with PyQt6 and Windows API extended styles (`WS_EX_TRANSPARENT | WS_EX_LAYERED | WS_EX_TOOLWINDOW`) ensuring complete hardware mouse click-through for zero disruption during work or gaming.
   - Color cues:
     - **Cyan Neon**: Listening to your voice.
     - **Electric Purple**: Reasoning / Grounding with web search.
     - **Warm Amber**: Proactive assistance prompt.
     - **Emerald Green**: Executing OS or GUI task.

2. **Ultra-Low-Latency Local Listening**:
   - Powered by `faster-whisper` (CTranslate2 INT8 quantized model) + `Silero VAD`.
   - Transcribes spoken audio locally in under 300ms, eliminating the lag, truncation, and inaccuracy of generic Python speech recognition.

3. **Dynamic Microphone Auto-Yielding**:
   - Automatically detects when communication or recording software (`Discord`, `Zoom`, `Teams`, `OBS`, `WhatsApp`, `Skype`, etc.) requires microphone access.
   - Instantly relinquishes hardware input to prevent audio conflicts or lockouts, then seamlessly resumes background listening when your call ends.

4. **Screen & Task Awareness + Proactive Intervention**:
   - Tracks active foreground applications and detects error dialogs, crashes, or user friction in real time.
   - **Proactive Help**: When stuck on an error, Ultron's border glows amber and it speaks: *"I noticed an error dialog in [App]. Would you like me to resolve this for you?"*
   - Say *"Yes"* or *"Fix it"*, and Ultron dismisses or handles the task autonomously.

5. **Multi-Model Intelligence & Offline Resilience**:
   - **Tier 0 (Deterministic Matcher)**: Instant (<1ms) offline execution of volume, app launch/close, file cleanup, and telemetry.
   - **Tier 1 (Free Cloud LLMs)**: High-speed inference using Groq (Llama 3.3 70B @ 250+ tokens/s) or Google Gemini Flash free tier.
   - **Tier 2 (Local Offline LLM)**: 100% offline local intelligence via Ollama (`qwen2.5:7b` or `llama3.2:3b`).
   - **Live Web Grounding**: Integrated free DuckDuckGo search tool provides real-time world events beyond training cutoffs.

6. **Direct OS & Hardware Control**:
   - **System Telemetry**: Real-time CPU, RAM, Disk, and Battery diagnostics.
   - **App Management**: Launch and close apps (`Chrome`, `VS Code`, `Task Manager`, `Notepad`, etc.).
   - **Audio & Media**: Volume adjustment, mute/unmute.
   - **System Care**: Temporary file cleanup and Windows Defender security scan.

7. **Android Companion Pairing**:
   - WebSocket bridge on port `8765`.
   - Run the companion client (`mobile/android_bridge/client.py`) on your Android device (inside Termux) to pair telemetry, notifications, and remote actions.

---

## 🚀 Quick Start

### 1. Launch Ultron
Double-click `run_ultron.bat` or run:
```bash
uv run python main.py
```

### 2. Spoken Commands
Speak **"Hey Ultron"** or **"Ultron"**, followed by your command:

| Spoken Command | Action Executed |
| :--- | :--- |
| *"Ultron, what is the battery and system status?"* | Reports CPU load, RAM usage, free disk space, and battery % |
| *"Ultron, clean temp files"* | Cleans Windows temporary cache and reports freed MBs |
| *"Ultron, set volume to 40"* | Adjusts master volume to 40% |
| *"Ultron, mute audio"* | Mutes master audio |
| *"Ultron, open Chrome"* | Launches Google Chrome |
| *"Ultron, close Task Manager"* | Terminates running taskmgr processes |
| *"Ultron, run a security scan"* | Triggers Windows Defender quick antivirus scan |
| *"Ultron, show desktop"* | Toggles desktop view (Win+D) |
| *"Ultron, what happened today in technology news?"* | Queries DuckDuckGo and synthesizes up-to-date live news |

---

## ⚙️ Configuration (`config.yaml`)

Customize wake words, sensitivity, TTS voice, and models in `config.yaml`:
```yaml
assistant:
  wake_word: "ultron"

audio:
  stt_model: "base.en"                  # 'tiny.en' (fastest) or 'base.en' (balanced)
  tts_voice: "en-US-ChristopherNeural"  # Microsoft Neural voice

models:
  groq:
    enabled: true
    model: "llama-3.3-70b-versatile"
  gemini:
    enabled: true
    model: "gemini-2.5-flash"
  ollama:
    enabled: true
    model: "qwen2.5:7b"
```

To enable free cloud LLMs, simply set the environment variable:
```powershell
set GROQ_API_KEY=your_free_groq_key
# or
set GEMINI_API_KEY=your_free_gemini_key
```
*(If no API keys are provided, Ultron runs in local offline mode with full hardware and deterministic command support).*

---

## 📱 Pairing with Android

1. Ensure your PC and Android phone are on the same Wi-Fi network.
2. Find your PC's local IP (run `ipconfig`).
3. On Android (inside **Termux**):
   ```bash
   pkg install python termux-api
   pip install websockets
   python client.py <YOUR_PC_IP>
   ```
4. Ultron is now linked to your mobile device!
