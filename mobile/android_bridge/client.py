"""
Ultron Android Client Companion (Termux / Python)
Run this script on Android (inside Termux) to pair your phone with Ultron on PC.
Supports battery telemetry, torch toggles, notifications, and vibration via Termux:API.
"""

import sys
import json
import time
import asyncio
import subprocess
import websockets

def run_termux_api(command: list) -> str:
    """Executes a termux-api command if available."""
    try:
        res = subprocess.run(command, capture_output=True, text=True, check=True)
        return res.stdout
    except Exception as e:
        return ""

async def android_client_loop(server_ip: str, port: int = 8765):
    uri = f"ws://{server_ip}:{port}"
    print(f"Connecting to Ultron at {uri}...")

    while True:
        try:
            async with websockets.connect(uri) as ws:
                print("Successfully paired with Ultron PC!")

                async def send_telemetry():
                    while True:
                        # Fetch battery status via termux-battery-status if available
                        raw_batt = run_termux_api(["termux-battery-status"])
                        payload = {}
                        if raw_batt:
                            try:
                                payload = json.loads(raw_batt)
                            except:
                                pass
                        
                        await ws.send(json.dumps({
                            "type": "telemetry",
                            "payload": payload
                        }))
                        await asyncio.sleep(15)

                async def receive_commands():
                    async for message in ws:
                        try:
                            cmd = json.loads(message)
                            action = cmd.get("action")
                            payload = cmd.get("payload", {})
                            print(f"[Ultron Command] Action: {action}, Payload: {payload}")

                            if action == "vibrate":
                                run_termux_api(["termux-vibrate", "-d", str(payload.get("duration", 500))])
                            elif action == "torch":
                                state = "on" if payload.get("state") else "off"
                                run_termux_api(["termux-torch", state])
                            elif action == "toast":
                                run_termux_api(["termux-toast", str(payload.get("text", "Ultron Alert"))])
                        except Exception as e:
                            print(f"Error executing command: {e}")

                await asyncio.gather(send_telemetry(), receive_commands())

        except Exception as e:
            print(f"Connection lost ({e}). Reconnecting in 5s...")
            await asyncio.sleep(5)

if __name__ == "__main__":
    ip = sys.argv[1] if len(sys.argv) > 1 else "192.168.1.100"
    print(f"Starting Ultron Android Bridge for host: {ip}")
    asyncio.run(android_client_loop(ip))
