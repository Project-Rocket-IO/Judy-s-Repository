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
from transformers import pipeline
from .models import TicketList

def create_ticket_prompt(message):
    return f"""
    The user is requesting to create a ticket. Extract the following information from the user's input:
    
    Required fields:
    - ticket_name
    - client
    - assigned_to

    Optional fields:
    - description
    - tags
    - end_date
    - due_date
    - ticket_type
    - status
    = priority
    = project
    
    The user's input: "{message}"
    
    Provide the extracted fields in JSON format, ensuring that missing values are explicitly set to null (not inferred or guessed). Format the response strictly as follows:
    
    {{
        "ticket_name": null or "actual_ticket_name",
        "client": null or "client_name",
        "priority": null or "priority_level",
        "status": null or "priority_level",
        "priority": null or "priority_level",
        "assigned_to": null or "person_assigned",
        "end_date": null or "YYYY-MM-DD",
        "due_date": null or "YYYY-MM-DD",
        "ticket_type": null or "work_time_type",
        "description": null or "optional_description",
        "tags": null or ["optional_tags"]
    }}
    """

def extract_ticket_fields(message):
    prompt = create_ticket_prompt(message)
    
    # Send the prompt to OpenAI's GPT model
    response = openai.completions.create(
        model="gpt-3.5-turbo-instruct",  # or you can use a newer model like gpt-3.5-turbo
        prompt=prompt,
        max_tokens=200
    )
    
    # Extract the fields from the response
    try:
        extracted_data = json.loads(response.choices[0].text.strip())
    except json.JSONDecodeError:
        return {"error": "Failed to parse GPT response"}
    
    return extracted_data

def validate_ticket_data(extracted_data):
    # Check for missing required fields
    missing_fields = []
    required_fields = ["ticket_name", "assigned_to", "client"]
    
    for field in required_fields:
        if not extracted_data.get(field):
            missing_fields.append(field)
    
    if missing_fields:
        return {"error": f"Missing fields: {', '.join(missing_fields)}", "missing_fields": missing_fields}
    return {"success": "Ticket data is valid", "ticket_data": extracted_data}

def get_ticket_in_context(session_id, ticket_name=None):
    """
    Retrieves the last mentioned ticket in the session, or finds one by name.
    """
    if ticket_name:
        try:
            ticket = TicketList.objects.get(ticket_name=ticket_name)
            session_context[session_id] = ticket.id  # Store in session
            return ticket
        except TicketList.DoesNotExist:
            return None
    elif session_id in session_context:
        try:
            return TicketList.objects.get(id=session_context[session_id])
        except TicketList.DoesNotExist:
            return None
    return None


def create_ticket(ticket_data):
    """
    Creates a new ticket in the database.
    """
    ticket = TicketList.objects.create(**ticket_data)
    return {"message": f"Ticket '{ticket.ticket_name}' created successfully!", "ticket_id": ticket.id}

def update_ticket(ticket_data, session_id):
    """
    Updates an existing ticket by finding it in the database and updating only the specified fields.
    """
    ticket = get_ticket_in_context(session_id, ticket_data.get("ticket_name"))

    if not ticket:
        return {"error": "No matching ticket found for update. Provide a ticket name."}

    updated_fields = {}

    for field, value in ticket_data.items():
        if value is not None and getattr(ticket, field) != value:
            setattr(ticket, field, value)
            updated_fields[field] = value

    if updated_fields:
        ticket.save()
        return {"message": f"Ticket '{ticket.ticket_name}' updated successfully!", "updated_fields": updated_fields}
    else:
        return {"message": "No changes detected, ticket remains the same."}