from django.conf import settings
from django.db import models
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
from django.utils import timezone

class Category(models.TextChoices):
    EVENING_DRESS = "evening_dress", "Abiye"
    GAME_CONSOLE = "game_console", "Oyun Konsolu"
    GAME_DISC = "game_disc", "Oyun CD/DVD"
    TOY = "toy", "Oyuncak"
    BOOK = "book", "Kitap"
    KIDS_OTHER = "kids_other", "Diğer Çocuk Ürünleri"

class Item(models.Model):
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="items")
    title = models.CharField(max_length=120)
    description = models.TextField(blank=True)
    category = models.CharField(max_length=32, choices=Category.choices)
    image = models.ImageField(upload_to="items/", blank=True, null=True)  # Primary image (backward compatibility)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title} - {self.owner}"
    
    @property
    def primary_image(self):
        """Ana görsel - ilk yüklenen veya legacy image"""
        first_image = self.images.first()
        return first_image.image if first_image else self.image
    
    @property
    def all_images(self):
        """Tüm görseller - yeni sistem + legacy"""
        images = list(self.images.all())
        if self.image and not images:
            # Legacy image varsa ve yeni system boşsa, mock object oluştur
            return [type('MockImage', (), {'image': self.image, 'alt_text': self.title, 'order': 0})()]
        return images
    
    @property 
    def image_count(self):
        """Toplam görsel sayısı"""
        count = self.images.count()
        return count if count > 0 else (1 if self.image else 0)


class ItemImage(models.Model):
    """Ürün için çoklu fotoğraf sistemi"""
    item = models.ForeignKey(Item, on_delete=models.CASCADE, related_name='images', null=True, blank=True)
    image = models.ImageField(upload_to='items/gallery/')
    alt_text = models.CharField(max_length=200, blank=True, help_text="Görsel açıklaması (SEO için)")
    order = models.PositiveIntegerField(default=0, help_text="Gösterim sırası")
    uploaded_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['order', 'uploaded_at']
        verbose_name = "Ürün Görseli"
        verbose_name_plural = "Ürün Görselleri"
    
    def __str__(self):
        return f"{self.item.title} - Görsel {self.order + 1}"
    
    def save(self, *args, **kwargs):
        # Eğer order belirtilmemişse, en sona ekle
        if self.order == 0:
            from django.db.models import Max
            max_order = ItemImage.objects.filter(item=self.item).aggregate(
                Max('order')
            )['order__max']
            self.order = (max_order or 0) + 1
        super().save(*args, **kwargs)

class TradeStatus(models.TextChoices):
    PENDING = "pending", "Beklemede"
    ACCEPTED = "accepted", "Kabul Edildi"
    REJECTED = "rejected", "Reddedildi"
    CANCELLED = "cancelled", "İptal"

class Trade(models.Model):
    requester = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="trades_requested")
    responder = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="trades_received")
    offered_item = models.ForeignKey(Item, on_delete=models.CASCADE, related_name="offers_made")
    requested_item = models.ForeignKey(Item, on_delete=models.CASCADE, related_name="offers_received")
    status = models.CharField(max_length=16, choices=TradeStatus.choices, default=TradeStatus.PENDING)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                check=~models.Q(requester=models.F("responder")),
                name="trade_requester_not_responder",
            ),
            models.CheckConstraint(
                check=~models.Q(offered_item=models.F("requested_item")),
                name="trade_offered_not_requested",
            ),
            # Aynı eşleşme için birden fazla bekleyen teklif olmasın
            models.UniqueConstraint(
                fields=["requester", "responder", "offered_item", "requested_item", "status"],
                condition=models.Q(status="pending"),
                name="uniq_pending_trade_per_pair",
            ),
        ]

class Message(models.Model):
    trade = models.ForeignKey(Trade, on_delete=models.CASCADE, related_name="messages")
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]


class Favorite(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="favorites")
    item = models.ForeignKey(Item, on_delete=models.CASCADE, related_name="favorited_by")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ["user", "item"]
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user.username} -> {self.item.title}"


