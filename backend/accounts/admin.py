from .models import MSPAuthUser, TechnicianUser
from django.contrib import admin


@admin.register(MSPAuthUser)
class MSPAuthUserListAdmin(admin.ModelAdmin):
    list_display = [
        'first_name',
        'last_name',
        'middle_initial',
        'username',
        'email',
        'phone',
        'picture',
        'cover',
        'password_needs_change',
        'title',
        'user_id',
    ]



@admin.register(TechnicianUser)
class TechnicianListAdmin(admin.ModelAdmin):
    list_display = ["auth_user", "role"]

    def get_role(self):
        return self.auth_user.groups.first()
