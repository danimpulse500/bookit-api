from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager
from django.utils import timezone
from cloudinary.models import CloudinaryField


class UserManager(BaseUserManager):
    def create_user(self, email, full_name, phone_number, password=None, **extra_fields):
        if not email:
            raise ValueError("The Email field must be set")
        if not full_name:
            raise ValueError("The full name must be set")
        if not phone_number:
            raise ValueError("The phone number must be set")

        email = self.normalize_email(email)
        user = self.model(
            email=email,
            full_name=full_name,
            phone_number=phone_number,
            username=email,
            **extra_fields
        )
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, full_name, phone_number, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_agent", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        return self.create_user(email, full_name, phone_number, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):

    username = models.CharField(max_length=150, blank=True, null=True)
    email = models.EmailField(unique=True)
    full_name = models.CharField(max_length=255)
    phone_number = models.CharField(max_length=15)
    is_agent = models.BooleanField(default=False)
    agency_name = models.CharField(max_length=255, blank=True, null=True)  # Added agency_name field

    is_staff = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    date_joined = models.DateTimeField(default=timezone.now)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["full_name", "phone_number"]

    def __str__(self):
        return self.full_name



# Define Location Choices
LOCATION_CHOICES = [
    ('AROMA', 'Aroma'),
    ('AMANSEA', 'Amansea'),
    ('IFITE_ANAMBRA', 'Ifite Anambra'),
    ('IFITE UP SCHOOL', 'Ifite Up School'),
    ('IFITE DOWN SCHOOL', 'Ifite Down School'),
    ('TEMP SITE', 'Temp Site'),
    ('OTHER', 'Other'),
]

# First, create the Amenity model
class Amenity(models.Model):
    name = models.CharField(max_length=100)
    icon = models.CharField(max_length=100, blank=True, null=True, help_text="Icon class or URL")
    description = models.TextField(blank=True, null=True)
    
    def __str__(self):
        return self.name
    
    class Meta:
        verbose_name_plural = "Amenities"
        ordering = ['name']

# Removed AMENITY_CHOICES constant entirely

class Listing(models.Model):
    # Rename title to lodge_name (with db_column to preserve data)
    lodge_name = models.CharField(max_length=255, db_column='title')
    
    description = models.TextField()
    first_price = models.DecimalField(max_digits=10, decimal_places=2, db_column='price')
    year_price = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    
    # Change location to CharField with Choices
    location = models.CharField(
        max_length=100,
        choices=LOCATION_CHOICES,
        default='IFITE_ANAMBRA'
    )
    old_location = models.CharField(max_length=255, blank=True, null=True)  # Temporary field for migration
    
    # Room type choices
    ROOM_TYPE_CHOICES = [
        ('SELF_CONTAINED', 'Self Contained'),
        ('ONE_BEDROOM', 'One Bedroom'),
        ('TWO_BEDROOM', 'Two Bedroom'),
        ('STUDIO', 'Studio'),
        ('SHARED_ROOM', 'Shared Room'),
        ('SINGLE_ROOM', 'Single Room'),
        ('OTHER', 'Other'),
    ]
    
    room_type = models.CharField(
        max_length=50, 
        choices=ROOM_TYPE_CHOICES, 
        default='SELF_CONTAINED'
    )
    
    # Replace JSONField with ManyToManyField for amenities
    amenities = models.ManyToManyField(
        Amenity,
        related_name='listings',
        blank=True,
        help_text="Select amenities available in this listing"
    )
    
    # Room numbers
    total_rooms = models.PositiveIntegerField(default=1, help_text="Total number of rooms in the property")
    # available_rooms = models.PositiveIntegerField(default=1, help_text="Number of rooms available")
    
    # Remove bedrooms, add room_number
    # bedrooms = models.PositiveIntegerField(blank=True, null=True)  # Keep for migration, will remove later
    room_number = models.CharField(max_length=50, blank=True, null=True, help_text="Room/Unit number")
    
    # Keep bathrooms for now, can phase out later
    # bathrooms = models.PositiveIntegerField(blank=True, null=True)
    
    # Video field (Cloudinary supports videos too)
    video = CloudinaryField('video', blank=True, null=True, resource_type='video')
    
    # REMOVED: cover_image - Use first image from ListingImage instead
    # Agent and agency information
    agent = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='listings',
        limit_choices_to={'is_agent': True}  # Only agents can create listings
    )
    agency = models.CharField(max_length=255, blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Additional useful fields
    is_available = models.BooleanField(default=True)
    rules = models.TextField(blank=True, null=True)
    contact_phone = models.CharField(max_length=20, blank=True, null=True)
    contact_email = models.EmailField(blank=True, null=True)
    
    def __str__(self):
        return self.lodge_name
    
    @property
    def cover_image_url(self):
        """Get the URL of the first image as cover image"""
        first_image = self.images.first()
        if first_image:
            return first_image.image.url
        return None
    
    @property
    def cover_image(self):
        """Backward compatibility property"""
        return self.cover_image_url
    
    def save(self, *args, **kwargs):
        # Auto-populate agency from agent if not provided
        if not self.agency and self.agent and self.agent.agency_name:
            self.agency = self.agent.agency_name
            
        super().save(*args, **kwargs)
    
    class Meta:
        ordering = ['-created_at']
        db_table = 'core_listing'  # Keep original table name

class ListingImage(models.Model):
    listing = models.ForeignKey(Listing, on_delete=models.CASCADE, related_name='images')
    image = CloudinaryField('image')
    uploaded_at = models.DateTimeField(auto_now_add=True)
    is_primary = models.BooleanField(default=False, help_text="Mark as primary/cover image")

    def __str__(self):
        return f"Image for {self.listing.lodge_name}"
    
    def save(self, *args, **kwargs):
        # If this is marked as primary, unmark other primary images for this listing
        if self.is_primary:
            ListingImage.objects.filter(listing=self.listing, is_primary=True).update(is_primary=False)
        super().save(*args, **kwargs)
    
    class Meta:
        ordering = ['-is_primary', 'uploaded_at']