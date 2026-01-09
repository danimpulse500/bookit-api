import os
import django
from rest_framework import serializers

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from core.models import AMENITY_CHOICES
from core.serializers import ListingSerializer

print("--- Testing Amenity Choices ---")

# Mock request and user
from rest_framework.request import Request
from rest_framework.test import APIRequestFactory
from django.contrib.auth import get_user_model
User = get_user_model()
factory = APIRequestFactory()
request = factory.get('/')
request.user = User.objects.first()

print(f"Amenities Choices: {[c[0] for c in AMENITY_CHOICES]}")

# Test Valid Data
valid_data = {
    "lodge_name": "Amenity Test Lodge",
    "description": "Test Description",
    "price": 50000,
    "location": "IFITE_ANAMBRA",
    "amenities": {"WIFI", "GYM"}, # Set of choices
    "agent": request.user.id
}
# Note: MultipleChoiceField accepts set or list

serializer = ListingSerializer(data=valid_data, context={'request': request})
if serializer.is_valid():
    print("VALID data passed validation.")
    print(f"Validated amenities: {serializer.validated_data.get('amenities')}")
else:
    print(f"VALID data FAILED validation: {serializer.errors}")

# Test Invalid Data
invalid_data = valid_data.copy()
invalid_data['amenities'] = {'INVALID_CHOICE', 'WIFI'}

serializer = ListingSerializer(data=invalid_data, context={'request': request})
if not serializer.is_valid():
    print("INVALID data correctly failed validation.")
    print(f"Errors: {serializer.errors.get('amenities')}")
else:
    print("INVALID data passed validation (Unexpected!)")
