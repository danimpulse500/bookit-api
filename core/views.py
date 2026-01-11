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
    Custom registration view that integrates with allauth email verification.
    """
    
    @extend_schema(
        summary="Register a new user",
        description="Create a new user account. A verification email will be sent to the provided email address.",
        request=UserRegistrationSerializer,
        responses={
            201: {
                'type': 'object',
                'properties': {
                    'detail': {'type': 'string', 'example': 'Verification email sent.'},
                    'email': {'type': 'string', 'example': 'user@example.com'}
                }
            },
            400: {
                'type': 'object',
                'properties': {
                    'detail': {'type': 'string'},
                    'email': {'type': 'string'},
                    'password1': {'type': 'string'},
                    'password2': {'type': 'string'}
                }
            }
        }
    )
    def create(self, request, *args, **kwargs):
        """
        Override the create method to integrate with allauth email verification.
        """
        try:
            # Call the parent RegisterView's create method
            response = super().create(request, *args, **kwargs)
            
            # Customize the response
            if response.status_code == status.HTTP_201_CREATED:
                response_data = {
                    'detail': 'Verification email sent. Please check your email to confirm your account.',
                    'email': request.data.get('email'),
                }
                return Response(response_data, status=status.HTTP_201_CREATED)
            
            return response
        except Exception as e:
            # Log the error for debugging
            import traceback
            error_details = traceback.format_exc()
            print(f"Registration error: {str(e)}")
            print(f"Traceback: {error_details}")
            
            # Return the actual error for debugging
            return Response(
                {
                    'detail': f'Registration error: {str(e)}',
                    'error_details': error_details[-500:]  # Last 500 chars of traceback
                },
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