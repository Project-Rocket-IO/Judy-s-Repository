import sqlite3
import os
import random
import re
import json
import spacy
import openai
from faker import Faker
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import generics
from transformers import pipeline
from .models import ChatHistory, TicketList
from .serializers import ChatHistorySerializer

### Files
from .tickets import *

# Define database path
db_path = os.path.join(os.path.dirname(__file__), "chatbot.db")

llm_pipeline = pipeline("text-generation", model="openai-community/gpt2")# Load model directly

# Load spaCy English model
nlp = spacy.load("en_core_web_sm")

# Define keywords for intent classification
create_keywords = {"create", "add", "new", "register", "open"}
update_keywords = {"update", "modify", "edit", "change", "adjust"}

def classify_intent(text):
    doc = nlp(text.lower())  # Process text with spaCy

    # Check for explicit keywords in the text
    for token in doc:
        if token.lemma_ in create_keywords:
            return "CREATE"
        elif token.lemma_ in update_keywords:
            return "UPDATE"

    return "UNKNOWN"

def generate_llm_response(message):
    return llm_pipeline(message, truncation=False, max_length=1000)[0]['generated_text']


class ChatBotAPI(APIView):
    def post(self, request):
        user_message = request.data.get("message")
        session_id = request.session.session_key  # Use Django session ID

        intent = classify_intent(user_message)
        extracted_data = extract_ticket_fields(user_message)
        print(user_message)
        print(session_id)
        print(intent)
        print(extracted_data)

        if "error" in extracted_data:
            return Response({"error": extracted_data["error"]})

        validation_result = validate_ticket_data(extracted_data)
        print(validation_result)
        if "error" in validation_result:
            return Response(validation_result)

        if intent == "CREATE":
            response = create_ticket(validation_result["ticket_data"])
        elif intent == "UPDATE":
            response = update_ticket(validation_result["ticket_data"], session_id)
        else:
            response = {"error": "Invalid request. Specify 'create' or 'update'."}

        return Response(response)

class ChatHistoryListCreate(generics.ListCreateAPIView):
    queryset = ChatHistory.objects.all()
    serializer_class = ChatHistorySerializer
