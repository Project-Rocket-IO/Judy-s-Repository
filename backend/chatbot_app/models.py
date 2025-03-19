from django.db import models

class User(models.Model):
    name = models.CharField(max_length=255, unique=True)
    age = models.IntegerField()
    gender = models.CharField(max_length=10)

    def __str__(self):
        return self.name

class ChatHistory(models.Model):
    user_input = models.TextField()
    bot_response = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Chat at {self.timestamp}"