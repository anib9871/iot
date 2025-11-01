from django.contrib import admin
from django.urls import path, include
from django.shortcuts import redirect
urlpatterns = [
     path('', lambda request: redirect('login'), name='root_redirect'),  # root pe login
    path('admin/', admin.site.urls),
    path('', include('iot_api.urls')),  # iot_api ke sab endpoints
    path('api/', include('iot_api.urls')),
]
