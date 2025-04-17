from decouple import config
from openai import OpenAI
import spacy
import json
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from chatbot_app.state import ACTIVE_INTENTS
from time import time
from django.db import transaction
from accounts.models import TechnicianUser
from chatbot_app.models import TicketList, ClientCompany, ProjectList, ChatHistory
from chatbot_app.tickets import extract_ticket_fields, merge_context, validate_ticket_data, create_ticket, update_ticket, get_ticket_in_context, get_ticket_context
from chatbot_app.client import extract_client_fields, merge_client_context, validate_client_data, create_client, update_client, get_client_in_context, get_client_context
from chatbot_app.project import extract_project_fields, merge_project_context, validate_project_data, create_project, update_project, get_project_in_context, get_project_context


client = OpenAI(api_key=config("OPENAI_API_KEY"))
nlp = spacy.load("en_core_web_sm")

create_keywords = {"create", "add", "new", "register", "open"}
update_keywords = {"update", "modify", "edit", "change", "adjust"}
ticket_keywords = {"ticket", "issue", "task"}
client_keywords = {"client", "company", "customer"}
project_keywords = {"project", "proj", "initiative"}

def classify_intent(text):
    doc = nlp(text.lower())
    action_intent = "UNKNOWN"
    model_intent = None
    cancel_keywords = {"cancel", "stop", "abort", "end"}

    if any(token.text in cancel_keywords for token in doc):
        return "CANCEL", None

    for token in doc:
        if token.lemma_ in create_keywords:
            action_intent = "CREATE"
            break
        elif token.lemma_ in update_keywords:
            action_intent = "UPDATE"
            break

    for token in doc:
        if token.text in ticket_keywords:
            model_intent = "TICKET"
            break
        elif token.text in client_keywords:
            model_intent = "CLIENT"
            break
        elif token.text in project_keywords:
            model_intent = "PROJECT"
            break

    return action_intent, model_intent

def get_conversation_key(request):
    if 'conversation_key' not in request.session:
        key = str(time())
        request.session['conversation_key'] = key
        request.session.modified = True
        request.session.save()
        print(f"Set new session conversation_key: {key}")
    else:
        key = request.session['conversation_key']
        print(f"Reusing session conversation_key: {key}")
    request.session.modified = True
    print(f"Session cookie: {request.session.session_key}")
    print(f"Request cookies: {request.COOKIES}")
    return key

