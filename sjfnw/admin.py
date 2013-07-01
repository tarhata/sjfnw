from django.contrib import admin
from django.contrib.admin.sites import AdminSite
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User, Group, Permission
from django.contrib.contenttypes.models import ContentType

advanced_admin = AdminSite(name='advanced')

admin.site.unregister(Group)

advanced_admin.register(User, UserAdmin)
advanced_admin.register(Group)
advanced_admin.register(Permission)
advanced_admin.register(ContentType)

