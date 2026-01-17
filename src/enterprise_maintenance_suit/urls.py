from django.urls import path
from .views import maintenance_status_view

urlpatterns = [
    path('maintenance/status/', maintenance_status_view, name='maintenance_status'),
]