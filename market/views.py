from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login as auth_login
from django.contrib.auth.models import User
from django.contrib import messages
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render

from .forms import ItemForm, TradeCreateForm, MessageForm, AdvancedSearchForm, SavedSearchForm
from .models import (Item, Trade, TradeStatus, Message, Favorite, ItemImage, UserPreference, 
                    UserInteraction, MatchRecommendation, Notification, UserOnlineStatus, LiveActivity,
                    SearchFilter, SearchHistory, PopularSearch, ItemPrice)
from .utils.email import notify_new_trade_offer, notify_trade_status_update, notify_new_message
from .utils.email import AuthEmailService
from .utils.smart_matching import smart_matching_engine
from .utils.notifications import NotificationService, LiveActivityService
from .utils.search_engine import search_engine
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
import json


def signup(request):
    if request.method == "POST":
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            auth_login(request, user)
            
            # Hoşgeldin emaili gönder
            try:
                AuthEmailService.send_welcome_email(user)
            except Exception as e:
                import logging
                logging.error(f"Welcome email failed for user {user.username}: {e}")
            
            return redirect("market:index")
    else:
        form = UserCreationForm()
    return render(request, "market/signup.html", {"form": form})


def index(request):
    # Mobil cihazlarda login olmuş kullanıcıları keşfet sayfasına yönlendir
    if request.user.is_authenticated:
        user_agent = request.META.get('HTTP_USER_AGENT', '')
        is_mobile = any(device in user_agent.lower() for device in ['mobile', 'android', 'iphone', 'ipad'])
        if is_mobile:
            return redirect('market:swipe_view')
    
    category = request.GET.get("cat")
    search_query = request.GET.get("q", "").strip()
    sort_by = request.GET.get("sort", "-created_at")
    
    items = Item.objects.all()
    if request.user.is_authenticated:
        items = items.exclude(owner=request.user)
    
    # Kategori filtresi
    if category:
        items = items.filter(category=category)
    
    # Arama filtresi
    if search_query:
        items = items.filter(
            Q(title__icontains=search_query) | 
            Q(description__icontains=search_query)
        )
    
    # Sıralama
    sort_options = {
        "-created_at": "En Yeni",
        "created_at": "En Eski", 
        "title": "Başlık (A-Z)",
        "-title": "Başlık (Z-A)"
    }
    
    if sort_by in sort_options:
        items = items.order_by(sort_by)
    else:
        items = items.order_by("-created_at")
    
    categories = Item._meta.get_field('category').choices
    
    # İstatistikler
    context = {
        "items": items, 
        "selected_category": category,
        "search_query": search_query,
        "sort_by": sort_by,
        "sort_options": sort_options,
        "categories": categories,
        "total_items": Item.objects.count(),
        "total_users": User.objects.count(),
        "total_trades": Trade.objects.filter(status=TradeStatus.ACCEPTED).count(),
    }
    return render(request, "market/item_list.html", context)


@login_required
def item_create(request):
    if request.method == "POST":
        form = ItemForm(request.POST, request.FILES)
        if form.is_valid():
            item = form.save(commit=False)
            item.owner = request.user
            item.save()
            
            # Çoklu fotoğraf işleme
            images_data = request.POST.get('images_data')
            if images_data:
                try:
                    images_list = json.loads(images_data)
                    for img_data in images_list:
                        # Frontend'den gelen image ID'leri ile ItemImage'ları item'a bağla
                        try:
                            item_image = ItemImage.objects.get(id=img_data.get('id'))
                            item_image.item = item
                            item_image.order = img_data.get('order', 0)
                            item_image.save()
                        except ItemImage.DoesNotExist:
                            continue
                except (json.JSONDecodeError, Exception) as e:
                    # Hata durumunda devam et, legacy image kullanılacak
                    pass
            
            # 🔔 Real-time: Create live activity
            LiveActivityService.track_item_created(item)
            
            messages.success(request, "Ürün başarıyla eklendi! 📸 Fotoğraflar yüklendi.")
            return redirect("market:item_detail", pk=item.pk)
    else:
        form = ItemForm()
    return render(request, "market/item_form.html", {"form": form})