class UserPreference(models.Model):
    """Kullanıcı tercih profili - AI için"""
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='preferences')
    
    # Kategori tercihleri (JSON field ile kategorilerin weight'lerini tutalım)
    category_weights = models.JSONField(default=dict, help_text="Kategori ağırlıkları {kategori: weight}")
    
    # Davranış metrikleri
    avg_response_time = models.FloatField(default=24.0, help_text="Ortalama yanıt süresi (saat)")
    trade_success_rate = models.FloatField(default=0.0, help_text="Takas başarı oranı (0-1)")
    activity_score = models.FloatField(default=0.0, help_text="Aktivite skoru (0-100)")
    
    # Tercih edilen takaslar
    preferred_item_age_min = models.IntegerField(default=0, help_text="Minimum ürün yaşı (gün)")
    preferred_item_age_max = models.IntegerField(default=365, help_text="Maksimum ürün yaşı (gün)")
    
    # Coğrafi tercihler (gelecekte kullanılabilir)
    max_distance = models.IntegerField(default=50, help_text="Maksimum mesafe (km)")
    
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Kullanıcı Tercihi"
        verbose_name_plural = "Kullanıcı Tercihleri"
    
    def __str__(self):
        return f"{self.user.username} - Tercihleri"


class UserInteraction(models.Model):
    """Kullanıcı etkileşimleri - ML için veri"""
    
    INTERACTION_TYPES = [
        ('view', 'Görüntüleme'),
        ('favorite', 'Favorileme'),
        ('unfavorite', 'Favoriden Çıkarma'),
        ('trade_request', 'Takas Teklifi'),
        ('trade_accept', 'Takas Kabul'),
        ('trade_reject', 'Takas Red'),
        ('swipe_right', 'Sağa Kaydırma (Beğeni)'),
        ('swipe_left', 'Sola Kaydırma (Beğenmeme)'),
        ('message_send', 'Mesaj Gönderme'),
    ]
    
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='interactions')
    item = models.ForeignKey(Item, on_delete=models.CASCADE, related_name='interactions')
    interaction_type = models.CharField(max_length=20, choices=INTERACTION_TYPES)
    
    # Detay bilgiler
    response_time = models.FloatField(null=True, blank=True, help_text="Yanıt süresi (saniye)")
    session_duration = models.FloatField(null=True, blank=True, help_text="Oturum süresi (saniye)")
    
    # Meta data
    created_at = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    
    class Meta:
        verbose_name = "Kullanıcı Etkileşimi"
        verbose_name_plural = "Kullanıcı Etkileşimleri"
        indexes = [
            models.Index(fields=['user', 'created_at']),
            models.Index(fields=['item', 'interaction_type']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.get_interaction_type_display()} - {self.item.title[:30]}"


class MatchRecommendation(models.Model):
    """AI tabanlı takas önerileri"""
    
    RECOMMENDATION_TYPES = [
        ('perfect_match', 'Mükemmel Eşleşme'),
        ('high_potential', 'Yüksek Potansiyel'),
        ('category_match', 'Kategori Eşleşmesi'),
        ('user_behavior', 'Davranış Bazlı'),
        ('trending', 'Trend Bazlı'),
    ]
    
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='recommendations')
    recommended_item = models.ForeignKey(Item, on_delete=models.CASCADE, related_name='recommendations')
    user_item = models.ForeignKey(Item, on_delete=models.CASCADE, related_name='potential_trades', 
                                  null=True, blank=True, help_text="Kullanıcının karşılık verebileceği ürün")
    
    # Skorlama
    match_score = models.FloatField(help_text="Eşleşme skoru (0-100)")
    recommendation_type = models.CharField(max_length=20, choices=RECOMMENDATION_TYPES)
    
    # AI özellikleri
    confidence_level = models.FloatField(help_text="Güven seviyesi (0-1)")
    reasoning = models.JSONField(default=dict, help_text="Öneri gerekçeleri")
    
    # Durum takibi
    is_shown = models.BooleanField(default=False)
    is_clicked = models.BooleanField(default=False)
    is_converted = models.BooleanField(default=False, help_text="Takasa dönüştü mü?")
    
    created_at = models.DateTimeField(auto_now_add=True)
    shown_at = models.DateTimeField(null=True, blank=True)
    clicked_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        verbose_name = "Takas Önerisi"
        verbose_name_plural = "Takas Önerileri"
        ordering = ['-match_score', '-created_at']
        indexes = [
            models.Index(fields=['user', 'is_shown']),
            models.Index(fields=['match_score']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"{self.user.username} → {self.recommended_item.title[:30]} ({self.match_score:.1f}%)"


class NotificationType(models.TextChoices):
    """Bildirim türleri"""
    TRADE_REQUEST = "trade_request", "Takas Teklifi"
    TRADE_ACCEPTED = "trade_accepted", "Takas Kabul Edildi"
    TRADE_REJECTED = "trade_rejected", "Takas Reddedildi"
    NEW_MESSAGE = "new_message", "Yeni Mesaj"
    ITEM_LIKED = "item_liked", "Ürününüz Beğenildi"
    NEW_RECOMMENDATION = "new_recommendation", "Yeni Öneri"
    SYSTEM_UPDATE = "system_update", "Sistem Güncellemesi"
    TRADE_REMINDER = "trade_reminder", "Takas Hatırlatması"
    PROFILE_VIEW = "profile_view", "Profil Görüntülendi"


class Notification(models.Model):
    """Gerçek zamanlı bildirim sistemi"""
    
    recipient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notifications')
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='sent_notifications', null=True, blank=True)
    
    # Bildirim içeriği
    notification_type = models.CharField(max_length=20, choices=NotificationType.choices)
    title = models.CharField(max_length=200)
    message = models.TextField()
    
    # İlgili objeler (generic foreign key)
    content_type = models.ForeignKey('contenttypes.ContentType', on_delete=models.CASCADE, null=True, blank=True)
    object_id = models.PositiveIntegerField(null=True, blank=True)
    content_object = GenericForeignKey('content_type', 'object_id')
    
    # Durum ve meta data
    is_read = models.BooleanField(default=False)
    is_sent = models.BooleanField(default=False)  # WebSocket ile gönderildi mi?
    is_push_sent = models.BooleanField(default=False)  # Push notification gönderildi mi?
    
    # Özel data (JSON field)
    extra_data = models.JSONField(default=dict, blank=True)
    
    # URL yönlendirme
    action_url = models.URLField(blank=True, help_text="Tıklandığında gidilecek URL")
    
    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['recipient', 'is_read']),
            models.Index(fields=['created_at']),
            models.Index(fields=['notification_type']),
        ]
        verbose_name = "Bildirim"
        verbose_name_plural = "Bildirimler"
    
    def __str__(self):
        return f"{self.recipient.username} - {self.title}"
    
    def mark_as_read(self):
        """Bildirimi okundu olarak işaretle"""
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save()
    
    @property
    def time_since_created(self):
        """Bildirim oluşturulmasından bu yana geçen süre"""
        from django.utils import timezone
        diff = timezone.now() - self.created_at
        
        if diff.days > 0:
            return f"{diff.days} gün önce"
        elif diff.seconds > 3600:
            return f"{diff.seconds // 3600} saat önce"
        elif diff.seconds > 60:
            return f"{diff.seconds // 60} dakika önce"
        else:
            return "Az önce"


