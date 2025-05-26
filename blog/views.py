import re

from bs4 import BeautifulSoup
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, HttpResponseBadRequest, HttpResponseForbidden, HttpResponseNotAllowed
from django.core.exceptions import PermissionDenied
from django.db.models import Q, Avg
from django.conf import settings
from django.core.paginator import Paginator
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
import random
import uuid
from yookassa import Configuration, Payment as YooPayment
from django.contrib import messages
from django.urls import reverse
from django.contrib.auth.decorators import login_required
from django.contrib.contenttypes.models import ContentType
from .models import (
    User, UserProfile, Banner, Plan, AnalyticsDummy,
    Category, Announcement, AnnouncementImage, Payment, Favorite,
    Comment, News, Chat, Message, GalleryImage, OtherAnnouncement, Donation, Notification
)
from .forms import (
    RegisterForm, LoginForm, AnnouncementForm, CommentForm
)
import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Sum
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.template.context_processors import request
import requests
from dal import autocomplete
from django.conf import settings

from .utils.fkko_search import search_fkko
from .utils.semantic_fkko import semantic_search_fkko

Configuration.account_id = settings.YOOKASSA_SHOP_ID
Configuration.secret_key = settings.YOOKASSA_SECRET_KEY

def pending_announcements_processor(request):
    """Context processor to add pending announcements count for admin users"""
    context = {}
    if request.user.is_authenticated and request.user.is_staff:
        context['pending_count'] = Announcement.objects.filter(status='pending').count()
    return context

def unread_notifications_processor(request):
    """Context processor to add unread notifications count for authenticated users"""
    context = {}
    if request.user.is_authenticated:
        context['unread_notifications_count'] = Notification.objects.filter(
            recipient=request.user, 
            is_read=False
        ).count()
    return context

def index_view(request):
    banners = Banner.objects.all()
    elonlar = Announcement.objects.filter(status='published').order_by('-priority', '-created_at')[:6]
    plans = Plan.objects.all()
    news = News.objects.order_by('-created_at')[:3]
    categories = Category.objects.all()
    context = {
        'banners': banners,
        'elonlar': elonlar,
        'plans': plans,
        'news': news,
        'categories': categories
    }
    return render(request, 'index.html', context)


def register_view(request):
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()  
            return redirect('login')
        else:
            return render(request, 'register.html', {'form': form})
    else:
        form = RegisterForm()
        return render(request, 'register.html', {'form': form})


def login_view(request):
    if request.method == 'POST':
        form = LoginForm(request=request, data=request.POST)
        if form.is_valid():
            user = form.get_user() 
            login(request, user)    
            return redirect('index')
        else:
            return render(request, 'login.html', {'form': form})
    else:
        form = LoginForm()
        return render(request, 'login.html', {'form': form})


def logout_view(request):
    logout(request)
    return redirect('index')  


@login_required
def user_profile_view(request):
    profile, created = UserProfile.objects.get_or_create(user=request.user)
    return render(request, 'profile.html', {'profile': profile})

@login_required
def user_profile_update_view(request):
    if request.method == 'POST':
        profile, created = UserProfile.objects.get_or_create(user=request.user)
        bio = request.POST.get('bio')
        telegram = request.POST.get('telegram_link')
        instagram = request.POST.get('instagram_link')
        if bio is not None:
            profile.bio = bio
        if telegram is not None:
            profile.telegram_link = telegram
        if instagram is not None:
            profile.instagram_link = instagram
        
        if 'avatar' in request.FILES:
            profile.avatar = request.FILES['avatar']
        
        profile.save()
        return redirect('profile')
    return HttpResponseNotAllowed(['POST'])


def banner_list_view(request):
    banners = Banner.objects.all()
    return render(request, "banners.html", {"banners": banners})


def gallery_list_view(request):
    gal = GalleryImage.objects.all()
    return render(request, 'gallery.html', {'gallery': gal})


def plan_list_view(request):
    plans = Plan.objects.all()
    return render(request, 'plans.html', {'plans': plans})


def plan_detail_view(request, pk):
    """Представление для отображения подробной информации о тарифе"""
    plan = get_object_or_404(Plan, pk=pk)
    return render(request, 'plan_detail.html', {'plan': plan})


