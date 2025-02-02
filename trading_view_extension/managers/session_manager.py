from config import logger

class SessionManager:
    def __init__(self):
        self.connections = {}  # Dictionary to store {websocket_id: websocket}
        logger.info("SessionManager initialized.")

    def register_websocket(self, websocket_id, websocket):
        """
        Add a WebSocket connection to the manager.
        
        Args:
            websocket_id: The unique identifier for the WebSocket.
            websocket: The WebSocket connection object.
        """
        self.connections[str(websocket_id)] = websocket
        logger.info(f"Registered WebSocket: {websocket} with ID: {websocket_id}")
        return websocket_id

    def get_websocket(self, websocket_id):
        """
        Retrieve a WebSocket connection from the manager.
        
        Args:
            websocket_id: The unique identifier for the WebSocket.
        
        Returns:
            The WebSocket connection object, or None if not found.
        """
        logger.info(f"Connections: {self.connections}")
        return self.connections.get(str(websocket_id))  # Use .get() to avoid KeyError

    def remove_websocket(self, websocket_id):
        """
        Remove a WebSocket connection from the manager.
        
        Args:
            websocket_id: The unique identifier for the WebSocket.
        """
        if str(websocket_id) in self.connections:
            logger.info(f"Removing WebSocket: {self.connections[str(websocket_id)]} with ID: {websocket_id}")
            del self.connections[str(websocket_id)]
