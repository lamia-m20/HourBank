from django.urls import path

from . import views


app_name = 'skills'

urlpatterns = [
    path('', views.explore, name='explore'),
    path('my-skills/', views.my_skills, name='my_skills'),
    path('create/', views.create_offer, name='create_offer'),
    path('offer/<int:pk>/', views.offer_detail, name='offer_detail'),
    path('offer/<int:pk>/edit/', views.offer_edit, name='offer_edit'),
    path('offer/<int:pk>/delete/', views.offer_delete, name='offer_delete'),
    path('offer/<int:pk>/toggle/', views.offer_toggle, name='offer_toggle'),
    path(
        'offer/<int:pk>/request/',
        views.request_session,
        name='request_session',
    ),
]
