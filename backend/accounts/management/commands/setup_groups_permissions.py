from django.core.management.base import BaseCommand
from django.core.management import call_command
from django.contrib.auth.models import Group, Permission
from django.conf import settings
from pathlib import Path
import json

class Command(BaseCommand):
    help = 'Set up groups and permissions from a JSON file'

    def handle(self, *args, **kwargs):
        file_path = settings.BASE_DIR / 'src' / 'json' / 'groups_and_permissions.json'
        print(file_path)
        if not file_path.exists():
            self.stdout.write(self.style.ERROR('File not found.'))
            return
        
        with open(file_path, 'r') as file:
            data = json.load(file)
            for item in data:
                group, created = Group.objects.get_or_create(name=item['fields']['name'])
                permissions = item['fields']['permissions']
                for perm in permissions:
                    permission = Permission.objects.get(codename=perm)
                    group.permissions.add(permission)
                group.save()

        self.stdout.write(self.style.SUCCESS('Groups and permissions set up successfully!'))


