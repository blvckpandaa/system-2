from django.db import models
from django.conf import settings
from django.utils.text import slugify
from django.utils import timezone
from datetime import timedelta
from django.contrib.auth.models import AbstractUser
import random
import string
from mptt.models import MPTTModel, TreeForeignKey
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType

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
        return f"Профиль: {self.user.username}"

    class Meta:
        db_table = "user_profiles"
        verbose_name = "Профиль пользователя"
        verbose_name_plural = "Профили пользователей"

class Banner(models.Model):
    image = models.ImageField(upload_to='banners/')
    alt_text = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.alt_text or "Баннер"

    class Meta:
        verbose_name = "Баннер"
        verbose_name_plural = "Баннеры"

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
        verbose_name = "Тарифный план"
        verbose_name_plural = "Тарифные планы"

class AnalyticsDummy(models.Model):
    class Meta:
        verbose_name = "Аналитика"
        verbose_name_plural = "Аналитика"

    def __str__(self):
        return "Аналитические данные"

class Category(MPTTModel):
    name = models.CharField(max_length=255)
    image = models.ImageField(upload_to='category_imgs/', null=True, blank=True)
    parent = TreeForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='children')
    meta_title = models.CharField(max_length=255, blank=True, null=True)
    meta_description = models.TextField(blank=True, null=True)

    class MPTTMeta:
        order_insertion_by = ['name']

    class Meta:
        verbose_name = "Категория"
        verbose_name_plural = "Категории"

    def __str__(self):
        return self.name

STATUS_CHOICES = (
    ('draft', 'Черновик'),
    ('published', 'Опубликовано'),
    ('archived', 'Архивировано')
)

def generate_unique_slug(title, model_class, pk=None):
    base_slug = slugify(title)
    slug_candidate = base_slug
    n = 1
    while True:
        existing = model_class.objects.filter(slug=slug_candidate)
        if pk:
            existing = existing.exclude(pk=pk)
        if not existing.exists():
            return slug_candidate
        random_suffix = ''.join(random.choices(string.digits, k=4))
        slug_candidate = f"{base_slug}-{random_suffix}"
        n += 1

class Announcement(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='announcements')
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True, related_name='announcements')
    title = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True, blank=True)
    description = models.TextField()
    STATUS_CHOICES = (
        ('draft', 'Черновик'),
        ('pending', 'На модерации'),
        ('published', 'Опубликовано'),
        ('archived', 'Архивировано')
    )
    condition = models.CharField(max_length=50, blank=True, null=True)
    location = models.CharField(max_length=255, blank=True, null=True)
    city = models.CharField(max_length=100, blank=True, null=True)
    phone = models.CharField(max_length=20, blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    plan = models.ForeignKey(Plan, on_delete=models.SET_NULL, null=True, blank=True)
    priority = models.IntegerField(default=1)
    fkko_code = models.CharField(max_length=500, blank=True, null=True, verbose_name="Код ФККО (через запятую)")
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    is_negotiable = models.BooleanField(default=False)
    views_count = models.PositiveIntegerField(default=0)
    expiration_date = models.DateTimeField(blank=True, null=True)
    meta_title = models.CharField(max_length=255, blank=True, null=True)
    meta_description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = generate_unique_slug(self.title, Announcement)
        else:
            self.slug = generate_unique_slug(self.title, Announcement, pk=self.pk)
        if self.plan:
            self.priority = self.plan.priority
        is_new = self.pk is None
        super().save(*args, **kwargs)
        if is_new:
            Notification.objects.create(
                content_type=ContentType.objects.get_for_model(self),
                object_id=self.pk,
                title="Новое объявление",
                message=f"Пользователь {self.user.username} создал новое объявление: {self.title}",
                notification_type="announcement_new"
            )

    def __str__(self):
        return self.title

    class Meta:
        verbose_name = "Объявление"
        verbose_name_plural = "Объявления"
        ordering = ['-priority', '-created_at']

class AnnouncementImage(models.Model):
    announcement = models.ForeignKey(Announcement, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='announcements/')

    def __str__(self):
        return f"Изображение: {self.announcement.title}"

    class Meta:
        verbose_name = "Изображение объявления"
        verbose_name_plural = "Изображения объявлений"

class GalleryImage(models.Model):
    image  = models.ImageField(upload_to='gallery/')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Галерея #{self.id}"

    class Meta:
        verbose_name = "Изображение в галерее"
        verbose_name_plural = "Галерея"

class Payment(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    announcement = models.ForeignKey(Announcement, on_delete=models.CASCADE)
    plan = models.ForeignKey(Plan, on_delete=models.SET_NULL, null=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_id = models.CharField(max_length=100, null=True, blank=True)
    paid = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        plan_name = self.plan.name if self.plan else 'Без плана'
        return f"Платёж: {self.user.username} - {plan_name} ({self.amount})"

    class Meta:
        verbose_name = "Платёж"
        verbose_name_plural = "Платежи"

class Favorite(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    announcement = models.ForeignKey(Announcement, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} -> {self.announcement.title}"

    class Meta:
        unique_together = ('user', 'announcement')
        verbose_name = "Избранное"
        verbose_name_plural = "Избранное"

class Comment(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    announcement = models.ForeignKey(Announcement, on_delete=models.CASCADE, related_name='comments')
    text = models.TextField()
    rating = models.PositiveIntegerField(default=5)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Комментарий от {self.user.username} на {self.announcement.title}"

    class Meta:
        verbose_name = "Комментарий"
        verbose_name_plural = "Комментарии"

class News(models.Model):
    title = models.CharField(max_length=255)
    content = models.TextField()
    image = models.ImageField(upload_to='news/', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title

    class Meta:
        verbose_name = "Новость"
        verbose_name_plural = "Новости"

class Chat(models.Model):
    announcement = models.ForeignKey(Announcement, on_delete=models.CASCADE, related_name='chats', null=True, blank=True)
    participants = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name='chats')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Чат: {self.announcement.title}" if self.announcement else "Чат"

class Message(models.Model):
    chat = models.ForeignKey(Chat, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.sender.username}: {self.text[:20]}"

    class Meta:
        ordering = ['created_at']
        verbose_name = "Сообщение"
        verbose_name_plural = "Сообщения"

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
        verbose_name = "Другое объявление"
        verbose_name_plural = "Другие объявления"

class Donation(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='donations')
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

class Notification(models.Model):
    NOTIFICATION_TYPES = [
        ('announcement_new', 'Новое объявление'),
        ('announcement_reported', 'Жалоба на объявление'),
        ('user_registered', 'Новый пользователь'),
        ('payment_received', 'Получен платёж'),
        ('announcement_approved', 'Объявление одобрено'),
        ('announcement_rejected', 'Объявление отклонено'),
    ]

    recipient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notifications', null=True, blank=True)
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')
    title = models.CharField(max_length=255)
    message = models.TextField()
    notification_type = models.CharField(max_length=50, choices=NOTIFICATION_TYPES)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title} ({self.created_at.strftime('%d.%m.%Y %H:%M')})"

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Уведомление"
        verbose_name_plural = "Уведомления"
