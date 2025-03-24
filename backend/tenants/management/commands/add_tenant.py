from django.core.management.base import BaseCommand
from tenants.models import MspCompany, Domain 
import uuid

class Command(BaseCommand):
    help = 'Create a new tenant'

    def add_arguments(self, parser):
        parser.add_argument('company_name', type=str)
        parser.add_argument('email', type=str)
        parser.add_argument('domain', type=str)

    def handle(self, *args, **kwargs):
        company_name = kwargs['company_name']
        email = kwargs['email']
        domain = kwargs['domain']
        
        schema_name = domain.split('.')[0].lower() 

        # Create the tenant
        tenant = MspCompany(
            company_name=company_name,
            email=email,
            schema_name=schema_name,
            company_id=uuid.uuid1(),
        )
        tenant.save()

        # Create domain for the tenant
        Domain.objects.create(domain=domain, tenant=tenant)

        self.stdout.write(self.style.SUCCESS(f'Successfully created tenant: {company_name} with domain: {domain}'))