def category_list_view(request):
    cats = Category.objects.all()
    return render(request, 'category_list.html', {'cats': cats})


def category_detail_view(request, pk):
    cat = get_object_or_404(Category, pk=pk)
    ann_list = cat.announcements.filter(status='published')
    context = {
        'cat': cat,
        'ann_list': ann_list
    }
    return render(request, 'category_detail.html', context)


def category_tree_view(request):
    root_cats = Category.objects.filter(parent__isnull=True).order_by('name')
    return render(request, 'category_tree.html', {
        'root_cats': root_cats
    })

def announcement_list_view(request):
    qs = Announcement.objects.filter(status='published').order_by('-priority', '-created_at')
    cat_id = request.GET.get('category')
    if cat_id:
        qs = qs.filter(category_id=cat_id)

    city = request.GET.get('city')
    if city:
        qs = qs.filter(city__icontains=city)

    price_min = request.GET.get('price_min')
    price_max = request.GET.get('price_max')
    if price_min and price_max:
        qs = qs.filter(price__range=(price_min, price_max))

    search_q = request.GET.get('q')
    if search_q:
        qs = qs.filter(Q(title__icontains=search_q) | Q(description__icontains=search_q))

    rating_min = request.GET.get('rating_min')
    if rating_min:
        qs = qs.annotate(avg_rating=Avg('comments__rating')).filter(avg_rating__gte=rating_min)

    paginator = Paginator(qs, 10)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    categories = Category.objects.all()

    return render(request, 'announcements_list.html', {
        'page_obj': page_obj,
        'total': paginator.count,    
        'categories': categories,   
    })

@login_required
def announcement_create_view(request):
    """Create new announcement"""
    if request.method == 'POST':
        # Проверка количества объявлений пользователя за последний час
        # чтобы избежать спама
        one_hour_ago = timezone.now() - timezone.timedelta(hours=1)
        recent_announcements_count = Announcement.objects.filter(
            user=request.user, 
            created_at__gte=one_hour_ago
        ).count()
        
        if recent_announcements_count >= 5:
            messages.error(request, "Вы можете создать не более 5 объявлений в час. Пожалуйста, попробуйте позже.")
            form = AnnouncementForm(request.POST)
            categories = Category.objects.all()
            plans = Plan.objects.all()
            return render(request, 'announcement_create.html', {
                'form': form,
                'categories': categories,
                'plans': plans,
            })
        
        # Используем атомарную транзакцию для предотвращения дублирования объявлений
        with transaction.atomic():
            # Создаем форму с данными из запроса
            form = AnnouncementForm(request.POST)
            
            if form.is_valid():
                announcement = form.save(commit=False)
                announcement.user = request.user
                announcement.status = 'pending'  # Change status to pending for moderation
                print(f"DEBUG: Creating announcement with status: {announcement.status}")
                
                # Проверка на запрещенный контент (можно расширить)
                forbidden_words = ["мошенничество", "нелегальный", "запрещено"]
                for word in forbidden_words:
                    if word.lower() in announcement.title.lower() or word.lower() in announcement.description.lower():
                        messages.error(request, f"Объявление содержит запрещенное слово: {word}")
                        return render(request, 'announcement_create.html', {
                            'form': form,
                            'categories': Category.objects.all(),
                            'plans': Plan.objects.all(),
                        })
                
                announcement.save()
                print(f"DEBUG: Saved announcement with ID: {announcement.id}, Status: {announcement.status}")
                
                if 'files' in request.FILES:
                    files = request.FILES.getlist('files')
                    for file in files:
                        AnnouncementImage.objects.create(
                            announcement=announcement,
                            image=file
                        )
                
                if announcement.plan and announcement.plan.amount > 0:
                    messages.success(request, "Объявление создано и отправлено на модерацию! Переходим к оплате тарифа.")
                    return redirect('payment_create', announcement_id=announcement.id, plan_id=announcement.plan.id)
                else:
                    # Changed: Announcement stays in pending status
                    messages.success(request, "Объявление успешно создано и отправлено на модерацию! После проверки администратором оно будет опубликовано.")
                    return redirect('announcement_detail', pk=announcement.id)
            else:
                messages.error(request, "Пожалуйста, исправьте ошибки в форме.")
                categories = Category.objects.all()
                plans = Plan.objects.all()
                return render(request, 'announcement_create.html', {
                    'form': form,
                    'categories': categories,
                    'plans': plans,
                })
    else:  # При GET запросе создаем пустую форму
        form = AnnouncementForm()
    
    categories = Category.objects.all()
    plans = Plan.objects.all()

    return render(request, 'announcement_create.html', {
        'form': form,
        'categories': categories,
        'plans': plans,
    })



