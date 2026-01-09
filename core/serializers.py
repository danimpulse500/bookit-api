from rest_framework import serializers
from dj_rest_auth.registration.serializers import RegisterSerializer
from .models import User, Listing, ListingImage, Location
from allauth.account.adapter import get_adapter
# Add to core/serializers.py
from dj_rest_auth.serializers import LoginSerializer
from django.contrib.auth import authenticate
from django.utils.translation import gettext_lazy as _

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
                 'is_agent', 'agency_name', 'date_joined', 'is_staff']
        read_only_fields = ['id', 'date_joined', 'is_staff']

class UserRegistrationSerializer(RegisterSerializer):
    username = serializers.CharField(required=False, allow_blank=True, max_length=150)
    full_name = serializers.CharField(required=True)
    phone_number = serializers.CharField(required=True)
    is_agent = serializers.BooleanField(default=False)
    agency_name = serializers.CharField(required=False, allow_blank=True)

    class Meta:
        fields = ('email', 'password1', 'password2', 'full_name', 
                 'phone_number', 'is_agent', 'agency_name')

    def validate_email(self, email):
        email = get_adapter().clean_email(email)
        
        if User.objects.filter(email=email).exists():
            raise serializers.ValidationError(
                "A user is already registered with this email address."
            )
        return email

    def get_cleaned_data(self):
        data = super().get_cleaned_data()
        data['username'] =  data.get('email')
        data['full_name'] = self.validated_data.get('full_name', '')
        data['phone_number'] = self.validated_data.get('phone_number', '')
        data['is_agent'] = self.validated_data.get('is_agent', False)
        data['agency_name'] = self.validated_data.get('agency_name', '')
        return data

    def save(self, request):
        user = super().save(request)
        user.full_name = self.cleaned_data.get('full_name')
        user.phone_number = self.cleaned_data.get('phone_number')
        user.is_agent = self.cleaned_data.get('is_agent')
        user.agency_name = self.cleaned_data.get('agency_name')
        user.save()
        return user

class LocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Location
        fields = ['id', 'name', 'description', 'is_active', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']

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
    location_detail = LocationSerializer(source='location', read_only=True)
    agent_detail = UserSerializer(source='agent', read_only=True)
    uploaded_images = serializers.ListField(
        child=serializers.ImageField(max_length=None, allow_empty_file=False), 
        write_only=True, 
        required=False
    )
    video_url = serializers.SerializerMethodField()
    
    # Remove old fields that don't exist in model
    # bedrooms, bathrooms are still in model but marked for deprecation
    # title field doesn't exist - it's now lodge_name

    class Meta:
        model = Listing
        fields = [
            'id', 'lodge_name', 'description', 'price', 
            'location', 'location_detail', 'old_location', 'room_type',
            'amenities', 'total_rooms', 
            'room_number', 'video', 'video_url',
            'agent', 'agent_detail', 'agency', 'created_at', 'updated_at',
            'is_available', 'rules', 'contact_phone', 'contact_email',
            'cover_image_url', 'images', 'uploaded_images'
        ]
        read_only_fields = [
            'id', 'created_at', 'updated_at', 'cover_image_url',
            'video_url', 'agent_detail', 'location_detail', 'old_location'
        ]
        extra_kwargs = {
            'location': {'required': False},
            'agent': {'required': False},
            'video': {'required': False, 'allow_null': True},
        }

    def get_cover_image_url(self, obj):
        """Get cover image URL from first ListingImage"""
        return obj.cover_image_url

    def get_video_url(self, obj):
        """Get video URL if exists"""
        return obj.video.url if obj.video else None

    def validate(self, data):
        """Custom validation"""
        request = self.context.get('request')
        
        # Ensure agent is set for non-staff users
        if request and not request.user.is_staff:
            data['agent'] = request.user
            
            # Check if user is an agent
            if not request.user.is_agent:
                raise serializers.ValidationError(
                    "Only agents can create listings."
                )
        
        # Auto-populate agency from agent
        if 'agent' in data and data['agent'] and not data.get('agency'):
            if hasattr(data['agent'], 'agency_name') and data['agent'].agency_name:
                data['agency'] = data['agent'].agency_name
        
        # Validate room availability
        # if 'total_rooms' in data and 'available_rooms' in data:
        #     if data['available_rooms'] > data['total_rooms']:
        #         raise serializers.ValidationError({
        #             'available_rooms': 'Available rooms cannot exceed total rooms.'
        #         })
        
        return data

    def create(self, validated_data):
        uploaded_images = validated_data.pop('uploaded_images', [])
        request = self.context.get('request')
        
        # Set agent if not provided
        if not validated_data.get('agent') and request:
            validated_data['agent'] = request.user
        
        listing = Listing.objects.create(**validated_data)
        
        # Create listing images
        for index, image in enumerate(uploaded_images):
            ListingImage.objects.create(
                listing=listing, 
                image=image,
                is_primary=(index == 0)  # First image as primary
            )
        
        return listing

    def update(self, instance, validated_data):
        uploaded_images = validated_data.pop('uploaded_images', [])
        
        # Update listing fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        # Add new images if provided
        if uploaded_images:
            for image in uploaded_images:
                ListingImage.objects.create(listing=instance, image=image)
        
        return instance

class ListingCreateUpdateSerializer(serializers.ModelSerializer):
    """Simplified serializer for create/update operations"""
    uploaded_images = serializers.ListField(
        child=serializers.ImageField(max_length=None, allow_empty_file=False), 
        write_only=True, 
        required=False
    )
    
    class Meta:
        model = Listing
        fields = [
            'lodge_name', 'description', 'price', 'location',
            'room_type', 'amenities', 'total_rooms', 'available_rooms',
            'room_number', 'bedrooms', 'bathrooms', 'video',
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