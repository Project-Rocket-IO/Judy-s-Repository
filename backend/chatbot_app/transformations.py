from difflib import get_close_matches
from .models import ClientCompany  # Assuming Client is the model storing existing clients

def find_existing_client(client_name):
    """Finds the closest matching client name from the database."""
    if not client_name:
        return None
    
    # Fetch all client names from the database
    existing_clients = list(ClientCompany.objects.values_list("name", flat=True))

    # Try to find an exact match
    if client_name in existing_clients:
        return client_name

    # Use fuzzy matching to find the closest name
    close_matches = get_close_matches(client_name, existing_clients, n=1, cutoff=0.6)
    
    return close_matches[0] if close_matches else None