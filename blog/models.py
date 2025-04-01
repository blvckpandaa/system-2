# myapp/models.py

from django.db import models
from django.conf import settings
from django.utils.text import slugify
from django.utils import timezone
from datetime import timedelta

# 1) Django auth uchun import
from django.contrib.auth.models import AbstractUser
import random
import string

# 2) MPTT uchun
from mptt.models import MPTTModel, TreeForeignKey

# --- Custom User model ---

class User(AbstractUser):


    email = models.EmailField(unique=True)


    def __str__(self):
        return self.username



class UserProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='profile')
    avatar = models.ImageField(upload_to='avatars/', null=True, blank=True)
    bio = models.TextField(blank=True, null=True)
    telegram_link = models.URLField(blank=True, null=True)
    instagram_link = models.URLField(blank=True, null=True)

    def __str__(self):
        return f"Profil: {self.user.username}"

    class Meta:
        db_table = "user_profiles"
        verbose_name = "Foydalanuvchi profili"
        verbose_name_plural = "Foydalanuvchi profillari"


class Banner(models.Model):
    image = models.ImageField(upload_to='banners/')
    alt_text = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.alt_text or "Banner"


PLAN_CHOICES = [
    ('basic', 'Базовый'),
    ('standard', 'Стандарт'),
    ('top', 'Топ'),
]

PLAN_PRIORITY = {
    'basic': 1,
    'standard': 2,
    'top': 3
}

class Plan(models.Model):
    name = models.CharField(max_length=20, choices=PLAN_CHOICES, unique=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    priority = models.IntegerField(default=1)

    def __str__(self):
        return f"{self.get_name_display()} - {self.amount} RUB"

    class Meta:
        verbose_name = "Tarif reja"
        verbose_name_plural = "Tarif rejalar"


class AnalyticsDummy(models.Model):
    """
    Faqat misol uchun - admin panelidagi statistika yoki umumiy tahlil ma'lumotlari.
    """
    class Meta:
        verbose_name = "Analitika"
        verbose_name_plural = "Analitikalar"

    def __str__(self):
        return "Analytics Data"


class Category(MPTTModel):
    name = models.CharField(max_length=255)
    image = models.ImageField(upload_to='category_imgs/', null=True, blank=True)
    parent = TreeForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='children'
    )
    meta_title = models.CharField(max_length=255, blank=True, null=True)
    meta_description = models.TextField(blank=True, null=True)

    class MPTTMeta:
        order_insertion_by = ['name']

    class Meta:
        verbose_name = "Kategoriya"
        verbose_name_plural = "Kategoriyalar"

    def __str__(self):
        return self.name

STATUS_CHOICES = (
    ('draft', 'Draft'),
    ('published', 'Published'),
    ('archived', 'Archived')
)

def generate_unique_slug(title, model_class, pk=None):
    base_slug = slugify(title)
    slug_candidate = base_slug
    n = 1

    while True:
        # Filter qilsak, o'zidan boshqa object bo'lmasin (pk!=pk).
        existing = model_class.objects.filter(slug=slug_candidate)
        if pk:
            existing = existing.exclude(pk=pk)

        if not existing.exists():
            return slug_candidate
        # Agar slug band bo'lsa, random qo'shamiz
        random_suffix = ''.join(random.choices(string.digits, k=4))
        slug_candidate = f"{base_slug}-{random_suffix}"
        n += 1


class Announcement(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='announcements')
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True, related_name='announcements')
    title = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True, blank=True)
    description = models.TextField()

    condition = models.CharField(max_length=50, blank=True, null=True)
    location = models.CharField(max_length=255, blank=True, null=True)
    city = models.CharField(max_length=100, blank=True, null=True)
    phone = models.CharField(max_length=20, blank=True, null=True)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    plan = models.ForeignKey(Plan, on_delete=models.SET_NULL, null=True, blank=True)
    priority = models.IntegerField(default=1)
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    is_negotiable = models.BooleanField(default=False)

    views_count = models.PositiveIntegerField(default=0)
    expiration_date = models.DateTimeField(blank=True, null=True)
    meta_title = models.CharField(max_length=255, blank=True, null=True)
    meta_description = models.TextField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "E'lon"
        verbose_name_plural = "E'lonlar"
        ordering = ['-priority', '-created_at']

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = generate_unique_slug(self.title, Announcement)
        else:
        
            self.slug = generate_unique_slug(self.title, Announcement, pk=self.pk)

        if self.plan:
            self.priority = self.plan.priority

        super().save(*args, **kwargs)

    def __str__(self):
        return self.title


class AnnouncementImage(models.Model):
    announcement = models.ForeignKey(Announcement, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='announcements/')

    def __str__(self):
        return f"Image of {self.announcement.title}"


class GalleryImage(models.Model):
    image  = models.ImageField(upload_to='gallery/')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"GalleryImage #{self.id}"


class Payment(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    announcement = models.ForeignKey(Announcement, on_delete=models.CASCADE)
    plan = models.ForeignKey(Plan, on_delete=models.SET_NULL, null=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_id = models.CharField(max_length=100, null=True, blank=True)
    paid = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        plan_name = self.plan.name if self.plan else 'NoPlan'
        return f"To'lov: {self.user.username} - {plan_name} ({self.amount})"

    class Meta:
        verbose_name = "To'lov"
        verbose_name_plural = "To'lovlar"


class Favorite(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    announcement = models.ForeignKey(Announcement, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'announcement')
        verbose_name = "Izbrannoe"
        verbose_name_plural = "Izbrannoe"

    def __str__(self):
        return f"{self.user.username} -> {self.announcement.title}"


class Comment(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    announcement = models.ForeignKey(Announcement, on_delete=models.CASCADE, related_name='comments')
    text = models.TextField()
    rating = models.PositiveIntegerField(default=5)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Comment by {self.user.username} on {self.announcement.title}"

    class Meta:
        verbose_name = "Koment"
        verbose_name_plural = "Komentlar"


class News(models.Model):
    title = models.CharField(max_length=255)
    content = models.TextField()
    image = models.ImageField(upload_to='news/', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title

    class Meta:
        verbose_name = "Yangilik"
        verbose_name_plural = "Yangiliklar"


class Chat(models.Model):
    announcement = models.ForeignKey(Announcement, on_delete=models.CASCADE, related_name='chats', null=True, blank=True)
    participants = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name='chats')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        if self.announcement:
            return f"Chat about: {self.announcement.title}"
        return "Chat"


class Message(models.Model):
    chat = models.ForeignKey(Chat, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"{self.sender.username}: {self.text[:20]}"


class OtherAnnouncement(models.Model):
    title = models.CharField(max_length=250)
    description = models.TextField()
    image = models.ImageField(upload_to='other_announcements/')
    price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    phone = models.CharField(max_length=30)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title

    class Meta:
        verbose_name = "Boshqa e'lon"
        verbose_name_plural = "Boshqa e'lonlar"

# Модель для пожертвований
class Donation(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, 
                            related_name='donations')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_id = models.CharField(max_length=100, null=True, blank=True)
    paid = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Пожертвование от {self.user.username}: {self.amount} RUB"
    
    class Meta:
        verbose_name = "Пожертвование"
        verbose_name_plural = "Пожертвования"
        ordering = ['-created_at']
