# myapp/admin.py

from django.contrib import admin
from django.urls import path
from django.shortcuts import render
from django.db.models import Count, Sum, Avg
from mptt.admin import MPTTModelAdmin
# Django auth admin import, custom User uchun
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from .models import (
    User,
    UserProfile, Banner, Plan, AnalyticsDummy,
    Category, Announcement, AnnouncementImage, GalleryImage,
    Payment, Favorite, Comment, News, Chat, Message, OtherAnnouncement, Donation, Notification, PasswordResetAttempt
)


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    model = User
    list_display = ('id', 'username', 'email', 'date_joined', 'is_staff', 'is_active')
    search_fields = ('username', 'email')
    readonly_fields = ('last_login', 'date_joined')
    ordering = ('-date_joined',)  
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Personal info', {
            'fields': ('email', 'first_name', 'last_name')
        }),
        ('Permissions', {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')
        }),
        ('Important dates', {
            'fields': ('last_login', 'date_joined')
        }),
    )





@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'avatar', 'bio')
    search_fields = ('user__username', 'bio')


@admin.register(Banner)
class BannerAdmin(admin.ModelAdmin):
    list_display = ('id', 'alt_text', 'created_at')
    search_fields = ('alt_text',)
    readonly_fields = ('created_at',)


@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'amount', 'priority')
    list_editable = ('amount', 'priority')
    search_fields = ('name',)


@admin.register(AnalyticsDummy)
class AnalyticsDummyAdmin(admin.ModelAdmin):
    list_display = ('id',)


@admin.register(Category)
class CategoryAdmin(MPTTModelAdmin):
    mptt_level_indent = 20
    list_display = ('name', 'parent', 'meta_title', 'meta_description')
    search_fields = ('name',)
    list_filter = ('parent',)



class AnnouncementImageInline(admin.TabularInline):
    model = AnnouncementImage
    extra = 1 


@admin.register(Announcement)
class AnnouncementAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'title', 'user', 'category',
        'price', 'priority', 'status', 'views_count','fkko_code', 'created_at'
    )
    list_filter = ('status', 'category', 'plan', 'created_at')
    search_fields = ('title', 'description', 'user__username')
    readonly_fields = ('slug', 'views_count', 'created_at', 'updated_at')
    inlines = [AnnouncementImageInline]
    list_editable = ('status',)

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        if 'user' in form.base_fields:
            form.base_fields['user'].initial = request.user
        return form

    def save_model(self, request, obj, form, change):
        if not obj.user_id:
            obj.user = request.user
        super().save_model(request, obj, form, change)

    fieldsets = (
        ("Asosiy ma'lumotlar", {
            "fields": (
                'title', 'slug', 'description',
                ('status', 'plan', 'priority'),
                ('price', 'is_negotiable'),
                'category',
                ('condition', 'location', 'city', 'phone'),
                'user', 
            ),
        }),
        ("SEO", {
            "fields": ('meta_title', 'meta_description'),
            "classes": ("collapse",),
        }),
        ("Vaqt va statistika", {
            "fields": ('views_count', 'expiration_date', 'created_at', 'updated_at'),
            "classes": ("collapse",),
        }),
    )


@admin.register(AnnouncementImage)
class AnnouncementImageAdmin(admin.ModelAdmin):
    list_display = ('id', 'announcement')
    autocomplete_fields = ('announcement',)


@admin.register(GalleryImage)
class GalleryImageAdmin(admin.ModelAdmin):
    list_display = ('id', 'image', 'created_at')
    readonly_fields = ('created_at',)


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'announcement', 'plan', 'amount', 'paid', 'created_at')
    list_filter = ('paid', 'plan', 'created_at')
    search_fields = ('user__username', 'announcement__title')
    autocomplete_fields = ('user', 'announcement', 'plan')


@admin.register(Favorite)
class FavoriteAdmin(admin.ModelAdmin):
    list_display = ('user', 'announcement', 'created_at')
    autocomplete_fields = ('user', 'announcement')
    search_fields = ('user__username', 'announcement__title')


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'announcement', 'rating', 'created_at')
    list_filter = ('rating', 'created_at')
    search_fields = ('user__username', 'announcement__title', 'text')
    autocomplete_fields = ('user', 'announcement')


@admin.register(News)
class NewsAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'created_at')
    search_fields = ('title',)
    readonly_fields = ('created_at',)


