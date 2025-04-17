from django.db.models import Field
from accounts.models import TechnicianUser
from chatbot_app.models import TicketList, ClientCompany, ProjectList, ChatHistory
import json
from decouple import config
from openai import OpenAI
from chatbot_app.state import ACTIVE_INTENTS

client = OpenAI(api_key=config("OPENAI_API_KEY"))

def create_ticket_prompt(message):
    return f"""
    The user is requesting to create or update a ticket. Extract the following information from the user's input and return it as a valid JSON string:

    Required fields for creation:
    - ticket_name (string, the identifier of the ticket)
    - client (string, client company name)
    - assigned_to (list of technician usernames, e.g., ["john_doe", "ali"])

    Optional fields:
    - new_ticket_name (string, new name for updates)
    - description (string)
    - end_date (string, YYYY-MM-DD)
    - due_date (string, YYYY-MM-DD)
    - ticket_type (string, e.g., "bug", "feature", "task")
    - status (string, e.g., "open", "in_progress", "closed")
    - priority (string, e.g., "low", "medium", "high")
    - project (string, project name)

    Rules:
    - Return the response as a valid JSON string with double quotes around keys and string values
    - Set missing values to null (do not infer or guess values)
    - assigned_to should be an array of technician usernames or null
    - Dates should be in YYYY-MM-DD format or null
    - If the user specifies "with a name X" or "to name X", set new_ticket_name to X for updates

    The user's input: "{message}"

    Example response format:
    {{
        "ticket_name": "454",
        "new_ticket_name": "111",
        "client": "ABC Corp",
        "assigned_to": ["john_doe", "ali"],
        "description": "Fix issue",
        "end_date": "2025-06-01",
        "due_date": "2025-05-15",
        "ticket_type": "bug",
        "status": "open",
        "priority": "high",
        "project": "Website Redesign"
    }}

    Now, process the input and return the extracted fields in this exact JSON format.
    """

def extract_ticket_fields(message):
    print(f"Extracting fields from message: {message}")
    prompt = create_ticket_prompt(message)
    try:
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
        extracted_data = json.loads(response_content)
        print("Extracted data:", extracted_data)
        return extracted_data
    except Exception as e:
        print(f"Extraction Error: {e}")
        return {"response": f"Failed to parse input: {str(e)}", "error": True}

def get_ticket_context():
    context = {
        "ticket_name": None,
        "new_ticket_name": None,
        "client": None,
        "assigned_to": None,
        "description": None,
        "end_date": None,
        "due_date": None,
        "ticket_type": None,
        "status": None,
        "priority": None,
        "project": None
    }
    if ChatHistory.objects.exists():
        history_entries = ChatHistory.objects.order_by('timestamp')
        for entry in history_entries:
            if "ticket" in entry.user_input.lower() or "You're almost there! Please provide for ticket" in entry.bot_response:
                try:
                    past_data = extract_ticket_fields(entry.user_input)
                    if not past_data.get("error"):
                        context = merge_context(context, past_data)
                except Exception as e:
                    print(f"Error re-extracting context: {e}")
    print("Ticket context:", context)
    return context

def merge_context(current_context, extracted_data):
    merged_data = current_context.copy()
    for key, value in extracted_data.items():
        if value is not None:
            if key == "assigned_to" and isinstance(value, list):
                merged_data[key] = value
            else:
                merged_data[key] = value
    return merged_data

