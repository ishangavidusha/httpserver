class EventSource:
    def __init__(self):
        self.clients = set()
        self.events = {}

    def add_client(self, client):
        self.clients.add(client)

    def remove_client(self, client):
        self.clients.remove(client)

    def add_event(self, event_name, data):
        self.events[event_name] = data
        self.broadcast(event_name, data)

    def broadcast(self, event_name, data):
        message = self.format_sse_message(event_name, data)
        disconnected_clients = set()
        for client in self.clients:
            try:
                client.send(message)
            except Exception:
                disconnected_clients.add(client)

        for client in disconnected_clients:
            self.remove_client(client)

    @staticmethod
    def format_sse_message(event, data):
        return f"event: {event}\ndata: {data}\n\n".encode("utf-8")