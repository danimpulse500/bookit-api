import os
import django
import random

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from core.models import Listing

# Sample amenities to choose from
AMENITIES_POOL = [
    "WiFi",
    "Parking",
    "Swimming Pool",
    "Gym",
    "Air Conditioning",
    "24/7 Security",
    "Power Backup",
    "Balcony",
    "Furnished",
    "Kitchen",
    "TV",
    "Washing Machine"
]

print("--- Populating Amenities for Listings ---")

listings = Listing.objects.all()
count = listings.count()
print(f"Found {count} listings.")

if count == 0:
    print("No listings found. create some listings first.")
else:
    for listing in listings:
        # Check if amenities are already set
        if not listing.amenities:
            # Pick 3-6 random amenities
            num_amenities = random.randint(3, 6)
            selected_amenities = random.sample(AMENITIES_POOL, num_amenities)
            
            listing.amenities = selected_amenities
            listing.save()
            print(f"Added amenities to '{listing.lodge_name}': {selected_amenities}")
        else:
            print(f"Listing '{listing.lodge_name}' already has amenities: {listing.amenities}")

print("--- Done ---")
