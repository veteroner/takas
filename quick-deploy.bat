@echo off
chcp 65001 >nul
echo =====================================
echo ⚡ SWAPZY QUICK DEPLOY TO RAILWAY ⚡
echo =====================================
echo.

:: Railway CLI kontrol et
railway --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Railway CLI yok. Node.js kurulu mu?
    echo 💡 Kurulum: npm install -g @railway/cli
    pause
    exit /b 1
)

:: Git kontrol et
git --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Git yüklü değil!
    pause
    exit /b 1
)

echo ✅ System OK
echo.

:: Git setup
if not exist ".git" (
    echo 📦 Git init...
    git init
    git add .
    git commit -m "Initial: Swapzy takas platformu"
)

echo 🔐 Railway login...
railway login

echo 🛠️ Railway project...
railway init

echo 🗄️ PostgreSQL ekleniyor...
railway add postgresql

echo ⚙️ Environment variables...
railway variables set SECRET_KEY=django-swapzy-%RANDOM%-%RANDOM%
railway variables set DEBUG=False
railway variables set ALLOWED_HOSTS=*.railway.app

echo 🚀 Deploying...
railway up

if errorlevel 0 (
    echo.
    echo ✅ BAŞARILI! Swapzy Railway'de live!
    echo 🌐 URL'inizi almak için: railway status
    echo.
    railway status
) else (
    echo ❌ Deploy hatası! Manual kontrol edin.
)

pause

