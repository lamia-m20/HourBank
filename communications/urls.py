from django.urls import path

from . import views


app_name = 'communications'

urlpatterns = [
    path('', views.conversation_list, name='conversation_list'),
    path('incoming-call/', views.incoming_call, name='incoming_call'),
    path('<int:pk>/', views.open_conversation, name='open_conversation'),
]