@admin.register(Chat)
class ChatAdmin(admin.ModelAdmin):
    list_display = ('id', 'announcement', 'created_at')
    autocomplete_fields = ('announcement', 'participants')
    filter_horizontal = ('participants',)
    search_fields = ('announcement__title', 'participants__username')


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ('id', 'chat', 'sender', 'created_at')
    search_fields = ('sender__username', 'text')
    autocomplete_fields = ('chat', 'sender')


@admin.register(OtherAnnouncement)
class OtherAnnouncementAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'price', 'phone', 'created_at')
    search_fields = ('title', 'phone')
    readonly_fields = ('created_at',)


@admin.register(Donation)
class DonationAdmin(admin.ModelAdmin):
    list_display = ('user', 'amount', 'created_at', 'paid')
    list_filter = ('paid', 'created_at')
    search_fields = ('user__username', 'user__email')
    date_hierarchy = 'created_at'


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('title', 'notification_type', 'created_at', 'is_read')
    list_filter = ('notification_type', 'is_read', 'created_at')
    search_fields = ('title', 'message')
    date_hierarchy = 'created_at'
    readonly_fields = ('content_type', 'object_id', 'content_object')
    
    actions = ['mark_as_read', 'mark_as_unread']
    
    def mark_as_read(self, request, queryset):
        updated = queryset.update(is_read=True)
        self.message_user(request, f'Отмечено как прочитанное: {updated} уведомлений.')
    mark_as_read.short_description = "Отметить как прочитанное"
    
    def mark_as_unread(self, request, queryset):
        updated = queryset.update(is_read=False)
        self.message_user(request, f'Отмечено как непрочитанное: {updated} уведомлений.')
    mark_as_unread.short_description = "Отметить как непрочитанное"


class MyAdminSite(admin.AdminSite):
    site_header = "Super Admin Panel"
    site_title = "Admin"

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('analytics/overview/', self.admin_view(self.analytics_view), name='analytics-overview'),
        ]
        return custom_urls + urls

    def analytics_view(self, request):
        """
        Bu yerda to'lovlar, e'lonlar, foydalanuvchilar soni va hokazo statistikani chiqarish mumkin.
        Hatto grafiklar chizish uchun Chart.js yoki plotly.js dan foydalansangiz bo'ladi (custom template orqali).
        """
        total_users = User.objects.count()
        total_announcements = Announcement.objects.count()
        avg_price = Announcement.objects.aggregate(avg_price=Avg('price'))['avg_price']
        monthly_payments = Payment.objects.filter(paid=True).values('created_at__year', 'created_at__month').annotate(
            total_sum=Sum('amount'),
            count=Count('id')
        ).order_by('-created_at__year', '-created_at__month')

        context = dict(
            self.each_context(request),
            total_users=total_users,
            total_announcements=total_announcements,
            avg_price=avg_price,
            monthly_payments=monthly_payments,
        )
        return render(request, 'admin/my_custom_analytics.html', context)

@admin.register(PasswordResetAttempt)
class PasswordResetAttemptAdmin(admin.ModelAdmin):
    list_display = ("created_at", "email", "ip", "success", "user")
    search_fields = ("email", "ip", "user_agent")
    list_filter = ("success", "created_at")
    
custom_admin_site = MyAdminSite(name='myadmin')

custom_admin_site.register(User, UserAdmin)
custom_admin_site.register(UserProfile, UserProfileAdmin)
custom_admin_site.register(Banner, BannerAdmin)
custom_admin_site.register(Plan, PlanAdmin)
custom_admin_site.register(AnalyticsDummy, AnalyticsDummyAdmin)
custom_admin_site.register(Category, CategoryAdmin)
custom_admin_site.register(Announcement, AnnouncementAdmin)
custom_admin_site.register(AnnouncementImage, AnnouncementImageAdmin)
custom_admin_site.register(GalleryImage, GalleryImageAdmin)
custom_admin_site.register(Payment, PaymentAdmin)
custom_admin_site.register(Favorite, FavoriteAdmin)
custom_admin_site.register(Comment, CommentAdmin)
custom_admin_site.register(News, NewsAdmin)
custom_admin_site.register(Chat, ChatAdmin)
custom_admin_site.register(Message, MessageAdmin)
custom_admin_site.register(OtherAnnouncement, OtherAnnouncementAdmin)
custom_admin_site.register(Donation, DonationAdmin)
custom_admin_site.register(Notification, NotificationAdmin)
