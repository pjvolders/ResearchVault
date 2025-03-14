from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    path('', views.home_view, name='home'),
    
    # Publication URLs
    path('publications/', views.PublicationListView.as_view(), name='publication_list'),
    path('publications/<int:pk>/', views.PublicationDetailView.as_view(), name='publication_detail'),
    
    # Dissertation URLs
    path('dissertations/', views.DissertationListView.as_view(), name='dissertation_list'),
    path('dissertations/<int:pk>/', views.DissertationDetailView.as_view(), name='dissertation_detail'),
]