@login_required
@require_http_methods(["POST"])
def upload_item_image(request):
    """AJAX ile çoklu fotoğraf yükleme"""
    try:
        if 'image' not in request.FILES:
            return JsonResponse({'error': 'Fotoğraf seçilmedi'}, status=400)
        
        image = request.FILES['image']
        alt_text = request.POST.get('alt_text', '')
        order = int(request.POST.get('order', 0))
        
        # Dosya validasyonu
        if image.size > 5 * 1024 * 1024:  # 5MB
            return JsonResponse({'error': 'Dosya çok büyük (Max: 5MB)'}, status=400)
        
        if not image.content_type.startswith('image/'):
            return JsonResponse({'error': 'Sadece resim dosyaları kabul edilir'}, status=400)
        
        # Geçici ItemImage oluştur (item olmadan)
        item_image = ItemImage.objects.create(
            item=None,  # Sonradan bağlanacak
            image=image,
            alt_text=alt_text,
            order=order
        )
        
        return JsonResponse({
            'success': True,
            'id': item_image.id,
            'url': item_image.image.url,
            'alt_text': item_image.alt_text,
            'order': item_image.order
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def smart_recommendations(request):
    """Kullanıcı için akıllı öneriler sayfası"""
    
    # Cached önerileri al
    recommendations = smart_matching_engine.get_cached_recommendations(request.user, limit=12)
    
    # Önerileri gösterildi olarak işaretle
    for rec in recommendations:
        smart_matching_engine.mark_recommendation_shown(rec.id)
    
    # Kullanıcı istatistiklerini al
    stats = smart_matching_engine.get_recommendation_stats(request.user)
    
    context = {
        'recommendations': recommendations,
        'stats': stats,
        'has_preferences': UserPreference.objects.filter(user=request.user).exists()
    }
    
    return render(request, 'market/smart_recommendations.html', context)


@login_required
@require_http_methods(["POST"])
def track_interaction(request):
    """AJAX ile kullanıcı etkileşimlerini takip et"""
    try:
        data = json.loads(request.body)
        item_id = data.get('item_id')
        interaction_type = data.get('interaction_type')
        response_time = data.get('response_time')
        session_duration = data.get('session_duration')
        
        if not item_id or not interaction_type:
            return JsonResponse({'error': 'Missing required parameters'}, status=400)
        
        item = get_object_or_404(Item, id=item_id)
        
        # Etkileşimi kaydet
        interaction = smart_matching_engine.update_user_interaction(
            user=request.user,
            item=item,
            interaction_type=interaction_type,
            response_time=response_time,
            session_duration=session_duration,
            request=request
        )
        
        if interaction:
            return JsonResponse({'success': True, 'interaction_id': interaction.id})
        else:
            return JsonResponse({'error': 'Failed to create interaction'}, status=500)
            
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@require_http_methods(["POST"])
def recommendation_clicked(request, recommendation_id):
    """Öneri tıklandığında çağrılan view"""
    try:
        rec = get_object_or_404(MatchRecommendation, id=recommendation_id, user=request.user)
        smart_matching_engine.mark_recommendation_clicked(recommendation_id)
        
        # İlgili ürün sayfasına yönlendir
        return redirect('market:item_detail', pk=rec.recommended_item.pk)
        
    except Exception as e:
        messages.error(request, 'Bir hata oluştu.')
        return redirect('market:smart_recommendations')


def item_detail(request, pk):
    item = get_object_or_404(Item, pk=pk)
    trade_form = None
    is_favorited = False
    
    # Görüntüleme etkileşimini kaydet
    if request.user.is_authenticated:
        smart_matching_engine.update_user_interaction(
            user=request.user,
            item=item,
            interaction_type='view',
            request=request
        )
    
    if request.user.is_authenticated:
        if request.user != item.owner:
            trade_form = TradeCreateForm(request.user)
        is_favorited = Favorite.objects.filter(user=request.user, item=item).exists()
    
    return render(request, "market/item_detail.html", {
        "item": item, 
        "trade_form": trade_form,
        "is_favorited": is_favorited
    })


@login_required
def trade_create(request, requested_item_id):
    requested_item = get_object_or_404(Item, pk=requested_item_id)
    if requested_item.owner == request.user:
        messages.error(request, "Kendi ürününe teklif veremezsin.")
        return redirect("market:item_detail", pk=requested_item_id)

    if request.method == "POST":
        form = TradeCreateForm(request.user, request.POST)
        if form.is_valid():
            offered_item = form.cleaned_data["offered_item"]
            # Yinelenen bekleyen teklifleri engelle
            existing = (
                Trade.objects.filter(
                    requester=request.user,
                    responder=requested_item.owner,
                    offered_item=offered_item,
                    requested_item=requested_item,
                    status=TradeStatus.PENDING,
                )
                .order_by("-created_at")
                .first()
            )
            if existing:
                messages.info(request, "Bu ürün için zaten beklemede bir teklifin var.")
                return redirect("market:trade_detail", pk=existing.pk)
            trade = Trade.objects.create(
                requester=request.user,
                responder=requested_item.owner,
                offered_item=offered_item,
                requested_item=requested_item,
            )
            
            # Email bildirimi gönder
            try:
                notify_new_trade_offer(trade)
            except Exception as e:
                # Email hatası trade'i etkilemesin
                import logging
                logging.error(f"Email notification failed for trade {trade.pk}: {e}")
            
            messages.success(request, "Takas teklifi gönderildi.")
            return redirect("market:trade_detail", pk=trade.pk)
    else:
        form = TradeCreateForm(request.user)
    return render(request, "market/trade_create.html", {"form": form, "requested_item": requested_item})


@login_required
def trade_list(request):
    trades = Trade.objects.filter(Q(requester=request.user) | Q(responder=request.user)).order_by("-created_at")
    return render(request, "market/trade_list.html", {"trades": trades})


@login_required
def trade_detail(request, pk):
    trade = get_object_or_404(Trade, pk=pk)
    if request.user not in [trade.requester, trade.responder]:
        messages.error(request, "Bu takasa erişim yetkin yok.")
        return redirect("market:index")

    if request.method == "POST":
        form = MessageForm(request.POST)
        if form.is_valid():
            message = Message.objects.create(trade=trade, sender=request.user, content=form.cleaned_data["content"])
            
            # Yeni mesaj email bildirimi gönder
            try:
                notify_new_message(message)
            except Exception as e:
                import logging
                logging.error(f"Email notification failed for new message {message.pk}: {e}")
            
            return redirect("market:trade_detail", pk=pk)
    else:
        form = MessageForm()

    return render(request, "market/trade_detail.html", {"trade": trade, "form": form})


@login_required
def trade_action(request, pk, action):
    trade = get_object_or_404(Trade, pk=pk)
    old_status = trade.status
    
    if action == "cancel" and trade.requester == request.user and trade.status == TradeStatus.PENDING:
        trade.status = TradeStatus.CANCELLED
        trade.save()
        messages.info(request, "Teklif iptal edildi.")
    elif action in ["accept", "reject"] and trade.responder == request.user and trade.status == TradeStatus.PENDING:
        trade.status = TradeStatus.ACCEPTED if action == "accept" else TradeStatus.REJECTED
        trade.save()
        
        # 🔔 Real-time: Send notification and track activity
        NotificationService.send_trade_response_notification(trade, action == "accept")
        if action == "accept":
            LiveActivityService.track_trade_completed(trade)
        
        messages.success(request, "Teklif güncellendi.")
        
        # Durum değişikliği email bildirimi gönder
        try:
            if old_status != trade.status:
                notify_trade_status_update(trade)
        except Exception as e:
            import logging
            logging.error(f"Email notification failed for trade status update {trade.pk}: {e}")
            
    else:
        messages.error(request, "Bu işlem için yetkin yok veya durum uygun değil.")
    return redirect("market:trade_detail", pk=pk)


def user_profile(request, username):
    user = get_object_or_404(User, username=username)
    user_items = Item.objects.filter(owner=user).order_by("-created_at")
    completed_trades = Trade.objects.filter(
        Q(requester=user) | Q(responder=user),
        status=TradeStatus.ACCEPTED
    ).count()
    
    context = {
        "profile_user": user,
        "user_items": user_items,
        "completed_trades": completed_trades,
        "total_items": user_items.count(),
    }
    return render(request, "market/user_profile.html", context)


@login_required
def my_items(request):
    items = Item.objects.filter(owner=request.user).order_by("-created_at")
    return render(request, "market/my_items.html", {"items": items})


@login_required
def toggle_favorite(request, item_id):
    item = get_object_or_404(Item, pk=item_id)
    if item.owner == request.user:
        messages.error(request, "Kendi ürününüzü favorilere ekleyemezsiniz.")
        return redirect("market:item_detail", pk=item_id)
    
    favorite, created = Favorite.objects.get_or_create(user=request.user, item=item)
    if not created:
        favorite.delete()
        messages.info(request, "Ürün favorilerden çıkarıldı.")
        # Unfavorite etkileşimini kaydet
        smart_matching_engine.update_user_interaction(
            user=request.user,
            item=item,
            interaction_type='unfavorite',
            request=request
        )
    else:
        messages.success(request, "Ürün favorilere eklendi.")
        # Favorite etkileşimini kaydet
        smart_matching_engine.update_user_interaction(
            user=request.user,
            item=item,
            interaction_type='favorite',
            request=request
        )
        
        # 🔔 Real-time: Send notification to item owner
        if item.owner != request.user:
            NotificationService.send_item_liked_notification(item, request.user)
            LiveActivityService.create_activity(
                user=request.user,
                activity_type='item_favorited',
                description=f"{request.user.first_name or request.user.username} bir ürünü beğendi",
                content_object=item
            )
    
    return redirect("market:item_detail", pk=item_id)


@login_required 
def favorites_list(request):
    favorites = Favorite.objects.filter(user=request.user).select_related('item')
    return render(request, "market/favorites_list.html", {"favorites": favorites})


@login_required
def swipe_view(request):
    """Tinder tarzı swipe interface"""
    # Kullanıcının kendisi hariç, henüz favorilere eklemediği ürünler
    user_favorites = Favorite.objects.filter(user=request.user).values_list('item_id', flat=True)
    
    items = Item.objects.exclude(owner=request.user).exclude(id__in=user_favorites).order_by('?')[:20]
    
    return render(request, "market/swipe_view.html", {"items": items})


@login_required
def swipe_action(request, item_id, action):
    """Swipe aksiyonları: like, skip, trade"""
    from django.http import JsonResponse
    
    item = get_object_or_404(Item, pk=item_id)
    
    if item.owner == request.user:
        return JsonResponse({"status": "error", "message": "Kendi ürününüz"})
    
    result = {"status": "success", "action": action}
    
    if action == "like":
        # Favorilere ekle
        favorite, created = Favorite.objects.get_or_create(user=request.user, item=item)
        result["message"] = "Favorilere eklendi" if created else "Zaten favorilerde"
    elif action == "trade":
        # Trade URL'ini döndür
        from django.urls import reverse
        result["redirect"] = reverse("market:trade_create", args=[item_id])
        result["message"] = "Takas sayfasına yönlendiriliyor"
    else:  # skip
        result["message"] = "Ürün geçildi"
    
    # AJAX request'ise JSON döndür
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse(result)
    
    # Normal request'ise redirect
    if action == "trade":
        return redirect("market:trade_create", requested_item_id=item_id)
    return redirect("market:swipe_view")


def manifest(request):
    """PWA manifest dosyası"""
    from django.http import JsonResponse
    
    manifest_data = {
        "name": "Swapzy - Güvenli Takas Platformu",
        "short_name": "Swapzy",
        "description": "Evinizde atıl duran eşyalarınızı güvenle takas edin",
        "start_url": "/",
        "display": "standalone",
        "background_color": "#667eea",
        "theme_color": "#667eea",
        "orientation": "portrait",
        "icons": [
            {
                "src": "data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='.9em' font-size='90'>🔄</text></svg>",
                "sizes": "192x192",
                "type": "image/svg+xml"
            },
            {
                "src": "data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='.9em' font-size='90'>🔄</text></svg>",
                "sizes": "512x512",
                "type": "image/svg+xml"
            }
        ]
    }
    
    response = JsonResponse(manifest_data)
    response['Content-Type'] = 'application/manifest+json'
    return response


# ==========================================
# 🔔 REAL-TIME NOTIFICATION VIEWS
# ==========================================

@login_required
def notifications_list(request):
    """Kullanıcının tüm bildirimlerini listele"""
    notifications = Notification.objects.filter(
        recipient=request.user
    ).order_by('-created_at')[:50]
    
    unread_count = Notification.objects.filter(
        recipient=request.user,
        is_read=False
    ).count()
    
    context = {
        'notifications': notifications,
        'unread_count': unread_count
    }
    
    return render(request, 'market/notifications.html', context)


@login_required
@require_http_methods(["POST"])
def mark_notification_read(request, notification_id):
    """Bildirimi okundu olarak işaretle"""
    try:
        notification = get_object_or_404(Notification, id=notification_id, recipient=request.user)
        notification.mark_as_read()
        
        return JsonResponse({
            'success': True,
            'message': 'Bildirim okundu olarak işaretlendi'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)


@login_required
@require_http_methods(["POST"])
def mark_all_notifications_read(request):
    """Tüm bildirimleri okundu olarak işaretle"""
    try:
        updated_count = NotificationService.mark_all_read(request.user)
        
        return JsonResponse({
            'success': True,
            'message': f'{updated_count} bildirim okundu olarak işaretlendi'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)


@login_required
def live_activity_feed(request):
    """Canlı aktivite feed'i"""
    activities = LiveActivity.objects.filter(
        is_public=True
    ).order_by('-created_at')[:100]
    
    context = {
        'activities': activities
    }
    
    return render(request, 'market/activity_feed.html', context)


@login_required
def online_users(request):
    """Online kullanıcıları göster"""
    online_users = UserOnlineStatus.objects.filter(
        is_online=True
    ).select_related('user')[:50]
    
    context = {
        'online_users': online_users,
        'total_online': online_users.count()
    }
    
    return render(request, 'market/online_users.html', context)


@login_required
@require_http_methods(["POST"])
def send_test_notification(request):
    """Test bildirimi gönder (sadece admin için)"""
    if not request.user.is_staff:
        return JsonResponse({
            'success': False,
            'error': 'Bu işlem için yetkiniz yok'
        }, status=403)
    
    try:
        data = json.loads(request.body)
        title = data.get('title', 'Test Bildirimi')
        message = data.get('message', 'Bu bir test bildirimidir.')
        
        NotificationService.create_notification(
            recipient=request.user,
            notification_type='system_update',
            title=title,
            message=message,
            sender=request.user
        )
        
        return JsonResponse({
            'success': True,
            'message': 'Test bildirimi gönderildi'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)


# ==========================================
# 🔍 ADVANCED SEARCH SYSTEM  
# ==========================================

def advanced_search(request):
    """Gelişmiş arama ana sayfası"""
    try:
        form = AdvancedSearchForm(request.GET or None)
        
        context = {
            'form': form,
            'saved_searches': [],
            'popular_searches': [],
            'search_performed': False,
            'show_results': False,
        }
        
        # Basic search functionality
        if request.GET.get('query'):
            query = request.GET.get('query', '').strip()
            items = Item.objects.filter(
                Q(title__icontains=query) |
                Q(description__icontains=query)
            )[:20]
            
            context.update({
                'search_performed': True,
                'show_results': True,
                'results': items,
                'total_count': items.count(),
                'search_time': 0.001,
                'suggestions': {},
                'filters_applied': [],
                'recommended_filters': {},
                'pagination': {'page': 1, 'pages': 1, 'has_next': False, 'has_previous': False}
            })
        
        return render(request, 'market/advanced_search.html', context)
        
    except Exception as e:
        # For debugging
        from django.http import HttpResponse
        import traceback
        return HttpResponse(f"Error: {str(e)}\n\nTraceback:\n{traceback.format_exc()}", content_type="text/plain")


@require_http_methods(["GET"])
def search_autocomplete(request):
    """AJAX autocomplete for search"""
    query = request.GET.get('q', '').strip()
    
    if len(query) < 2:
        return JsonResponse({'suggestions': []})
    
    try:
        suggestions = search_engine.get_autocomplete_suggestions(query, limit=10)
        return JsonResponse({'suggestions': suggestions})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@require_http_methods(["POST"])
def save_search(request):
    """Aramayı kaydet"""
    try:
        data = json.loads(request.body)
        
        search_params = data.get('search_params', {})
        name = data.get('name', '')
        
        if not name:
            return JsonResponse({
                'success': False,
                'error': 'Arama adı gerekli'
            }, status=400)
        
        # Create saved search
        search_filter = SearchFilter.objects.create(
            user=request.user,
            name=name,
            query=search_params.get('query', ''),
            categories=search_params.get('categories', []),
            conditions=search_params.get('conditions', []),
            price_range=search_params.get('price_range', ''),
            min_price=search_params.get('min_price'),
            max_price=search_params.get('max_price'),
            city=search_params.get('city', ''),
            district=search_params.get('district', ''),
            distance_range=search_params.get('distance_range', 'all'),
            has_image=search_params.get('has_image', False),
            trade_type=search_params.get('trade_type', ''),
            exclude_own_items=search_params.get('exclude_own_items', True),
            only_favorites=search_params.get('only_favorites', False),
            sort_by=search_params.get('sort_by', 'newest'),
            is_saved=True
        )
        
        return JsonResponse({
            'success': True,
            'message': 'Arama başarıyla kaydedildi',
            'search_id': search_filter.id
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


# ==========================================
# 📊 MONITORING DASHBOARD VIEWS  
# ==========================================

from django.contrib.admin.views.decorators import staff_member_required
from .utils.monitoring import system_monitor, error_tracker, performance_analyzer, health_checker
from .utils.performance import cache_manager, query_optimizer
from .utils.security import security_manager


@staff_member_required
def monitoring_dashboard(request):
    """Ana monitoring dashboard"""
    
    # Get basic system stats
    system_stats = system_monitor.get_system_stats()
    health_status = health_checker.run_health_checks()
    error_summary = error_tracker.get_error_summary()
    
    context = {
        'system_stats': system_stats,
        'health_status': health_status,
        'error_summary': error_summary,
        'page_title': 'System Monitoring Dashboard'
    }
    
    return render(request, 'admin/monitoring/dashboard.html', context)


@staff_member_required
@require_http_methods(["GET"])
def system_metrics_api(request):
    """System metrics API endpoint"""
    
    try:
        # Get current system stats
        system_stats = system_monitor.get_system_stats()
        database_stats = system_monitor.get_database_stats()
        django_stats = system_monitor.get_django_stats()
        
        # Store metrics for history
        metrics = {
            'system': system_stats,
            'database': database_stats,
            'django': django_stats
        }
        system_monitor.store_metrics(metrics)
        
        return JsonResponse({
            'success': True,
            'data': metrics,
            'timestamp': timezone.now().isoformat()
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@staff_member_required
@require_http_methods(["GET"])
def performance_metrics_api(request):
    """Performance metrics API endpoint"""
    
    try:
        performance_insights = performance_analyzer.get_performance_insights()
        cache_stats = cache_manager.get_cache_stats()
        query_stats = query_optimizer.get_query_stats()
        
        return JsonResponse({
            'success': True,
            'data': {
                'performance': performance_insights,
                'cache': cache_stats,
                'queries': query_stats
            }
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@staff_member_required
@require_http_methods(["GET"])
def security_metrics_api(request):
    """Security metrics API endpoint"""
    
    try:
        # Get security events from cache
        from django.core.cache import cache
        today = timezone.now().strftime('%Y%m%d')
        security_events = cache.get(f"security_events:{today}", [])
        
        # Analyze security events
        event_types = {}
        recent_events = []
        
        for event in security_events[-100:]:  # Last 100 events
            event_type = event.get('event_type', 'unknown')
            event_types[event_type] = event_types.get(event_type, 0) + 1
            
            # Include only recent events (last 24 hours)
            event_time = timezone.datetime.fromisoformat(event['timestamp'].replace('Z', '+00:00'))
            if (timezone.now() - event_time).total_seconds() < 86400:
                recent_events.append(event)
        
        return JsonResponse({
            'success': True,
            'data': {
                'event_summary': event_types,
                'recent_events': recent_events[-20:],  # Last 20 events
                'total_events_today': len(security_events)
            }
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@staff_member_required
@require_http_methods(["GET"])
def health_check_api(request):
    """Health check API endpoint"""
    
    try:
        health_status = health_checker.run_health_checks()
        return JsonResponse({
            'success': True,
            'data': health_status
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@staff_member_required
@require_http_methods(["GET"])
def metrics_history_api(request):
    """Metrics history API endpoint"""
    
    try:
        hours = int(request.GET.get('hours', 1))
        metrics_history = system_monitor.get_metrics_history(hours)
        
        return JsonResponse({
            'success': True,
            'data': {
                'metrics_history': metrics_history,
                'timespan_hours': hours
            }
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@staff_member_required
@require_http_methods(["POST"])
def clear_cache_api(request):
    """Clear cache API endpoint"""
    
    try:
        from django.core.cache import cache
        cache.clear()
        
        # Reset cache stats
        cache_manager.clear_all_stats()
        
        return JsonResponse({
            'success': True,
            'message': 'Cache cleared successfully'
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@staff_member_required
@require_http_methods(["POST"])
def reset_metrics_api(request):
    """Reset performance metrics API endpoint"""
    
    try:
        # Reset performance monitor
        from .utils.performance import performance_monitor
        performance_monitor.request_times = []
        performance_monitor.db_query_times = []
        
        # Reset query optimizer stats
        query_optimizer.reset_query_stats()
        
        # Reset cache stats
        cache_manager.clear_all_stats()
        
        return JsonResponse({
            'success': True,
            'message': 'Performance metrics reset successfully'
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@staff_member_required
@require_http_methods(["GET"])
def database_info_api(request):
    """Database information API endpoint"""
    
    try:
        from django.db import connection
        from django.apps import apps
        
        # Database connection info
        db_info = {
            'vendor': connection.vendor,
            'database_name': connection.settings_dict.get('NAME', ''),
            'host': connection.settings_dict.get('HOST', 'localhost'),
            'port': connection.settings_dict.get('PORT', ''),
        }
        
        # Model statistics
        model_stats = {}
        total_records = 0
        
        for model in apps.get_models():
            try:
                count = model.objects.count()
                model_name = f"{model._meta.app_label}.{model._meta.model_name}"
                model_stats[model_name] = count
                total_records += count
            except:
                pass
        
        # Recent query analysis
        recent_queries = connection.queries[-50:] if connection.queries else []
        slow_queries = [
            query for query in recent_queries 
            if float(query.get('time', 0)) > 0.1
        ]
        
        return JsonResponse({
            'success': True,
            'data': {
                'database_info': db_info,
                'model_stats': model_stats,
                'total_records': total_records,
                'recent_query_count': len(recent_queries),
                'slow_query_count': len(slow_queries)
            }
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@staff_member_required
def system_logs_view(request):
    """System logs view"""
    
    try:
        import os
        import glob
        from django.conf import settings
        
        # Try to find log files
        log_files = []
        possible_log_paths = [
            '/var/log/',
            settings.BASE_DIR / 'logs',
            '/tmp/',
        ]
        
        for log_path in possible_log_paths:
            if os.path.exists(log_path):
                log_files.extend(glob.glob(os.path.join(log_path, '*.log')))
        
        # Get recent log entries (simplified)
        recent_logs = []
        if log_files:
            try:
                with open(log_files[0], 'r') as f:
                    recent_logs = f.readlines()[-100:]  # Last 100 lines
            except:
                pass
        
        context = {
            'log_files': log_files,
            'recent_logs': recent_logs,
            'page_title': 'System Logs'
        }
        
        return render(request, 'admin/monitoring/logs.html', context)
        
    except Exception as e:
        context = {
            'error': str(e),
            'page_title': 'System Logs'
        }
        return render(request, 'admin/monitoring/logs.html', context)


def item_list(request):
    """Ürün listesi sayfası"""
    items = Item.objects.all().order_by('-created_at')
    
    # Pagination
    from django.core.paginator import Paginator
    paginator = Paginator(items, 12)  # 12 items per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'items': page_obj,
        'page_obj': page_obj,
        'page_title': 'Tüm Ürünler'
    }
    
    return render(request, 'market/item_list.html', context)


def quick_search(request):
    """Hızlı arama (header'daki search box için)"""
    query = request.GET.get('q', '').strip()
    
    if not query:
        return redirect('market:index')
    
    # Simple search - redirect to advanced search with query
    return redirect(f'/search/?query={query}')

