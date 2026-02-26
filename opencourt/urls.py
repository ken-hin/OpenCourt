# urls.py — URL routes for the opencourt app.
#
# Map URL patterns to views defined in opencourt/views.py.
# This file is included in the project-level config/urls.py via include().
# The app_name enables URL namespacing (e.g. {% url 'opencourt:home' %}).

from django.urls import path
from . import views

app_name = 'opencourt'

urlpatterns = [
    path('', views.HomeView.as_view(), name='home'),
    # Additional URLs will be added here (e.g. team list, team detail, conferences)
    path('about/', views.AboutView.as_view(), name='about'),
    path('teams/', views.TeamListView.as_view(), name='teams'),
]
