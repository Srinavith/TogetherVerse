from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


class Room(models.Model):
    """A collaborative workspace room."""
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_rooms'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    is_private = models.BooleanField(default=False)

    def __str__(self):
        return self.name

    def get_member_count(self):
        return self.memberships.filter(is_active=True).count()


class RoomMembership(models.Model):
    """Tracks which users are members of which rooms."""

    ROLE_CHOICES = [
        ('owner', 'Owner'),
        ('editor', 'Editor'),
        ('viewer', 'Viewer'),
    ]

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='memberships'
    )
    room = models.ForeignKey(
        Room,
        on_delete=models.CASCADE,
        related_name='memberships'
    )
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='editor')
    joined_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        # A user can only have one membership per room
        unique_together = ('user', 'room')

    def __str__(self):
        return f"{self.user.username} in {self.room.name} ({self.role})"


class Message(models.Model):
    """A chat message sent inside a room."""
    room = models.ForeignKey(
        Room,
        on_delete=models.CASCADE,
        related_name='messages'
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='messages'
    )
    content = models.TextField()
    timestamp = models.DateTimeField(default=timezone.now)
    is_system_message = models.BooleanField(default=False)  # e.g. "John joined the room"

    class Meta:
        ordering = ['timestamp']

    def __str__(self):
        return f"{self.user.username} @ {self.room.name}: {self.content[:40]}"


class Document(models.Model):
    """The shared collaborative text document inside a room."""
    room = models.OneToOneField(
        Room,
        on_delete=models.CASCADE,
        related_name='document'
    )
    content = models.TextField(blank=True, default='')
    last_edited_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='edited_documents'
    )
    last_edited_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Document for room: {self.room.name}"


class ActivityLog(models.Model):
    """Tracks all significant actions inside a room."""

    ACTION_CHOICES = [
        ('joined', 'User Joined'),
        ('left', 'User Left'),
        ('edited', 'Document Edited'),
        ('messaged', 'Message Sent'),
        ('created', 'Room Created'),
    ]

    room = models.ForeignKey(
        Room,
        on_delete=models.CASCADE,
        related_name='activity_logs'
    )
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='activity_logs'
    )
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    detail = models.CharField(max_length=255, blank=True)
    timestamp = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['-timestamp']  # newest first

    def __str__(self):
        return f"{self.user} - {self.action} in {self.room} at {self.timestamp}"