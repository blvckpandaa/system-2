from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType

from .models import Announcement, Notification, Payment, User

@receiver(post_save, sender=Announcement)
def create_announcement_notification(sender, instance, created, **kwargs):
    """Создает уведомление для администраторов о новом объявлении"""
    if created:
        # Получаем всех администраторов
        admins = User.objects.filter(is_staff=True)
        
        # Тип контента для Announcement
        content_type = ContentType.objects.get_for_model(instance)
        
        # Создаем уведомление для каждого администратора
        for admin in admins:
            Notification.objects.create(
                recipient=admin,
                content_type=content_type,
                object_id=instance.pk,
                title="Новое объявление",
                message=f"Пользователь {instance.user.username} создал новое объявление: {instance.title}",
                notification_type="announcement_new"
            )

@receiver(post_save, sender=get_user_model())
def create_user_registered_notification(sender, instance, created, **kwargs):
    """Создает уведомление для администраторов о новом пользователе"""
    if created:
        # Получаем всех администраторов
        admins = User.objects.filter(is_staff=True)
        
        # Тип контента для User
        content_type = ContentType.objects.get_for_model(instance)
        
        # Создаем уведомление для каждого администратора
        for admin in admins:
            # Пропускаем отправку уведомления самому себе
            if admin.pk != instance.pk:
                Notification.objects.create(
                    recipient=admin,
                    content_type=content_type,
                    object_id=instance.pk,
                    title="Новый пользователь",
                    message=f"Зарегистрирован новый пользователь: {instance.username}",
                    notification_type="user_registered"
                )

@receiver(post_save, sender=Payment)
def create_payment_notification(sender, instance, created, **kwargs):
    """Создает уведомление для администраторов о новой оплате"""
    if created or (not created and instance.paid):
        # Получаем всех администраторов
        admins = User.objects.filter(is_staff=True)
        
        # Тип контента для Payment
        content_type = ContentType.objects.get_for_model(instance)
        
        # Создаем уведомление для каждого администратора
        status = "оплачен" if instance.paid else "создан"
        for admin in admins:
            Notification.objects.create(
                recipient=admin,
                content_type=content_type,
                object_id=instance.pk,
                title="Платеж " + status,
                message=f"Платеж от пользователя {instance.user.username} на сумму {instance.amount} руб. {status}",
                notification_type="payment_received"
            ) 
