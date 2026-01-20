# core/adapters.py
from allauth.account.adapter import DefaultAccountAdapter
from allauth.account.models import EmailAddress
from django.conf import settings
from django.urls import reverse
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from allauth.account.utils import perform_login
from allauth.exceptions import ImmediateHttpResponse
from django.http import HttpResponseRedirect
from django.urls import reverse

class CustomSocialAccountAdapter(DefaultSocialAccountAdapter):
    def pre_social_login(self, request, sociallogin):
        # Auto connect social account to existing user with same email
        user = sociallogin.user
        if user.id:
            return
        
        try:
            # Check if user with same email exists
            from django.contrib.auth import get_user_model
            User = get_user_model()
            existing_user = User.objects.get(email=user.email)
            # Connect social account to existing user
            sociallogin.connect(request, existing_user)
        except User.DoesNotExist:
            pass

class CustomAccountAdapter(DefaultAccountAdapter):
    """
    Custom adapter for allauth to handle account-related operations.
    """
    
    def save_user(self, request, user, form, commit=True):
        """
        Saves a new `User` instance using information provided in the signup form.
        """
        from allauth.account.utils import user_email, user_field, user_username
        
        data = form.cleaned_data
        email = data.get('email')
        username = data.get('username')
        
        # Call parent to handle standard fields
        user = super().save_user(request, user, form, commit=False)
        
        # Handle custom fields
        user.full_name = data.get('full_name', '')
        user.phone_number = data.get('phone_number', '')
        user.is_agent = data.get('is_agent', False)
        user.agency_name = data.get('agency_name', '')
        
        if commit:
            user.save()
        
        return user
    
    def get_email_confirmation_url(self, request, emailconfirmation):
        """
        Returns the URL for email confirmation.
        """
        from django.conf import settings
        frontend_url = getattr(settings, 'FRONTEND_URL', 'https://bookit-ecru-sigma.vercel.app')
        key = emailconfirmation.key
        return f'{settings.FRONTEND_URL}/verify-email.html?key={key}'
    
    def send_confirmation_mail(self, request, emailconfirmation, signup):
        """
        Send confirmation email, but skip for agents.
        """
        user = emailconfirmation.email_address.user
        
        # Bypass email verification for agents
        if user.is_agent:
            # Auto-verify the email
            emailconfirmation.email_address.verified = True
            emailconfirmation.email_address.primary = True
            emailconfirmation.email_address.save()
            
            # Also activate the user if needed
            if not user.is_active:
                user.is_active = True
                user.save()
            
            # Don't send verification email
            return
        
        # Send normal verification email for non-agents
        super().send_confirmation_mail(request, emailconfirmation, signup)
    
    def is_open_for_signup(self, request):
        """
        Whether to allow signups.
        """
        return True
    
    def confirm_email(self, request, email_address):
        """
        Confirm email address. For agents, auto-confirm.
        """
        user = email_address.user
        if user.is_agent:
            email_address.verified = True
            email_address.save()
            return email_address
        
        return super().confirm_email(request, email_address)
    
    def respond_email_verification_sent(self, request, user):
        """
        Custom response when email verification is sent.
        For agents, return a success response since they're auto-verified.
        """
        from rest_framework.response import Response
        from rest_framework import status
        
        if user.is_agent:
            # Return success response for agents
            return Response(
                {
                    "detail": "Registration successful. You can now login.",
                    "user_id": user.id,
                    "email": user.email,
                    "is_agent": True,
                    "verified": True
                },
                status=status.HTTP_201_CREATED
            )
        
        return super().respond_email_verification_sent(request, user)