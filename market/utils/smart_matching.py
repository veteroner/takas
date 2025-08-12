"""
🧠 Smart Matching Engine - AI Tabanlı Takas Önerisi Sistemi
Bu modül kullanıcı davranışlarını analiz ederek akıllı takas önerileri üretir.
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
from django.db.models import Q, Count, Avg, F, Sum, Case, When, FloatField
from django.contrib.auth.models import User
from django.utils import timezone
from django.core.cache import cache

from ..models import Item, UserPreference, UserInteraction, MatchRecommendation, Trade, Favorite, Category

logger = logging.getLogger(__name__)


class SmartMatchingEngine:
    """AI Tabanlı Takas Önerisi Motoru"""
    
    def __init__(self):
        self.category_weights = {
            Category.EVENING_DRESS: 1.0,
            Category.GAME_CONSOLE: 1.2,
            Category.GAME_DISC: 1.1,
            Category.TOY: 0.9,
            Category.BOOK: 0.8,
            Category.KIDS_OTHER: 0.7,
        }
    
    def generate_recommendations_for_user(self, user: User, limit: int = 10) -> List[MatchRecommendation]:
        """Kullanıcı için akıllı öneriler oluştur"""
        try:
            # Önce kullanıcı tercihlerini al/oluştur
            user_prefs = self._get_or_create_user_preferences(user)
            
            # Farklı algoritmaları kombine et
            recommendations = []
            
            # 1. Davranış bazlı öneriler (%40)
            behavior_recs = self._generate_behavior_based_recommendations(user, user_prefs, limit // 2)
            recommendations.extend(behavior_recs)
            
            # 2. Kategori bazlı öneriler (%30)
            category_recs = self._generate_category_based_recommendations(user, user_prefs, limit // 3)
            recommendations.extend(category_recs)
            
            # 3. Mükemmel eşleşmeler (%20)
            perfect_matches = self._find_perfect_matches(user, limit // 4)
            recommendations.extend(perfect_matches)
            
            # 4. Trend bazlı öneriler (%10)
            trending_recs = self._generate_trending_recommendations(user, limit // 10 + 1)
            recommendations.extend(trending_recs)
            
            # Skorlara göre sırala ve tekrarları temizle
            unique_recommendations = self._deduplicate_and_rank(recommendations, limit)
            
            # Veritabanına kaydet
            saved_recommendations = []
            for rec_data in unique_recommendations:
                rec = MatchRecommendation.objects.create(**rec_data)
                saved_recommendations.append(rec)
            
            logger.info(f"Generated {len(saved_recommendations)} recommendations for user {user.username}")
            return saved_recommendations
            
        except Exception as e:
            logger.error(f"Error generating recommendations for user {user.username}: {e}")
            return []
    
    def _get_or_create_user_preferences(self, user: User) -> UserPreference:
        """Kullanıcı tercihlerini al veya oluştur"""
        prefs, created = UserPreference.objects.get_or_create(
            user=user,
            defaults={
                'category_weights': {},
                'avg_response_time': 24.0,
                'trade_success_rate': 0.0,
                'activity_score': 0.0,
            }
        )
        
        if created or not prefs.category_weights:
            # İlk kez oluşturuluyorsa veya boşsa, kullanıcı davranışlarından öğren
            self._learn_user_preferences(user, prefs)
        
        return prefs
    
    def _learn_user_preferences(self, user: User, prefs: UserPreference):
        """Kullanıcı davranışlarından tercihleri öğren"""
        # Son 30 günün etkileşimlerini analiz et
        since_date = timezone.now() - timedelta(days=30)
        
        interactions = UserInteraction.objects.filter(
            user=user,
            created_at__gte=since_date
        ).select_related('item')
        
        category_scores = {}
        total_interactions = interactions.count()
        
        if total_interactions > 0:
            # Kategori tercihlerini hesapla
            for interaction in interactions:
                category = interaction.item.category
                weight = self._get_interaction_weight(interaction.interaction_type)
                
                if category not in category_scores:
                    category_scores[category] = 0
                category_scores[category] += weight
            
            # Normalize et
            max_score = max(category_scores.values()) if category_scores else 1
            for category in category_scores:
                category_scores[category] = category_scores[category] / max_score
            
            prefs.category_weights = category_scores
            
            # Aktivite skorunu hesapla
            prefs.activity_score = min(100, total_interactions * 2)
            
            # Takas başarı oranını hesapla
            successful_trades = Trade.objects.filter(
                Q(requester=user) | Q(responder=user),
                status='accepted',
                created_at__gte=since_date
            ).count()
            
            total_trades = Trade.objects.filter(
                Q(requester=user) | Q(responder=user),
                created_at__gte=since_date
            ).count()
            
            if total_trades > 0:
                prefs.trade_success_rate = successful_trades / total_trades
            
            prefs.save()
    
    def _get_interaction_weight(self, interaction_type: str) -> float:
        """Etkileşim tipine göre ağırlık döndür"""
        weights = {
            'view': 0.1,
            'favorite': 0.5,
            'unfavorite': -0.3,
            'trade_request': 0.8,
            'trade_accept': 1.0,
            'trade_reject': -0.2,
            'swipe_right': 0.6,
            'swipe_left': -0.1,
            'message_send': 0.7,
        }
        return weights.get(interaction_type, 0.1)
    
    def _generate_behavior_based_recommendations(self, user: User, prefs: UserPreference, limit: int) -> List[Dict]:
        """Davranış bazlı öneriler"""
        recommendations = []
        
        # Kullanıcının beğendiği/favorilediği ürünlere benzer ürünler bul
        liked_items = UserInteraction.objects.filter(
            user=user,
            interaction_type__in=['favorite', 'swipe_right', 'trade_request']
        ).values_list('item', flat=True)
        
        if liked_items:
            # Benzer kategorilerdeki ürünleri bul
            similar_items = Item.objects.filter(
                category__in=Item.objects.filter(id__in=liked_items).values_list('category', flat=True)
            ).exclude(
                owner=user
            ).exclude(
                id__in=liked_items
            ).annotate(
                interaction_count=Count('interactions')
            ).order_by('-interaction_count', '-created_at')[:limit]
            
            for item in similar_items:
                score = self._calculate_behavior_score(user, item, prefs)
                if score > 50:  # Minimum threshold
                    recommendations.append({
                        'user': user,
                        'recommended_item': item,
                        'match_score': score,
                        'recommendation_type': 'user_behavior',
                        'confidence_level': min(0.9, score / 100),
                        'reasoning': {
                            'type': 'Davranış bazlı',
                            'description': f'Benzer ürünleri beğendiniz: {item.category}',
                            'factors': ['user_behavior', 'category_match']
                        }
                    })
        
        return recommendations[:limit]
    
    def _calculate_behavior_score(self, user: User, item: Item, prefs: UserPreference) -> float:
        """Davranış bazlı skor hesapla"""
        score = 50.0  # Base score
        
        # Kategori tercihi
        category_weight = prefs.category_weights.get(item.category, 0.5)
        score += category_weight * 20
        
        # Ürün yaşı
        item_age = (timezone.now() - item.created_at).days
        if prefs.preferred_item_age_min <= item_age <= prefs.preferred_item_age_max:
            score += 15
        
        # Popülerlik
        interaction_count = item.interactions.count()
        if interaction_count > 5:
            score += min(10, interaction_count)
        
        # Sahip aktivitesi
        owner_prefs = UserPreference.objects.filter(user=item.owner).first()
        if owner_prefs:
            score += owner_prefs.activity_score * 0.1
            score += owner_prefs.trade_success_rate * 10
        
        return min(100, score)
    
    def _generate_category_based_recommendations(self, user: User, prefs: UserPreference, limit: int) -> List[Dict]:
        """Kategori bazlı öneriler"""
        recommendations = []
        
        # En beğenilen kategorilerden ürünler öner
        for category, weight in sorted(prefs.category_weights.items(), key=lambda x: x[1], reverse=True)[:3]:
            if weight > 0.3:  # Minimum ilgi threshold'u
                items = Item.objects.filter(
                    category=category
                ).exclude(
                    owner=user
                ).annotate(
                    popularity=Count('interactions')
                ).order_by('-popularity', '-created_at')[:limit//3]
                
                for item in items:
                    score = 60 + (weight * 30)  # Kategori ağırlığına göre skor
                    
                    # Ek faktörler
                    if item.image_count > 1:
                        score += 5  # Çoklu fotoğraf bonusu
                    
                    if item.interactions.filter(interaction_type='favorite').count() > 2:
                        score += 5  # Popülerlik bonusu
                    
                    recommendations.append({
                        'user': user,
                        'recommended_item': item,
                        'match_score': min(100, score),
                        'recommendation_type': 'category_match',
                        'confidence_level': weight,
                        'reasoning': {
                            'type': 'Kategori eşleşmesi',
                            'description': f'{category} kategorisine ilgi gösterdiniz',
                            'factors': ['category_preference', 'popularity']
                        }
                    })
        
        return recommendations[:limit]
    
    def _find_perfect_matches(self, user: User, limit: int) -> List[Dict]:
        """Mükemmel eşleşmeleri bul - mutual interest"""
        recommendations = []
        
        # Kullanıcının ürünlerine ilgi gösteren kişilerin ürünlerini bul
        interested_users = UserInteraction.objects.filter(
            item__owner=user,
            interaction_type__in=['favorite', 'swipe_right', 'trade_request']
        ).values_list('user', flat=True).distinct()
        
        for interested_user_id in interested_users:
            interested_user = User.objects.get(id=interested_user_id)
            their_items = Item.objects.filter(owner=interested_user).exclude(
                id__in=UserInteraction.objects.filter(
                    user=user,
                    interaction_type='swipe_left'
                ).values_list('item', flat=True)
            )
            
            for item in their_items[:limit//len(interested_users) if interested_users else 1]:
                # Karşılıklı ilgi var mı kontrol et
                mutual_interest = UserInteraction.objects.filter(
                    user=interested_user,
                    item__owner=user,
                    interaction_type__in=['favorite', 'swipe_right']
                ).exists()
                
                if mutual_interest:
                    score = 85 + (15 if item.image_count > 1 else 0)
                    
                    recommendations.append({
                        'user': user,
                        'recommended_item': item,
                        'match_score': score,
                        'recommendation_type': 'perfect_match',
                        'confidence_level': 0.95,
                        'reasoning': {
                            'type': 'Mükemmel eşleşme',
                            'description': f'{interested_user.username} ürününüze ilgi gösterdi',
                            'factors': ['mutual_interest', 'high_compatibility']
                        }
                    })
        
        return recommendations[:limit]
    
    def _generate_trending_recommendations(self, user: User, limit: int) -> List[Dict]:
        """Trend ürünler öner"""
        recommendations = []
        
        # Son 7 günde en çok etkileşim alan ürünler
        since_date = timezone.now() - timedelta(days=7)
        trending_items = Item.objects.filter(
            created_at__gte=since_date
        ).exclude(
            owner=user
        ).annotate(
            trend_score=Count('interactions')
        ).filter(
            trend_score__gt=2
        ).order_by('-trend_score')[:limit]
        
        for item in trending_items:
            score = 50 + min(30, item.trend_score * 3)
            
            recommendations.append({
                'user': user,
                'recommended_item': item,
                'match_score': score,
                'recommendation_type': 'trending',
                'confidence_level': 0.7,
                'reasoning': {
                    'type': 'Trend ürün',
                    'description': f'Son günlerde popüler: {item.trend_score} etkileşim',
                    'factors': ['trending', 'recent_popularity']
                }
            })
        
        return recommendations
    
    def _deduplicate_and_rank(self, recommendations: List[Dict], limit: int) -> List[Dict]:
        """Tekrarları temizle ve en iyi skorlara göre sırala"""
        # Item ID'sine göre en yüksek skorlu olanları tut
        best_recs = {}
        
        for rec in recommendations:
            item_id = rec['recommended_item'].id
            if item_id not in best_recs or rec['match_score'] > best_recs[item_id]['match_score']:
                best_recs[item_id] = rec
        
        # Skorlara göre sırala
        sorted_recs = sorted(best_recs.values(), key=lambda x: x['match_score'], reverse=True)
        
        return sorted_recs[:limit]
    
    def update_user_interaction(self, user: User, item: Item, interaction_type: str, 
                              response_time: Optional[float] = None, session_duration: Optional[float] = None,
                              request=None):
        """Kullanıcı etkileşimini kaydet ve tercihleri güncelle"""
        try:
            # IP ve User Agent bilgilerini al
            ip_address = None
            user_agent = ""
            
            if request:
                ip_address = self._get_client_ip(request)
                user_agent = request.META.get('HTTP_USER_AGENT', '')[:500]  # Limit to 500 chars
            
            # Etkileşimi kaydet
            interaction = UserInteraction.objects.create(
                user=user,
                item=item,
                interaction_type=interaction_type,
                response_time=response_time,
                session_duration=session_duration,
                ip_address=ip_address,
                user_agent=user_agent
            )
            
            # Cache'deki önerileri temizle
            cache_key = f"recommendations_user_{user.id}"
            cache.delete(cache_key)
            
            # Tercihleri async güncelle (opsiyonel - performans için)
            self._async_update_preferences(user)
            
            return interaction
            
        except Exception as e:
            logger.error(f"Error updating user interaction: {e}")
            return None
    
    def _get_client_ip(self, request):
        """Client IP adresini al"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
    
    def _async_update_preferences(self, user: User):
        """Kullanıcı tercihlerini asenkron güncelle"""
        # Bu method'u Celery task olarak implement edebiliriz
        # Şimdilik basit versiyonu yapalım
        try:
            prefs = UserPreference.objects.get(user=user)
            self._learn_user_preferences(user, prefs)
        except UserPreference.DoesNotExist:
            pass
    
    def get_cached_recommendations(self, user: User, limit: int = 10) -> List[MatchRecommendation]:
        """Cache'den önerileri getir, yoksa oluştur"""
        cache_key = f"recommendations_user_{user.id}"
        recommendations = cache.get(cache_key)
        
        if not recommendations:
            # Son 24 saat içinde oluşturulan önerileri kontrol et
            recent_recs = MatchRecommendation.objects.filter(
                user=user,
                created_at__gte=timezone.now() - timedelta(hours=24),
                is_shown=False
            ).order_by('-match_score')[:limit]
            
            if recent_recs.count() >= limit // 2:
                recommendations = list(recent_recs)
            else:
                # Yeni öneriler oluştur
                recommendations = self.generate_recommendations_for_user(user, limit)
            
            # Cache'le (1 saat)
            cache.set(cache_key, recommendations, 3600)
        
        return recommendations
    
    def mark_recommendation_shown(self, recommendation_id: int):
        """Öneriyi gösterildi olarak işaretle"""
        try:
            rec = MatchRecommendation.objects.get(id=recommendation_id)
            rec.is_shown = True
            rec.shown_at = timezone.now()
            rec.save()
        except MatchRecommendation.DoesNotExist:
            pass
    
    def mark_recommendation_clicked(self, recommendation_id: int):
        """Öneriyi tıklandı olarak işaretle"""
        try:
            rec = MatchRecommendation.objects.get(id=recommendation_id)
            rec.is_clicked = True
            rec.clicked_at = timezone.now()
            rec.save()
        except MatchRecommendation.DoesNotExist:
            pass
    
    def get_recommendation_stats(self, user: User) -> Dict:
        """Kullanıcı için öneri istatistikleri"""
        stats = MatchRecommendation.objects.filter(user=user).aggregate(
            total_recommendations=Count('id'),
            shown_recommendations=Count('id', filter=Q(is_shown=True)),
            clicked_recommendations=Count('id', filter=Q(is_clicked=True)),
            converted_recommendations=Count('id', filter=Q(is_converted=True)),
            avg_match_score=Avg('match_score')
        )
        
        # CTR ve Conversion rate hesapla
        if stats['shown_recommendations'] > 0:
            stats['ctr'] = stats['clicked_recommendations'] / stats['shown_recommendations']
        else:
            stats['ctr'] = 0
        
        if stats['clicked_recommendations'] > 0:
            stats['conversion_rate'] = stats['converted_recommendations'] / stats['clicked_recommendations']
        else:
            stats['conversion_rate'] = 0
        
        return stats


# Global instance
smart_matching_engine = SmartMatchingEngine()
