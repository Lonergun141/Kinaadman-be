from django.contrib import admin
from django.urls import path
from config.api import api
from django.contrib.auth import logout
from django.shortcuts import redirect
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import TemplateView

admin.site.site_header = "Kinaadman Super Admin"
admin.site.site_title = "Kinaadman Dashboard"
admin.site.index_title = "Workspace Management"


def custom_admin_logout(request):
    """Django 5+ restricts admin logout to POST requests. 
    Custom UI themes often still use <a> tags (GET). This intercepts and logs them out."""
    logout(request)
    return redirect('/admin/login/')


urlpatterns = [
    path('', TemplateView.as_view(template_name='index.html'), name='home'),
    path('admin/logout/', custom_admin_logout),
    path('admin/', admin.site.urls),
    path('v1/', api.urls),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
