from typing import List, Dict
from fastapi import WebSocket

class ConnectionManager:
    def __init__(self):
        # forum_id -> List[WebSocket]
        self.active_connections: Dict[int, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, forum_id: int):
        try:
            await websocket.accept()
            if forum_id not in self.active_connections:
                self.active_connections[forum_id] = []
            self.active_connections[forum_id].append(websocket)
            print(f"WS Connected: Forum {forum_id}") # Log connection
        except Exception as e:
            print(f"WS Connect Error: {e}")
            raise

    async def disconnect(self, websocket: WebSocket, forum_id: int):
        if forum_id in self.active_connections:
            if websocket in self.active_connections[forum_id]:
                self.active_connections[forum_id].remove(websocket)
            if not self.active_connections[forum_id]:
                del self.active_connections[forum_id]
        print(f"WS Disconnected: Forum {forum_id}") # Log disconnection

    async def broadcast(self, forum_id: int, message: dict):
        if forum_id in self.active_connections:
            for connection in self.active_connections[forum_id]:
                await connection.send_json(message)

manager = ConnectionManager()
