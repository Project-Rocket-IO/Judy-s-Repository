import re
from django import forms
from .models import TechnicianUser, MSPAuthUser

class CleanPhoneFaxParent:
    def clean_phone(self):
        phone = self.cleaned_data.get('phone')
        # Reuse the validator logic here
        if phone:
            if re.match(r'^\+\d{1,4}$', str(phone)):
                return ""  # Remove the phone number if it's just the international code
        
        return phone  # Return the validated phone number if it doesn't match the criteria

    def clean_fax(self):
        fax = self.cleaned_data.get('fax')
        # Reuse the validator logic here
        if fax:
            if re.match(r'^\+\d{1,4}$', str(fax)):
                return ""  # Remove the fax number if it's just the international code
        
        return fax 


class TechnicianUserForm(forms.ModelForm):
    class Meta:
        model = TechnicianUser
        fields = '__all__'


class MSPAuthUserForm(forms.ModelForm, CleanPhoneFaxParent):
    class Meta:
        model = MSPAuthUser
        fields = [
            # BaseModel
            "address_1",
            "address_2",
            "city",
            "state",
            "zip",
            "country",
            "timezone",
            "phone",

            # MSPAuthUser
            "first_name",
            "last_name",
            "middle_initial",
            "username",
            "email",
            "picture",
            "cover",
            "password_needs_change",
            "title",
        ]
