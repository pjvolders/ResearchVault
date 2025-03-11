from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    path('', views.home_view, name='home'),
    path('publications/', views.PublicationListView.as_view(), name='publication_list'),
    path('publications/<int:pk>/', views.PublicationDetailView.as_view(), name='publication_detail'),
]