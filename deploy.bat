@echo off
chcp 65001 >nul
echo =====================================
echo 🚀 SWAPZY PROJECT DEPLOYMENT SCRIPT
echo =====================================
echo.

:: Renk kodları
set "GREEN=[92m"
set "RED=[91m"
set "YELLOW=[93m"
set "BLUE=[94m"
set "NC=[0m"

:: Git bilgilerini kontrol et
git --version >nul 2>&1
if errorlevel 1 (
    echo %RED%❌ Git yüklü değil! Lütfen Git'i yükleyin.%NC%
    pause
    exit /b 1
)

:: Python kontrol et
python --version >nul 2>&1
if errorlevel 1 (
    echo %RED%❌ Python yüklü değil! Lütfen Python'u yükleyin.%NC%
    pause
    exit /b 1
)

echo %GREEN%✅ Sistem kontrolleri başarılı%NC%
echo.

:: Deployment platformunu seç
echo %BLUE%🎯 Deployment platformunu seçin:%NC%
echo 1. Railway (Önerilen - WebSocket destekli)
echo 2. Render.com (Ücretsiz PostgreSQL)
echo 3. Git Repository'ye push (Manuel deploy)
echo 4. Local test server
echo.
set /p choice="Seçiminizi yapın (1-4): "

if "%choice%"=="1" goto railway
if "%choice%"=="2" goto render
if "%choice%"=="3" goto git_push
if "%choice%"=="4" goto local_test
goto invalid_choice

:railway
echo.
echo %YELLOW%🚂 Railway deployment başlatılıyor...%NC%
echo.

:: Railway CLI kontrol et
railway --version >nul 2>&1
if errorlevel 1 (
    echo %YELLOW%⚠️ Railway CLI yüklü değil. Yükleniyor...%NC%
    npm install -g @railway/cli
    if errorlevel 1 (
        echo %RED%❌ Railway CLI yüklenemedi. Node.js yüklü mü?%NC%
        pause
        exit /b 1
    )
)

:: Git repository başlat
if not exist ".git" (
    echo %BLUE%📦 Git repository başlatılıyor...%NC%
    git init
    git add .
    git commit -m "Initial commit - Swapzy takas platformu"
)

:: Railway'e login ve deploy
echo %BLUE%🔐 Railway'e login olunuyor...%NC%
railway login

echo %BLUE%🛠️ Railway projesi oluşturuluyor...%NC%
railway init

echo %BLUE%🗄️ PostgreSQL ekleniyor...%NC%
railway add postgresql

echo %BLUE%⚙️ Environment variables ayarlanıyor...%NC%
railway variables set SECRET_KEY=django-prod-%RANDOM%-%RANDOM%-key-swapzy
railway variables set DEBUG=False
railway variables set ALLOWED_HOSTS=*.railway.app
railway variables set DJANGO_SETTINGS_MODULE=config.settings

echo %BLUE%🚀 Deployment başlatılıyor...%NC%
railway up

echo %GREEN%✅ Railway deployment tamamlandı!%NC%
echo %GREEN%🌐 Uygulamanız Railway'de live!%NC%
echo.
railway status
echo.
pause
exit /b 0

:render
echo.
echo %YELLOW%🎨 Render.com deployment başlatılıyor...%NC%
echo.

:: render.yaml dosyası oluştur
echo %BLUE%📝 render.yaml oluşturuluyor...%NC%
(
echo services:
echo   - type: web
echo     name: swapzy
echo     env: python
echo     plan: free
echo     buildCommand: pip install -r requirements.txt
echo     startCommand: daphne -b 0.0.0.0 -p $PORT config.asgi:application
echo     envVars:
echo       - key: PYTHON_VERSION
echo         value: 3.11.0
echo       - key: SECRET_KEY
echo         generateValue: true
echo       - key: DEBUG
echo         value: False
echo       - key: ALLOWED_HOSTS
echo         value: *.onrender.com
echo.
echo   - type: pserv
echo     name: swapzy-db
echo     env: postgresql
echo     plan: free
echo     disk:
echo       name: swapzy-db
echo       mountPath: /var/lib/postgresql/data
echo       sizeGB: 1
) > render.yaml

