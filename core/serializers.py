from rest_framework import serializers
from dj_rest_auth.registration.serializers import RegisterSerializer
from .models import User, Listing, ListingImage, Amenity
from allauth.account.adapter import get_adapter
from allauth.account import app_settings as allauth_settings
from dj_rest_auth.serializers import LoginSerializer
from django.contrib.auth import authenticate
from django.utils.translation import gettext_lazy as _
from django.contrib.auth import get_user_model


class CustomLoginSerializer(LoginSerializer):
    username = None  # Remove username field
    email = serializers.EmailField(required=True, allow_blank=False)
    
    def authenticate(self, **kwargs):
        return authenticate(self.context['request'], **kwargs)
    
    def get_auth_user_using_allauth(self, username, email, password):
        # Override to use email instead of username
        from allauth.account import app_settings
        from allauth.account.utils import filter_users_by_email
        
        User = get_user_model()
        
        if email:
            users = filter_users_by_email(email)
            if not users:
                raise serializers.ValidationError(
                    {'email': _('E-mail address is not verified.')}
                )
            user = users[0]
            if user.check_password(password):
                return user
        return None
    
    def get_auth_user(self, username, email, password):
        """
        Retrieve the auth user via allauth or Django's auth.
        Returns the authenticated user instance if credentials are correct,
        else raises ValidationError.
        """
        from allauth.account import app_settings as allauth_settings
        from allauth.account.utils import filter_users_by_email

        # Authentication through email
        if allauth_settings.AUTHENTICATION_METHOD == allauth_settings.AuthenticationMethod.EMAIL:
            return self.get_auth_user_using_allauth(username, email, password)

        # Authentication through username
        if allauth_settings.AUTHENTICATION_METHOD == allauth_settings.AuthenticationMethod.USERNAME:
            return self.get_auth_user_using_allauth(username, email, password)

        # Authentication through either username or email
        return self.get_auth_user_using_allauth(username, email, password)


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'full_name', 'phone_number', 
                 'is_agent', 'agency_name', 'date_joined', 'is_staff', 'is_active']
        read_only_fields = ['id', 'date_joined', 'is_staff', 'is_active']


