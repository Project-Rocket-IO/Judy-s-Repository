import sqlite3
import os
import random
import re
from faker import Faker
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import generics
from transformers import pipeline
from .models import ChatHistory
from .serializers import ChatHistorySerializer

# Define database path
db_path = os.path.join(os.path.dirname(__file__), "chatbot.db")
fake = Faker()
llm_pipeline = pipeline("text-generation", model="openai-community/gpt2")# Load model directly

def generate_synthetic_users(n=30):
    genders = ["male", "female"]
    users = []
    for _ in range(n):
        name = fake.first_name().lower()
        age = random.randint(18, 60)
        gender = random.choice(genders)
        users.append((name, age, gender))
    return users

def initialize_database():
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Create users table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE,
        age INTEGER,
        gender TEXT
    )
    ''')
    
    # Insert initial data
    users = [
        ("john", 20, "male"),
        ("torres", 30, "male"),
        ("emma", 25, "female"),
        ("liam", 28, "male"),
        ("olivia", 22, "female"),
        ("noah", 35, "male"),
        ("ava", 27, "female"),
        ("william", 40, "male"),
        ("sophia", 33, "female"),
        ("james", 45, "male")
    ]
    
    # Generate synthetic users
    users.extend(generate_synthetic_users(30))
    
    cursor.executemany("INSERT OR IGNORE INTO users (name, age, gender) VALUES (?, ?, ?)", users)
    conn.commit()
    conn.close()
    print("Database initialized with users.")

def classify_message(message):
    update_patterns = [
    # Age Updates
    r"change (\w+)'s age (?:into|to) (\d+)",
    r"update (\w+)'s age (?:into|to) (\d+)",
    r"modify (\w+)'s age (?:into|to) (\d+)",
    r"set (\w+)'s age (?:into|to) (\d+)",
    r"alter (\w+)'s age (?:into|to) (\d+)",
    r"adjust (\w+)'s age (?:into|to) (\d+)",
    r"make (\w+)'s age (\d+)",
    r"set (\w+)'s age as (\d+)",
    r"update (\w+)'s birth year to (\d+)",
    r"change (\w+)'s birth year into (\d+)",
    r"(\w+) just turned (\d+)",
    r"(\w+) is now (\d+) years old",

    # Gender Updates
    r"change (\w+)'s gender (?:into|to) (male|female)",
    r"update (\w+)'s gender (?:into|to) (male|female)",
    r"modify (\w+)'s gender (?:into|to) (male|female)",
    r"set (\w+)'s gender (?:into|to) (male|female)",
    r"alter (\w+)'s gender (?:into|to) (male|female)",
    r"adjust (\w+)'s gender (?:into|to) (male|female)",
    r"switch (\w+)'s gender to (male|female)",
    r"(\w+) is now (male|female)",
    r"(\w+) identifies as (male|female)",
    r"mark (\w+) as (male|female)",

    # Name Changes - Ensuring Proper Handling
    r"change (\w+)'s name (?:into|to) (\w+)",
    r"rename (\w+) to (\w+)",
    r"modify (\w+)'s name to (\w+)",
    r"set (\w+)'s name to (\w+)",
    r"alter (\w+)'s name to (\w+)",
    r"update (\w+)'s name to (\w+)",
    r"(\w+) now goes by (\w+)",
    r"(\w+) prefers to be called (\w+)",
    r"(\w+) is now known as (\w+)",
    r"(\w+) has changed their name to (\w+)",

    # Direct Changes
    r"change (\w+) into (\d+)",  # If second word is a number, change age
    r"change (\w+) into (male|female)",  # If second word is gender, update gender
    r"change (\w+) into (\w+)",  # Otherwise, change name

    # Natural Phrasing
    r"(\w+)'s new age is (\d+)",
    r"(\w+)'s new gender is (male|female)",
    r"(\w+)'s new name is (\w+)",
    r"(\w+) should be called (\w+)",
    ]
    
    for pattern in update_patterns:
        match = re.search(pattern, message, re.IGNORECASE)
        if match:
            print("NOT LLM")
            return "DB_UPDATE", match.groups()
    print("LLM")
    return "LLM", None

def update_database(field, name, value):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute(f"UPDATE users SET {field} = ? WHERE name = ?", (value, name))
    conn.commit()
    conn.close()

def generate_llm_response(message):
    return llm_pipeline(message, truncation=False, max_length=1000)[0]['generated_text']

@csrf_exempt
def setup_database_view(request):
    initialize_database()
    return JsonResponse({"message": "Database initialized with users."})

class ChatBotAPI(APIView):
    def post(self, request):
        initialize_database()
        user_message = request.data.get("message")
        action, params = classify_message(user_message)

        if action == "LLM":
            response = generate_llm_response(user_message)
        else:
            old_name, new_value = params
            
            # Determine update field
            if new_value.isdigit():
                field = "age"
                update_database(field, old_name, new_value)
                response = f"Updated {old_name}'s age to {new_value}."
            elif new_value.lower() in ["male", "female"]:
                field = "gender"
                update_database(field, old_name, new_value)
                response = f"Updated {old_name}'s gender to {new_value}."
            else:
                field = "name"

                # Ensure name change doesn't create duplicates
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM users WHERE name = ?", (new_value,))
                exists = cursor.fetchone()[0] > 0
                conn.close()

                if exists:
                    response = f"Error: Name '{new_value}' already exists in the database."
                else:
                    update_database(field, old_name, new_value)
                    response = f"Updated {old_name}'s name to {new_value}."
        print(db_path);
        ChatHistory.objects.create(user_input=user_message, bot_response=response)
        return Response({"response": response})

class ChatHistoryListCreate(generics.ListCreateAPIView):
    queryset = ChatHistory.objects.all()
    serializer_class = ChatHistorySerializer
