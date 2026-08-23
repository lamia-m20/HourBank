"""
URL configuration for HourBank project.
"""

from django.contrib import admin
from django.urls import include, path


urlpatterns = [
    # لوحة الإدارة
    path('admin/', admin.site.urls),

    # الصفحة الرئيسية
    path('', include('marketplace.urls')),

    # تطبيقات المشروع
    path('accounts/', include('accounts.urls')),
    path('skills/', include('skills.urls')),
    path('exchanges/', include('exchanges.urls')),
    path('wallet/', include('wallet.urls')),
    path('communications/', include('communications.urls')),
]