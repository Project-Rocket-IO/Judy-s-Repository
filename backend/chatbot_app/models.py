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
from accounts.models import MyBaseModel, TechnicianUser
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

PROJECT_STATUS = (
    ("New", "New"),
    ("In Progress", "In Progress"),
    ("Scheduled", "Scheduled"),
    ("Follow Up", "Follow Up"),
    ("Reviewing", "Reviewing"),
    ("Observing", "Inprogress"),
    ("Waiting on Client", "Waiting on Client"),
    ("Waiting on Vendor", "Waiting on Vendor"),
    ("Waiting on Client", "Waiting on Client"),
    ("Postponed", "Postponed"),
    ("Post to Call Waiting", "Post to Call Waiting"),
    ("Completed", "Completed"),
)

PRIORITY = (
    ("Emergency", "Emergency"),
    ("High", "High"),
    ("Low", "Low"),
    ("Medium", "Medium"),
)

LABOR_INTERVAL = (
    ("6 Minute Intervals", "6 Minute Intervals"),
    ("15 Minute Intervals", "15 Minute Intervals"),
)

TYPE_CHOICE = (("Full Time", "Full Time"), ("Part Time", "Part Time"))

LABOR_TYPE = (
    ("6 Minute Intervals", "6 Minute Intervals"),
    ("15 Minute Intervals", "15 Minute Intervals"),
)

INDUSTRY_TYPE = (
    ("", "Select industry type"),
    ("Agriculture", "Agriculture"),
    ("Construction", "Construction"),
    ("Education", "Education"),
    ("Entertainment", "Entertainment"),
    ("Finance & Insurance", "Finance &  Insurance"),
    ("Healthcare", "Healthcare"),
    ("Higher Education", "Higher  Education"),
    ("Hospitality", "Hospitality"),
    ("Information Technology", "Information  Technology"),
    ("Manufacturing", "Manufacturing"),
    ("Nonprofit", "Nonprofit"),
    ("Professional Services", "Professional  Services"),
    ("Real Estate", "Real  Estate"),
    ("Retail", "Retail"),
    ("Telecommunications", "Telecommunications"),
    ("Transportation", "Transportation"),
    ("Utilities", "Utilities"),
    ("Wholesale", "Wholesale"),
)

class ChatHistory(models.Model):
    user_input = models.TextField()
    bot_response = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Chat at {self.timestamp}"
    
class TicketList(models.Model):
    identifier = models.AutoField(primary_key=True) 
    name = models.CharField(max_length=150)
    description = RichTextField(default="Add description for Ticket: ", null=True, blank=True)
    client = models.ForeignKey('ClientCompany', on_delete=models.CASCADE)
    assignment = models.ManyToManyField(TechnicianUser)
    create_date = models.DateField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    end_date = models.DateField(null=True, blank=True)
    due_date = models.DateField(blank=True, null=True)
    ticket_type = models.CharField(max_length=50, choices=TYPE_CHOICE, null=True, blank=True)
    status = models.CharField(max_length=50, choices=TICKET_STATUS)
    priority = models.CharField(max_length=10,choices=PRIORITY, null=True, blank=True)
    project = models.ForeignKey('ProjectList', on_delete=models.CASCADE, blank=True, null=True)

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
        
class ProjectList(models.Model):
    identifier = models.AutoField(primary_key=True) 
    name = models.CharField(max_length=50)
    client = models.ForeignKey('ClientCompany', on_delete=models.CASCADE)   
    description = RichTextField(default="Please add Project description... ", null=True, blank=True)
    create_date = models.DateField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    end_date = models.DateField(blank=True, null=True)
    due_date = models.DateField(blank=True, null=True)
    assignment = models.ManyToManyField(TechnicianUser)
    status = models.CharField(
        max_length=50, choices=PROJECT_STATUS, blank=True, null=True
    )
    priority = models.CharField(max_length=10, choices=PRIORITY, null=True, blank=True)
    

    # Metadata
    class Meta:
        ordering = ["-name"]
        permissions = [
            ("view_own_projects", "Can view their own projects"),
            # ("view_estimated_work", "Can view estimated work"),
            ("assign_own_project", "Can assign themselves to a project"),
            ("assign_other_project", "Can assign others to a project"),

        ]

    @property
    def identifier_thousand(self):
        thousand = self.identifier + 1000
        return thousand

    def __str__(self):
        """String for representing the MyModelName object (in Admin site etc.)."""
        return self.name

class ClientCompany(MyBaseModel, models.Model):
    name = models.CharField(max_length=150)
    contact_first = models.CharField(max_length=50)
    contact_last = models.CharField(max_length=50)
    industry = models.CharField(max_length=50,choices=INDUSTRY_TYPE, blank=True, null=True)
    website = models.URLField(max_length=150, blank=True, null=True)
    date_added = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    email = models.EmailField(max_length=150, unique=True)
    main_tech = models.ForeignKey(TechnicianUser, on_delete=models.DO_NOTHING)
    
    class Meta:
        verbose_name_plural = "Crm Companies"

    def __str__(self):
        return self.name if self.name else repr(self)
