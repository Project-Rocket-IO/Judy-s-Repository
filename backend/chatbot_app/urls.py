from django.urls import path
from .views import ChatBotAPI, ChatHistoryListCreate

urlpatterns = [
    path("", ChatBotAPI.as_view(), name="chatbot"),
    path("history/", ChatHistoryListCreate.as_view(), name="chat-history"),
]
