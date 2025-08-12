# 🔄 Swapzy - Güvenli Takas Platformu

Evinizde atıl duran eşyalarınızı para kullanmadan güvenle takas etmenizi sağlayan modern web platformu.

## ✨ Özellikler

### 🎯 Temel Özellikler
- **Güvenli Kullanıcı Sistemi**: Kayıt, giriş ve profil yönetimi
- **Ürün Yönetimi**: Fotoğraflı ürün ekleme ve düzenleme
- **6 Kategori**: Abiye, Oyun Konsolu, Oyun CD/DVD, Oyuncak, Kitap, Diğer Çocuk Ürünleri
- **Takas Sistemi**: Teklif gönderme, kabul/ret, iptal işlemleri
- **Mesajlaşma**: Takas başına özel anlık mesajlaşma

### 🔍 Gelişmiş Özellikler
- **Akıllı Arama**: Ürün adı ve açıklamada arama
- **Filtreleme**: Kategori ve sıralama seçenekleri
- **Favoriler**: Beğenilen ürünleri kaydetme
- **Bildirimler**: Bekleyen teklifler için canlı sayaç
- **Responsive Tasarım**: Mobil, tablet ve masaüstü uyumlu

### 🎨 UI/UX
- **Modern Tasarım**: Gradient arka plan ve cam efekti
- **Hover Animasyonları**: Etkileşimli butonlar ve kartlar
- **Durum Göstergeleri**: Emoji ile görsel durum takibi
- **Bildirim Sistemi**: Canlı sayaçlar ve uyarılar

## 🚀 Kurulum

### 💻 Local Development

1. **Projeyi klonlayın**:
```bash
git clone https://github.com/veteroner/takas.git
cd swapzy
```

2. **Sanal ortam oluşturun**:
```bash
python -m venv venv
```

3. **Sanal ortamı aktifleştirin**:
```bash
# Windows
venv\Scripts\activate
# Linux/Mac
source venv/bin/activate
```

4. **Bağımlılıkları kurun**:
```bash
pip install -r requirements.txt
```

5. **Environment variables ayarlayın**:
```bash
# env-example.txt dosyasını .env olarak kopyalayın
copy env-example.txt .env  # Windows
cp env-example.txt .env    # Linux/Mac
```

6. **Veritabanını oluşturun**:
```bash
python manage.py migrate
```

7. **Demo verileri ekleyin** (isteğe bağlı):
```bash
python manage.py create_demo_data
python manage.py add_demo_images
```

8. **Sunucuyu başlatın**:
```bash
python manage.py runserver
```

9. **Tarayıcıda açın**: http://localhost:8000

### 🚀 Production Deployment

**Otomatik Deployment (Önerilen):**
```bash
# deploy.bat dosyasını çalıştırın
deploy.bat
```

Bu script size platform seçimi sunar:
1. **Railway** (Önerilen - WebSocket destekli)
2. **Render.com** (Ücretsiz PostgreSQL)
3. **Manual Git Push**
4. **Local Test Server**

### 🌐 Platform Detayları

#### Railway (Önerilen)
- ✅ WebSocket tam desteği
- ✅ Ücretsiz PostgreSQL
- ✅ $5/ay ücretsiz kredi
- ✅ Otomatik SSL
- ✅ Sleep mode yok

```bash
# Manuel Railway deployment:
npm install -g @railway/cli
railway login
railway init
railway add postgresql
railway up
```

#### Render.com
- ✅ Ücretsiz PostgreSQL
- ✅ Otomatik HTTPS
- ⚠️ 15 dakika inaktiflik sonrası sleep
- ⚠️ WebSocket sınırlı

#### Environment Variables (Production)
```bash
# Gerekli environment variables:
SECRET_KEY=your-secret-key-here
DEBUG=False
ALLOWED_HOSTS=yourdomain.com
DATABASE_URL=postgresql://user:pass@host:port/db
```

## 🧪 Demo Hesaplar

Platformu test etmek için hazır demo hesaplar:

| Kullanıcı | Şifre | Açıklama |
|-----------|-------|----------|
| `ayse` | `demo123` | 5 farklı kategori ürünü |
| `mehmet` | `demo123` | Oyun odaklı ürünler |
| `zehra` | `demo123` | Kitap ve oyuncaklar |
| `ali` | `demo123` | Çeşitli ürünler |
| `fatma` | `demo123` | Konsol ve abiye ürünler |

## 📁 Proje Yapısı

