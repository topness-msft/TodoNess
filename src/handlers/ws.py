"""WebSocket handler for live dashboard updates."""

import json
import tornado.websocket

# Connected clients
_clients: set[tornado.websocket.WebSocketHandler] = set()


class TaskWebSocketHandler(tornado.websocket.WebSocketHandler):
    """WebSocket endpoint at /ws for real-time task updates."""

    def check_origin(self, origin):
        return True  # Allow local connections

    def open(self):
        _clients.add(self)

    def on_close(self):
        _clients.discard(self)

    def on_message(self, message):
        # Clients don't send messages; this is a push-only channel
        pass


def broadcast(data: dict):
    """Send a JSON message to all connected WebSocket clients."""
    msg = json.dumps(data)
    dead = []
    for client in _clients:
        try:
            client.write_message(msg)
        except tornado.websocket.WebSocketClosedError:
            dead.append(client)
    for client in dead:
        _clients.discard(client)
