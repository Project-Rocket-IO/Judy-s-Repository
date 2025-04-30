#TODO: template file copied from AI
# In a new file, e.g., management/commands/assign_permissions.py
from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from your_app.models import TicketList, TechnicianUser, ClientCompany

class Command(BaseCommand):
    help = 'Assigns custom permissions to roles'

    def handle(self, *args, **options):
        # Create roles if they don't exist
        manager_role, _ = Group.objects.get_or_create(name='Manager')
        technician_role, _ = Group.objects.get_or_create(name='Technician')

        # Get content types
        ticket_ct = ContentType.objects.get_for_model(TicketList)
        technician_ct = ContentType.objects.get_for_model(TechnicianUser)
        client_ct = ContentType.objects.get_for_model(ClientCompany)

        # Assign permissions to Manager role
        manager_permissions = [
            Permission.objects.get(codename='view_tickets', content_type=ticket_ct),
            Permission.objects.get(codename='view_ticket_stats', content_type=ticket_ct),
            Permission.objects.get(codename='view_labor_stats', content_type=ticket_ct),
            Permission.objects.get(codename='view_estimated_work', content_type=ticket_ct),
            Permission.objects.get(codename='view_technicians', content_type=technician_ct),
            Permission.objects.get(codename='view_clients', content_type=client_ct),
        ]
        manager_role.permissions.add(*manager_permissions)

        # Assign permissions to Technician role
        technician_permissions = [
            Permission.objects.get(codename='view_tickets', content_type=ticket_ct),
            Permission.objects.get(codename='view_ticket_stats', content_type=ticket_ct),
        ]
        technician_role.permissions.add(*technician_permissions)

        self.stdout.write(self.style.SUCCESS('Successfully assigned permissions to roles'))