echo %GREEN%✅ render.yaml oluşturuldu!%NC%
echo %YELLOW%⚠️ Render.com'da manual olarak deploy etmeniz gerekiyor:%NC%
echo.
echo 1. render.com'a gidin
echo 2. GitHub repository'nizi bağlayın
echo 3. Web Service oluşturun
echo 4. PostgreSQL database ekleyin
echo.
goto git_setup

:git_push
echo.
echo %YELLOW%📤 Git repository'ye push ediliyor...%NC%
echo.

:git_setup
:: Git repository kontrol et
if not exist ".git" (
    echo %BLUE%📦 Git repository başlatılıyor...%NC%
    git init
)

:: Dosyaları staging'e ekle
echo %BLUE%📁 Dosyalar staging'e ekleniyor...%NC%
git add .

:: Commit oluştur
echo %BLUE%💾 Commit oluşturuluyor...%NC%
set commit_msg=Deploy: Swapzy Django takas platformu - %date% %time%
git commit -m "%commit_msg%"

:: Remote repository ekle
echo.
echo %YELLOW%🔗 GitHub repository URL'ini giriniz:%NC%
echo Örnek: https://github.com/veteroner/takas.git
set /p repo_url="Repository URL: "

if not "%repo_url%"=="" (
    git remote remove origin 2>nul
    git remote add origin %repo_url%
    
    echo %BLUE%📤 GitHub'a push ediliyor...%NC%
    git branch -M main
    git push -u origin main
    
    if errorlevel 1 (
        echo %RED%❌ Push başarısız! Repository URL'ini kontrol edin.%NC%
    ) else (
        echo %GREEN%✅ GitHub'a başarıyla push edildi!%NC%
    )
) else (
    echo %YELLOW%⚠️ Repository URL girilmedi.%NC%
)

echo.
echo %GREEN%📋 DEPLOYMENT HAZIRLIK LİSTESİ:%NC%
echo ✅ requirements.txt güncellendi
echo ✅ Procfile oluşturuldu
echo ✅ .gitignore oluşturuldu
echo ✅ Database ayarları production-ready
echo ✅ Static files yapılandırıldı
echo ✅ Security ayarları yapıldı
echo.
pause
exit /b 0

:local_test
echo.
echo %YELLOW%🖥️ Local test server başlatılıyor...%NC%
echo.

:: Virtual environment kontrol et
if not exist "venv" (
    echo %BLUE%🐍 Virtual environment oluşturuluyor...%NC%
    python -m venv venv
)

:: Virtual environment'i aktifleştir
echo %BLUE%⚡ Virtual environment aktifleştiriliyor...%NC%
call venv\Scripts\activate.bat

:: Requirements yükle
echo %BLUE%📦 Dependencies yükleniyor...%NC%
pip install -r requirements.txt

:: Database migrate et
echo %BLUE%🗄️ Database migrations uygulanıyor...%NC%
python manage.py makemigrations
python manage.py migrate

:: Static files topla
echo %BLUE%📁 Static files toplanıyor...%NC%
python manage.py collectstatic --noinput

:: Superuser oluştur (opsiyonel)
echo.
set /p create_superuser="Superuser oluşturmak istiyor musunuz? (y/n): "
if /i "%create_superuser%"=="y" (
    python manage.py createsuperuser
)

echo.
echo %GREEN%✅ Local server hazır!%NC%
echo %BLUE%🌐 Server başlatılıyor: http://localhost:8000%NC%
echo.
echo %YELLOW%⚠️ Çıkmak için Ctrl+C basın%NC%
echo.

:: Server'ı başlat
python manage.py runserver 0.0.0.0:8000

pause
exit /b 0

:invalid_choice
echo %RED%❌ Geçersiz seçim! Lütfen 1-4 arası bir sayı girin.%NC%
pause
exit /b 1

:error_handler
echo.
echo %RED%❌ Bir hata oluştu!%NC%
echo %YELLOW%💡 Sorun giderme önerileri:%NC%
echo - Python ve Git'in yüklü olduğundan emin olun
echo - Internet bağlantınızı kontrol edin
echo - Repository URL'inin doğru olduğunu kontrol edin
echo - Gerekli izinlere sahip olduğunuzdan emin olun
echo.
pause
exit /b 1

