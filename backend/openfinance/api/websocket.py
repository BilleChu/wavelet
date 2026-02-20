"""
WebSocket Handler for OpenFinance.
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)

router = APIRouter()


class ConnectionManager:
    """Manages WebSocket connections."""

    def __init__(self) -> None:
        self.active_connections: dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket, client_id: str) -> None:
        await websocket.accept()
        self.active_connections[client_id] = websocket

    def disconnect(self, client_id: str) -> None:
        self.active_connections.pop(client_id, None)

    async def send_message(self, client_id: str, message: dict[str, Any]) -> None:
        websocket = self.active_connections.get(client_id)
        if websocket:
            await websocket.send_json(message)


manager = ConnectionManager()


@router.websocket("/chat")
async def websocket_chat(websocket: WebSocket):
    """WebSocket endpoint for real-time chat."""
    client_id = f"client_{datetime.now().strftime('%Y%m%d%H%M%S%f')}"
    await manager.connect(websocket, client_id)

    try:
        while True:
            data = await websocket.receive_text()
            try:
                message = json.loads(data)
            except json.JSONDecodeError:
                await manager.send_message(client_id, {
                    "type": "error",
                    "data": {"error": "Invalid JSON format"},
                })
                continue

            if message.get("type") == "query":
                query_data = message.get("data", {})
                query = query_data.get("query", "")
                
                await manager.send_message(client_id, {
                    "type": "response",
                    "data": {"content": f"收到消息: {query}", "done": True},
                })
            elif message.get("type") == "ping":
                await manager.send_message(client_id, {
                    "type": "pong",
                    "data": {"timestamp": datetime.now().isoformat()},
                })

    except WebSocketDisconnect:
        manager.disconnect(client_id)