def announcement_detail_view(request, pk):
    ann = get_object_or_404(Announcement, pk=pk)
    ann.views_count += 1
    ann.save(update_fields=['views_count'])
    breadcrumb_list = []
    if ann.category:
        breadcrumb_list = ann.category.get_ancestors(include_self=True)

    is_favorite = False
    if request.user.is_authenticated:
        is_favorite = Favorite.objects.filter(user=request.user, announcement=ann).exists()
    
    similar_announcements = []
    if ann.category:
        similar_announcements = Announcement.objects.filter(
            category=ann.category, 
            status='published'
        ).exclude(id=pk)[:3]

    source_type = "user"
    
    # Adding admin approval ability
    is_pending = ann.status == 'pending'
    is_admin = request.user.is_authenticated and request.user.is_staff

    return render(request, 'announcement_detail.html', {
        'announcement': ann,
        'breadcrumb_list': breadcrumb_list,
        'is_favorite': is_favorite,
        'similar_announcements': similar_announcements,
        'source_type': source_type,
        'is_pending': is_pending,
        'is_admin': is_admin
    })


@login_required
def announcement_update_view(request, pk):
    """Update announcement"""
    ann = get_object_or_404(Announcement, pk=pk)
    if ann.user != request.user:
        raise PermissionDenied("Faqat o'z e'loningizni o'zgarta olasiz.")

    if request.method == 'POST':
        form = AnnouncementForm(request.POST, request.FILES, instance=ann)
        if form.is_valid():
            updated = form.save(commit=False)
            if updated.plan:
                updated.priority = updated.plan.priority
            # If the announcement is in draft status, set it to pending when updated
            if updated.status == 'draft':
                updated.status = 'pending'
            updated.save()
            return redirect('announcement_detail', pk=pk)
        else:
            categories = Category.objects.all()
            plans = Plan.objects.all()
            return render(request, 'announcement_create.html', {
                'form': form,
                'categories': categories,
                'plans': plans
            })
    else:
        form = AnnouncementForm(instance=ann)
        categories = Category.objects.all()
        plans = Plan.objects.all()
        return render(request, 'announcement_create.html', {
            'form': form,
            'categories': categories,
            'plans': plans
        })



@login_required
def announcement_delete_view(request, pk):
    ann = get_object_or_404(Announcement, pk=pk)
    if ann.user != request.user:
        raise PermissionDenied("Faqat o'z e'loningizni o'chira olasiz.")
    ann.delete()
    return redirect('announcement_list')


@login_required
def announcement_activate_view(request, pk):
    """Activate announcement (status=published)"""
    ann = get_object_or_404(Announcement, pk=pk)
    if ann.user != request.user:
        raise PermissionDenied("Вы можете активировать только свои объявления.")
    ann.status = 'published'
    ann.save(update_fields=['status'])
    return redirect('announcement_detail', pk=pk)


@login_required
def announcement_deactivate_view(request, pk):
    """Deactivate announcement (status=archived)"""
    ann = get_object_or_404(Announcement, pk=pk)
    if ann.user != request.user:
        raise PermissionDenied("Вы можете деактивировать только свои объявления.")
    ann.status = 'draft'
    ann.save(update_fields=['status'])
    return redirect('announcement_detail', pk=pk)


