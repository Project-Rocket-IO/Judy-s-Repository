from django.db import models
from django.core.files import File as DjangoFile
# from auditlog.models import AuditlogHistoryField
# from auditlog.registry import auditlog
from django.conf import settings
from datetime import date
from django.db import models
from ckeditor.fields import RichTextField
# from taggit.managers import TaggableManager
# from accounts.models import MyBaseModel, TechnicianUser, MSPAuthUser
from django.core.exceptions import ValidationError
import random
import re
import os
import pytz

TYPE_CHOICE = (("Full Time", "Full Time"), ("Part Time", "Part Time"))

TICKET_STATUS = (
    ("New", "New"),
    ("In Progress", "In Progress"),
    ("Scheduled", "Scheduled"),
    ("Postponed", "Postponed"),
    ("Waiting on Client", "Waiting on Client"),
    ("Waiting on Vendor", "Waiting on Vendor"),
    ("Follow-Up", "Follow-Up"),
    ("Need to Post", "Need to Post"),
    ("Completed", "Completed"),
    ("Closed", "Closed"),
)

PRIORITY = (
    ("Emergency", "Emergency"),
    ("High", "High"),
    ("Low", "Low"),
    ("Medium", "Medium"),
)

class User(models.Model):
    name = models.CharField(max_length=255, unique=True)
    age = models.IntegerField()
    gender = models.CharField(max_length=10)

    def __str__(self):
        return self.name

class ChatHistory(models.Model):
    user_input = models.TextField()
    bot_response = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Chat at {self.timestamp}"
    
class TicketList(models.Model):
    #logo = models.ImageField(upload_to=ticket_directory_path, blank=True, null=True)
    identifier = models.AutoField(primary_key=True) 
    name = models.CharField(max_length=150)
    description = RichTextField(default="Add description for Ticket: ", null=True, blank=True)
    #client = models.ForeignKey('ClientCompany', on_delete=models.CASCADE)
    #assignment = models.ManyToManyField(TechnicianUser)
    create_date = models.DateField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    end_date = models.DateField(null=True, blank=True)
    due_date = models.DateField(blank=True, null=True)
    ticket_type = models.CharField(max_length=50, choices=TYPE_CHOICE, null=True, blank=True)
    status = models.CharField(max_length=50, choices=TICKET_STATUS)
    priority = models.CharField(max_length=10,choices=PRIORITY, null=True, blank=True)
    #project = models.ForeignKey('ProjectList', on_delete=models.CASCADE, blank=True, null=True)
    #tag = TaggableManager(blank=True)
    #files = models.FileField(upload_to=ticket_directory_path, blank=True, null=True)
    # slug = models.SlugField(max_length=50)
    # labor = models.ForeignKey(TechnicianLabor,
    #     on_delete=models.CASCADE,
    #     default="Pick Labor"
    # )

    # Metadata
    class Meta:
        ordering = ["-identifier"]
        permissions = [
            ("view_own_tickets", "Can view own tickets"),
            ("view_ticket_stats", "Can view ticket statistics"),
            ("view_estimated_work", "Can view estimated work"),
            ("assign_own_ticket", "Can assign themselves to a ticket"),
            ("assign_other_ticket", "Can assign others to a ticket"),
            ("complete_ticket", "Can mark a ticket as Completed"),
            ("close_ticket", "Can mark a ticket as Closed"),
        ]

    # Methods
    @property
    def days_until(self):
        if self.due_date: 
            date_diff = self.due_date - date.today()
            day_until = date_diff.days
        else: 
            day_until = 0
        return day_until
    
    @property
    def identifier_thousand(self):
        thousand = self.identifier + 1000
        return thousand

    # def get_photo_url(self):
    #     if self.logo and hasattr(self.logo, "url"):
    #         return self.logo.url
    #     else:
    #         return "/static/images/galaxy/img-1.jpg"
        
