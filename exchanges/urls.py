from django.urls import path

from . import views


app_name = 'exchanges'

urlpatterns = [
    path('requests/notifications/', views.request_notifications, name='request_notifications'),
    path('requests/', views.exchange_requests, name='requests'),
    path('sessions/', views.sessions, name='sessions'),
    path('requests/<int:pk>/accept/', views.accept_request, name='accept_request'),
    path('requests/<int:pk>/reject/', views.reject_request, name='reject_request'),
    path('requests/<int:pk>/cancel/', views.cancel_request, name='cancel_request'),
    path('session/<int:pk>/room/', views.session_room, name='session_room'),
    path('session/<int:pk>/messages/', views.room_messages, name='room_messages'),
    path('session/<int:pk>/signals/', views.room_signals, name='room_signals'),
    path('session/<int:pk>/finish/', views.finish_session, name='finish_session'),
    path('session/<int:pk>/confirm/', views.confirm_session, name='confirm_session'),
    path('session/<int:pk>/issue/', views.report_issue, name='report_issue'),
]