@login_required
def announcement_upgrade_view(request, pk):
    """Upgrade announcement with payment"""
    ann = get_object_or_404(Announcement, pk=pk)
    if ann.user != request.user:
        raise PermissionDenied("Вы можете изменять тариф только своих объявлений.")
    
    if request.method == 'POST':
        plan_id = request.POST.get('plan_id')
        if plan_id:
            plan = get_object_or_404(Plan, id=plan_id)
            if plan.amount > 0:
                # Если тариф платный, перенаправляем на страницу оплаты
                return redirect('payment_create', announcement_id=ann.id, plan_id=plan.id)
            else:
                # Если тариф бесплатный, сразу применяем его
                ann.plan = plan
                ann.priority = plan.priority
                ann.save()
                return redirect('announcement_detail', pk=pk)
    
    # Если GET-запрос или не указан план, показываем форму выбора тарифа
    plans = Plan.objects.all()
    return render(request, 'announcement_upgrade.html', {
        'announcement': ann,
        'plans': plans
    })


@login_required
def create_payment_view(request, announcement_id, plan_id):
    announcement = get_object_or_404(Announcement, id=announcement_id)
    plan = get_object_or_404(Plan, id=plan_id)
    if announcement.user != request.user:
        return HttpResponseForbidden("Недоступно.")
    if plan.amount == 0:
        pay = Payment.objects.create(user=request.user, announcement=announcement, plan=plan, amount=0, payment_id='', paid=True)
        announcement.plan = plan
        announcement.priority = plan.priority
        # Status stays as 'pending' instead of being set to 'published'
        announcement.save()
        messages.success(request, "План применен. Объявление ожидает проверки администратором.")
        return redirect('announcement_detail', pk=announcement.pk)
    try:
        yoo_payment = YooPayment.create({
            "amount": {"value": str(plan.amount), "currency": "RUB"},
            "confirmation": {
                "type": "redirect",
                "return_url": "https://example.com/payment/success/"
            },
            "capture": True,
            "description": f"Оплата '{announcement.title}' (Тариф: {plan.name})",
            "receipt": {
                "customer": {
                    "email": request.user.email
                },
                "items": [
                    {
                        "description": f"Тариф: {plan.name}",
                        "quantity": "1.00",
                        "amount": {
                            "value": str(plan.amount),
                            "currency": "RUB"
                        },
                        "vat_code": 1,
                        "payment_mode": "full_payment",
                        "payment_subject": "commodity"
                    }
                ]
            }
        }, uuid.uuid4())
    except Exception as e:
        return HttpResponse(f"Ошибка YooKassa: {e}", status=500)
    pay_obj = Payment.objects.create(user=request.user, announcement=announcement, plan=plan, amount=plan.amount, payment_id=yoo_payment.id, paid=False)
    confirmation_url = yoo_payment.confirmation.confirmation_url
    return render(request, 'payment_create.html', {"payment": pay_obj, "confirmation_url": confirmation_url})


@login_required
def check_payment_status_view(request, payment_id):
    pay = get_object_or_404(Payment, payment_id=payment_id, user=request.user)
    
    try:
        yoo_pay = YooPayment.find_one(payment_id)
    except Exception as e:
        return render(request, 'payment_status.html', {
            'error': "Ошибка YooKassa",
            'details': str(e)
        })

    if yoo_pay.status == 'succeeded':
        if not pay.paid:
            pay.paid = True
            pay.save()
            ann = pay.announcement
            ann.plan = pay.plan
            ann.priority = pay.plan.priority
            # Status stays as 'pending' instead of being set to 'published'
            ann.save()
            messages.success(request, "Оплата прошла успешно. Объявление ожидает проверки администратором.")
        return redirect('announcement_detail', pk=pay.announcement.pk)

    elif yoo_pay.status == 'pending':
        return render(request, 'payment_status.html', {
            'pay': pay,
            'status': yoo_pay.status,
            'message': "Оплата в процессе"
        })

    else:
        return render(request, 'payment_status.html', {
            'pay': pay,
            'status': yoo_pay.status,
            'message': "Оплата не прошла"
        })


@login_required
def favorite_list_view(request):
    favs = Favorite.objects.filter(user=request.user)
    return render(request, 'favorite_list.html', {'favs': favs})

@login_required
def favorite_add_view(request):
    if request.method == 'POST':
        ann_id = request.POST.get('announcement')
        ann = get_object_or_404(Announcement, id=ann_id)
        Favorite.objects.get_or_create(user=request.user, announcement=ann)
        return redirect('favorite_list')
    return HttpResponseNotAllowed(['POST'])

