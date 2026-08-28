"""
URL configuration for HourBank project.
"""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from accounts.views import set_language


urlpatterns = [
    path('i18n/setlang/', set_language, name='set_language'),
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
    path('i18n/', include('django.conf.urls.i18n')),
]


# ==================================================
# تشغيل ملفات Media أثناء التطوير
# ==================================================

if settings.DEBUG:
    urlpatterns += static(
        settings.MEDIA_URL,
        document_root=settings.MEDIA_ROOT
    )

    urlpatterns += static(
        settings.STATIC_URL,
        document_root=settings.STATIC_ROOT
    )
