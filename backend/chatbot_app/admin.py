from django.contrib import admin
from .models import User, ChatHistory

# Register the models with the admin site
admin.site.register(User)
admin.site.register(ChatHistory)