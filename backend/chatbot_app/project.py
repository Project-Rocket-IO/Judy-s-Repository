import json
from decouple import config
from openai import OpenAI
from django.db.models import Q
from accounts.models import TechnicianUser
from chatbot_app.models import ProjectList, ClientCompany, ChatHistory

client = OpenAI(api_key=config("OPENAI_API_KEY"))

def create_project_prompt(message):
    return f"""
    The user is requesting to create or update a project. Extract the following information from the user's input and return it as a valid JSON string:
    
    Required fields for creation:
    - name (string)
    - client (string, client company name)
    - assignment (list of technician usernames, e.g., ["john_doe", "ali"])

    Optional fields:
    - new_name (string, for updates)
    - description (string)
    - end_date (string, YYYY-MM-DD)
    - due_date (string, YYYY-MM-DD)
    - status (string, e.g., "open", "in_progress", "completed")
    - priority (string, e.g., "low", "medium", "high")

    Rules:
    - Return the response as a valid JSON string with double quotes around keys and string values
    - Set missing values to null (do not infer or guess values)
    - assignment should be an array of technician usernames or null if not provided
    - Dates should be in YYYY-MM-DD format or null
    - If the input suggests an update (e.g., "change name to"), extract the new name as "new_name"

    The user's input: "{message}"
    
    Example response format:
    {{
        "name": "Website Redesign",
        "new_name": null,
        "client": "ABC Corp",
        "assignment": ["john_doe", "ali"],
        "description": "Redesign company website",
        "end_date": "2025-06-01",
        "due_date": "2025-05-15",
        "status": "open",
        "priority": "high"
    }}

    Now, process the input and return the extracted fields in this exact JSON format.
    """

def extract_project_fields(message):
    prompt = create_project_prompt(message)
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

def get_project_context():
    """Get project context from ChatHistory or initialize default."""
    context = {
        "name": None,
        "new_name": None,
        "client": None,
        "assignment": None,
        "description": None,
        "end_date": None,
        "due_date": None,
        "status": None,
        "priority": None
    }
    if ChatHistory.objects.exists():
        history_entries = ChatHistory.objects.order_by('timestamp')
        for entry in history_entries:
            if "project" in entry.user_input.lower() or "You're almost there! Please provide for project" in entry.bot_response:
                try:
                    
                    past_data = extract_project_fields(entry.user_input)
                    if not past_data.get("error"):
                        context = merge_project_context(context, past_data)
                except Exception as e:
                    print(f"Error re-extracting context: {e}")
    print("Project context:", context)
    return context

def merge_project_context(current_context, extracted_data):
    merged_data = current_context.copy()
    for key, value in extracted_data.items():
        if value is not None:
            if key == "assignment" and isinstance(value, list):
                merged_data[key] = value 
            else:
                merged_data[key] = value
    return merged_data

def validate_project_data(project_data):
    missing_fields = []
    required_fields = ["name"]
    action_intent = project_data.get("action_intent", "CREATE")
    
    if action_intent == "CREATE":
        required_fields.extend(["client", "assignment"])
    
    for field in required_fields:
        value = project_data.get(field)
        if field == "assignment":
            if not value or not isinstance(value, list) or not all(isinstance(u, str) and u for u in value):
                missing_fields.append(field)
        elif not value:
            missing_fields.append(field)
    
    if missing_fields:
        return {
            "response": f"You're almost there! Please provide for project: {', '.join(missing_fields)}.",
            "error": True,
            "missing_fields": missing_fields
        }

    client_name = project_data.get("client")
    if client_name and not ClientCompany.objects.filter(name=client_name).exists():
        return {
            "response": f"Sorry, client '{client_name}' does not exist. Please create it first.",
            "error": True
        }

    assignment = project_data.get("assignment", [])
    if assignment:
        invalid_users = [
            username for username in assignment
            if not TechnicianUser.objects.filter(auth_user__username=username).exists()
        ]
        if invalid_users:
            return {
                "response": f"Sorry, technician(s) {', '.join(invalid_users)} do not exist. Please assign valid technicians.",
                "error": True
            }

    return {
        "success": "Project data is valid",
        "project_data": project_data,
        "response": "Data is valid",
        "error": False
    }

