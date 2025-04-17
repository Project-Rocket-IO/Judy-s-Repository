from django.db.models import Field
from django.db import IntegrityError
from accounts.models import TechnicianUser
from chatbot_app.models import ClientCompany, ChatHistory
import json
from decouple import config
from openai import OpenAI
import re

client = OpenAI(api_key=config("OPENAI_API_KEY"))

def create_client_prompt(message):
    return f"""
    The user is requesting to create or update a client company. Extract the following information from the user's input and return it as a valid JSON string:

    Required fields:
    - name (the current name of the client to create or update)
    - contact_first
    - contact_last
    - email
    - main_tech

    Optional fields:
    - new_name (new name for the client if updating, e.g., "NewCo" in "update client TechNova with name NewCo")
    - industry
    - website

    Rules:
    - Return the response as a valid JSON string with double quotes around keys and string values
    - Set missing values to null (do not infer or guess values)
    - main_tech should be a technician username (e.g., "john_doe")
    - If the user specifies "with a name X" or "to name X", set new_name to X for updates
    - name is the current client identifier; new_name is the desired name
    - email must be a valid email format

    The user's input: "{message}"

    Example response format:
    {{
        "name": "TechNova",
        "new_name": "NewCo",
        "contact_first": "John",
        "contact_last": "Doe",
        "email": "contact@technova.com",
        "main_tech": "john_doe",
        "industry": "Tech",
        "website": "https://technova.com"
    }}

    Now, process the input and return the extracted fields in this exact JSON format.
    """

def extract_client_fields(message):
    print(f"Extracting fields from message: {message}")
    prompt = create_client_prompt(message)
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "You are a precise data extraction assistant that returns valid JSON."},
            {"role": "user", "content": prompt}
        ],
        max_tokens=200
    )
    response_content = response.choices[0].message.content.strip()
    print("Raw GPT response:", response_content)
    try:
        extracted_data = json.loads(response_content)
        print("Extracted data:", extracted_data)
        return extracted_data
    except json.JSONDecodeError as e:
        print(f"JSON Parse Error: {e}")
        return {"response": f"Failed to parse input: {str(e)}", "error": True}

def merge_client_context(existing_context, new_data):
    merged = existing_context.copy()
    for key, value in new_data.items():
        if value is not None:
            merged[key] = value
    return merged

def get_client_context():
    context = {
        "name": None,
        "new_name": None,
        "contact_first": None,
        "contact_last": None,
        "email": None,
        "main_tech": None,
        "industry": None,
        "website": None
    }
    history = ChatHistory.objects.all().order_by('-timestamp')[:10]
    print("ChatHistory for context:", [(h.user_input, h.bot_response) for h in history])
    for entry in history:
        try:
            extracted = extract_client_fields(entry.user_input)
            if not isinstance(extracted, dict) or "error" in extracted:
                continue
            context = merge_client_context(context, extracted)
        except Exception as e:
            print(f"Error extracting context from {entry.user_input}: {e}")
            continue
    print("Client context:", context)
    return context

