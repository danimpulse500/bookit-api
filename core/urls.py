from django.urls import path
from .views import CustomRegisterView, ListingListCreateView, ListingDetailView

app_name = 'core'

urlpatterns = [
    path('auth/register/', CustomRegisterView.as_view(), name='user-register'),
    path('listings/', ListingListCreateView.as_view(), name='listing-list-create'),
    path('listings/<int:pk>/', ListingDetailView.as_view(), name='listing-detail'),
]