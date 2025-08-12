from django.urls import path, include
from . import views

app_name = "market"

urlpatterns = [
    path("", views.index, name="index"),
    path("items/new/", views.item_create, name="item_create"),
    path("items/<int:pk>/", views.item_detail, name="item_detail"),
    path("trade/create/<int:requested_item_id>/", views.trade_create, name="trade_create"),
    path("trades/", views.trade_list, name="trade_list"),
    path("trade/<int:pk>/", views.trade_detail, name="trade_detail"),
    path("trade/<int:pk>/<str:action>/", views.trade_action, name="trade_action"),
    path("signup/", views.signup, name="signup"),
    path("profile/<str:username>/", views.user_profile, name="user_profile"),
    path("my-items/", views.my_items, name="my_items"),
    path("favorites/", views.favorites_list, name="favorites_list"),
    path("favorite/toggle/<int:item_id>/", views.toggle_favorite, name="toggle_favorite"),
    path("swipe/", views.swipe_view, name="swipe_view"),
    path("swipe/action/<int:item_id>/<str:action>/", views.swipe_action, name="swipe_action"),
    path("manifest.json", views.manifest, name="manifest"),
    # Multi-photo API
    path("api/upload-item-image/", views.upload_item_image, name="upload_item_image"),
    # Smart Matching API
    path("recommendations/", views.smart_recommendations, name="smart_recommendations"),
    path("api/track-interaction/", views.track_interaction, name="track_interaction"),
    path("api/recommendation-clicked/<int:recommendation_id>/", views.recommendation_clicked, name="recommendation_clicked"),
    
    # Real-time Notification API
    path("notifications/", views.notifications_list, name="notifications_list"),
    path("api/notification/read/<int:notification_id>/", views.mark_notification_read, name="mark_notification_read"),
    path("api/notifications/read-all/", views.mark_all_notifications_read, name="mark_all_notifications_read"),
    path("activity-feed/", views.live_activity_feed, name="live_activity_feed"),
    path("online-users/", views.online_users, name="online_users"),
    path("api/test-notification/", views.send_test_notification, name="send_test_notification"),
    
    # Advanced Search System
    path("search/", views.advanced_search, name="advanced_search"),
    path("api/search/autocomplete/", views.search_autocomplete, name="search_autocomplete"),
    path("api/search/save/", views.save_search, name="save_search"),
    path("quick-search/", views.quick_search, name="quick_search"),
    path("items/", views.item_list, name="item_list"),
    
    # Monitoring Dashboard URLs (Admin only)
    path("admin/monitoring/", include([
        path("dashboard/", views.monitoring_dashboard, name="monitoring_dashboard"),
        path("api/system-metrics/", views.system_metrics_api, name="system_metrics_api"),
        path("api/performance-metrics/", views.performance_metrics_api, name="performance_metrics_api"),
        path("api/security-metrics/", views.security_metrics_api, name="security_metrics_api"),
        path("api/health-check/", views.health_check_api, name="health_check_api"),
        path("api/metrics-history/", views.metrics_history_api, name="metrics_history_api"),
        path("api/clear-cache/", views.clear_cache_api, name="clear_cache_api"),
        path("api/reset-metrics/", views.reset_metrics_api, name="reset_metrics_api"),
        path("api/database-info/", views.database_info_api, name="database_info_api"),
        path("logs/", views.system_logs_view, name="system_logs_view"),
    ])),
]

