from django.contrib import admin
from . models import MspCompany

# Register your models here.

@admin.register(MspCompany)
class MspCompanyAdmin(admin.ModelAdmin):
    list_display = ['company_name',]


