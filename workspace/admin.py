from django.contrib import admin
from .models import Room, RoomMembership, Message, Document, ActivityLog


@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'created_by', 'is_private', 'created_at']
    prepopulated_fields = {'slug': ('name',)}  # auto-fills slug from name
    search_fields = ['name']


@admin.register(RoomMembership)
class RoomMembershipAdmin(admin.ModelAdmin):
    list_display = ['user', 'room', 'role', 'joined_at', 'is_active']
    list_filter = ['role', 'is_active']


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ['user', 'room', 'content', 'timestamp', 'is_system_message']
    list_filter = ['room', 'is_system_message']


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ['room', 'last_edited_by', 'last_edited_at']


@admin.register(ActivityLog)
class ActivityLogAdmin(admin.ModelAdmin):
    list_display = ['user', 'room', 'action', 'detail', 'timestamp']
    list_filter = ['action', 'room']