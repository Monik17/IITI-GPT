from django.contrib import admin
from django.urls import path, include
from django.views.generic import RedirectView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('navigation/', include('navigation.urls')),
    path('chatbot/', include('chatbot.urls')),
    path('', RedirectView.as_view(url='/navigation/login/', permanent=False), name='root'),
    path('accounts/', include('django.contrib.auth.urls')),  # Add this line
]