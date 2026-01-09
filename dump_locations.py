import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from core.models import Location 

try:
    locations = Location.objects.all().values_list('name', flat=True)
    print("--- EXISTING LOCATIONS ---")
    for loc in locations:
        print(loc)
    print("--------------------------")
except Exception as e:
    print(f"Error reading locations (maybe table is empty or deleted?): {e}")