@csrf_exempt
def chatbot(request):
    if request.method != "POST":
        response = {"response": "Invalid request method. Use POST.", "error": True}
        with transaction.atomic():
            ChatHistory.objects.create(
                user_input="",
                bot_response=response["response"]
            )
        return JsonResponse(response, status=405)

    try:
        data = json.loads(request.body)
        message = data.get("message")
        print(f"Received message: {message}")
        print(f"Session keys: {request.session.keys()}")
        print(f"Session data: {request.session.items()}")

        if not message:
            response = {"response": "No message provided", "error": True}
            with transaction.atomic():
                ChatHistory.objects.create(
                    user_input="",
                    bot_response=response["response"]
                )
            return JsonResponse(response, status=400)

        if message.lower() == "clear":
            with transaction.atomic():
                ChatHistory.objects.all().delete()
            ACTIVE_INTENTS.clear()
            request.session.flush()
            print("Cleared ChatHistory, ACTIVE_INTENTS, and session")
            return JsonResponse({"response": "Chatbot state cleared. What would you like to do next?", "error": False})

        conversation_key = get_conversation_key(request)
        print(f"Conversation key: {conversation_key}")
        print(f"ACTIVE_INTENTS state: {ACTIVE_INTENTS}")
        print(f"ChatHistory exists: {ChatHistory.objects.exists()}")

        if message.lower() in {"cancel", "stop", "abort", "end"}:
            with transaction.atomic():
                ChatHistory.objects.all().delete()
            ACTIVE_INTENTS.pop(conversation_key, None)
            if 'conversation_key' in request.session:
                del request.session['conversation_key']
                request.session.modified = True
            response = {"response": "Task cancelled. What would you like to do next?", "error": False}
            with transaction.atomic():
                ChatHistory.objects.create(
                    user_input=message,
                    bot_response=response["response"]
                )
            return JsonResponse(response)

        if not ChatHistory.objects.exists() and conversation_key not in ACTIVE_INTENTS:
            action_intent, model_intent = classify_intent(message)
            if action_intent == "CANCEL":
                response = {"response": "No task to cancel. What would you like to do next?", "error": False}

                return JsonResponse(response)

            if not model_intent or action_intent == "UNKNOWN":
                response = client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {"role": "system", "content": "You are a helpful assistant managing tickets, clients, and projects."},
                        {"role": "user", "content": message}
                    ]
                )
                answer = response.choices[0].message.content.strip()

                return JsonResponse({"response": answer, "error": False})

            ACTIVE_INTENTS[conversation_key] = {
                "action_intent": action_intent,
                "model_intent": model_intent
            }
            print(f"Locked intent: {action_intent}/{model_intent}")
        elif conversation_key in ACTIVE_INTENTS:
            action_intent = ACTIVE_INTENTS[conversation_key]["action_intent"]
            model_intent = ACTIVE_INTENTS[conversation_key]["model_intent"]
            print(f"Using locked intent: {action_intent}/{model_intent}")
        else:
            history_entries = ChatHistory.objects.order_by('timestamp')
            print("ChatHistory for intent:", [(entry.user_input, entry.bot_response) for entry in history_entries])
            action_intent, model_intent = None, None
            for entry in list(history_entries):
                input_lower = entry.user_input.lower()
                if any(kw in input_lower for kw in ticket_keywords):
                    model_intent = "TICKET"
                    action_intent = "CREATE" if any(k in input_lower for k in create_keywords) else \
                                    "UPDATE" if any(k in input_lower for k in update_keywords) else "CREATE"
                    break
                elif any(kw in input_lower for kw in client_keywords):
                    model_intent = "CLIENT"
                    action_intent = "CREATE" if any(k in input_lower for k in create_keywords) else \
                                "UPDATE" if any(k in input_lower for k in update_keywords) else "CREATE"
                    break
                elif any(kw in input_lower for kw in project_keywords):
                    model_intent = "PROJECT"
                    action_intent = "CREATE" if any(k in input_lower for k in create_keywords) else \
                                "UPDATE" if any(k in input_lower for k in update_keywords) else "CREATE"
                    break

            if not model_intent:
                response = {"response": "Conversation lost context. Please start a new task.", "error": True}
                with transaction.atomic():
                    ChatHistory.objects.create(
                        user_input=message,
                        bot_response=response["response"]
                    )
                return JsonResponse(response, status=400)

            ACTIVE_INTENTS[conversation_key] = {
                "action_intent": action_intent,
                "model_intent": model_intent
            }
            print(f"Recovered intent: {action_intent}/{model_intent}")

        new_action_intent, _ = classify_intent(message)
        if new_action_intent in {"CREATE", "UPDATE", "DELETE"} and new_action_intent != action_intent:
            action_intent = new_action_intent
            ACTIVE_INTENTS[conversation_key]["action_intent"] = action_intent
            print(f"Updated action_intent: {action_intent}/{model_intent}")

        if model_intent == "TICKET":
            extracted_data = extract_ticket_fields(message)
            if "error" in extracted_data:
                with transaction.atomic():
                    ChatHistory.objects.create(
                        user_input=message,
                        bot_response=extracted_data["response"]
                    )
                return JsonResponse(extracted_data, status=400)

            ticket_context = get_ticket_context()
            merged_data = merge_context(ticket_context, extracted_data)
            merged_data["action_intent"] = action_intent
            print("Merged Ticket Data:", merged_data)

            validation_result = validate_ticket_data(merged_data)
            if validation_result.get("error", False):
                with transaction.atomic():
                    ChatHistory.objects.create(
                        user_input=message,
                        bot_response=validation_result["response"]
                    )
                return JsonResponse({
                    "response": validation_result["response"],
                    "error": True,
                    "current_data": merged_data
                }, status=200)

            original_ticket_name = merged_data.get("ticket_name")
            new_ticket_name = merged_data.get("new_ticket_name")
            
            if action_intent == "CREATE":
                if TicketList.objects.filter(name=original_ticket_name).exists():
                    response = {"response": f"Ticket '{original_ticket_name}' already exists.", "error": True}
                else:
                    response = create_ticket(merged_data, conversation_key)
            elif action_intent == "UPDATE":
                if not TicketList.objects.filter(name=original_ticket_name).exists():
                    response = {"response": f"Ticket '{original_ticket_name}' not found.", "error": True}
                elif new_ticket_name and TicketList.objects.filter(name=new_ticket_name).exists():
                    response = {"response": f"Ticket '{new_ticket_name}' already exists.", "error": True}
                else:
                    response = update_ticket(merged_data, conversation_key)
            else:
                response = {"response": "Invalid ticket operation", "error": True}

            with transaction.atomic():
                ChatHistory.objects.create(
                    user_input=message,
                    bot_response=response["response"]
                )
                if not response.get("error", False):
                    ChatHistory.objects.all().delete()
                    ACTIVE_INTENTS.pop(conversation_key, None)
                    if 'conversation_key' in request.session:
                        del request.session['conversation_key']
                        request.session.modified = True
            return JsonResponse(response)

        elif model_intent == "CLIENT":
            extracted_data = extract_client_fields(message)
            if "error" in extracted_data:
                with transaction.atomic():
                    ChatHistory.objects.create(
                        user_input=message,
                        bot_response=extracted_data["response"]
                    )
                return JsonResponse(extracted_data, status=400)

            client_context = get_client_context()
            merged_data = merge_client_context(client_context, extracted_data)
            merged_data["action_intent"] = action_intent
            print("Merged Client Data:", merged_data)

            validation_result = validate_client_data(merged_data)
            if validation_result.get("error", False):
                with transaction.atomic():
                    ChatHistory.objects.create(
                        user_input=message,
                        bot_response=validation_result["response"]
                    )
                return JsonResponse({
                    "response": validation_result["response"],
                    "error": True,
                    "current_data": merged_data
                }, status=200)

            original_name = merged_data.get("name")
            new_name = merged_data.get("new_name")

            if action_intent == "CREATE":
                if ClientCompany.objects.filter(name=original_name).exists():
                    response = {"response": f"Client '{original_name}' already exists.", "error": True}
                else:
                    response = create_client(merged_data, conversation_key)
            elif action_intent == "UPDATE":
                if not ClientCompany.objects.filter(name=original_name).exists():
                    response = {"response": f"Client '{original_name}' not found.", "error": True}
                elif new_name and ClientCompany.objects.filter(name=new_name).exists():
                    response = {"response": f"Client '{new_name}' already exists.", "error": True}
                else:
                    response = update_client(merged_data, conversation_key)
            else:
                response = {"response": "Invalid client operation", "error": True}

            with transaction.atomic():
                ChatHistory.objects.create(
                    user_input=message,
                    bot_response=response["response"]
                )
                if not response.get("error", False):
                    ChatHistory.objects.all().delete()
                    ACTIVE_INTENTS.pop(conversation_key, None)
                    if 'conversation_key' in request.session:
                        del request.session['conversation_key']
                        request.session.modified = True
            return JsonResponse(response)

        elif model_intent == "PROJECT":
            extracted_data = extract_project_fields(message)
            if "error" in extracted_data:
                with transaction.atomic():
                    ChatHistory.objects.create(
                        user_input=message,
                        bot_response=extracted_data["response"]
                    )
                return JsonResponse(extracted_data, status=400)

            project_context = get_project_context()
            merged_data = merge_project_context(project_context, extracted_data)
            merged_data["action_intent"] = action_intent
            print("Merged Project Data:", merged_data)

            validation_result = validate_project_data(merged_data)
            if validation_result.get("error", False):
                with transaction.atomic():
                    ChatHistory.objects.create(
                        user_input=message,
                        bot_response=validation_result["response"]
                    )
                return JsonResponse({
                    "response": validation_result["response"],
                    "error": True,
                    "current_data": merged_data
                }, status=200)
            original_name = merged_data.get("name")
            new_name = merged_data.get("new_name")

            if action_intent == "CREATE":

                if ProjectList.objects.filter(name=original_name).exists():
                    response = {"response": f"Project '{original_name}' already exists.", "error": True}
                else:
                    response = create_project(merged_data, conversation_key)
            elif action_intent == "UPDATE":
                if not ProjectList.objects.filter(name=original_name).exists():
                    response = {"response": f"Project '{original_name}' not found.", "error": True}
                elif new_name and ProjectList.objects.filter(name=new_name).exists():
                    response = {"response": f"Project '{new_name}' already exists.", "error": True}
                else:
                    response = update_project(merged_data, conversation_key)
            else:
                response = {"response": "Invalid project operation", "error": True}

            with transaction.atomic():
                ChatHistory.objects.create(
                    user_input=message,
                    bot_response=response["response"]
                )
                if not response.get("error", False):
                    ChatHistory.objects.all().delete()
                    ACTIVE_INTENTS.pop(conversation_key, None)
                    if 'conversation_key' in request.session:
                        del request.session['conversation_key']
                        request.session.modified = True
            return JsonResponse(response)

    except Exception as e:
        print("ERROR:", e)
        response = {"response": f"An unexpected error occurred: {str(e)}", "error": True}
        with transaction.atomic():
            ChatHistory.objects.create(
                user_input=message or "Unknown",
                bot_response=response["response"]
            )
        return JsonResponse(response, status=500)
