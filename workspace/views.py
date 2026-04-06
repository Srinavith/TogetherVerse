from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils.text import slugify
from django.contrib.auth.models import User
from .models import Room, RoomMembership, Message, Document, ActivityLog


# ─────────────────────────────────────────
# LANDING
# ─────────────────────────────────────────

def landing_view(request):
    if request.user.is_authenticated:
        return redirect('room_list')
    return render(request, 'workspace/landing.html')


# ─────────────────────────────────────────
# AUTH
# ─────────────────────────────────────────

def register_view(request):
    if request.user.is_authenticated:
        return redirect('room_list')
    form = UserCreationForm(request.POST or None)
    if request.method == 'POST':
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, f'Welcome to TogetherVerse, {user.username}! 🎉')
            return redirect('room_list')
        else:
            messages.error(request, 'Please fix the errors below.')
    return render(request, 'workspace/register.html', {'form': form})


def login_view(request):
    if request.user.is_authenticated:
        return redirect('room_list')
    form = AuthenticationForm(data=request.POST or None)
    if request.method == 'POST':
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            messages.success(request, f'Welcome back, {user.username}!')
            next_url = request.GET.get('next', 'room_list')
            return redirect(next_url)
        else:
            messages.error(request, 'Invalid username or password.')
    return render(request, 'workspace/login.html', {'form': form})


def logout_view(request):
    logout(request)
    messages.success(request, 'You have been logged out.')
    return redirect('login')


# ─────────────────────────────────────────
# ROOMS
# ─────────────────────────────────────────

@login_required
def room_list(request):
    # All public rooms
    all_rooms = Room.objects.filter(is_private=False).order_by('-created_at')

    # Rooms the current user is a member of
    my_room_ids = RoomMembership.objects.filter(
        user=request.user, is_active=True
    ).values_list('room_id', flat=True)
    my_rooms = Room.objects.filter(id__in=my_room_ids).order_by('-created_at')

    return render(request, 'workspace/room_list.html', {
        'all_rooms': all_rooms,
        'my_rooms': my_rooms,
    })


@login_required
def create_room(request):
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        description = request.POST.get('description', '').strip()
        is_private = request.POST.get('is_private') == 'on'

        if not name:
            messages.error(request, 'Room name cannot be empty.')
            return redirect('create_room')

        # Auto-generate unique slug
        base_slug = slugify(name)
        slug = base_slug
        counter = 1
        while Room.objects.filter(slug=slug).exists():
            slug = f'{base_slug}-{counter}'
            counter += 1

        # Check duplicate name
        if Room.objects.filter(name=name).exists():
            messages.error(request, 'A room with that name already exists.')
            return redirect('create_room')

        # Create room
        room = Room.objects.create(
            name=name,
            slug=slug,
            description=description,
            created_by=request.user,
            is_private=is_private
        )

        # Create the document for this room automatically
        Document.objects.create(room=room)

        # Make creator the owner
        RoomMembership.objects.create(
            user=request.user,
            room=room,
            role='owner'
        )

        # Log it
        ActivityLog.objects.create(
            room=room,
            user=request.user,
            action='created',
            detail=f'{request.user.username} created the room.'
        )

        messages.success(request, f'Room "{name}" created successfully!')
        return redirect('room_detail', slug=room.slug)

    return render(request, 'workspace/create_room.html')


@login_required
def join_room(request, slug):
    room = get_object_or_404(Room, slug=slug)

    # Check if already a member
    membership = RoomMembership.objects.filter(
        user=request.user, room=room
    ).first()

    if membership:
        if membership.is_active:
            messages.info(request, f'You are already a member of "{room.name}".')
        else:
            # Re-activate if they had left before
            membership.is_active = True
            membership.save()
            messages.success(request, f'Welcome back to "{room.name}"!')
    else:
        RoomMembership.objects.create(
            user=request.user,
            room=room,
            role='editor'
        )
        ActivityLog.objects.create(
            room=room,
            user=request.user,
            action='joined',
            detail=f'{request.user.username} joined the room.'
        )
        messages.success(request, f'You joined "{room.name}"!')

    return redirect('room_detail', slug=room.slug)


@login_required
def leave_room(request, slug):
    room = get_object_or_404(Room, slug=slug)
    membership = RoomMembership.objects.filter(
        user=request.user, room=room, is_active=True
    ).first()

    if membership:
        if membership.role == 'owner':
            messages.error(request, 'Owners cannot leave their own room.')
            return redirect('room_detail', slug=slug)
        membership.is_active = False
        membership.save()
        ActivityLog.objects.create(
            room=room,
            user=request.user,
            action='left',
            detail=f'{request.user.username} left the room.'
        )
        messages.success(request, f'You left "{room.name}".')
    else:
        messages.error(request, 'You are not a member of this room.')

    return redirect('room_list')


@login_required
def room_detail(request, slug):
    room = get_object_or_404(Room, slug=slug)

    # Check membership
    membership = RoomMembership.objects.filter(
        user=request.user, room=room, is_active=True
    ).first()

    is_member = membership is not None
    is_owner = membership.role == 'owner' if membership else False

    # Get active members
    members = RoomMembership.objects.filter(
        room=room, is_active=True
    ).select_related('user')

    # Get last 50 messages
    chat_messages = Message.objects.filter(
        room=room
    ).select_related('user').order_by('timestamp')[:50]

    # Get document
    document = getattr(room, 'document', None)

    # Get activity log
    activity = ActivityLog.objects.filter(room=room).order_by('-timestamp')[:10]

    return render(request, 'workspace/room_detail.html', {
        'room': room,
        'membership': membership,
        'is_member': is_member,
        'is_owner': is_owner,
        'members': members,
        'chat_messages': chat_messages,
        'document': document,
        'activity': activity,
    })