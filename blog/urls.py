# myapp/urls.py
from django.urls import path
from . import views
from . import views_registration
from . import views_ai_chat

from django.conf import settings
from django.conf.urls.static import static
from .views import *

urlpatterns = [
    path('', views.index_view, name='index'),
    path('register/', views.register_view, name='register'),
    path('verify-email/', views_registration.verify_email_view, name='verify_email'),
    path('verify-email/resend/', views_registration.resend_verification_view, name='resend_verification'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('profile/', views.user_profile_view, name='profile'),
    path('profile/update/', views.user_profile_update_view, name='profile_update'),
    path('banners/', views.banner_list_view, name='banner_list'),
    path('gallery/', views.gallery_list_view, name='gallery_list'),
    path('plans/', views.plan_list_view, name='plan_list'),
    path('plans/<int:pk>/', views.plan_detail_view, name='plan_detail'),
    path('categories/', views.category_list_view, name='category_list'),
    path('categories/<int:pk>/', views.category_detail_view, name='category_detail'),
    path('categories-tree/', views.category_tree_view, name='category_tree'),
    path('announcements/', views.announcement_list_view, name='announcement_list'),
    path('announcements/create/', views.announcement_create_view, name='announcement_create'),
    path('announcements/<int:pk>/', views.announcement_detail_view, name='announcement_detail'),
    path('announcements/<int:pk>/update/', views.announcement_update_view, name='announcement_update'),
    path('announcements/<int:pk>/delete/', views.announcement_delete_view, name='announcement_delete'),
    path('announcements/<int:pk>/activate/', views.announcement_activate_view, name='announcement_activate'),
    path('announcements/<int:pk>/deactivate/', views.announcement_deactivate_view, name='announcement_deactivate'),
    path('announcements/<int:pk>/upgrade/', views.announcement_upgrade_view, name='upgrade_announcement'),
    path('payments/create/<int:announcement_id>/<int:plan_id>/', views.create_payment_view, name='payment_create'),
    path('payments/check/<str:payment_id>/', views.check_payment_status_view, name='payment_check'),
    # Favorites
    path('favorites/', views.favorite_list_view, name='favorite_list'),
    path('favorites/add/', views.favorite_add_view, name='favorite_add'),
    path('favorites/<int:pk>/delete/', views.favorite_delete_view, name='favorite_delete'),

    # Comments
    path('comments/', views.comment_list_create_view, name='comment_list_create'),

    # Recommendations
    path('announcements/<int:pk>/recommendations/', views.announcement_recommendation_view, name='announcement_recommendation'),

    # Global Search
    path('search/', views.global_search_view, name='global_search'),

    # News
    path('news/', views.news_list_view, name='news_list'),


    # Chat
    path('chat/create/', views.chat_create_or_get_view, name='chat_create'),
    path('chat/<int:chat_id>/', views.chat_detail_view, name='chat_detail'),
    path('chat/<int:chat_id>/message/', views.message_create_view, name='message_create'),
    path('chats/', views.user_chats_view, name='chat_list'),

    # AI support chat (DeepSeek)
    path('api/ai-chat/', views_ai_chat.ai_chat_view, name='ai_chat'),

    # OtherAnnouncement
    path('others/', views.other_announcement_list_create_view, name='other_announcement_list'),
    
    # User's Announcements
    path('my-announcements/', views.user_announcements_view, name='announcement_user_list'),
    path('donation/', views.donation_view, name='donation'),
    path('donation/process/', views.process_donation, name='process_donation'),
    path('donation/success/', views.donation_success, name='donation_success'),
    path('donation/list/', views.donation_list, name='donation_list'),
    path('webhook/yookassa/', views.yookassa_webhook, name='yookassa_webhook'),
    
    # Admin views
    path('approval/announcements/', views.admin_announcement_approval_view, name='admin_announcement_approval'),
    
    # Notifications
    path('notifications/', views.user_notifications_view, name='notifications'),
    path('fkko-autocomplete/', FkkoAutocomplete.as_view(), name='fkko-autocomplete'),
    path('fkko-suggestions/', fkko_suggestions, name='fkko-suggestions'),

]

if settings.DEBUG:  # Только для разработки
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

    