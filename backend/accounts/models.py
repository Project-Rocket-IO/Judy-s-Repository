from django.core.files import File
from django_tenants.utils import get_tenant_model, tenant_context
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.db import transaction
from django.conf import settings
from django.db import models
import re
import os
import random
import uuid

COUNTRY_CHOICES = (("United States", "United States"), ("Canada", "Canada"))


def random_img_users():
    chosen_file = random.choice(os.listdir(f"{settings.STATICFILES_DIRS[0]}/images/default/users"))
    img_path = f"/images/default/users/{chosen_file}" # /images/default/users/img-1.png
    return img_path

def user_directory_path(instance, filename):
    if hasattr(instance, 'technician'):
        return "user_{0}/{1}".format(instance.technician.id, filename)
    elif hasattr(instance, 'client'):
        return "user_{0}/{1}".format(instance.client.id, filename)

def validate_unique_user(user):
    if hasattr(user, "technician") and hasattr(user, "client"):
        raise ValidationError(
            "A user cannot be both a TechnicianUser and a ClientUser."
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


# Legitimate Models
class MyBaseModel(models.Model):
    optional_attrubite = {"null": True, "blank": True}
    address_1 = models.CharField(max_length=50, **optional_attrubite)
    address_2 = models.CharField(max_length=50, **optional_attrubite)
    city = models.CharField(max_length=50, **optional_attrubite)
    state = models.CharField(max_length=50, **optional_attrubite)
    zip = models.CharField(max_length=50, **optional_attrubite)
    country = models.CharField(
        max_length=50, choices=COUNTRY_CHOICES, **optional_attrubite
    )
    timezone = models.CharField(max_length=50, **optional_attrubite)
    phone = models.CharField(**optional_attrubite, validators=[validate_phone_or_fax])
    fax = models.CharField(**optional_attrubite, validators=[validate_phone_or_fax])

    # Metadata
    class Meta:
        abstract = True

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


class MSPAuthUserManager(BaseUserManager):

    def create_superuser(self, email, password, tenant=None, **other_fields):
        other_fields.setdefault('is_staff', True)
        other_fields.setdefault('is_active', True)
        other_fields.setdefault('is_superuser', True)
        if not email:
            raise ValueError("User must have an email")
        if not password:
            raise ValueError("User must have a password")
        if not other_fields.get('is_staff'):
            raise ValueError("SuperUser must have assigned is_staff=True")
        if not other_fields.get('is_superuser'):
            raise ValueError("SuperUser must have assigned is_superuser=True")

        # Default tenant to 'public' schema if not provided
        TenantModel = get_tenant_model()

        if tenant:
            tenant = TenantModel.objects.get(schema_name=tenant)    
            with tenant_context(tenant):
                self.create_user(email, password, **other_fields)
        else:
            self.create_user(email, password, **other_fields)
    

    def create_user(self, email, password=None, **other_fields):
        """Create a plain MSPAuthUser with TechnicianUser profile.
         Important for Social Authentication, Google Auth"""
        with transaction.atomic():
            user = self.model(
                email=self.normalize_email(email), **other_fields)
            
            # Password provided or not, difference will come from
            # command line or social auth
            if password: user.set_password(password)
            else: 
                user.password_needs_change = True

            user.save()
            # Create a Technician whenever creating an auth user
            TechnicianUser.objects.create(auth_user=user)
            return user


# Create your views here.
class MSPAuthUser(AbstractUser, MyBaseModel):
    """MSPAuthUser Model for Authentication and Authorization
    can either be a TechnicianUser or ClientUser etc."""

    optional_attribute = {"null": True, "blank": True}
    first_name = models.CharField(max_length=50, **optional_attribute)
    last_name = models.CharField(max_length=50, **optional_attribute)
    middle_initial = models.CharField(max_length=50, **optional_attribute)
    username = models.CharField(max_length=30, unique=True)
    email = models.EmailField(max_length=150, unique=True)
    picture = models.ImageField(upload_to=user_directory_path, **optional_attribute)
    cover = models.ImageField(upload_to=user_directory_path, **optional_attribute)
    password_needs_change = models.BooleanField(default=False)
    title = models.CharField(max_length=50, **optional_attribute)
    user_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    REQUIRED_FIELDS = ["username"]
    USERNAME_FIELD = "email"
    objects = MSPAuthUserManager()

    @property
    def get_profile_picture(self):
        if self.picture:
            return self.picture.url
        # First time rendering will save a default image
        if not self.picture:
            picture_path = random_img_users()
            picture_path = settings.STATICFILES_DIRS[0] + picture_path
            self.picture.save(
                os.path.basename(picture_path), 
                File(open(picture_path, 'rb'))
            )
        return self.picture.url
    
    @property
    def get_title(self):
        if self.title:
            return self.title
        return ''
    
    @property
    def get_name(self):
        if self.first_name is not None and self.last_name is not None:
            return self.first_name + self.last_name
        if self.first_name is not None and self.last_name is None:
            return self.first_name
        return self.username

    class Meta:
        abstract = False

    def __str__(self):
        """String for representing the MyModelName object (in Admin site etc.)."""
        return f"{self.username}"
    


class TechnicianUser(models.Model):
    """Technician User Model inheriting from MSPAuthUser."""

    auth_user = models.OneToOneField(
        MSPAuthUser, on_delete=models.CASCADE, related_name="technician"
    )

    def __str__(self):
        return str(self.auth_user)


    @property
    def role(self):
        return self.auth_user.groups.first()
    
    
    def get_role_display(self):
        return self.auth_user.groups.first()

    def clean(self):
        validate_unique_user(self.auth_user)
        super().clean()

    class Meta:
        verbose_name = "Technician User"
        verbose_name_plural = "Technician Users"
        unique_together = ("auth_user",)
        permissions = [
            ("view_technicians", "Can view technician list"),
        ]

        