# In core/adapters.py (create this file):
from allauth.account.adapter import DefaultAccountAdapter
from django.conf import settings

class CustomAccountAdapter(DefaultAccountAdapter):
    def save_user(self, request, user, form, commit=True):
        user = super().save_user(request, user, form, commit=False)
        
        # Save additional fields
        user.full_name = form.cleaned_data.get('full_name', '')
        user.phone_number = form.cleaned_data.get('phone_number', '')
        user.is_agent = form.cleaned_data.get('is_agent', False)
        user.agency_name = form.cleaned_data.get('agency_name', '')
        
        if commit:
            user.save()
        return user