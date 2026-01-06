# account/admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, Listing, ListingImage, Listing

class UserAdmin(BaseUserAdmin):
    ordering = ["email"]
    list_display = ["email", "full_name", "is_staff", "is_agent"]
    fieldsets = (
        (None, {"fields": ("email", "full_name", "phone_number", "password")}),
        ("Permissions", {"fields": ("is_staff", "is_superuser", "is_agent")}),
        ("Important dates", {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("email", "full_name", "phone_number", "password1", "password2", "is_staff", "is_superuser", "is_agent"),
        }),
    )
    search_fields = ("email", "full_name", "phone_number")

class ListingImageInline(admin.TabularInline):
    model = ListingImage
    extra = 1  # Show 1 empty form by default
    fields = ['image']
    readonly_fields = ['uploaded_at']

@admin.register(Listing)
class ListingAdmin(admin.ModelAdmin):
    list_display = ['title', 'price', 'location', 'bedrooms', 'bathrooms', 'created_by', 'created_at']
    list_filter = ['created_at', 'bedrooms', 'bathrooms', 'created_by__is_agent']
    search_fields = ['title', 'description', 'location']
    readonly_fields = ['created_at', 'updated_at']
    
    inlines = [ListingImageInline]

@admin.register(ListingImage)
class ListingImageAdmin(admin.ModelAdmin):
    list_display = ['listing', 'image', 'uploaded_at']
    list_filter = ['uploaded_at']
    search_fields = ['listing__title']

admin.site.register(User, UserAdmin)
