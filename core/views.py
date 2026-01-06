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
    @extend_schema(
        summary="Register a new user",
        description="Create a new user account and return JWT tokens.",
        request=UserRegistrationSerializer,
        responses={
            201: {
                'type': 'object',
                'properties': {
                    'access': {'type': 'string'},
                    'refresh': {'type': 'string'},
                    'user': UserSerializer().data
                }
            }
        }
    )
    def create(self, request, *args, **kwargs):
        response = super().create(request, *args, **kwargs)
        if response.status_code == 201:
            user = response.data
            refresh = RefreshToken.for_user(user)
            response.data = {
                'access': str(refresh.access_token),
                'refresh': str(refresh),
                'user': user
            }
        return response


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
