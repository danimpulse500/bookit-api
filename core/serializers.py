from rest_framework import serializers
from dj_rest_auth.registration.serializers import RegisterSerializer
from .models import User, Listing, ListingImage
from rest_framework import serializers
from allauth.account import app_settings as allauth_settings
from allauth.account.adapter import get_adapter
from allauth.account.utils import setup_user_email
from django.db import IntegrityError
from django.core.exceptions import ValidationError

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'full_name', 'email', 'phone_number', 'is_agent', 'date_joined']
        read_only_fields = ['id', 'date_joined']


class UserRegistrationSerializer(RegisterSerializer):
    username = serializers.CharField(required=False, allow_blank=True, max_length=150)
    full_name = serializers.CharField(required=True)
    phone_number = serializers.CharField(required=True)
    is_agent = serializers.BooleanField(default=False)

    class Meta:
        fields = ('email', 'password1', 'password2', 'full_name', 'phone_number', 'is_agent')

    def validate_email(self, email):
        email = get_adapter().clean_email(email)
        
        # CRITICAL: Check if email already exists BEFORE trying to create user
        from django.contrib.auth import get_user_model
        User = get_user_model()
        
        if User.objects.filter(email=email).exists():
            raise serializers.ValidationError(
                "A user is already registered with this email address."
            )
        
        return email

    def get_cleaned_data(self):
        data = super().get_cleaned_data()
        data['username'] = data.get('username') or data.get('email')
        data['full_name'] = self.validated_data.get('full_name', '')
        data['phone_number'] = self.validated_data.get('phone_number', '')
        data['is_agent'] = self.validated_data.get('is_agent', False)
        return data

    def save(self, request):
        user = super().save(request)
        user.full_name = self.cleaned_data.get('full_name')
        user.phone_number = self.cleaned_data.get('phone_number')
        user.is_agent = self.cleaned_data.get('is_agent')
        user.save()
        return user

class ListingImageSerializer(serializers.ModelSerializer):
    image = serializers.SerializerMethodField()  # Fix: return full URL

    class Meta:
        model = ListingImage
        fields = ['id', 'image', 'uploaded_at']
        read_only_fields = ['id', 'uploaded_at']

    def get_image(self, obj):
        return obj.image.url if obj.image else None


class ListingSerializer(serializers.ModelSerializer):
    images = ListingImageSerializer(many=True, read_only=True)
    cover_image_url = serializers.SerializerMethodField()  # Added cover_image URL
    uploaded_images = serializers.ListField(
        child=serializers.ImageField(), write_only=True, required=False
    )

    class Meta:
        model = Listing
        fields = [
            'id', 'title', 'description', 'price', 'location',
            'bedrooms', 'bathrooms', 'cover_image_url', 'images', 'uploaded_images', 
            'created_by', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'created_by']

    def get_cover_image_url(self, obj):
        return obj.cover_image.url if obj.cover_image else None

    def create(self, validated_data):
        uploaded_images = validated_data.pop('uploaded_images', [])
        validated_data['created_by'] = self.context['request'].user
        listing = super().create(validated_data)
        
        for image in uploaded_images:
            ListingImage.objects.create(listing=listing, image=image)
        
        return listing