def validate_client_data(extracted_data):
    print("Validating data:", extracted_data)
    missing_fields = []
    required_fields = ["name"]
    action_intent = extracted_data.get("action_intent", "CREATE")

    if action_intent == "CREATE":
        required_fields.extend(["contact_first", "contact_last", "email", "main_tech"])

    for field in required_fields:
        if not extracted_data.get(field):
            missing_fields.append(field)

    email = extracted_data.get("email")
    if email and not re.match(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$", email):
        return {
            "response": "Please provide a valid email address.",
            "error": True,
            "missing_fields": ["email"]
        }

    if missing_fields:
        return {
            "response": f"You're almost there! Please provide for client: {', '.join(missing_fields)}.",
            "error": True,
            "missing_fields": missing_fields
        }
    return {
        "success": "Client data is valid",
        "client_data": extracted_data,
        "response": "Data is valid",
        "error": False
    }

def get_client_in_context(client_name=None):
    if client_name:
        try:
            client = ClientCompany.objects.get(name=client_name)
            return client
        except ClientCompany.DoesNotExist:
            return None
        except ClientCompany.MultipleObjectsReturned:
            return {
                "response": f"Multiple clients named '{client_name}' found. Please use a unique client name or email.",
                "error": True
            }
    return None

def create_client(client_data, conversation_key):
    try:
        model_data = {
            'name': client_data['name'],
            'contact_first': client_data['contact_first'],
            'contact_last': client_data['contact_last'],
            'email': client_data['email'],
            'industry': client_data.get('industry'),
            'website': client_data.get('website'),
        }

        main_tech_username = client_data.get('main_tech')
        if main_tech_username:
            try:
                main_tech = TechnicianUser.objects.get(auth_user__username=main_tech_username)
                model_data['main_tech'] = main_tech
            except TechnicianUser.DoesNotExist:
                return {
                    "response": f"Sorry, technician '{main_tech_username}' does not exist. Please assign a valid technician.",
                    "error": True
                }
        else:
            return {"response": "Main technician is required for the client.", "error": True}

        client = ClientCompany.objects.create(**model_data)
        return {
            "response": f"Client '{client.name}' created successfully!",
            "client_id": client.id,
            "error": False
        }

    except IntegrityError as e:
        if "unique constraint" in str(e) and "email" in str(e):
            return {
                "response": f"Failed to create client: Email '{client_data['email']}' already exists. Please use a unique email.",
                "error": True
            }
        return {"response": f"Failed to create client: {str(e)}", "error": True}
    except Exception as e:
        return {"response": f"Failed to create client: {str(e)}", "error": True}

def update_client(client_data, conversation_key):
    client = get_client_in_context(client_data.get("name"))
    if isinstance(client, dict) and client.get("error"):
        return client
    if not client:
        return {
            "response": "No matching client found for update. Please provide a valid client name.",
            "error": True
        }
    updated_fields = {}
    new_name = client_data.get("new_name")
    if new_name and new_name != client.name:
        if ClientCompany.objects.filter(name=new_name).exists():
            return {
                "response": f"A client named '{new_name}' already exists. Choose a unique name.",
                "error": True
            }
        client.name = new_name
        updated_fields["name"] = new_name

    for field, value in client_data.items():
        if field == 'main_tech' and value is not None:
            try:
                main_tech = TechnicianUser.objects.get(auth_user__username=value)
                if client.main_tech != main_tech:
                    client.main_tech = main_tech
                    updated_fields['main_tech'] = value
            except TechnicianUser.DoesNotExist:
                return {
                    "response": f"Sorry, technician '{value}' does not exist. Please assign a valid technician.",
                    "error": True
                }
        elif field == 'email' and value is not None and value != client.email:
            if ClientCompany.objects.filter(email=value).exclude(id=client.id).exists():
                return {
                    "response": f"Failed to update client: Email '{value}' is already in use by another client.",
                    "error": True
                }
            client.email = value
            updated_fields['email'] = value
        elif field not in ('name', 'new_name') and value is not None and getattr(client, field, None) != value:
            setattr(client, field, value)
            updated_fields[field] = value

    if updated_fields:
        try:
            client.save()
            return {
                "response": f"Client '{client.name}' updated successfully!",
                "updated_fields": updated_fields,
                "error": False
            }
        except IntegrityError as e:
            if "unique constraint" in str(e) and "email" in str(e):
                return {
                    "response": f"Failed to update client: Email '{client_data.get('email')}' is already in use by another client.",
                    "error": True
                }
            return {"response": f"Failed to update client: {str(e)}", "error": True}
        except Exception as e:
            return {"response": f"Failed to update client: {str(e)}", "error": True}
    else:
        return {"response": "No changes detected, client remains the same.", "error": False}
