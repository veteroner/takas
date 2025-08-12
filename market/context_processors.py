from .models import Trade, TradeStatus

def notifications(request):
    """Kullanıcı bildirimleri için context processor"""
    if not request.user.is_authenticated:
        return {}
    
    # Gelen bekleyen teklifler
    pending_trades = Trade.objects.filter(
        responder=request.user,
        status=TradeStatus.PENDING
    ).count()
    
    # Gelen yeni kabul/ret durumları
    recent_responses = Trade.objects.filter(
        requester=request.user,
        status__in=[TradeStatus.ACCEPTED, TradeStatus.REJECTED]
    ).count()
    
    total_notifications = pending_trades + recent_responses
    
    return {
        'pending_trades_count': pending_trades,
        'recent_responses_count': recent_responses,
        'total_notifications': total_notifications,
    }
