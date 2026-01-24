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
from rest_framework import generics, permissions, filters
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema
from .models import Listing
from .serializers import ListingSerializer, ListingCreateUpdateSerializer
from .permissions import IsAgentOrReadOnly

class GoogleLogin(SocialLoginView):
    adapter_class = GoogleOAuth2Adapter
    client_class = OAuth2Client
    
    @property
    def callback_url(self):
        # This should match what you entered in Django admin
        # For development:
        if settings.DEBUG:
            return "http://localhost:5500"  # Your frontend URL
        # For production:
        return "https://bookit-ecru-sigma.vercel.app"
    

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
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    
    # Add filtering options
    filterset_fields = [
        'location', 
        'room_type', 
        'is_available',
        'agent',
        'first_price', 
        'year_price',
        'total_rooms'
    ]
    
    # Add search functionality
    search_fields = [
        'lodge_name',
        'description',
        'room_number',
        'agency',
        'contact_phone',
        'contact_email'
    ]
    
    # Add ordering options
    ordering_fields = [
        'first_price', 
        'year_price',
        'created_at',
        'updated_at',
        'total_rooms'
    ]
    ordering = ['-created_at']  # Default ordering
    
    def get_serializer_class(self):
        """Use different serializer for POST requests"""
        if self.request.method == 'POST':
            return ListingCreateUpdateSerializer
        return ListingSerializer

    @extend_schema(
        summary="List all listings",
        description="Retrieve a list of all property listings with filtering, search and ordering options.",
        parameters=[
            {
                'name': 'location',
                'in': 'query',
                'required': False,
                'description': 'Filter by location',
                'schema': {'type': 'string'}
            },
            {
                'name': 'room_type',
                'in': 'query',
                'required': False,
                'description': 'Filter by room type',
                'schema': {'type': 'string'}
            },
            {
                'name': 'is_available',
                'in': 'query',
                'required': False,
                'description': 'Filter by availability (true/false)',
                'schema': {'type': 'boolean'}
            },
            {
                'name': 'min_price',
                'in': 'query',
                'required': False,
                'description': 'Minimum price filter',
                'schema': {'type': 'number'}
            },
            {
                'name': 'max_price',
                'in': 'query',
                'required': False,
                'description': 'Maximum price filter',
                'schema': {'type': 'number'}
            },
            {
                'name': 'search',
                'in': 'query',
                'required': False,
                'description': 'Search in lodge name, description, room number, etc.',
                'schema': {'type': 'string'}
            },
            {
                'name': 'ordering',
                'in': 'query',
                'required': False,
                'description': 'Order by field (first_price, year_price, created_at, -first_price, -year_price, -created_at, etc.)',
                'schema': {'type': 'string'}
            },
            {
                'name': 'amenities',
                'in': 'query',
                'required': False,
                'description': 'Filter by amenities (comma-separated amenity names)',
                'schema': {'type': 'string'}
            }
        ],
        responses={200: ListingSerializer(many=True)}
    )
    def get(self, request, *args, **kwargs):
        # Apply custom filtering for amenities
        amenities_filter = request.query_params.get('amenities')
        if amenities_filter:
            amenities_list = [a.strip() for a in amenities_filter.split(',') if a.strip()]
            if amenities_list:
                # Filter listings that have all specified amenities
                queryset = self.get_queryset()
                for amenity_name in amenities_list:
                    queryset = queryset.filter(amenities__name__iexact=amenity_name)
                queryset = queryset.distinct()
                
                # Apply pagination to the filtered queryset
                page = self.paginate_queryset(queryset)
                if page is not None:
                    serializer = self.get_serializer(page, many=True)
                    return self.get_paginated_response(serializer.data)
                
                serializer = self.get_serializer(queryset, many=True)
                return Response(serializer.data)
        
        return super().get(request, *args, **kwargs)

    @extend_schema(
        summary="Create a new listing",
        description="Create a new property listing. Only agents can create listings.",
        request=ListingCreateUpdateSerializer,
        responses={201: ListingSerializer}
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)
    
    def perform_create(self, serializer):
        """Set the agent to the current user"""
        serializer.save(agent=self.request.user)


class ListingDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Listing.objects.all()
    permission_classes = [IsAgentOrReadOnly]
    
    def get_serializer_class(self):
        """Use different serializer for PUT/PATCH requests"""
        if self.request.method in ['PUT', 'PATCH']:
            return ListingCreateUpdateSerializer
        return ListingSerializer

    @extend_schema(
        summary="Retrieve a listing",
        description="Retrieve details of a specific property listing.",
        responses={200: ListingSerializer}
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @extend_schema(
        summary="Update a listing",
        description="Update a property listing. Only the listing agent or admin can update.",
        request=ListingCreateUpdateSerializer,
        responses={200: ListingSerializer}
    )
    def put(self, request, *args, **kwargs):
        return super().put(request, *args, **kwargs)

    @extend_schema(
        summary="Partial update a listing",
        description="Partially update a property listing. Only the listing agent or admin can update.",
        request=ListingCreateUpdateSerializer,
        responses={200: ListingSerializer}
    )
    def patch(self, request, *args, **kwargs):
        return super().patch(request, *args, **kwargs)

    @extend_schema(
        summary="Delete a listing",
        description="Delete a property listing. Only the listing agent or admin can delete.",
        responses={204: None}
    )
    def delete(self, request, *args, **kwargs):
        return super().delete(request, *args, **kwargs)
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