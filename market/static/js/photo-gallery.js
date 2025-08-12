/**
 * Professional Photo Gallery Component
 * Features: Touch/Swipe, Keyboard, Thumbnails, Fullscreen
 */

class PhotoGallery {
    constructor(containerId, images) {
        this.container = document.getElementById(containerId);
        this.images = images || [];
        this.currentIndex = 0;
        this.isFullscreen = false;
        
        if (this.images.length > 0) {
            this.init();
        }
    }
    
    init() {
        this.createHTML();
        this.attachEvents();
    }
    
    createHTML() {
        if (this.images.length === 1) {
            // Single image layout
            this.container.innerHTML = `
                <div class="photo-gallery single-photo">
                    <div class="main-image">
                        <img src="${this.images[0].url}" alt="${this.images[0].alt || ''}" onclick="photoGallery.openFullscreen(0)">
                        <div class="image-count">1 fotoğraf</div>
                    </div>
                </div>
            `;
        } else {
            // Multiple images layout
            this.container.innerHTML = `
                <div class="photo-gallery multi-photos">
                    <!-- Main Display -->
                    <div class="main-image">
                        <img id="mainImage" src="${this.images[0].url}" alt="${this.images[0].alt || ''}" onclick="photoGallery.openFullscreen()">
                        
                        <!-- Navigation Arrows -->
                        <button class="nav-btn prev-btn" onclick="photoGallery.prev()">‹</button>
                        <button class="nav-btn next-btn" onclick="photoGallery.next()">›</button>
                        
                        <!-- Image Counter -->
                        <div class="image-count">
                            <span id="currentNumber">1</span> / ${this.images.length}
                        </div>
                        
                        <!-- Fullscreen Button -->
                        <button class="fullscreen-btn" onclick="photoGallery.openFullscreen()">⛶</button>
                    </div>
                    
                    <!-- Thumbnails -->
                    <div class="thumbnails" id="thumbnails">
                        ${this.images.map((img, index) => `
                            <div class="thumbnail ${index === 0 ? 'active' : ''}" onclick="photoGallery.goTo(${index})">
                                <img src="${img.url}" alt="${img.alt || ''}">
                            </div>
                        `).join('')}
                    </div>
                </div>
                
                <!-- Fullscreen Modal -->
                <div class="fullscreen-modal" id="fullscreenModal" style="display: none;">
                    <div class="fullscreen-content">
                        <img id="fullscreenImage" src="" alt="">
                        <button class="close-fullscreen" onclick="photoGallery.closeFullscreen()">✕</button>
                        <button class="fullscreen-prev" onclick="photoGallery.prev()">‹</button>
                        <button class="fullscreen-next" onclick="photoGallery.next()">›</button>
                        <div class="fullscreen-counter">
                            <span id="fullscreenNumber">1</span> / ${this.images.length}
                        </div>
                    </div>
                </div>
            `;
        }
        
        this.addStyles();
    }
    
