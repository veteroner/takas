from django.contrib import admin
from .models import (Item, Trade, Message, Favorite, ItemImage, UserPreference,
                    UserInteraction, MatchRecommendation, Notification, UserOnlineStatus, LiveActivity,
                    SearchFilter, SearchHistory, PopularSearch, ItemPrice)

class MessageInline(admin.TabularInline):
    model = Message
    extra = 0
    readonly_fields = ("created_at",)

@admin.register(Trade)
class TradeAdmin(admin.ModelAdmin):
    list_display = ("id", "offered_item", "requested_item", "requester", "responder", "status", "created_at")
    list_filter = ("status", "created_at")
    inlines = [MessageInline]

class ItemImageInline(admin.TabularInline):
    model = ItemImage
    extra = 1
    fields = ("image", "alt_text", "order")
    readonly_fields = ("uploaded_at",)

@admin.register(Item)
class ItemAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "owner", "category", "image_count", "created_at")
    list_filter = ("category", "created_at")
    inlines = [ItemImageInline]
    
    def image_count(self, obj):
        return f"{obj.image_count} fotoğraf"
    image_count.short_description = "Fotoğraf Sayısı"

@admin.register(ItemImage)
class ItemImageAdmin(admin.ModelAdmin):
    list_display = ("id", "item", "alt_text", "order", "uploaded_at")
    list_filter = ("uploaded_at",)
    search_fields = ("item__title", "alt_text")


@admin.register(Favorite)
class FavoriteAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "item", "created_at")
    list_filter = ("created_at",)
    search_fields = ("user__username", "item__title")


@admin.register(UserPreference)
class UserPreferenceAdmin(admin.ModelAdmin):
    list_display = ("user", "activity_score", "trade_success_rate", "avg_response_time", "updated_at")
    list_filter = ("activity_score", "trade_success_rate", "updated_at")
    search_fields = ("user__username",)
    readonly_fields = ("updated_at",)
    
    fieldsets = (
        ("Kullanıcı", {
            "fields": ("user",)
        }),
        ("Davranış Metrikleri", {
            "fields": ("activity_score", "trade_success_rate", "avg_response_time")
        }),
        ("Tercihler", {
            "fields": ("category_weights", "preferred_item_age_min", "preferred_item_age_max", "max_distance")
        }),
        ("Meta", {
            "fields": ("updated_at",)
        })
    )


@admin.register(UserInteraction)
class UserInteractionAdmin(admin.ModelAdmin):
    list_display = ("user", "item_title", "interaction_type", "response_time", "created_at")
    list_filter = ("interaction_type", "created_at", "item__category")
    search_fields = ("user__username", "item__title")
    readonly_fields = ("created_at",)
    date_hierarchy = "created_at"
    
    def item_title(self, obj):
        return obj.item.title[:30]
    item_title.short_description = "Ürün"
    
    fieldsets = (
        ("Temel Bilgiler", {
            "fields": ("user", "item", "interaction_type")
        }),
        ("Metrikler", {
            "fields": ("response_time", "session_duration")
        }),
        ("Meta Data", {
            "fields": ("created_at", "ip_address", "user_agent")
        })
    )