class UserOnlineStatus(models.Model):
    """Kullanıcı online durumu takibi"""
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='online_status')
    is_online = models.BooleanField(default=False)
    last_seen = models.DateTimeField(auto_now=True)
    
    # WebSocket connection info
    channel_name = models.CharField(max_length=200, blank=True)
    user_agent = models.TextField(blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    
    class Meta:
        verbose_name = "Kullanıcı Online Durumu"
        verbose_name_plural = "Kullanıcı Online Durumları"
    
    def __str__(self):
        status = "🟢 Online" if self.is_online else "🔴 Offline"
        return f"{self.user.username} - {status}"
    
    @property
    def time_since_last_seen(self):
        """Son görülmeden bu yana geçen süre"""
        from django.utils import timezone
        if self.is_online:
            return "Şu anda online"
        
        diff = timezone.now() - self.last_seen
        if diff.days > 0:
            return f"{diff.days} gün önce görüldü"
        elif diff.seconds > 3600:
            return f"{diff.seconds // 3600} saat önce görüldü"
        elif diff.seconds > 60:
            return f"{diff.seconds // 60} dakika önce görüldü"
        else:
            return "Az önce görüldü"


class LiveActivity(models.Model):
    """Canlı aktivite feed sistemi"""
    
    ACTIVITY_TYPES = [
        ('item_created', '🆕 Yeni Ürün'),
        ('trade_created', '🔄 Yeni Takas'),
        ('trade_completed', '✅ Takas Tamamlandı'),
        ('user_joined', '👋 Yeni Üye'),
        ('item_favorited', '❤️ Ürün Beğenildi'),
        ('recommendation_clicked', '🎯 Öneri Tıklandı'),
        ('user_online', '🟢 Kullanıcı Online'),
    ]
    
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='activities')
    activity_type = models.CharField(max_length=30, choices=ACTIVITY_TYPES)
    description = models.CharField(max_length=300)
    
    # İlgili objeler
    content_type = models.ForeignKey('contenttypes.ContentType', on_delete=models.CASCADE, null=True, blank=True)
    object_id = models.PositiveIntegerField(null=True, blank=True)
    content_object = GenericForeignKey('content_type', 'object_id')
    
    # Metadata
    extra_data = models.JSONField(default=dict, blank=True)
    is_public = models.BooleanField(default=True)  # Herkese gösterilsin mi?
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['created_at']),
            models.Index(fields=['activity_type']),
            models.Index(fields=['is_public']),
        ]
        verbose_name = "Canlı Aktivite"
        verbose_name_plural = "Canlı Aktiviteler"
    
    def __str__(self):
        return f"{self.user.username} - {self.get_activity_type_display()}"