@login_required
def favorite_delete_view(request, pk):
    if request.method == 'POST':
        fav = get_object_or_404(Favorite, pk=pk, user=request.user)
        fav.delete()
        return redirect('favorite_list')
    return HttpResponseNotAllowed(['POST'])


def comment_list_create_view(request):
    if request.method == 'GET':
        announcement_id = request.GET.get('announcement')
        qs = Comment.objects.all().order_by('-created_at')
        if announcement_id:
            qs = qs.filter(announcement_id=announcement_id)
        return render(request, 'comment_list.html', {'comments': qs})

    elif request.method == 'POST':
        if not request.user.is_authenticated:
            raise PermissionDenied("Avval kiring.")
        form = CommentForm(request.POST)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.user = request.user
            obj.save()
            return redirect('announcement_detail', pk=obj.announcement.id)
        else:
            return render(request, 'comment_list.html', {'form_errors': form.errors})
    return HttpResponseNotAllowed(['GET', 'POST'])


def announcement_recommendation_view(request, pk):
    ann = get_object_or_404(Announcement, pk=pk)
    cat = ann.category
    recommended = []
    if cat:
        qs = Announcement.objects.filter(category=cat, status='published').exclude(id=pk)
        all_ids = list(qs.values_list('id', flat=True))
        if all_ids:
            random_ids = random.sample(all_ids, min(len(all_ids), 5))
            recommended = Announcement.objects.filter(pk__in=random_ids)
    return render(request, 'announcements_list.html', {
        'page_obj': recommended
    })


def global_search_view(request):
    query = request.GET.get('q', '')
    category_id = request.GET.get('category', '')
    city = request.GET.get('city', '')

    # Начальное фильтрующее условие: только опубликованные объявления
    announcements = Announcement.objects.filter(status='published')

    # Фильтрация по поисковому запросу
    if query:
        announcements = announcements.filter(
            Q(title__icontains=query) |
            Q(description__icontains=query) |
            Q(fkko_code__icontains=query)  # Добавляем поиск по коду ФККО
        )

    # Фильтрация по категории
    if category_id:
        try:
            category = Category.objects.get(id=category_id)
            # Получаем все подкатегории
            descendant_ids = category.get_descendants(include_self=True).values_list('id', flat=True)
            announcements = announcements.filter(category__in=descendant_ids)
        except Category.DoesNotExist:
            pass

    # Фильтрация по городу
    if city:
        announcements = announcements.filter(city__icontains=city)

    # Сортировка по приоритету и дате
    announcements = announcements.order_by('-priority', '-created_at')

    # Получаем список уникальных городов для фильтра
    cities = Announcement.objects.filter(status='published').exclude(city__isnull=True).exclude(city='').values_list(
        'city', flat=True).distinct()

    # Передаем данные в контекст
    context = {
        'query': query,
        'category_id': category_id,
        'city': city,
        'announcements': announcements,
        'cities': cities,
        'categories': Category.objects.all(),  # передаем все категории для фильтра
    }

    return render(request, 'search.html', context)


def news_list_view(request):
    news = News.objects.all().order_by('-created_at')
    return render(request, 'news_list.html', {'news': news})


@login_required
def chat_create_or_get_view(request):
    if request.method == 'POST':
        announcement_id = request.POST.get('announcement_id')
        if announcement_id:
            ann = get_object_or_404(Announcement, id=announcement_id)
            chat, created = Chat.objects.get_or_create(announcement=ann)
            chat.participants.add(request.user)
            chat.participants.add(ann.user)
            return redirect('chat_detail', chat_id=chat.id)
        return HttpResponse("announcement_id kerak!", status=400)
    return HttpResponseNotAllowed(['POST'])

@login_required
def chat_detail_view(request, chat_id):
    chat = get_object_or_404(Chat, id=chat_id)
    if request.user not in chat.participants.all():
        return HttpResponseForbidden("Siz bu chatda emassiz!")
    messages = chat.messages.order_by('created_at')
    return render(request, 'chat_detail.html', {
        'chat': chat,
        'messages': messages,
    })

