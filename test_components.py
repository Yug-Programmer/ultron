"""
Ultron Verification & Test Suite
Validates each subsystem: Fast STT imports, Screen Capture, System Telemetry,
Web Search, Fast Intent Filtering, and Model Router.
"""

import os
import sys
import logging
import yaml

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

def test_system_vitals():
    print("\n--- 1. Testing System & Hardware Telemetry ---")
    from tools.system_windows import WindowsSystemTool
    vitals = WindowsSystemTool.get_system_vitals()
    print(f"System Vitals: {vitals}")
    assert "cpu_usage_percent" in vitals
    assert "ram_percent" in vitals
    assert "disk_free_gb" in vitals
    print("[PASS] System vitals test passed.")

def test_screen_monitor():
    print("\n--- 2. Testing Screen Monitor & Window Tracker ---")
    from vision.screen_monitor import ScreenMonitor
    monitor = ScreenMonitor()
    info = monitor.get_active_window_info()
    print(f"Active Window Info: {info}")
    
    screenshot = monitor.capture_screenshot()
    if screenshot:
        print(f"Screenshot Captured: {screenshot.size} format: {screenshot.mode}")
        assert screenshot.size[0] > 0 and screenshot.size[1] > 0
        print("[PASS] Screen capture test passed.")
    else:
        print("! Screen capture returned None (may be headless environment).")

def test_web_search():
    print("\n--- 3. Testing Real-Time DuckDuckGo Web Search ---")
    from tools.web_search import WebSearchTool
    results = WebSearchTool.search("latest technology news", max_results=2)
    print(f"Search Results Sample:\n{results[:300]}...")
    assert len(results) > 20
    print("[PASS] Web search test passed.")

def test_fast_intent_filter():
    print("\n--- 4. Testing Fast Deterministic Intent Filter ---")
    from core.intent_filter import FastIntentFilter
    res = FastIntentFilter.evaluate("what is the battery and system vitals")
    print(f"Query 'what is the battery and system vitals' -> Response: {res}")
    assert res is not None
    print("[PASS] Intent filter test passed.")

def test_model_router():
    print("\n--- 5. Testing Model Router Fallback ---")
    from core.router import ModelRouter
    with open("config.yaml", "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    router = ModelRouter(cfg)
    resp = router.generate_response("Hello Ultron")
    print(f"Router fallback response: {resp}")
    assert len(resp) > 5
    print("[PASS] Model router fallback test passed.")

def test_stt_import():
    print("\n--- 6. Testing faster-whisper CTranslate2 Import ---")
    import faster_whisper
    print(f"faster-whisper version: {faster_whisper.__version__}")
    print("[PASS] faster-whisper import passed.")

def main():
    print("Starting Ultron System Verification...")
    test_stt_import()
    test_system_vitals()
    test_screen_monitor()
    test_web_search()
    test_fast_intent_filter()
    test_model_router()
    print("\n==========================================")
    print("ALL ULTRON SUBSYSTEM TESTS PASSED!")
    print("==========================================")

if __name__ == "__main__":
    main()
