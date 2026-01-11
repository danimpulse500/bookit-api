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


class CustomRegisterView(RegisterView):
    """
    Custom registration view that handles email sending errors gracefully.
    """
    
    @extend_schema(
        summary="Register a new user",
        description="Create a new user account. A verification email will be sent.",
        request=UserRegistrationSerializer,
        responses={
            201: {
                'type': 'object',
                'properties': {
                    'detail': {'type': 'string', 'example': 'Registration successful.'},
                    'email': {'type': 'string', 'example': 'user@example.com'},
                    'warning': {'type': 'string', 'example': 'Verification email may have failed.'}
                }
            }
        }
    )
    def create(self, request, *args, **kwargs):
        try:
            response = super().create(request, *args, **kwargs)
            
            if response.status_code == status.HTTP_201_CREATED:
                response_data = {
                    'detail': 'Registration successful. Please check your email for verification.',
                    'email': request.data.get('email'),
                }
                return Response(response_data, status=status.HTTP_201_CREATED)
            
            return response
            
        except Exception as e:
            # Check if it's an SMTP/email error
            error_msg = str(e).lower()
            email_errors = ['smtp', 'socket', 'connection', 'timeout', 'email']
            
            if any(err in error_msg for err in email_errors):
                # User was created but email failed
                # We need to manually create the user without triggering email
                return self._create_user_without_email(request)
            
            # For other errors, return 400
            return Response(
                {'detail': f'Registration error: {str(e)}'},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    def _create_user_without_email(self, request):
        """
        Manually create user when email sending fails.
        """
        from django.contrib.auth import get_user_model
        from rest_framework import serializers
        
        User = get_user_model()
        
        try:
            # Get data from request
            data = request.data
            
            # Check if user already exists
            if User.objects.filter(email=data.get('email')).exists():
                return Response(
                    {'detail': 'User with this email already exists.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Create user manually
            user = User.objects.create_user(
                email=data.get('email'),
                password=data.get('password1'),
                username=data.get('email'),  # Use email as username
                full_name=data.get('full_name', ''),
                phone_number=data.get('phone_number', ''),
                is_agent=data.get('is_agent', False),
                agency_name=data.get('agency_name', ''),
                is_active=False  # User needs to verify email
            )
            
            # Create EmailAddress record for allauth
            from allauth.account.models import EmailAddress
            EmailAddress.objects.create(
                user=user,
                email=user.email,
                verified=False,
                primary=True
            )
            
            # Return success but with warning
            return Response({
                'detail': 'Registration successful but verification email failed to send.',
                'email': user.email,
                'warning': 'Please contact support to verify your email.',
                'user_id': user.id
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
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