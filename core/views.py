from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiExample
from django.contrib.auth import authenticate
from dj_rest_auth.registration.views import RegisterView
from .models import User, Listing
from .serializers import UserSerializer, UserRegistrationSerializer, ListingSerializer
from .permissions import IsAgentOrReadOnly
from rest_framework import status
from rest_framework.response import Response
from dj_rest_auth.registration.views import RegisterView
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from django.urls import path, include
from allauth.socialaccount.providers.google.views import GoogleOAuth2Adapter
from allauth.socialaccount.providers.oauth2.client import OAuth2Client
from dj_rest_auth.registration.views import SocialLoginView

class GoogleLogin(SocialLoginView):
    adapter_class = GoogleOAuth2Adapter
    callback_url = "https://bookit-ecru-sigma.vercel.app"  # Your frontend callback URL
    client_class = OAuth2Client
    
class CustomRegisterView(RegisterView):
    """
    Simple wrapper around dj-rest-auth's RegisterView with better error handling.
    """
    
    def create(self, request, *args, **kwargs):
        email = request.data.get('email')
        User = get_user_model()
        
        # Check if user exists
        if User.objects.filter(email=email).exists():
            return Response(
                {'detail': 'User with this email already exists.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Call parent class method
            response = super().create(request, *args, **kwargs)
            
            if response.status_code == 201:
                # Success - format response nicely
                return Response(
                    {
                        'detail': 'Registration successful. Please check your email for verification.',
                        'email': email,
                    },
                    status=status.HTTP_201_CREATED
                )
            
            return response
            
        except Exception as e:
            error_str = str(e).lower()
            
            # Check specific error types
            if 'smtp' in error_str or 'email' in error_str or 'connection' in error_str:
                # Email sending failed, but user might have been created
                if User.objects.filter(email=email).exists():
                    user = User.objects.get(email=email)
                    return Response(
                        {
                            'detail': 'Registration completed but verification email failed to send.',
                            'email': email,
                            'user_id': user.id,
                            'warning': 'Please contact support to verify your email.',
                            'error': str(e)
                        },
                        status=status.HTTP_201_CREATED
                    )
                
                return Response(
                    {
                        'detail': 'Registration failed due to email service issue.',
                        'error': str(e),
                        'solution': 'Please try again later or contact support.'
                    },
                    status=status.HTTP_503_SERVICE_UNAVAILABLE
                )
            
            # Other errors
            return Response(
                {'detail': f'Registration failed: {str(e)}'},
                status=status.HTTP_400_BAD_REQUEST
            )
class ListingListCreateView(generics.ListCreateAPIView):
    queryset = Listing.objects.all().order_by('-created_at')
    serializer_class = ListingSerializer
    permission_classes = [IsAgentOrReadOnly]

    @extend_schema(
        summary="List all listings",
        description="Retrieve a list of all property listings.",
        responses={200: ListingSerializer(many=True)}
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @extend_schema(
        summary="Create a new listing",
        description="Create a new property listing. Only agents can create listings.",
        request=ListingSerializer,
        responses={201: ListingSerializer}
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


class ListingDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Listing.objects.all()
    serializer_class = ListingSerializer
    permission_classes = [IsAgentOrReadOnly]

    @extend_schema(
        summary="Retrieve a listing",
        description="Get details of a specific property listing.",
        responses={200: ListingSerializer}
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @extend_schema(
        summary="Update a listing",
        description="Update a property listing. Only the agent who created it can update.",
        request=ListingSerializer,
        responses={200: ListingSerializer}
    )
    def put(self, request, *args, **kwargs):
        return super().put(request, *args, **kwargs)

    @extend_schema(
        summary="Partially update a listing",
        description="Partially update a property listing. Only the agent who created it can update.",
        request=ListingSerializer,
        responses={200: ListingSerializer}
    )
    def patch(self, request, *args, **kwargs):
        return super().patch(request, *args, **kwargs)

    @extend_schema(
        summary="Delete a listing",
        description="Delete a property listing. Only the agent who created it can delete.",
        responses={204: None}
    )
    def delete(self, request, *args, **kwargs):
        return super().delete(request, *args, **kwargs)