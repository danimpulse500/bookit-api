# core/adapters.py
from allauth.account.adapter import DefaultAccountAdapter
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
        # Use the FRONTEND_URL from settings for the confirmation link
        from django.conf import settings
        frontend_url = getattr(settings, 'FRONTEND_URL', 'https://bookit-ecru-sigma.vercel.app')
        key = emailconfirmation.key
        return f'{settings.FRONTEND_URL}/verify-email.html?key={key}'