def get_project_in_context(project_name):
    if project_name:
        try:
            return ProjectList.objects.get(name=project_name)
        except ProjectList.DoesNotExist:
            return None
    return None

def create_project(project_data, conversation_key):
    try:
        client_name = project_data.get("client")
        client_instance = ClientCompany.objects.get(name=client_name)

        project = ProjectList.objects.create(
            name=project_data["name"],
            client=client_instance,
            description=project_data.get("description", "Please add Project description..."),
            end_date=project_data.get("end_date"),
            due_date=project_data.get("due_date"),
            status=project_data.get("status", "open"),
            priority=project_data.get("priority")
        )

        assignment_usernames = project_data.get("assignment", [])
        if assignment_usernames:
            for username in assignment_usernames:
                tech = TechnicianUser.objects.get(auth_user__username=username)
                project.assignment.add(tech)

        return {
            "response": f"Project '{project.name}' created successfully!",
            "project_id": project.identifier,
            "error": False
        }
    except ClientCompany.DoesNotExist:
        return {
            "response": f"Sorry, client '{client_name}' does not exist. Please create it first.",
            "error": True
        }
    except TechnicianUser.DoesNotExist:
        return {
            "response": f"Sorry, one or more technicians do not exist. Please assign valid technicians.",
            "error": True
        }
    except Exception as e:
        return {
            "response": f"Failed to create project: {str(e)}",
            "error": True
        }

def update_project(project_data, conversation_key):
    project_name = project_data.get("name")
    project = get_project_in_context(project_name)
    if not project:
        return {
            "response": f"No matching project found for update. Please provide a valid project name.",
            "error": True
        }

    try:
        updated_fields = {}
        if project_data.get("new_name") and project_data["new_name"] != project.name:
            if ProjectList.objects.filter(name=project_data["new_name"]).exists():
                return {
                    "response": f"A project named '{project_data['new_name']}' already exists.",
                    "error": True
                }
            project.name = project_data["new_name"]
            updated_fields["name"] = project_data["new_name"]

        client_name = project_data.get("client")
        if client_name and client_name != project.client.name:
            client_instance = ClientCompany.objects.get(name=client_name)
            project.client = client_instance
            updated_fields["client"] = client_name

        if project_data.get("description") is not None:
            project.description = project_data["description"]
            updated_fields["description"] = project_data["description"]

        if project_data.get("end_date") is not None:
            project.end_date = project_data["end_date"]
            updated_fields["end_date"] = project_data["end_date"]

        if project_data.get("due_date") is not None:
            project.due_date = project_data["due_date"]
            updated_fields["due_date"] = project_data["due_date"]

        if project_data.get("status") is not None:
            project.status = project_data["status"]
            updated_fields["status"] = project_data["status"]

        if project_data.get("priority") is not None:
            project.priority = project_data["priority"]
            updated_fields["priority"] = project_data["priority"]

        assignment_usernames = project_data.get("assignment")
        if assignment_usernames is not None:
            new_assignments = []
            for username in assignment_usernames:
                tech = TechnicianUser.objects.get(auth_user__username=username)
                new_assignments.append(tech)
            if set(project.assignment.all()) != set(new_assignments):
                project.assignment.clear()
                for tech in new_assignments:
                    project.assignment.add(tech)
                updated_fields["assignment"] = assignment_usernames

        if updated_fields:
            project.save()
            return {
                "response": f"Project '{project.name}' updated successfully!",
                "updated_fields": updated_fields,
                "error": False
            }
        return {
            "response": "No changes detected, project remains the same.",
            "error": False
        }
    except ClientCompany.DoesNotExist:
        return {
            "response": f"Sorry, client '{client_name}' does not exist.",
            "error": True
        }
    except TechnicianUser.DoesNotExist:
        return {
            "response": f"Sorry, one or more technicians do not exist. Please assign valid technicians.",
            "error": True
        }
    except Exception as e:
        return {
            "response": f"Failed to update project: {str(e)}",
            "error": True
        }