class SearchFilter(models.Model):
    """Gelişmiş arama filtreleri"""
    
    PRICE_RANGES = [
        ('0-50', '0-50 TL'),
        ('50-100', '50-100 TL'), 
        ('100-250', '100-250 TL'),
        ('250-500', '250-500 TL'),
        ('500-1000', '500-1000 TL'),
        ('1000+', '1000+ TL'),
    ]
    
    DISTANCE_RANGES = [
        ('5', '5 km içinde'),
        ('10', '10 km içinde'),
        ('25', '25 km içinde'),
        ('50', '50 km içinde'),
        ('100', '100 km içinde'),
        ('all', 'Tüm Türkiye'),
    ]
    
    SORT_OPTIONS = [
        ('newest', 'En Yeni'),
        ('oldest', 'En Eski'),
        ('name_asc', 'A-Z'),
        ('name_desc', 'Z-A'),
        ('price_asc', 'Ucuzdan Pahalıya'),
        ('price_desc', 'Pahalıdan Ucuza'),
        ('distance', 'Yakından Uzağa'),
        ('popularity', 'En Popüler'),
        ('match_score', 'En Uygun'),
    ]
    
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='search_filters')
    name = models.CharField(max_length=100, help_text="Filtre adı")
    
    # Temel filtreler
    query = models.CharField(max_length=255, blank=True, help_text="Arama kelimesi")
    categories = models.JSONField(default=list, help_text="Seçili kategoriler")
    conditions = models.JSONField(default=list, help_text="Ürün durumları")
    
    # Fiyat filtreleri
    price_range = models.CharField(max_length=20, choices=PRICE_RANGES, blank=True)
    min_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    max_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    
    # Konum filtreleri
    city = models.CharField(max_length=100, blank=True)
    district = models.CharField(max_length=100, blank=True)
    distance_range = models.CharField(max_length=10, choices=DISTANCE_RANGES, default='all')
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    
    # Tarih filtreleri
    date_from = models.DateField(null=True, blank=True)
    date_to = models.DateField(null=True, blank=True)
    
    # Gelişmiş filtreler
    has_image = models.BooleanField(default=False)
    trade_type = models.CharField(max_length=50, blank=True, help_text="Takas türü tercihi")
    exclude_own_items = models.BooleanField(default=True)
    only_favorites = models.BooleanField(default=False)
    
    # Sıralama
    sort_by = models.CharField(max_length=20, choices=SORT_OPTIONS, default='newest')
    
    # Meta
    is_saved = models.BooleanField(default=False, help_text="Kaydedilmiş arama mı?")
    is_default = models.BooleanField(default=False, help_text="Varsayılan filtre mi?")
    usage_count = models.PositiveIntegerField(default=0)
    last_used = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-last_used']
        verbose_name = "Arama Filtresi"
        verbose_name_plural = "Arama Filtreleri"
    
    def __str__(self):
        return f"{self.user.username} - {self.name}"
    
    def to_dict(self):
        """Filtre verilerini dictionary olarak döndür"""
        return {
            'query': self.query,
            'categories': self.categories,
            'conditions': self.conditions,
            'price_range': self.price_range,
            'min_price': float(self.min_price) if self.min_price else None,
            'max_price': float(self.max_price) if self.max_price else None,
            'city': self.city,
            'district': self.district,
            'distance_range': self.distance_range,
            'latitude': self.latitude,
            'longitude': self.longitude,
            'date_from': self.date_from.isoformat() if self.date_from else None,
            'date_to': self.date_to.isoformat() if self.date_to else None,
            'has_image': self.has_image,
            'trade_type': self.trade_type,
            'exclude_own_items': self.exclude_own_items,
            'only_favorites': self.only_favorites,
            'sort_by': self.sort_by,
        }


