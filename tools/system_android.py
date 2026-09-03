"""
Android Companion Bridge
WebSocket server enabling bi-directional communication between Ultron on PC
and an Android companion client (Termux:API or Android app).
"""

import json
import asyncio
import logging
import threading
import websockets

logger = logging.getLogger("Ultron.AndroidBridge")

class AndroidBridge:
    def __init__(self, host: str = "0.0.0.0", port: int = 8765, auth_token: str = "ultron_secure_sync"):
        self.host = host
        self.port = port
        self.auth_token = auth_token
        
        self.connected_clients = set()
        self.last_device_telemetry = {}
        self.is_running = False
        self._server = None
        self._loop = None

    async def _handle_connection(self, websocket):
        logger.info(f"[AndroidBridge] New connection from {websocket.remote_address}")
        self.connected_clients.add(websocket)
        try:
            async for message in websocket:
                try:
                    data = json.loads(message)
                    msg_type = data.get("type", "")
                    
                    if msg_type == "telemetry":
                        self.last_device_telemetry = data.get("payload", {})
                    elif msg_type == "notification":
                        logger.info(f"[Android] Notification from phone: {data.get('payload')}")
                except Exception as e:
                    logger.debug(f"Invalid packet from client: {e}")
        except websockets.exceptions.ConnectionClosed:
            pass
        finally:
            self.connected_clients.remove(websocket)
            logger.info("[AndroidBridge] Client disconnected.")

    async def send_command_to_device(self, action: str, payload: dict = None) -> dict:
        """Sends a remote command to the paired Android device."""
        if not self.connected_clients:
            return {"status": "error", "message": "No Android device currently connected."}

        message = json.dumps({
            "action": action,
            "payload": payload or {}
        })

        # Broadcast to all connected mobile clients
        results = []
        for client in list(self.connected_clients):
            try:
                await client.send(message)
                results.append(True)
            except Exception as e:
                logger.error(f"Failed to send to client: {e}")
                results.append(False)

        return {"status": "success", "sent": sum(results)}

    def get_mobile_status(self) -> dict:
        """Returns the status of paired Android devices."""
        return {
            "connected_devices": len(self.connected_clients),
            "telemetry": self.last_device_telemetry
        }

    def _run_server(self):
        async def _serve():
            logger.info(f"Android Bridge WebSocket listening on ws://{self.host}:{self.port}")
            async with websockets.serve(self._handle_connection, self.host, self.port) as server:
                self._server = server
                await asyncio.Future()  # Run forever

        try:
            asyncio.run(_serve())
        except Exception as e:
            logger.debug(f"Android Bridge server stopped: {e}")

    def start(self):
        if self.is_running:
            return
        self.is_running = True
        thread = threading.Thread(target=self._run_server, daemon=True)
        thread.start()

    def stop(self):
        self.is_running = False
        if self._server:
            try:
                self._server.close()
            except Exception:
                pass
