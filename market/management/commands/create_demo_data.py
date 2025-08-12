from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from market.models import Item, Category
import random

class Command(BaseCommand):
    help = 'Demo kullanıcılar ve ürünler oluşturur'

    def handle(self, *args, **options):
        # Demo kullanıcılar
        demo_users = [
            {'username': 'ayse', 'email': 'ayse@example.com', 'first_name': 'Ayşe', 'last_name': 'Yılmaz'},
            {'username': 'mehmet', 'email': 'mehmet@example.com', 'first_name': 'Mehmet', 'last_name': 'Demir'},
            {'username': 'zehra', 'email': 'zehra@example.com', 'first_name': 'Zehra', 'last_name': 'Kaya'},
            {'username': 'ali', 'email': 'ali@example.com', 'first_name': 'Ali', 'last_name': 'Özkan'},
            {'username': 'fatma', 'email': 'fatma@example.com', 'first_name': 'Fatma', 'last_name': 'Çelik'},
        ]

        users = []
        for user_data in demo_users:
            user, created = User.objects.get_or_create(
                username=user_data['username'],
                defaults={
                    'email': user_data['email'],
                    'first_name': user_data['first_name'],
                    'last_name': user_data['last_name'],
                }
            )
            if created:
                user.set_password('demo123')
                user.save()
                self.stdout.write(f'✓ Kullanıcı oluşturuldu: {user.username}')
            users.append(user)

        # Demo ürünler
        demo_items = [
            # Abiye elbiseler
            {'title': 'Siyah Abiye Elbise', 'description': 'Düğün için aldım, sadece bir kez giyildi. 38 beden, çok şık.', 'category': Category.EVENING_DRESS},
            {'title': 'Kırmızı Uzun Abiye', 'description': 'Baloya gittim, temiz ve bakımlı. 40 beden.', 'category': Category.EVENING_DRESS},
            {'title': 'Mavi Payet Abiye', 'description': 'Nişan töreninden kaldı, hiç kullanmadım. 36 beden.', 'category': Category.EVENING_DRESS},
            
            # Oyun konsolları
            {'title': 'PlayStation 4 Slim', 'description': 'PlayStation 5 aldım, bu artık kullanılmıyor. 2 kol ile birlikte.', 'category': Category.GAME_CONSOLE},
            {'title': 'Xbox One S', 'description': 'Çok az kullanıldı, kutusunda. Garanti süresi dolmuş ama hiç sorun yok.', 'category': Category.GAME_CONSOLE},
            {'title': 'Nintendo Switch Lite', 'description': 'Sarı renk, temiz. Çocuğum büyüdü artık oynamıyor.', 'category': Category.GAME_CONSOLE},
            
            # Oyun diskleri
            {'title': 'FIFA 23 PS4', 'description': 'Orijinal disk, çizik yok. Satıcı gerçek oyuncu.', 'category': Category.GAME_DISC},
            {'title': 'The Last of Us Part II', 'description': 'Muhteşem bir oyun, bitirdim artık ihtiyacım yok.', 'category': Category.GAME_DISC},
            {'title': 'Mario Kart 8 Deluxe', 'description': 'Nintendo Switch için, ailecek oynuyorduk.', 'category': Category.GAME_DISC},
            {'title': 'Call of Duty Modern Warfare', 'description': 'Xbox One versiyonu, online oynamıyorum artık.', 'category': Category.GAME_DISC},
            
            # Oyuncaklar
            {'title': 'LEGO Creator Set', 'description': '1200 parça, eksik parça yok. 8+ yaş için ideal.', 'category': Category.TOY},
            {'title': 'Barbie Bebek Seti', 'description': '5 adet barbie ve aksesuarları, kızım artık oynamıyor.', 'category': Category.TOY},
            {'title': 'Hot Wheels Yarış Pisti', 'description': 'Büyük pist seti, 20 adet araba ile birlikte.', 'category': Category.TOY},
            {'title': 'Puzzle 1000 Parça', 'description': 'Manzara puzzlei, bir kez yapıldı sonra tekrar kutusuna kondu.', 'category': Category.TOY},
            
            # Kitaplar
            {'title': 'Harry Potter Seti (7 kitap)', 'description': 'Türkçe çeviri, YKY yayınları. Çok iyi durumda.', 'category': Category.BOOK},
            {'title': 'Küçük Prens', 'description': 'Antoine de Saint-Exupéry, resimli baskı.', 'category': Category.BOOK},
            {'title': 'Çocuk Ansiklopedisi', 'description': '10 ciltlik set, 6-12 yaş arası için mükemmel.', 'category': Category.BOOK},
            {'title': 'Nasreddin Hoca Hikayeleri', 'description': 'Renkli resimli, çocuklar çok seviyor.', 'category': Category.BOOK},
            
            # Diğer çocuk ürünleri
            {'title': 'Bebek Arabası Quinny', 'description': 'Premium marka, çok az kullanıldı. 0-3 yaş için.', 'category': Category.KIDS_OTHER},
            {'title': 'Çocuk Bisikleti 16 jant', 'description': '4-7 yaş arası için, yan tekerlek ile birlikte.', 'category': Category.KIDS_OTHER},
            {'title': 'Mama Sandalyesi', 'description': 'Katlanabilir, yıkanabilir. Chicco marka.', 'category': Category.KIDS_OTHER},
            {'title': 'Çocuk Kıyafetleri (2-3 yaş)', 'description': '20 parça karışık, kız çocuğu için. Hepsi markalı.', 'category': Category.KIDS_OTHER},
        ]

        # Ürünleri rastgele kullanıcılara dağıt
        for item_data in demo_items:
            item = Item.objects.create(
                owner=random.choice(users),
                title=item_data['title'],
                description=item_data['description'],
                category=item_data['category']
            )
            self.stdout.write(f'✓ Ürün oluşturuldu: {item.title} ({item.owner.username})')

        self.stdout.write(
            self.style.SUCCESS(f'Demo veriler oluşturuldu! {len(users)} kullanıcı, {len(demo_items)} ürün.')
        )
        self.stdout.write('Giriş için: kullanıcı adı ve şifre demo123')