class SearchHistory(models.Model):
    """Arama geçmişi"""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='search_history')
    query = models.CharField(max_length=255)
    filters = models.JSONField(default=dict, help_text="Kullanılan filtreler")
    results_count = models.PositiveIntegerField(default=0)
    clicked_items = models.JSONField(default=list, help_text="Tıklanan ürün ID'leri")
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = "Arama Geçmişi"
        verbose_name_plural = "Arama Geçmişleri"
    
    def __str__(self):
        return f"{self.user.username} - {self.query} ({self.results_count} sonuç)"


class PopularSearch(models.Model):
    """Popüler aramalar ve trendler"""
    query = models.CharField(max_length=255, unique=True)
    search_count = models.PositiveIntegerField(default=1)
    last_searched = models.DateTimeField(auto_now=True)
    
    # Trend analizi
    daily_count = models.PositiveIntegerField(default=0)
    weekly_count = models.PositiveIntegerField(default=0)
    monthly_count = models.PositiveIntegerField(default=0)
    
    # Kategorik analiz
    related_categories = models.JSONField(default=list)
    related_cities = models.JSONField(default=list)
    
    class Meta:
        ordering = ['-search_count', '-last_searched']
        verbose_name = "Popüler Arama"
        verbose_name_plural = "Popüler Aramalar"
    
    def __str__(self):
        return f"{self.query} ({self.search_count} kez)"


class ItemPrice(models.Model):
    """Ürün fiyat geçmişi ve değer tahmini"""
    item = models.OneToOneField(Item, on_delete=models.CASCADE, related_name='price_info')
    estimated_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    price_confidence = models.FloatField(default=0.0, help_text="Fiyat tahmini güven skoru (0-1)")
    
    # Pazar analizi
    similar_items_avg = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    market_demand = models.CharField(max_length=20, choices=[
        ('low', 'Düşük'),
        ('medium', 'Orta'),
        ('high', 'Yüksek'),
        ('very_high', 'Çok Yüksek'),
    ], default='medium')
    
    # Fiyat faktörleri
    condition_factor = models.FloatField(default=1.0)
    age_factor = models.FloatField(default=1.0)
    location_factor = models.FloatField(default=1.0)
    demand_factor = models.FloatField(default=1.0)
    
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Ürün Fiyat Bilgisi"
        verbose_name_plural = "Ürün Fiyat Bilgileri"
    
    def __str__(self):
        return f"{self.item.title} - {self.estimated_price} TL"
    
    def calculate_price_estimate(self):
        """Fiyat tahmini hesapla"""
        # Basit algoritma - daha gelişmiş ML modeli kullanılabilir
        base_price = 100  # Varsayılan fiyat
        
        # Faktörleri uygula
        estimated = (base_price * 
                    self.condition_factor * 
                    self.age_factor * 
                    self.location_factor * 
                    self.demand_factor)
        
        self.estimated_price = round(estimated, 2)
        self.save()
        return self.estimated_price

