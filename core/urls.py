from django.contrib import admin
from django.conf.urls.static import static
from django.http import HttpResponse
from django.urls import path, include
from . import settings
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView


def health_check(request):
    return HttpResponse("OK", status=200)


urlpatterns = [
    path('health/', health_check, name='health_check'),


    path('auth/', include('accounts.urls')),
    path('exams/',include('exams.urls')),
    path('challenges/', include('challenges.urls')),
    path("ckeditor5/", include('django_ckeditor_5.urls')),
    path(settings.ADMIN_URL, admin.site.urls),
]

# Serve media files via Django's dev server in development
if settings.DEBUG:
    urlpatterns += [
        path('docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
        path('schema/', SpectacularAPIView.as_view(), name='schema'),
        path('redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
    ]

    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