@login_required
def message_create_view(request, chat_id):
    if request.method == 'POST':
        chat = get_object_or_404(Chat, id=chat_id)
        if request.user not in chat.participants.all():
            return HttpResponseForbidden("Siz bu chatda emassiz!")
        text = request.POST.get('text')
        if not text:
            return HttpResponse("Matn yozilmadi!", status=400)
        Message.objects.create(chat=chat, sender=request.user, text=text)
        return redirect('chat_detail', chat_id=chat.id)
    return HttpResponseNotAllowed(['POST'])

@login_required
def user_chats_view(request):
    chats = Chat.objects.filter(participants=request.user)
    return render(request, 'chat_list.html', {'chats': chats})

@login_required
def user_announcements_view(request):
    """Показывает список объявлений текущего пользователя"""
    announcements = Announcement.objects.filter(user=request.user).order_by('-created_at')
    
    # Считаем количество объявлений по статусам
    published_count = announcements.filter(status='published').count()
    pending_count = announcements.filter(status='pending').count()  # Added for pending count
    draft_count = announcements.filter(status='draft').count()
    archived_count = announcements.filter(status='archived').count()
    
    print(f"DEBUG: User {request.user.username} has {pending_count} pending announcements")
    print(f"DEBUG: Status counts - published: {published_count}, pending: {pending_count}, draft: {draft_count}, archived: {archived_count}")
    
    context = {
        'announcements': announcements,
        'approved_count': published_count,
        'pending_count': pending_count,  # Added to context
        'draft_count': draft_count,
        'archived_count': archived_count
    }
    
    return render(request, 'announcement_user_list.html', context)

def other_announcement_list_create_view(request):
    others = OtherAnnouncement.objects.all().order_by('-created_at')
    return render(request, 'other_announcement_list.html', {
        'other_list': others
    })

@login_required
def donation_view(request):
    """Страница создания пожертвования"""
    return render(request, 'donation.html')

@login_required
def process_donation(request):
    """Обработка платежа пожертвования"""
    if request.method == 'POST':
        amount = request.POST.get('amount')
        
        try:
            # Создаем запись в базе данных
            donation = Donation.objects.create(
                user=request.user,
                amount=amount,
                paid=False
            )
            
            # Создаем платеж в ЮKassa
            payment = YooPayment.create({
                "amount": {
                    "value": amount,
                    "currency": "RUB"
                },
                "confirmation": {
                    "type": "redirect",
                    "return_url": request.build_absolute_uri(reverse('donation_success'))
                },
                "capture": True,
                "description": f"Пожертвование от {request.user.username}",
                "receipt": {
                    "customer": {
                        "email": request.user.email
                    },
                    "items": [
                        {
                            "description": "Пожертвование",
                            "quantity": "1.00",
                            "amount": {
                                "value": amount,
                                "currency": "RUB"
                            },
                            "vat_code": 1,
                            "payment_mode": "full_payment",
                            "payment_subject": "service"
                        }
                    ]
                },
                "metadata": {
                    "donation_id": donation.id
                }
            })
            
            # Обновляем запись в БД с ID платежа
            donation.payment_id = payment.id
            donation.save()
            
            # Перенаправляем на страницу оплаты
            return redirect(payment.confirmation.confirmation_url)
            
        except Exception as e:
            messages.error(request, f"Ошибка при создании платежа: {str(e)}")
            return redirect('donation')
            
    return redirect('donation')

@login_required
def donation_success(request):
    """Страница успешного пожертвования"""
    return render(request, 'donation_success.html')

@login_required
def donation_list(request):
    """Список пожертвований пользователя"""
    donations = Donation.objects.filter(user=request.user).order_by('-created_at')
    total_amount = donations.filter(paid=True).aggregate(Sum('amount'))['amount__sum'] or 0
    
    return render(request, 'donation_list.html', {
        'donations': donations,
        'total_amount': total_amount
    })

