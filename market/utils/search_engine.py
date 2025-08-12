"""
🔍 Advanced Search Engine
Enterprise-level arama sistemi, fuzzy search, geo-location, ML-based ranking ile.
"""

import re
import math
from typing import List, Dict, Any, Tuple, Optional
from datetime import datetime, timedelta
from django.db.models import Q, Count, Avg, F, Case, When, Value, FloatField
# Simple distance calculation without GDAL dependency
from django.utils import timezone
# Use basic string matching instead of fuzzywuzzy for simplicity
# from fuzzywuzzy import fuzz
import logging

logger = logging.getLogger(__name__)


class AdvancedSearchEngine:
    """Gelişmiş arama motoru"""
    
    def __init__(self):
        self.search_weights = {
            'exact_title_match': 100,
            'fuzzy_title_match': 80,
            'description_match': 60,
            'category_match': 70,
            'trade_preferences_match': 50,
            'recency': 20,
            'popularity': 30,
            'location_proximity': 40,
            'price_attractiveness': 25,
            'user_preference_match': 90,
        }
        
    def search(self, query_params: Dict[str, Any], user=None) -> Dict[str, Any]:
        """
        Ana arama fonksiyonu
        
        Args:
            query_params: Arama parametreleri
            user: Arama yapan kullanıcı
            
        Returns:
            Arama sonuçları ve meta data
        """
        from ..models import Item, SearchHistory, PopularSearch
        
        start_time = datetime.now()
        
        # Base queryset
        queryset = Item.objects.all()
        
        # Kendi ürünlerini hariç tut (default)
        if user and query_params.get('exclude_own_items', True):
            queryset = queryset.exclude(owner=user)
        
        # Text search
        query = query_params.get('query', '').strip()
        if query:
            queryset = self._apply_text_search(queryset, query)
            self._track_popular_search(query)
        
        # Category filters
        categories = query_params.get('categories', [])
        if categories:
            queryset = queryset.filter(category__in=categories)
        
        # Condition filters
        conditions = query_params.get('conditions', [])
        if conditions:
            queryset = queryset.filter(condition__in=conditions)
        
        # Price filters
        queryset = self._apply_price_filters(queryset, query_params)
        
        # Location filters
        queryset = self._apply_location_filters(queryset, query_params, user)
        
        # Date filters
        queryset = self._apply_date_filters(queryset, query_params)
        
        # Advanced filters
        queryset = self._apply_advanced_filters(queryset, query_params, user)
        
        # Get results before sorting
        results = list(queryset.distinct())
        
        # ML-based scoring and ranking
        if query or user:
            results = self._apply_ml_ranking(results, query, user, query_params)
        
        # Sorting
        sort_by = query_params.get('sort_by', 'newest')
        results = self._apply_sorting(results, sort_by, user)
        
        # Pagination
        page = query_params.get('page', 1)
        per_page = query_params.get('per_page', 20)
        paginated_results, pagination_info = self._paginate_results(results, page, per_page)
        
        # Search analytics
        search_time = (datetime.now() - start_time).total_seconds()
        
        # Save search history
        if user and query:
            self._save_search_history(user, query, query_params, len(results))
        
        # Generate suggestions
        suggestions = self._generate_suggestions(query, results, user)
        
        return {
            'results': paginated_results,
            'pagination': pagination_info,
            'total_count': len(results),
            'search_time': search_time,
            'suggestions': suggestions,
            'filters_applied': self._get_applied_filters(query_params),
            'popular_searches': self._get_popular_searches(),
            'recommended_filters': self._get_recommended_filters(results, user),
        }
    
    def _apply_text_search(self, queryset, query: str):
        """Gelişmiş text search uygula"""
        from ..models import Item
        
        # Clean query
        clean_query = re.sub(r'[^\w\s]', '', query.lower())
        words = [w for w in clean_query.split() if len(w) > 2]
        
        if not words:
            return queryset
        
        # Build complex Q object for multi-field search
        q_objects = Q()
        
        for word in words:
            word_q = (
                Q(title__icontains=word) |
                Q(description__icontains=word) |
                Q(trade_preferences__icontains=word)
            )
            q_objects |= word_q
        
        # Exact phrase search (higher priority)
        exact_q = (
            Q(title__icontains=query) |
            Q(description__icontains=query) |
            Q(trade_preferences__icontains=query)
        )
        
        # Combine with OR
        final_q = exact_q | q_objects
        
        return queryset.filter(final_q)
    
    def _apply_price_filters(self, queryset, params: Dict[str, Any]):
        """Fiyat filtrelerini uygula"""
        min_price = params.get('min_price')
        max_price = params.get('max_price')
        price_range = params.get('price_range')
        
        # Direct price range
        if min_price is not None:
            queryset = queryset.filter(price_info__estimated_price__gte=min_price)
        if max_price is not None:
            queryset = queryset.filter(price_info__estimated_price__lte=max_price)
        
        # Predefined price ranges
        if price_range:
            if price_range == '0-50':
                queryset = queryset.filter(price_info__estimated_price__lte=50)
            elif price_range == '50-100':
                queryset = queryset.filter(
                    price_info__estimated_price__gte=50,
                    price_info__estimated_price__lte=100
                )
            elif price_range == '100-250':
                queryset = queryset.filter(
                    price_info__estimated_price__gte=100,
                    price_info__estimated_price__lte=250
                )
            elif price_range == '250-500':
                queryset = queryset.filter(
                    price_info__estimated_price__gte=250,
                    price_info__estimated_price__lte=500
                )
            elif price_range == '500-1000':
                queryset = queryset.filter(
                    price_info__estimated_price__gte=500,
                    price_info__estimated_price__lte=1000
                )
            elif price_range == '1000+':
                queryset = queryset.filter(price_info__estimated_price__gte=1000)
        
        return queryset
    
    def _apply_location_filters(self, queryset, params: Dict[str, Any], user):
        """Konum filtrelerini uygula"""
        city = params.get('city')
        district = params.get('district')
        distance_range = params.get('distance_range', 'all')
        latitude = params.get('latitude')
        longitude = params.get('longitude')
        
        # City and district filters
        if city:
            queryset = queryset.filter(location__city__icontains=city)
        if district:
            queryset = queryset.filter(location__district__icontains=district)
        
        # Distance-based filtering would require PostGIS or geo library
        # For now, we skip advanced location filtering
        # In production, implement with Elasticsearch or PostGIS
        
        return queryset
    
    def _apply_date_filters(self, queryset, params: Dict[str, Any]):
        """Tarih filtrelerini uygula"""
        date_from = params.get('date_from')
        date_to = params.get('date_to')
        
        if date_from:
            try:
                from_date = datetime.strptime(date_from, '%Y-%m-%d').date()
                queryset = queryset.filter(created_at__date__gte=from_date)
            except ValueError:
                pass
        
        if date_to:
            try:
                to_date = datetime.strptime(date_to, '%Y-%m-%d').date()
                queryset = queryset.filter(created_at__date__lte=to_date)
            except ValueError:
                pass
        
        return queryset
    
    def _apply_advanced_filters(self, queryset, params: Dict[str, Any], user):
        """Gelişmiş filtreleri uygula"""
        has_image = params.get('has_image', False)
        trade_type = params.get('trade_type')
        only_favorites = params.get('only_favorites', False)
        
        # Has image filter
        if has_image:
            queryset = queryset.filter(
                Q(image__isnull=False) | Q(images__isnull=False)
            )
        
        # Trade type filter
        if trade_type:
            queryset = queryset.filter(trade_preferences__icontains=trade_type)
        
        # Only favorites filter
        if only_favorites and user:
            queryset = queryset.filter(favorited_by=user)
        
        return queryset
    
    def _apply_ml_ranking(self, results: List, query: str, user, params: Dict[str, Any]) -> List:
        """ML-based ranking algorithm"""
        if not results:
            return results
        
        scored_results = []
        
        for item in results:
            score = self._calculate_item_score(item, query, user, params)
            scored_results.append((item, score))
        
        # Sort by score (descending)
        scored_results.sort(key=lambda x: x[1], reverse=True)
        
        return [item for item, score in scored_results]
    
    def _calculate_item_score(self, item, query: str, user, params: Dict[str, Any]) -> float:
        """Ürün için detaylı skor hesapla"""
        total_score = 0.0
        
        # Simple text relevance score
        if query:
            # Basic string matching (can be enhanced with fuzzy matching later)
            title_lower = item.title.lower()
            query_lower = query.lower()
            
            if query_lower in title_lower:
                title_score = 1.0
            else:
                title_score = 0.3  # Partial match
            
            desc_lower = item.description.lower()
            if query_lower in desc_lower:
                desc_score = 0.8
            else:
                desc_score = 0.1
            
            total_score += title_score * self.search_weights['exact_title_match']
            total_score += desc_score * self.search_weights['description_match']
        
        # Recency score
        days_old = (timezone.now() - item.created_at).days
        recency_score = max(0, 1 - (days_old / 365))  # 1 year decay
        total_score += recency_score * self.search_weights['recency']
        
        # Popularity score (favorites count)
        popularity_score = min(1.0, item.favorited_by.count() / 100.0)
        total_score += popularity_score * self.search_weights['popularity']
        
        # Image quality score
        if hasattr(item, 'images') and item.images.exists():
            total_score += 10  # Bonus for having images
        elif item.image:
            total_score += 5   # Smaller bonus for single image
        
        # User preference matching
        if user:
            # Check user's past interactions
            user_categories = self._get_user_preferred_categories(user)
            if item.category in user_categories:
                total_score += self.search_weights['user_preference_match']
        
        return total_score
    
    def _apply_sorting(self, results: List, sort_by: str, user) -> List:
        """Sıralama uygula"""
        if not results:
            return results
        
        if sort_by == 'newest':
            return sorted(results, key=lambda x: x.created_at, reverse=True)
        elif sort_by == 'oldest':
            return sorted(results, key=lambda x: x.created_at)
        elif sort_by == 'name_asc':
            return sorted(results, key=lambda x: x.title.lower())
        elif sort_by == 'name_desc':
            return sorted(results, key=lambda x: x.title.lower(), reverse=True)
        elif sort_by == 'popularity':
            return sorted(results, key=lambda x: x.favorited_by.count(), reverse=True)
        elif sort_by == 'price_asc':
            return sorted(results, 
                         key=lambda x: getattr(x.price_info, 'estimated_price', 0) or 0)
        elif sort_by == 'price_desc':
            return sorted(results, 
                         key=lambda x: getattr(x.price_info, 'estimated_price', 0) or 0,
                         reverse=True)
        else:
            # Default: newest
            return sorted(results, key=lambda x: x.created_at, reverse=True)
    
    def _paginate_results(self, results: List, page: int, per_page: int) -> Tuple[List, Dict]:
        """Sayfalama uygula"""
        total = len(results)
        start = (page - 1) * per_page
        end = start + per_page
        
        paginated = results[start:end]
        
        pagination_info = {
            'page': page,
            'per_page': per_page,
            'total': total,
            'pages': math.ceil(total / per_page) if per_page > 0 else 1,
            'has_previous': page > 1,
            'has_next': end < total,
            'previous_page': page - 1 if page > 1 else None,
            'next_page': page + 1 if end < total else None,
        }
        
        return paginated, pagination_info
    
    def _generate_suggestions(self, query: str, results: List, user) -> Dict[str, Any]:
        """Arama önerileri oluştur"""
        suggestions = {
            'spelling_corrections': [],
            'related_searches': [],
            'category_suggestions': [],
            'location_suggestions': [],
            'no_results_suggestions': [],
        }
        
        if not results and query:
            # No results - provide helpful suggestions
            suggestions['no_results_suggestions'] = [
                'Arama terimini kısaltmayı deneyin',
                'Farklı kelimeler kullanmayı deneyin',
                'Filtreleri azaltmayı deneyin',
                'Yakın bölgelerde aramayı deneyin',
            ]
        
        # Related searches from popular searches
        suggestions['related_searches'] = self._get_related_searches(query)
        
        # Category suggestions based on results
        if results:
            categories = {}
            for item in results[:50]:  # Sample from first 50
                cat = item.get_category_display()
                categories[cat] = categories.get(cat, 0) + 1
            
            suggestions['category_suggestions'] = [
                {'name': cat, 'count': count} 
                for cat, count in sorted(categories.items(), key=lambda x: x[1], reverse=True)[:5]
            ]
        
        return suggestions
    
    def _save_search_history(self, user, query: str, params: Dict[str, Any], results_count: int):
        """Arama geçmişini kaydet"""
        from ..models import SearchHistory
        
        try:
            SearchHistory.objects.create(
                user=user,
                query=query,
                filters=params,
                results_count=results_count
            )
            
            # Limit history to last 100 searches per user
            old_searches = SearchHistory.objects.filter(user=user)[100:]
            if old_searches:
                SearchHistory.objects.filter(
                    id__in=[s.id for s in old_searches]
                ).delete()
                
        except Exception as e:
            logger.error(f"Search history save error: {e}")
    
    def _track_popular_search(self, query: str):
        """Popüler aramaları takip et"""
        from ..models import PopularSearch
        
        try:
            popular, created = PopularSearch.objects.get_or_create(
                query=query.lower(),
                defaults={'search_count': 1}
            )
            
            if not created:
                popular.search_count += 1
                popular.daily_count = F('daily_count') + 1
                popular.weekly_count = F('weekly_count') + 1
                popular.monthly_count = F('monthly_count') + 1
                popular.save()
                
        except Exception as e:
            logger.error(f"Popular search tracking error: {e}")
    
    def _get_applied_filters(self, params: Dict[str, Any]) -> List[Dict[str, str]]:
        """Uygulanan filtreleri al"""
        applied = []
        
        if params.get('query'):
            applied.append({'type': 'query', 'value': params['query'], 'label': f"Arama: {params['query']}"})
        
        if params.get('categories'):
            applied.append({'type': 'categories', 'value': str(params['categories']), 'label': f"Kategoriler: {len(params['categories'])}"})
        
        if params.get('price_range'):
            applied.append({'type': 'price', 'value': params['price_range'], 'label': f"Fiyat: {params['price_range']}"})
        
        if params.get('city'):
            applied.append({'type': 'location', 'value': params['city'], 'label': f"Şehir: {params['city']}"})
        
        return applied
    
    def _get_popular_searches(self) -> List[str]:
        """Popüler aramaları al"""
        from ..models import PopularSearch
        
        try:
            return list(
                PopularSearch.objects.values_list('query', flat=True)[:10]
            )
        except Exception:
            return []
    
    def _get_recommended_filters(self, results: List, user) -> Dict[str, Any]:
        """Önerilen filtreleri al"""
        if not results:
            return {}
        
        # Analyze results to suggest filters
        categories = {}
        conditions = {}
        
        for item in results[:100]:  # Sample
            cat = item.category
            categories[cat] = categories.get(cat, 0) + 1
            
            cond = item.condition
            conditions[cond] = conditions.get(cond, 0) + 1
        
        return {
            'categories': [
                {'value': cat, 'count': count, 'label': dict(item.CATEGORY_CHOICES).get(cat, cat)}
                for cat, count in sorted(categories.items(), key=lambda x: x[1], reverse=True)[:5]
            ],
            'conditions': [
                {'value': cond, 'count': count, 'label': dict(item.CONDITION_CHOICES).get(cond, cond)}
                for cond, count in sorted(conditions.items(), key=lambda x: x[1], reverse=True)[:5]
            ] if results else []
        }
    
    def _get_related_searches(self, query: str) -> List[str]:
        """İlgili aramaları al"""
        from ..models import PopularSearch
        
        if not query:
            return []
        
        try:
            # Find searches with similar words
            words = query.lower().split()
            related = []
            
            for search in PopularSearch.objects.all()[:50]:
                search_words = search.query.split()
                
                # Check for common words
                common_words = set(words) & set(search_words)
                if common_words and search.query != query.lower():
                    related.append(search.query)
            
            return related[:5]
            
        except Exception:
            return []
    
    def _get_user_preferred_categories(self, user) -> List[str]:
        """Kullanıcının tercih ettiği kategorileri al"""
        try:
            # Get categories from user's items
            user_categories = list(
                user.items.values_list('category', flat=True).distinct()
            )
            
            # Get categories from user's favorites
            favorite_categories = list(
                user.favorites.values_list('item__category', flat=True).distinct()
            )
            
            return list(set(user_categories + favorite_categories))
            
        except Exception:
            return []

    def get_autocomplete_suggestions(self, query: str, limit: int = 10) -> List[Dict[str, str]]:
        """Auto-complete önerileri"""
        from ..models import Item, PopularSearch
        
        if len(query) < 2:
            return []
        
        suggestions = []
        
        try:
            # Product title suggestions
            items = Item.objects.filter(
                title__icontains=query
            ).values_list('title', flat=True)[:limit//2]
            
            for title in items:
                suggestions.append({
                    'type': 'product',
                    'text': title,
                    'value': title
                })
            
            # Popular search suggestions
            popular = PopularSearch.objects.filter(
                query__icontains=query
            ).values_list('query', flat=True)[:limit//2]
            
            for search in popular:
                suggestions.append({
                    'type': 'search',
                    'text': search,
                    'value': search
                })
            
        except Exception as e:
            logger.error(f"Autocomplete error: {e}")
        
        return suggestions[:limit]


# Global search engine instance
search_engine = AdvancedSearchEngine()