@admin.register(MatchRecommendation)
class MatchRecommendationAdmin(admin.ModelAdmin):
    list_display = ("user", "recommended_item_title", "match_score", "recommendation_type", 
                   "confidence_level", "is_shown", "is_clicked", "is_converted", "created_at")
    list_filter = ("recommendation_type", "is_shown", "is_clicked", "is_converted", 
                  "created_at", "confidence_level")
    search_fields = ("user__username", "recommended_item__title")
    readonly_fields = ("created_at", "shown_at", "clicked_at")
    date_hierarchy = "created_at"
    
    def recommended_item_title(self, obj):
        return obj.recommended_item.title[:30]
    recommended_item_title.short_description = "Önerilen Ürün"
    
    fieldsets = (
        ("Temel Bilgiler", {
            "fields": ("user", "recommended_item", "user_item")
        }),
        ("AI Skorlaması", {
            "fields": ("match_score", "confidence_level", "recommendation_type", "reasoning")
        }),
        ("Durum Takibi", {
            "fields": ("is_shown", "is_clicked", "is_converted", "shown_at", "clicked_at")
        }),
        ("Meta", {
            "fields": ("created_at",)
        })
    )
    
    actions = ["mark_as_shown", "regenerate_recommendations"]
    
    def mark_as_shown(self, request, queryset):
        updated = queryset.update(is_shown=True)
        self.message_user(request, f"{updated} öneri gösterildi olarak işaretlendi.")
    mark_as_shown.short_description = "Seçili önerileri gösterildi olarak işaretle"
    
    def regenerate_recommendations(self, request, queryset):
        from .utils.smart_matching import smart_matching_engine
        users = queryset.values_list('user', flat=True).distinct()
        total_generated = 0
        
        for user_id in users:
            from django.contrib.auth.models import User
            user = User.objects.get(id=user_id)
            new_recs = smart_matching_engine.generate_recommendations_for_user(user, 10)
            total_generated += len(new_recs)
        
        self.message_user(request, f"{total_generated} yeni öneri oluşturuldu.")
    regenerate_recommendations.short_description = "Seçili kullanıcılar için yeni öneriler oluştur"


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("recipient", "notification_type", "title", "is_read", "is_sent", "created_at")
    list_filter = ("notification_type", "is_read", "is_sent", "created_at")
    search_fields = ("recipient__username", "title", "message")
    readonly_fields = ("created_at", "read_at")
    date_hierarchy = "created_at"
    
    fieldsets = (
        ("Temel Bilgiler", {
            "fields": ("recipient", "sender", "notification_type")
        }),
        ("İçerik", {
            "fields": ("title", "message", "action_url", "extra_data")
        }),
        ("Durum", {
            "fields": ("is_read", "is_sent", "is_push_sent", "read_at")
        }),
        ("Meta", {
            "fields": ("created_at", "content_type", "object_id")
        })
    )
    
    actions = ["mark_as_read", "mark_as_sent", "send_test_notification"]
    
    def mark_as_read(self, request, queryset):
        updated = queryset.update(is_read=True)
        self.message_user(request, f"{updated} bildirim okundu olarak işaretlendi.")
    mark_as_read.short_description = "Seçili bildirimleri okundu olarak işaretle"
    
    def mark_as_sent(self, request, queryset):
        updated = queryset.update(is_sent=True)
        self.message_user(request, f"{updated} bildirim gönderildi olarak işaretlendi.")
    mark_as_sent.short_description = "Seçili bildirimleri gönderildi olarak işaretle"


@admin.register(UserOnlineStatus)
class UserOnlineStatusAdmin(admin.ModelAdmin):
    list_display = ("user", "is_online", "last_seen", "channel_name")
    list_filter = ("is_online", "last_seen")
    search_fields = ("user__username",)
    readonly_fields = ("last_seen",)
    
    fieldsets = (
        ("Kullanıcı", {
            "fields": ("user",)
        }),
        ("Durum", {
            "fields": ("is_online", "last_seen")
        }),
        ("Bağlantı Bilgileri", {
            "fields": ("channel_name", "user_agent", "ip_address")
        })
    )
    
    actions = ["set_offline", "cleanup_inactive"]
    
    def set_offline(self, request, queryset):
        updated = queryset.update(is_online=False)
        self.message_user(request, f"{updated} kullanıcı offline olarak işaretlendi.")
    set_offline.short_description = "Seçili kullanıcıları offline yap"
    
    def cleanup_inactive(self, request, queryset):
        from django.utils import timezone
        cutoff = timezone.now() - timezone.timedelta(hours=24)
        deleted = queryset.filter(last_seen__lt=cutoff, is_online=False).delete()[0]
        self.message_user(request, f"{deleted} eski kayıt temizlendi.")
    cleanup_inactive.short_description = "24 saattir offline olan kayıtları temizle"


