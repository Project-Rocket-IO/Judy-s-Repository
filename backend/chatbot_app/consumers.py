import json
from channels.generic.websocket import WebsocketConsumer

class ChatConsumer(WebsocketConsumer):
    def connect(self):
        self.accept()

    def receive(self, text_data):
        data = json.loads(text_data)
        message = data["message"]
        response = f"Echo: {message}"
        self.send(json.dumps({"response": response}))