def validate_ticket_data(ticket_data):
    print("Validating data:", ticket_data)
    missing_fields = []
    required_fields = ["ticket_name"]
    action_intent = ticket_data.get("action_intent", "CREATE")

    if action_intent == "CREATE":
        required_fields.extend(["client", "assigned_to"])

    for field in required_fields:
        value = ticket_data.get(field)
        if field == "assigned_to":
            if not value or not isinstance(value, list) or not all(isinstance(u, str) and u for u in value):
                missing_fields.append(field)
        elif not value:
            missing_fields.append(field)

    if missing_fields:
        return {
            "response": f"You're almost there! Please provide for ticket: {', '.join(missing_fields)}.",
            "error": True,
            "missing_fields": missing_fields
        }

    ticket_name = ticket_data.get("ticket_name")
    new_ticket_name = ticket_data.get("new_ticket_name")
    client = ticket_data.get("client")
    assigned_to = ticket_data.get("assigned_to")

    if action_intent == "CREATE":
        if TicketList.objects.filter(name=ticket_name).exists():
            return {"response": f"Ticket '{ticket_name}' already exists.", "error": True}
        if client and not ClientCompany.objects.filter(name=client).exists():
            return {"response": f"Client '{client}' does not exist.", "error": True}
        if assigned_to:
            invalid_users = [user for user in assigned_to if not TechnicianUser.objects.filter(auth_user__username=user).exists()]
            if invalid_users:
                return {"response": f"Technician(s) {', '.join(invalid_users)} do not exist.", "error": True}
    elif action_intent == "UPDATE":
        if not TicketList.objects.filter(name=ticket_name).exists():
            return {"response": f"Ticket '{ticket_name}' does not exist.", "error": True}
        
        if new_ticket_name and TicketList.objects.filter(name=new_ticket_name).exists():
            return {"response": f"A ticket named '{new_ticket_name}' already exists.", "error": True}
        if client and not ClientCompany.objects.filter(name=client).exists():
            return {"response": f"Client '{client}' does not exist.", "error": True}
        if assigned_to:
            invalid_users = [user for user in assigned_to if not TechnicianUser.objects.filter(auth_user__username=user).exists()]
            if invalid_users:
                return {"response": f"Technician(s) {', '.join(invalid_users)} do not exist.", "error": True}
    elif action_intent == "DELETE":
        if not TicketList.objects.filter(name=ticket_name).exists():
            return {"response": f"Ticket '{ticket_name}' does not exist.", "error": True}

    return {
        "success": "Ticket data is valid",
        "ticket_data": ticket_data,
        "response": "Data is valid",
        "error": False
    }

def get_ticket_in_context(ticket_name):
    if ticket_name:
        try:
            return TicketList.objects.get(name=ticket_name)
        except TicketList.DoesNotExist:
            return None
        except TicketList.MultipleObjectsReturned:
            return {
                "response": f"Multiple tickets named '{ticket_name}' found. Please use a unique ticket name.",
                "error": True
            }
    return None

def create_ticket(ticket_data, conversation_key):
    try:
        client_name = ticket_data.get("client")
        client_instance = ClientCompany.objects.get(name=client_name)

        model_data = {
            "name": ticket_data["ticket_name"],
            "client": client_instance,
            "description": ticket_data.get("description", "Please add ticket description..."),
            "end_date": ticket_data.get("end_date"),
            "due_date": ticket_data.get("due_date"),
            "ticket_type": ticket_data.get("ticket_type"),
            "status": ticket_data.get("status", "open") or open,
            "priority": ticket_data.get("priority")
        }

        project_name = ticket_data.get("project")
        if project_name:
            try:
                project_instance = ProjectList.objects.get(name=project_name)
                model_data["project"] = project_instance
            except ProjectList.DoesNotExist:
                return {
                    "response": f"Sorry, project '{project_name}' does not exist.",
                    "error": True
                }

        ticket = TicketList.objects.create(**model_data)

        assigned_usernames = ticket_data.get("assigned_to", [])
        if assigned_usernames:
            for username in assigned_usernames:
                tech = TechnicianUser.objects.get(auth_user__username=username)
                ticket.assignment.add(tech)
        else:
            return {
                "response": "At least one technician must be assigned to the ticket.",
                "error": True
            }

        return {
            "response": f"Ticket '{ticket.name}' created successfully!",
            "ticket_id": ticket.identifier,
            "error": False
        }
    except ClientCompany.DoesNotExist:
        return {
            "response": f"Sorry, client '{client_name}' does not exist. Please create it first.",
            "error": True
        }
    except TechnicianUser.DoesNotExist:
        return {
            "response": f"Sorry, one or more technicians do not exist.",
            "error": True
        }
    except Exception as e:
        print(f"Create ticket error: {e}")
        return {"response": f"Failed to create ticket: {str(e)}", "error": True}