class UserRegistrationSerializer(RegisterSerializer):
    full_name = serializers.CharField(required=True)
    phone_number = serializers.CharField(required=True)
    is_agent = serializers.BooleanField(default=False)
    agency_name = serializers.CharField(required=False, allow_blank=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Remove username field from validation since we're not using it
        self.fields.pop('username', None)

    def get_cleaned_data(self):
        """
        Get cleaned data including custom fields.
        """
        data = super().get_cleaned_data()
        # Generate a username from email
        email = data.get('email', '')
        if email:
            data['username'] = email.split('@')[0]  # Use part before @ as username
        
        # Add custom fields
        data.update({
            'full_name': self.validated_data.get('full_name', ''),
            'phone_number': self.validated_data.get('phone_number', ''),
            'is_agent': self.validated_data.get('is_agent', False),
            'agency_name': self.validated_data.get('agency_name', ''),
        })
        return data

    def custom_signup(self, request, user):
        """
        This method is automatically called by allauth after user creation.
        Set custom fields here.
        """
        user.full_name = self.cleaned_data.get('full_name', '')
        user.phone_number = self.cleaned_data.get('phone_number', '')
        user.is_agent = self.cleaned_data.get('is_agent', False)
        user.agency_name = self.cleaned_data.get('agency_name', '')
        
        # Set username to email if not set
        if not user.username:
            user.username = self.cleaned_data.get('email', '')
        
        user.save()


class AmenitySerializer(serializers.ModelSerializer):
    class Meta:
        model = Amenity
        fields = ['id', 'name', 'icon', 'description']
        read_only_fields = ['id']


class ListingImageSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()
    
    class Meta:
        model = ListingImage
        fields = ['id', 'image', 'image_url', 'uploaded_at', 'is_primary']
        read_only_fields = ['id', 'uploaded_at', 'image_url']

    def get_image_url(self, obj):
        return obj.image.url if obj.image else None


class ListingSerializer(serializers.ModelSerializer):
    images = ListingImageSerializer(many=True, read_only=True)
    cover_image_url = serializers.SerializerMethodField()
    location_display = serializers.CharField(source='get_location_display', read_only=True)
    
    # Updated to use AmenitySerializer for nested representation
    amenities = AmenitySerializer(many=True, read_only=True)
    
    # For writing/updating amenities (accept list of amenity names)
    amenity_names = serializers.ListField(
        child=serializers.CharField(max_length=100),
        write_only=True,
        required=False,
        help_text="List of amenity names (e.g., ['WiFi', 'Parking', 'Swimming Pool'])"
    )
    
    agent_detail = UserSerializer(source='agent', read_only=True)
    uploaded_images = serializers.ListField(
        child=serializers.ImageField(max_length=None, allow_empty_file=False), 
        write_only=True, 
        required=False
    )
    video_url = serializers.SerializerMethodField()
    
    class Meta:
        model = Listing
        fields = [
            'id', 'lodge_name', 'description', 'price', 
            'location', 'location_display', 'old_location', 'room_type',
            'amenities', 'amenity_names', 'total_rooms', 
            'room_number', 'video', 'video_url',
            'agent', 'agent_detail', 'agency', 'created_at', 'updated_at',
            'is_available', 'rules', 'contact_phone', 'contact_email',
            'cover_image_url', 'images', 'uploaded_images'
        ]
        read_only_fields = [
            'id', 'created_at', 'updated_at', 'cover_image_url',
            'video_url', 'agent_detail', 'location_display', 'old_location'
        ]
        extra_kwargs = {
            'location': {'required': True},
            'agent': {'required': False},
            'video': {'required': False, 'allow_null': True},
        }

    def get_cover_image_url(self, obj):
        return obj.cover_image_url

    def get_video_url(self, obj):
        return obj.video.url if obj.video else None

    def validate(self, data):
        request = self.context.get('request')
        
        if request and not request.user.is_staff:
            data['agent'] = request.user
            
            if not request.user.is_agent:
                raise serializers.ValidationError(
                    "Only agents can create listings."
                )
        
        if 'agent' in data and data['agent'] and not data.get('agency'):
            if hasattr(data['agent'], 'agency_name') and data['agent'].agency_name:
                data['agency'] = data['agent'].agency_name
        
        # Validate amenity names
        amenity_names = data.get('amenity_names', [])
        if amenity_names:
            # Check if any amenity names are too long
            for name in amenity_names:
                if len(name) > 100:
                    raise serializers.ValidationError(
                        f"Amenity name '{name}' is too long. Maximum length is 100 characters."
                    )
        
        return data

    def create(self, validated_data):
        uploaded_images = validated_data.pop('uploaded_images', [])
        amenity_names = validated_data.pop('amenity_names', [])
        request = self.context.get('request')
        
        if not validated_data.get('agent') and request:
            validated_data['agent'] = request.user
        
        # Create the listing first
        listing = Listing.objects.create(**validated_data)
        
        # Process amenities - get or create by name
        amenities = []
        for name in amenity_names:
            # Clean the name (strip whitespace, capitalize first letters)
            cleaned_name = name.strip()
            if cleaned_name:  # Skip empty names
                # Get or create the amenity
                amenity, created = Amenity.objects.get_or_create(
                    name=cleaned_name,
                    defaults={
                        'name': cleaned_name
                    }
                )
                amenities.append(amenity)
        
        # Add amenities to the listing
        if amenities:
            listing.amenities.set(amenities)
        
        # Create listing images
        for index, image in enumerate(uploaded_images):
            ListingImage.objects.create(
                listing=listing, 
                image=image,
                is_primary=(index == 0)
            )
        
        return listing

    def update(self, instance, validated_data):
        uploaded_images = validated_data.pop('uploaded_images', [])
        amenity_names = validated_data.pop('amenity_names', None)
        
        # Update basic fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        # Update amenities if provided
        if amenity_names is not None:
            amenities = []
            for name in amenity_names:
                cleaned_name = name.strip()
                if cleaned_name:
                    amenity, created = Amenity.objects.get_or_create(
                        name=cleaned_name,
                        defaults={'name': cleaned_name}
                    )
                    amenities.append(amenity)
            instance.amenities.set(amenities)
        
        # Add new images if provided
        if uploaded_images:
            for image in uploaded_images:
                ListingImage.objects.create(listing=instance, image=image)
        
        return instance


class ListingCreateUpdateSerializer(serializers.ModelSerializer):
    uploaded_images = serializers.ListField(
        child=serializers.ImageField(max_length=None, allow_empty_file=False), 
        write_only=True, 
        required=False
    )
    amenity_names = serializers.ListField(
        child=serializers.CharField(max_length=100),
        write_only=True,
        required=False,
        help_text="List of amenity names (e.g., ['WiFi', 'Parking', 'Swimming Pool'])"
    )
    
    class Meta:
        model = Listing
        fields = [
            'lodge_name', 'description', 'price', 'location',
            'room_type', 'amenity_names', 'total_rooms', 
            'room_number', 'video',
            'is_available', 'rules', 'contact_phone', 'contact_email',
            'uploaded_images'
        ]
        
    def create(self, validated_data):
        return ListingSerializer.create(self, validated_data)
    
    def update(self, instance, validated_data):
        return ListingSerializer.update(self, instance, validated_data)


class AgentProfileSerializer(serializers.ModelSerializer):
    listings_count = serializers.SerializerMethodField()
    active_listings_count = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = [
            'id', 'full_name', 'email', 'phone_number', 
            'agency_name', 'date_joined', 'listings_count', 'active_listings_count'
        ]
        read_only_fields = ['id', 'date_joined']
    
    def get_listings_count(self, obj):
        return obj.listings.count()
    
    def get_active_listings_count(self, obj):
        return obj.listings.filter(is_available=True).count()