@admin.register(LiveActivity)
class LiveActivityAdmin(admin.ModelAdmin):
    list_display = ("user", "activity_type", "description", "is_public", "created_at")
    list_filter = ("activity_type", "is_public", "created_at")
    search_fields = ("user__username", "description")
    readonly_fields = ("created_at",)
    date_hierarchy = "created_at"
    
    fieldsets = (
        ("Temel Bilgiler", {
            "fields": ("user", "activity_type", "description")
        }),
        ("Ayarlar", {
            "fields": ("is_public", "extra_data")
        }),
        ("Meta", {
            "fields": ("created_at", "content_type", "object_id")
        })
    )
    
    actions = ["make_public", "make_private", "cleanup_old"]
    
    def make_public(self, request, queryset):
        updated = queryset.update(is_public=True)
        self.message_user(request, f"{updated} aktivite herkese açık yapıldı.")
    make_public.short_description = "Seçili aktiviteleri herkese açık yap"
    
    def make_private(self, request, queryset):
        updated = queryset.update(is_public=False)
        self.message_user(request, f"{updated} aktivite gizli yapıldı.")
    make_private.short_description = "Seçili aktiviteleri gizli yap"
    
    def cleanup_old(self, request, queryset):
        from django.utils import timezone
        cutoff = timezone.now() - timezone.timedelta(days=30)
        deleted = queryset.filter(created_at__lt=cutoff).delete()[0]
        self.message_user(request, f"{deleted} eski aktivite temizlendi.")
    cleanup_old.short_description = "30 günden eski aktiviteleri temizle"


@admin.register(SearchFilter)
class SearchFilterAdmin(admin.ModelAdmin):
    list_display = ("name", "user", "query", "is_saved", "is_default", "usage_count", "last_used")
    list_filter = ("is_saved", "is_default", "created_at", "last_used")
    search_fields = ("name", "user__username", "query")
    readonly_fields = ("usage_count", "last_used", "created_at")
    
    fieldsets = (
        ("Temel Bilgiler", {
            "fields": ("user", "name", "query")
        }),
        ("Filtreler", {
            "fields": ("categories", "conditions", "price_range", "min_price", "max_price"),
            "classes": ("collapse",)
        }),
        ("Konum", {
            "fields": ("city", "district", "distance_range"),
            "classes": ("collapse",)
        }),
        ("Gelişmiş", {
            "fields": ("has_image", "trade_type", "exclude_own_items", "only_favorites", "sort_by"),
            "classes": ("collapse",)
        }),
        ("Meta", {
            "fields": ("is_saved", "is_default", "usage_count", "last_used", "created_at"),
            "classes": ("collapse",)
        })
    )


@admin.register(SearchHistory)
class SearchHistoryAdmin(admin.ModelAdmin):
    list_display = ("user", "query", "results_count", "created_at")
    list_filter = ("created_at", "results_count")
    search_fields = ("user__username", "query")
    readonly_fields = ("created_at",)
    date_hierarchy = "created_at"


@admin.register(PopularSearch)
class PopularSearchAdmin(admin.ModelAdmin):
    list_display = ("query", "search_count", "daily_count", "weekly_count", "monthly_count", "last_searched")
    list_filter = ("last_searched",)
    search_fields = ("query",)
    readonly_fields = ("last_searched",)
    ordering = ("-search_count",)


@admin.register(ItemPrice)
class ItemPriceAdmin(admin.ModelAdmin):
    list_display = ("item", "estimated_price", "price_confidence", "market_demand", "updated_at")
    list_filter = ("market_demand", "price_confidence", "updated_at")
    search_fields = ("item__title",)
    readonly_fields = ("updated_at",)

