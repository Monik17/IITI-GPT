from django.urls import path
from . import views
from .home_view import home
from .reminder_view import reminder, delete_reminder

urlpatterns = [
    path('get_map/', views.get_map, name='get_map'),
    path('', home, name='home'),
    path('signup/', views.signup, name='signup'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('navigation/', views.navigation_home, name='navigation_home'),
    path('reminder/', reminder, name='reminder'),
    path('reminder/delete/<int:reminder_id>/', delete_reminder, name='delete_reminder'),
]