```
swapzy/
├── config/                 # Django ayarları
│   ├── settings.py        # Ana ayarlar
│   ├── urls.py           # URL yönlendirmeleri
│   └── wsgi.py           # WSGI yapılandırması
├── market/                # Ana uygulama
│   ├── models.py         # Veri modelleri
│   ├── views.py          # Görünüm fonksiyonları
│   ├── urls.py           # URL pattern'leri
│   ├── forms.py          # Form tanımları
│   ├── admin.py          # Admin panel
│   ├── templates/        # HTML şablonları
│   └── management/       # Özel Django komutları
├── media/                # Yüklenen dosyalar
├── db.sqlite3           # SQLite veritabanı
├── requirements.txt     # Python bağımlılıkları
└── README.md           # Bu dosya
```

## 💾 Veri Modelleri

### 👤 User (Django varsayılan)
- Kullanıcı kimlik bilgileri
- Profil bilgileri

### 📦 Item (Ürün)
- `title`: Ürün başlığı
- `description`: Açıklama
- `category`: Kategori (6 seçenek)
- `image`: Ürün fotoğrafı
- `owner`: Ürün sahibi
- `created_at`: Oluşturma tarihi

### 🔄 Trade (Takas)
- `requester`: Teklif veren kullanıcı
- `responder`: Ürün sahibi
- `offered_item`: Teklif edilen ürün
- `requested_item`: İstenen ürün
- `status`: Durum (beklemede/kabul/ret/iptal)
- `created_at`: Teklif tarihi

### 💬 Message (Mesaj)
- `trade`: Hangi takasa ait
- `sender`: Mesaj gönderen
- `content`: Mesaj içeriği
- `created_at`: Gönderim tarihi

### ❤️ Favorite (Favori)
- `user`: Kullanıcı
- `item`: Favori ürün
- `created_at`: Ekleme tarihi

## 🔧 Teknik Detaylar

- **Framework**: Django 5.2.5
- **Veritabanı**: SQLite (geliştirme), PostgreSQL önerilir (production)
- **Frontend**: Vanilla CSS3, responsive grid
- **Dosya Yönetimi**: Django FileField
- **Güvenlik**: CSRF koruması, SQL injection koruması
- **Resim İşleme**: Pillow kütüphanesi

## 🌐 URL Yapısı

```
/                          # Ana sayfa (ürün listesi)
/items/new/               # Yeni ürün ekleme
/items/<id>/              # Ürün detayı
/my-items/                # Benim ürünlerim
/favorites/               # Favorilerim
/trades/                  # Takaslarım
/trade/<id>/              # Takas detayı
/profile/<username>/      # Kullanıcı profili
/accounts/login/          # Giriş
/accounts/logout/         # Çıkış
/signup/                  # Kayıt
/admin/                   # Admin panel
```

## 🚦 Durum Kodları

### Takas Durumları
- `pending`: Beklemede (sarı ⏳)
- `accepted`: Kabul edildi (yeşil ✅)
- `rejected`: Reddedildi (kırmızı ❌)
- `cancelled`: İptal edildi (gri ⭕)

## 🔒 Güvenlik

- **CSRF Token**: Tüm formlarda CSRF koruması
- **Authentication**: Giriş gerektiren işlemler korumalı
- **Validation**: Form ve model validasyonları
- **Permissions**: Kullanıcı yetki kontrolleri
- **SQL Injection**: Django ORM ile korunmalı

## 🎯 Gelecek Özellikler

- [ ] E-posta bildirimleri
- [ ] Çoklu fotoğraf yükleme
- [ ] Şehir/konum bazlı filtreleme
- [ ] Çoklu ürün takası
- [ ] Rating/değerlendirme sistemi
- [ ] Real-time mesajlaşma (WebSocket)
- [ ] Mobil uygulama (React Native)

## 🤝 Katkıda Bulunma

1. Fork yapın
2. Feature branch oluşturun (`git checkout -b feature/yeni-ozellik`)
3. Commit yapın (`git commit -am 'Yeni özellik: Açıklama'`)
4. Push yapın (`git push origin feature/yeni-ozellik`)
5. Pull Request oluşturun

## 📄 Lisans

Bu proje MIT lisansı altında lisanslanmıştır.

## 👨‍💻 Geliştirici

Yapay Zeka destekli geliştirme ile oluşturulmuştur.

---

**Not**: Bu platform eğitim amaçlı geliştirilmiştir. Production ortamında kullanım için ek güvenlik önlemleri alınmalıdır.
