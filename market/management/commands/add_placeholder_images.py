from PIL import Image, ImageDraw, ImageFont
import io
from django.core.management.base import BaseCommand
from django.core.files.base import ContentFile
from market.models import Item

class Command(BaseCommand):
    help = 'Resmi olmayan ürünler için placeholder resimler oluşturur'

    def handle(self, *args, **options):
        # Kategorilere göre renkler ve emojiler
        category_styles = {
            'evening_dress': {'color': '#e53e3e', 'emoji': '👗', 'bg': '#fed7d7'},
            'game_console': {'color': '#3182ce', 'emoji': '🎮', 'bg': '#bee3f8'},
            'game_disc': {'color': '#38a169', 'emoji': '💿', 'bg': '#c6f6d5'},
            'toy': {'color': '#d69e2e', 'emoji': '🧸', 'bg': '#faf089'},
            'book': {'color': '#805ad5', 'emoji': '📚', 'bg': '#e9d8fd'},
            'kids_other': {'color': '#ed8936', 'emoji': '🎁', 'bg': '#fed7aa'},
        }

        items_without_images = Item.objects.filter(image__in=['', None])
        
        for item in items_without_images:
            try:
                style = category_styles.get(item.category, category_styles['kids_other'])
                
                # 400x400 resim oluştur
                img = Image.new('RGB', (400, 400), style['bg'])
                draw = ImageDraw.Draw(img)
                
                # Çember çiz
                circle_size = 200
                circle_x = (400 - circle_size) // 2
                circle_y = (400 - circle_size) // 2
                draw.ellipse([circle_x, circle_y, circle_x + circle_size, circle_y + circle_size], 
                           fill=style['color'])
                
                # Emoji (Unicode desteklenmediği için basit çizim)
                try:
                    # Büyük font için emoji simülasyonu
                    font_size = 80
                    text = style['emoji']
                    
                    # Metin konumunu hesapla
                    text_bbox = draw.textbbox((0, 0), text)
                    text_width = text_bbox[2] - text_bbox[0]
                    text_height = text_bbox[3] - text_bbox[1]
                    text_x = (400 - text_width) // 2
                    text_y = (400 - text_height) // 2
                    
                    draw.text((text_x, text_y), text, fill='white')
                except:
                    # Emoji yazamazsa basit metin
                    text = item.category.replace('_', ' ').upper()[:3]
                    draw.text((180, 180), text, fill='white')
                
                # Resmi byte array'e çevir
                img_buffer = io.BytesIO()
                img.save(img_buffer, format='JPEG', quality=85)
                img_buffer.seek(0)
                
                # Dosya adı oluştur
                filename = f"placeholder_{item.category}_{item.id}.jpg"
                
                # Resmi kaydet
                item.image.save(
                    filename,
                    ContentFile(img_buffer.getvalue()),
                    save=True
                )
                
                self.stdout.write(self.style.SUCCESS(f'✓ {item.title} için placeholder resim oluşturuldu'))
                    
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'✗ {item.title} için hata: {str(e)}'))
                
        self.stdout.write(self.style.SUCCESS('Placeholder resimler oluşturuldu!'))
