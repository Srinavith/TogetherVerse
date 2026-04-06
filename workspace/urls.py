from django.urls import path
from . import views

urlpatterns = [
    # Landing
    path('', views.landing_view, name='landing'),

    # Auth
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),

    # Rooms
    path('rooms/', views.room_list, name='room_list'),
    path('rooms/create/', views.create_room, name='create_room'),
    path('rooms/<slug:slug>/', views.room_detail, name='room_detail'),
    path('rooms/<slug:slug>/join/', views.join_room, name='join_room'),
    path('rooms/<slug:slug>/leave/', views.leave_room, name='leave_room'),
]