def update_ticket(ticket_data, conversation_key):
    ticket_name = ticket_data.get("new_ticket_name") or ticket_data.get("ticket_name")
    ticket = get_ticket_in_context(ticket_data.get("ticket_name"))
    if isinstance(ticket, dict) and ticket.get("error"):
        return ticket
    if not ticket:
        return {
            "response": f"Ticket '{ticket_data.get('ticket_name')}' does not exist.",
            "error": True
        }

    try:
        updated_fields = {}
        if ticket_data.get("new_ticket_name") and ticket_data["new_ticket_name"] != ticket.name:
            if TicketList.objects.filter(name=ticket_data["new_ticket_name"]).exists():
                return {
                    "response": f"A ticket named '{ticket_data['new_ticket_name']}' already exists.",
                    "error": True
                }
            ticket.name = ticket_data["new_ticket_name"]
            updated_fields["name"] = ticket_data["new_ticket_name"]

        client_name = ticket_data.get("client")
        if client_name and client_name != ticket.client.name:
            client_instance = ClientCompany.objects.get(name=client_name)
            ticket.client = client_instance
            updated_fields["client"] = client_name

        if ticket_data.get("description") is not None:
            ticket.description = ticket_data["description"]
            updated_fields["description"] = ticket_data["description"]

        if ticket_data.get("end_date") is not None:
            ticket.end_date = ticket_data["end_date"]
            updated_fields["end_date"] = ticket_data["end_date"]

        if ticket_data.get("due_date") is not None:
            ticket.due_date = ticket_data["due_date"]
            updated_fields["due_date"] = ticket_data["due_date"]

        if ticket_data.get("ticket_type") is not None:
            ticket.ticket_type = ticket_data["ticket_type"]
            updated_fields["ticket_type"] = ticket_data["ticket_type"]

        if ticket_data.get("status") is not None:
            ticket.status = ticket_data["status"]
            updated_fields["status"] = ticket_data["status"]

        if ticket_data.get("priority") is not None:
            ticket.priority = ticket_data["priority"]
            updated_fields["priority"] = ticket_data["priority"]

        project_name = ticket_data.get("project")
        if project_name is not None:
            try:
                project_instance = ProjectList.objects.get(name=project_name)
                if ticket.project != project_instance:
                    ticket.project = project_instance
                    updated_fields["project"] = project_name
            except ProjectList.DoesNotExist:
                return {
                    "response": f"Sorry, project '{project_name}' does not exist.",
                    "error": True
                }

        assigned_usernames = ticket_data.get("assigned_to")
        if assigned_usernames is not None:
            new_assignments = []
            for username in assigned_usernames:
                tech = TechnicianUser.objects.get(auth_user__username=username)
                new_assignments.append(tech)
            if set(ticket.assignment.all()) != set(new_assignments):
                ticket.assignment.clear()
                for tech in new_assignments:
                    ticket.assignment.add(tech)
                updated_fields["assigned_to"] = assigned_usernames

        if updated_fields:
            ticket.save()
            return {
                "response": f"Ticket '{ticket.name}' updated successfully!",
                "updated_fields": updated_fields,
                "error": False
            }
        return {
            "response": "No changes detected, ticket remains the same.",
            "error": False
        }
    except ClientCompany.DoesNotExist:
        return {
            "response": f"Sorry, client '{client_name}' does not exist.",
            "error": True
        }
    except TechnicianUser.DoesNotExist:
        return {
            "response": f"Sorry, one or more technicians do not exist.",
            "error": True
        }
    except Exception as e:
        print(f"Update ticket error: {e}")
        return {"response": f"Failed to update ticket: {str(e)}", "error": True}
