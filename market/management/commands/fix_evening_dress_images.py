import requests
from django.core.management.base import BaseCommand
from django.core.files.base import ContentFile
from market.models import Item

class Command(BaseCommand):
    help = 'Abiye elbise resimlerini düzeltir'

    def handle(self, *args, **options):
        # Alternatif abiye elbise resimleri
        evening_dress_images = [
            'https://images.unsplash.com/photo-1595777457583-95e059d581b8?w=400&h=400&fit=crop',
            'https://images.unsplash.com/photo-1539119630297-1de43a1ddd55?w=400&h=400&fit=crop', 
            'https://images.unsplash.com/photo-1594736797933-d0cc64a7dea3?w=400&h=400&fit=crop',
        ]

        evening_dress_items = Item.objects.filter(category='evening_dress', image__in=['', None])
        
        for i, item in enumerate(evening_dress_items):
            try:
                image_url = evening_dress_images[i % len(evening_dress_images)]
                self.stdout.write(f'Abiye resmi indiriliyor: {item.title} için {image_url}')
                
                response = requests.get(image_url, timeout=10)
                if response.status_code == 200:
                    filename = f"evening_dress_{item.id}.jpg"
                    
                    item.image.save(
                        filename,
                        ContentFile(response.content),
                        save=True
                    )
                    self.stdout.write(self.style.SUCCESS(f'✓ {item.title} için abiye resmi eklendi'))
                else:
                    self.stdout.write(self.style.WARNING(f'⚠ {item.title} için resim indirilemedi'))
                    
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'✗ {item.title} için hata: {str(e)}'))
                
        self.stdout.write(self.style.SUCCESS('Abiye elbise resimleri düzeltildi!'))