# Webhook для получения уведомлений от ЮKassa
@csrf_exempt
def yookassa_webhook(request):
    if request.method == 'POST':
        # Получаем данные от ЮKassa
        event_json = json.loads(request.body)
        payment_id = event_json['object']['id']
        status = event_json['object']['status']
        
        # Проверяем статус платежа
        if status == 'succeeded':
            # Получаем ID пожертвования из метаданных
            donation_id = event_json['object']['metadata'].get('donation_id')
            if donation_id:
                try:
                    # Обновляем статус пожертвования
                    donation = Donation.objects.get(id=donation_id)
                    donation.paid = True
                    donation.save()
                except Donation.DoesNotExist:
                    return JsonResponse({'status': 'error'}, status=404)
        
        return JsonResponse({'status': 'success'})
    
    return JsonResponse({'status': 'error'}, status=405)

@login_required
def admin_announcement_approval_view(request):
    """View for administrators to approve or reject pending announcements"""
    # Check if user is staff/admin
    if not request.user.is_staff:
        raise PermissionDenied("Только администраторы могут одобрять объявления.")
    
    # Get pending announcements
    pending_announcements = Announcement.objects.filter(status='pending').order_by('-created_at')
    print(f"DEBUG: Admin approval page found {pending_announcements.count()} pending announcements")
    for ann in pending_announcements:
        print(f"DEBUG: Pending announcement ID: {ann.id}, Title: {ann.title}, User: {ann.user.username}")
    
    # Handle approval/rejection
    if request.method == 'POST':
        announcement_id = request.POST.get('announcement_id')
        action = request.POST.get('action')
        
        if announcement_id and action:
            announcement = get_object_or_404(Announcement, id=announcement_id)
            
            if action == 'approve':
                announcement.status = 'published'
                announcement.save()
                # Create notification for the announcement owner
                Notification.objects.create(
                    recipient=announcement.user,
                    content_type=ContentType.objects.get_for_model(announcement),
                    object_id=announcement.id,
                    title="Объявление одобрено",
                    message=f"Ваше объявление \"{announcement.title}\" было одобрено администратором и опубликовано.",
                    notification_type="announcement_approved"
                )
                messages.success(request, f"Объявление '{announcement.title}' одобрено и опубликовано.")
            elif action == 'reject':
                announcement.status = 'draft'
                announcement.save()
                # Create notification for the announcement owner
                Notification.objects.create(
                    recipient=announcement.user,
                    content_type=ContentType.objects.get_for_model(announcement),
                    object_id=announcement.id,
                    title="Объявление отклонено",
                    message=f"Ваше объявление \"{announcement.title}\" было отклонено администратором. Вы можете отредактировать его и отправить на повторное рассмотрение.",
                    notification_type="announcement_rejected"
                )
                messages.warning(request, f"Объявление '{announcement.title}' отклонено.")
            
            # Check if request came from the detail page and redirect back there
            referer = request.META.get('HTTP_REFERER', '')
            if f'/announcements/{announcement_id}/' in referer:
                return redirect('announcement_detail', pk=announcement_id)
            
    return render(request, 'admin_announcement_approval.html', {
        'pending_announcements': pending_announcements
    })

@login_required
def user_notifications_view(request):
    """Display notifications for the current user"""
    notifications = Notification.objects.filter(recipient=request.user).order_by('-created_at')
    
    # Mark notifications as read when viewed
    if request.GET.get('mark_read') == 'true':
        notifications.update(is_read=True)
    
    # Get unread count for the navbar
    unread_count = notifications.filter(is_read=False).count()
    
    context = {
        'notifications': notifications,
        'unread_count': unread_count
    }
    
    return render(request, 'notifications.html', context)

class FkkoAutocomplete(autocomplete.Select2ListView):
    """
    Автодополнение из локального CSV с кодами ФККО.
    """
    def get_list(self):
        term = self.q or ''
        results = search_fkko(term)
        return [f"{row['code']} — {row['name']}" for row in results]
def fkko_suggestions(request):
    q = request.GET.get('q', '').strip()
    if len(q) < 2:
        from .utils.fkko_search import search_fkko
        return JsonResponse(search_fkko(q, limit=10), safe=False)

    sem = semantic_search_fkko(q, top_k=10, threshold=0.45)
    if sem:
        return JsonResponse(sem, safe=False)

    # fallback на простую подстроку
    from .utils.fkko_search import search_fkko
    return JsonResponse(search_fkko(q, limit=10), safe=False)

