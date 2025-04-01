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
from .models import (
    User, UserProfile, Banner, Plan, AnalyticsDummy,
    Category, Announcement, AnnouncementImage, Payment, Favorite,
    Comment, News, Chat, Message, GalleryImage, OtherAnnouncement, Donation
)
from .forms import (
    RegisterForm, LoginForm, AnnouncementForm, CommentForm
)
import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Sum

# YOOKASSA SOZLAMALARI
Configuration.account_id = settings.YOOKASSA_SHOP_ID
Configuration.secret_key = settings.YOOKASSA_SECRET_KEY

def index_view(request):
    banners = Banner.objects.all()
    # Получаем только опубликованные объявления, отсортированные по приоритету и дате создания
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
            user = form.save()  # user saqlanadi
            # Avtomatik login qilmoqchi bo'lsak:
            # login(request, user)
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
            user = form.get_user()  # authenticate qilinadi
            login(request, user)    # sessionga foydalanuvchini kiritdik
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
        # Создаем форму с данными из запроса
        form = AnnouncementForm(request.POST)
        
        # Выводим полученные данные для отладки
        print("POST data:", request.POST)
        print("FILES data:", request.FILES)
        
        if form.is_valid():
            # Создаем объявление, но пока не сохраняем
            announcement = form.save(commit=False)
            # Устанавливаем пользователя
            announcement.user = request.user
            # Устанавливаем статус черновика
            announcement.status = 'draft'
            # Сохраняем объявление
            announcement.save()
            
            # Обрабатываем изображения
            if 'files' in request.FILES:
                files = request.FILES.getlist('files')
                for file in files:
                    AnnouncementImage.objects.create(
                        announcement=announcement,
                        image=file
                    )
            
            # Если выбран тарифный план с оплатой
            if announcement.plan and announcement.plan.amount > 0:
                return redirect('payment_create', announcement_id=announcement.id, plan_id=announcement.plan.id)
            else:
                # Если бесплатный план или план не выбран, сразу публикуем
                announcement.status = 'published'
                announcement.save()
                return redirect('announcement_detail', pk=announcement.id)
        else:
            # В случае ошибок валидации
            print("Form errors:", form.errors)
            # Получаем списки категорий и тарифов для повторного отображения формы
            categories = Category.objects.all()
            plans = Plan.objects.all()
            # Передаем форму обратно с ошибками
            return render(request, 'announcement_create.html', {
                'form': form,
                'categories': categories,
                'plans': plans,
            })
    else:
        # При GET запросе создаем пустую форму
        form = AnnouncementForm()
    
    # Получаем списки категорий и тарифов из базы данных
    categories = Category.objects.all()
    plans = Plan.objects.all()
    
    # Передаем все в шаблон
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
    
    # Проверяем, добавлено ли объявление в избранное текущим пользователем
    is_favorite = False
    if request.user.is_authenticated:
        is_favorite = Favorite.objects.filter(user=request.user, announcement=ann).exists()
    
    # Получаем похожие объявления
    similar_announcements = []
    if ann.category:
        similar_announcements = Announcement.objects.filter(
            category=ann.category, 
            status='published'
        ).exclude(id=pk)[:3]

    # Всегда используем одинаковый шаблон независимо от источника объявления
    source_type = "user"

    return render(request, 'announcement_detail.html', {
        'announcement': ann,
        'breadcrumb_list': breadcrumb_list,
        'is_favorite': is_favorite,
        'similar_announcements': similar_announcements,
        'source_type': source_type
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
            updated.save()
            return redirect('announcement_detail', pk=pk)
        else:
            return render(request, 'announcement_create.html', {'form': form})
    else:
        form = AnnouncementForm(instance=ann)
        return render(request, 'announcement_create.html', {'form': form})


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
        announcement.status = 'published'
        announcement.save()
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
            ann.status = 'published' 
            ann.save()
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
    return render(request, 'favorites_list.html', {'favs': favs})

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
    query = request.GET.get('q', '').strip()
    ann_qs = Announcement.objects.none()
    cat_qs = Category.objects.none()
    if query:
        ann_qs = Announcement.objects.filter(
            Q(title__icontains=query) | Q(description__icontains=query),
            status='published'
        )
        cat_qs = Category.objects.filter(name__icontains=query)
    return render(request, 'search.html', {
        'query': query,
        'announcements': ann_qs,
        'categories': cat_qs
    })


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
    draft_count = announcements.filter(status='draft').count()
    archived_count = announcements.filter(status='archived').count()
    
    context = {
        'announcements': announcements,
        'approved_count': published_count,
        'pending_count': 0,  # У вас нет статуса "на модерации", оставляем 0
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

