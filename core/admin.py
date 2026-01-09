# account/admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html
from .models import User, Listing, ListingImage

class UserAdmin(BaseUserAdmin):
    ordering = ["email"]
    list_display = ["email", "full_name", "phone_number", "is_staff", "is_agent", "agency_name"]
    list_filter = ["is_staff", "is_superuser", "is_agent", "date_joined"]
    fieldsets = (
        ("Personal Info", {"fields": ("email", "full_name", "phone_number", "password")}),
        ("Agency Info", {"fields": ("is_agent", "agency_name")}),
        ("Permissions", {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
        ("Important dates", {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("email", "full_name", "phone_number", "password1", "password2", 
                      "is_staff", "is_superuser", "is_agent", "agency_name"),
        }),
    )
    search_fields = ("email", "full_name", "phone_number", "agency_name")
    readonly_fields = ("date_joined", "last_login")

class ListingImageInline(admin.TabularInline):
    model = ListingImage
    extra = 1  # Show 1 empty form by default
    fields = ['image', 'is_primary', 'uploaded_at']
    readonly_fields = ['uploaded_at', 'image_preview']
    
    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" width="100" height="75" />', obj.image.url)
        return "No image"
    image_preview.short_description = "Preview"

# LocationAdmin REMOVED

@admin.register(Listing)
class ListingAdmin(admin.ModelAdmin):
    list_display = [
        'lodge_name', 'price', 'location_display', 'room_type_display', 
         'is_available', 'agent_display', 'created_at'
    ]
    list_filter = [
        'is_available', 'room_type', 'location', 'created_at', 
        'agent__is_agent', 'agent__agency_name'
    ]
    search_fields = [
        'lodge_name', 'description', 'room_number', 
        'agent__full_name', 'agent__email', 'agency'
    ]
    readonly_fields = [
        'created_at', 'updated_at', 'cover_image_preview', 
        'video_preview', 'old_location'
    ]
    list_editable = ['is_available', 'price', ]
    raw_id_fields = ['agent'] # Remove location from raw_id_fields
    filter_horizontal = []
    
    fieldsets = (
        ("Basic Information", {
            "fields": ("lodge_name", "description", "price", "is_available")
        }),
        ("Location & Type", {
            "fields": ("location", "old_location", "room_type", "room_number")
        }),
        ("Room Details", {
            "fields": ("total_rooms",)  # FIXED: Added comma to make it a tuple
        }),
        ("Amenities & Rules", {
            "fields": ("amenities", "rules")
        }),
        ("Contact Information", {
            "fields": ("contact_phone", "contact_email")
        }),
        ("Media", {
            "fields": ("video", "video_preview", "cover_image_preview")
        }),
        ("Agent Information", {
            "fields": ("agent", "agency")
        }),
        ("Metadata", {
            "fields": ("created_at", "updated_at"),
            "classes": ("collapse",)
        }),
    )
    
    inlines = [ListingImageInline]
    
    def location_display(self, obj):
        # Simply return the display value of the choice
        return obj.get_location_display()
    location_display.short_description = "Location"
    location_display.admin_order_field = 'location'
    
    def room_type_display(self, obj):
        return dict(Listing.ROOM_TYPE_CHOICES).get(obj.room_type, obj.room_type)
    room_type_display.short_description = "Room Type"
    
    def agent_display(self, obj):
        if obj.agent:
            return f"{obj.agent.full_name} ({obj.agent.email})"
        return "No agent"
    agent_display.short_description = "Agent"
    agent_display.admin_order_field = 'agent__full_name'
    
    def cover_image_preview(self, obj):
        if obj.cover_image_url:
            return format_html('<img src="{}" width="200" height="150" />', obj.cover_image_url)
        return "No cover image"
    cover_image_preview.short_description = "Cover Image Preview"
    
    def video_preview(self, obj):
        if obj.video:
            return format_html(
                '<video width="200" height="150" controls>'
                '<source src="{}" type="video/mp4">'
                'Your browser does not support the video tag.'
                '</video>',
                obj.video.url
            )
        return "No video"
    video_preview.short_description = "Video Preview"
    
    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        # Remove select_related for location (not a FK anymore)
        queryset = queryset.select_related('agent')
        return queryset

@admin.register(ListingImage)
class ListingImageAdmin(admin.ModelAdmin):
    list_display = ['listing_display', 'image_preview', 'is_primary', 'uploaded_at']
    list_filter = ['is_primary', 'uploaded_at', 'listing__location']
    search_fields = ['listing__lodge_name', 'listing__room_number']
    readonly_fields = ['uploaded_at', 'image_preview_large']
    list_editable = ['is_primary']
    raw_id_fields = ['listing']
    
    def listing_display(self, obj):
        return f"{obj.listing.lodge_name} - {obj.listing.room_number or 'No number'}"
    listing_display.short_description = "Listing"
    listing_display.admin_order_field = 'listing__lodge_name'
    
    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" width="50" height="50" />', obj.image.url)
        return "No image"
    image_preview.short_description = "Preview"
    
    def image_preview_large(self, obj):
        if obj.image:
            return format_html('<img src="{}" width="300" height="225" />', obj.image.url)
        return "No image"
    image_preview_large.short_description = "Large Preview"
    
    def save_model(self, request, obj, form, change):
        # Ensure only one primary image per listing
        if obj.is_primary:
            ListingImage.objects.filter(
                listing=obj.listing, 
                is_primary=True
            ).exclude(id=obj.id).update(is_primary=False)
        super().save_model(request, obj, form, change)

admin.site.register(User, UserAdmin)