    addStyles() {
        const style = document.createElement('style');
        style.textContent = `
            .photo-gallery {
                margin: 20px 0;
            }
            
            .main-image {
                position: relative;
                width: 100%;
                aspect-ratio: 4/3;
                border-radius: 15px;
                overflow: hidden;
                background: #f7fafc;
                box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
            }
            
            .main-image img {
                width: 100%;
                height: 100%;
                object-fit: cover;
                cursor: pointer;
                transition: transform 0.3s ease;
            }
            
            .main-image img:hover {
                transform: scale(1.05);
            }
            
            .nav-btn {
                position: absolute;
                top: 50%;
                transform: translateY(-50%);
                background: rgba(0, 0, 0, 0.5);
                color: white;
                border: none;
                width: 40px;
                height: 40px;
                border-radius: 50%;
                cursor: pointer;
                font-size: 20px;
                display: flex;
                align-items: center;
                justify-content: center;
                opacity: 0;
                transition: all 0.3s ease;
                backdrop-filter: blur(10px);
            }
            
            .photo-gallery:hover .nav-btn {
                opacity: 1;
            }
            
            .nav-btn:hover {
                background: rgba(0, 0, 0, 0.7);
                transform: translateY(-50%) scale(1.1);
            }
            
            .prev-btn {
                left: 15px;
            }
            
            .next-btn {
                right: 15px;
            }
            
            .image-count {
                position: absolute;
                bottom: 15px;
                left: 15px;
                background: rgba(0, 0, 0, 0.7);
                color: white;
                padding: 6px 12px;
                border-radius: 20px;
                font-size: 14px;
                backdrop-filter: blur(10px);
            }
            
            .fullscreen-btn {
                position: absolute;
                top: 15px;
                right: 15px;
                background: rgba(0, 0, 0, 0.5);
                color: white;
                border: none;
                width: 35px;
                height: 35px;
                border-radius: 8px;
                cursor: pointer;
                font-size: 16px;
                opacity: 0;
                transition: all 0.3s ease;
                backdrop-filter: blur(10px);
            }
            
            .photo-gallery:hover .fullscreen-btn {
                opacity: 1;
            }
            
            .thumbnails {
                display: flex;
                gap: 10px;
                margin-top: 15px;
                overflow-x: auto;
                padding: 10px 0;
            }
            
            .thumbnail {
                flex-shrink: 0;
                width: 80px;
                height: 60px;
                border-radius: 8px;
                overflow: hidden;
                cursor: pointer;
                opacity: 0.6;
                transition: all 0.3s ease;
                border: 2px solid transparent;
            }
            
            .thumbnail.active {
                opacity: 1;
                border-color: #667eea;
                box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3);
            }
            
            .thumbnail img {
                width: 100%;
                height: 100%;
                object-fit: cover;
            }
            
            .thumbnail:hover {
                opacity: 1;
                transform: scale(1.05);
            }
            
            /* Fullscreen Modal */
            .fullscreen-modal {
                position: fixed;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                background: rgba(0, 0, 0, 0.95);
                z-index: 10000;
                display: flex;
                align-items: center;
                justify-content: center;
            }
            
            .fullscreen-content {
                position: relative;
                max-width: 90%;
                max-height: 90%;
            }
            
            .fullscreen-content img {
                max-width: 100%;
                max-height: 100%;
                object-fit: contain;
            }
            
            .close-fullscreen {
                position: absolute;
                top: 20px;
                right: 20px;
                background: rgba(255, 255, 255, 0.2);
                color: white;
                border: none;
                width: 40px;
                height: 40px;
                border-radius: 50%;
                cursor: pointer;
                font-size: 20px;
                backdrop-filter: blur(10px);
            }
            
            .fullscreen-prev, .fullscreen-next {
                position: absolute;
                top: 50%;
                transform: translateY(-50%);
                background: rgba(255, 255, 255, 0.2);
                color: white;
                border: none;
                width: 50px;
                height: 50px;
                border-radius: 50%;
                cursor: pointer;
                font-size: 24px;
                backdrop-filter: blur(10px);
            }
            
            .fullscreen-prev {
                left: 20px;
            }
            
            .fullscreen-next {
                right: 20px;
            }
            
            .fullscreen-counter {
                position: absolute;
                bottom: 20px;
                left: 50%;
                transform: translateX(-50%);
                background: rgba(255, 255, 255, 0.2);
                color: white;
                padding: 8px 16px;
                border-radius: 20px;
                backdrop-filter: blur(10px);
            }
            
            /* Single Photo Styles */
            .single-photo .main-image {
                cursor: pointer;
            }
            
            .single-photo .image-count {
                background: rgba(102, 126, 234, 0.8);
            }
            
            /* Mobile Responsive */
            @media (max-width: 768px) {
                .main-image {
                    aspect-ratio: 1;
                }
                
                .nav-btn {
                    width: 35px;
                    height: 35px;
                    font-size: 18px;
                    opacity: 1;
                }
                
                .thumbnail {
                    width: 60px;
                    height: 45px;
                }
                
                .fullscreen-prev, .fullscreen-next {
                    width: 45px;
                    height: 45px;
                    font-size: 20px;
                }
            }
        `;
        document.head.appendChild(style);
    }
    
    attachEvents() {
        // Keyboard navigation
        document.addEventListener('keydown', (e) => {
            if (this.isFullscreen) {
                switch(e.key) {
                    case 'ArrowLeft':
                        this.prev();
                        break;
                    case 'ArrowRight':
                        this.next();
                        break;
                    case 'Escape':
                        this.closeFullscreen();
                        break;
                }
            }
        });
        
        // Touch/Swipe support
        let startX = 0;
        let endX = 0;
        
        this.container.addEventListener('touchstart', (e) => {
            startX = e.touches[0].clientX;
        });
        
        this.container.addEventListener('touchend', (e) => {
            endX = e.changedTouches[0].clientX;
            const diff = startX - endX;
            
            if (Math.abs(diff) > 50) { // Minimum swipe distance
                if (diff > 0) {
                    this.next();
                } else {
                    this.prev();
                }
            }
        });
    }
    
    goTo(index) {
        if (index < 0 || index >= this.images.length) return;
        
        this.currentIndex = index;
        this.updateDisplay();
    }
    
    next() {
        this.goTo((this.currentIndex + 1) % this.images.length);
    }
    
    prev() {
        this.goTo((this.currentIndex - 1 + this.images.length) % this.images.length);
    }
    
    updateDisplay() {
        const mainImage = document.getElementById('mainImage');
        const currentNumber = document.getElementById('currentNumber');
        const fullscreenImage = document.getElementById('fullscreenImage');
        const fullscreenNumber = document.getElementById('fullscreenNumber');
        
        if (mainImage) {
            mainImage.src = this.images[this.currentIndex].url;
            mainImage.alt = this.images[this.currentIndex].alt || '';
        }
        
        if (currentNumber) {
            currentNumber.textContent = this.currentIndex + 1;
        }
        
        if (fullscreenImage) {
            fullscreenImage.src = this.images[this.currentIndex].url;
            fullscreenImage.alt = this.images[this.currentIndex].alt || '';
        }
        
        if (fullscreenNumber) {
            fullscreenNumber.textContent = this.currentIndex + 1;
        }
        
        // Update thumbnails
        document.querySelectorAll('.thumbnail').forEach((thumb, index) => {
            thumb.classList.toggle('active', index === this.currentIndex);
        });
    }
    
    openFullscreen(index = null) {
        if (index !== null) {
            this.goTo(index);
        }
        
        const modal = document.getElementById('fullscreenModal');
        if (modal) {
            modal.style.display = 'flex';
            this.isFullscreen = true;
            document.body.style.overflow = 'hidden';
            this.updateDisplay();
        }
    }
    
    closeFullscreen() {
        const modal = document.getElementById('fullscreenModal');
        if (modal) {
            modal.style.display = 'none';
            this.isFullscreen = false;
            document.body.style.overflow = '';
        }
    }
}

// Global instance for template access
let photoGallery;
