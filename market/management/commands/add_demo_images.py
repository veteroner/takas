import os
import requests
from django.core.management.base import BaseCommand
from django.core.files.base import ContentFile
from django.db.models import Q
from market.models import Item

class Command(BaseCommand):
    help = 'Demo ürünlere gerçek resimler ekler'

    def handle(self, *args, **options):
        # Demo resim URL'leri - Unsplash'dan kategoriye uygun resimler
        demo_images = {
            # Abiye elbiseler
            'evening_dress': [
                'https://images.unsplash.com/photo-1566479179817-c0a7b6e1f26a?w=400&h=400&fit=crop',
                'https://images.unsplash.com/photo-1515372039744-b8f02a3ae446?w=400&h=400&fit=crop',
                'https://images.unsplash.com/photo-1539008835657-9e8e9680c956?w=400&h=400&fit=crop',
            ],
            # Oyun konsolları
            'game_console': [
                'https://images.unsplash.com/photo-1606144042614-b2417e99c4e3?w=400&h=400&fit=crop',
                'https://images.unsplash.com/photo-1578662996442-48f60103fc96?w=400&h=400&fit=crop',
                'https://images.unsplash.com/photo-1635514571250-b4e1dd7ba34a?w=400&h=400&fit=crop',
            ],
            # Oyun diskleri
            'game_disc': [
                'https://images.unsplash.com/photo-1511512578047-dfb367046420?w=400&h=400&fit=crop',
                'https://images.unsplash.com/photo-1493711662062-fa541adb3fc8?w=400&h=400&fit=crop',
                'https://images.unsplash.com/photo-1556864764-60bf87bd62c1?w=400&h=400&fit=crop',
                'https://images.unsplash.com/photo-1552820728-8b83bb6b773f?w=400&h=400&fit=crop',
            ],
            # Oyuncaklar
            'toy': [
                'https://images.unsplash.com/photo-1515488042361-ee00e0ddd4e4?w=400&h=400&fit=crop',
                'https://images.unsplash.com/photo-1558618666-fcd25c85cd64?w=400&h=400&fit=crop',
                'https://images.unsplash.com/photo-1596461404969-9ae70f2830c1?w=400&h=400&fit=crop',
                'https://images.unsplash.com/photo-1570303345338-e1f0eddf4946?w=400&h=400&fit=crop',
            ],
            # Kitaplar
            'book': [
                'https://images.unsplash.com/photo-1481627834876-b7833e8f5570?w=400&h=400&fit=crop',
                'https://images.unsplash.com/photo-1544947950-fa07a98d237f?w=400&h=400&fit=crop',
                'https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=400&h=400&fit=crop',
                'https://images.unsplash.com/photo-1512820790803-83ca734da794?w=400&h=400&fit=crop',
            ],
            # Diğer çocuk ürünleri
            'kids_other': [
                'https://images.unsplash.com/photo-1515488042361-ee00e0ddd4e4?w=400&h=400&fit=crop',
                'https://images.unsplash.com/photo-1586023492125-27b2c045efd7?w=400&h=400&fit=crop',
                'https://images.unsplash.com/photo-1567306226416-28f0efdc88ce?w=400&h=400&fit=crop',
                'https://images.unsplash.com/photo-1566479179817-c0a7b6e1f26a?w=400&h=400&fit=crop',
            ],
        }

        items_without_images = Item.objects.filter(Q(image__isnull=True) | Q(image=''))
        
        for item in items_without_images:
            category_images = demo_images.get(item.category, [])
            if category_images:
                try:
                    # Kategori için ilk resmi al
                    image_url = category_images[0]
                    # Kategorideki ürünlerin sayısına göre farklı resimler kullan
                    existing_count = Item.objects.filter(category=item.category, image__isnull=False).count()
                    if existing_count < len(category_images):
                        image_url = category_images[existing_count]
                    
                    self.stdout.write(f'Resim indiriliyor: {item.title} için {image_url}')
                    
                    response = requests.get(image_url, timeout=10)
                    if response.status_code == 200:
                        # Dosya adı oluştur
                        filename = f"{item.category}_{item.id}.jpg"
                        
                        # Resmi kaydet
                        item.image.save(
                            filename,
                            ContentFile(response.content),
                            save=True
                        )
                        self.stdout.write(self.style.SUCCESS(f'✓ {item.title} için resim eklendi'))
                    else:
                        self.stdout.write(self.style.WARNING(f'⚠ {item.title} için resim indirilemedi'))
                        
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f'✗ {item.title} için hata: {str(e)}'))
                    
        self.stdout.write(self.style.SUCCESS('Demo resimler ekleme işlemi tamamlandı!'))
