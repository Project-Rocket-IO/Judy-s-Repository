from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from django_tenants.models import TenantMixin, DomainMixin
from accounts.models import MyBaseModel
from django.db import models
import re
import uuid

COUNTRY_CHOICES = (
    ('United States', 'United States'),
    ('Canada', 'Canada')
)


INDUSTRY_TYPE = (
    ('','Select industry type'),
    ('Agriculture', 'Agriculture'),
    ('Construction', 'Construction'),
    ('Education', 'Education'),
    ('Entertainment', 'Entertainment'),
    ('Finance & Insurance', 'Finance &  Insurance'),
    ('Healthcare', 'Healthcare'),
    ('Higher Education', 'Higher  Education'),
    ('Hospitality', 'Hospitality'),
    ('Information Technology', 'Information  Technology'),
    ('Manufacturing', 'Manufacturing'),
    ('Nonprofit', 'Nonprofit'),
    ('Professional Services', 'Professional  Services'),
    ('Real Estate', 'Real  Estate'),
    ('Retail', 'Retail'),
    ('Telecommunications', 'Telecommunications'),
    ('Transportation', 'Transportation'),
    ('Utilities', 'Utilities'),
    ('Wholesale', 'Wholesale')
)

def validate_phone_or_fax(value):
    if value:
        phone_number_str = str(value)
        # Check if it's only the international code
        if re.match(r'^\+\d{1,4}$', phone_number_str):
            return
        # Optional: Further relaxed validations, e.g., length check (but not strict)
        digits_only = re.sub(r'\D', '', phone_number_str)  # Strip all non-numeric characters
        if len(digits_only) < 10 or len(digits_only) > 15:  # Basic length check for phone numbers
            raise ValidationError("Phone number or fax number seems incorrect.")



class MyBaseModel(models.Model):
    optional_attrubite = {"null": True, "blank": True}

    address_1 = models.CharField(max_length=50)
    address_2 = models.CharField(max_length=50, null=True, blank=True)
    city = models.CharField(max_length=50)
    state = models.CharField(max_length=50)
    zip = models.CharField(max_length=50)
    country = models.CharField(max_length=50, choices=COUNTRY_CHOICES)
    timezone = models.CharField(max_length=50)
    phone = models.CharField(**optional_attrubite, validators=[validate_phone_or_fax])
    fax = models.CharField(**optional_attrubite, validators=[validate_phone_or_fax])

    # Metadata
    class Meta:
        abstract = True

        # Methods
    def get_phone(self):
        if self.phone:
            return self.phone
        else:
            return self.company.phone
        
    def get_fax(self):
        if self.fax:
            return self.fax
        else:
            return self.company.fax

class MspCompany(MyBaseModel, TenantMixin):
    company_name = models.CharField(max_length=60)
    industry_type = models.CharField(max_length=68, choices=INDUSTRY_TYPE)
    email = models.EmailField(max_length=150, unique=True)
    owner_name = models.CharField(max_length=60, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    picture = models.ImageField(upload_to='images/company',blank=True,null=True)
    users = models.ForeignKey(get_user_model(), 
                            related_name='users',
                            on_delete=models.CASCADE,
                            blank=True,
                            null=True
                            )
    # subscription = models.ForeignKey('djstripe.Subscription', 
    #                                  null=True,
    #                                  blank=True,
    #                                  help_text="The team's Stripe Subscription object, if it exists",
    #                                  on_delete=models.CASCADE
    #)
    company_id = models.UUIDField(
    primary_key = True,
    default = uuid.uuid1,
    editable = False
    )

    auto_create_schema = True
    # Metadata
    class Meta:
        pass

    # Methods
    def get_photo_url(self):
        if self.profile_pic and hasattr(self.picture, 'url'):
            return self.picture.url
        else:
            return "/static/images/users/user-dummy-img.jpg"

class Domain(DomainMixin):
    pass
