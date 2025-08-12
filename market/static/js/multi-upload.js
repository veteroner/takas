/**
 * 📁 Multi-Upload JavaScript Module
 * Advanced drag & drop file upload system
 */

class MultiUpload {
    constructor(containerId, options = {}) {
        this.container = document.getElementById(containerId);
        this.options = {
            maxFiles: options.maxFiles || 5,
            maxFileSize: options.maxFileSize || 10 * 1024 * 1024, // 10MB
            allowedTypes: options.allowedTypes || ['image/jpeg', 'image/png', 'image/gif'],
            uploadUrl: options.uploadUrl || '/api/upload-item-image/',
            ...options
        };
        
        this.files = [];
        this.uploadedFiles = [];
        
        this.init();
    }
    
    init() {
        this.createUploadArea();
        this.bindEvents();
    }
    
    createUploadArea() {
        if (!this.container) return;
        
        this.container.innerHTML = `
            <div class="multi-upload-area" id="upload-area">
                <div class="upload-drop-zone">
                    <div class="upload-icon">📁</div>
                    <div class="upload-text">
                        <p><strong>Dosyaları buraya sürükleyin</strong></p>
                        <p>veya <button type="button" class="upload-btn">dosya seçin</button></p>
                        <small>Maksimum ${this.options.maxFiles} dosya, her biri ${this.formatFileSize(this.options.maxFileSize)} boyutunda</small>
                    </div>
                </div>
                <input type="file" id="file-input" multiple accept="${this.options.allowedTypes.join(',')}" style="display: none;">
                <div class="file-preview-container" id="file-preview"></div>
                <div class="upload-progress" id="upload-progress" style="display: none;">
                    <div class="progress-bar">
                        <div class="progress-fill"></div>
                    </div>
                    <div class="progress-text">Yükleniyor...</div>
                </div>
            </div>
        `;
    }
    
    bindEvents() {
        const dropZone = this.container.querySelector('.upload-drop-zone');
        const fileInput = this.container.querySelector('#file-input');
        const uploadBtn = this.container.querySelector('.upload-btn');
        
        // Drag & Drop events
        dropZone.addEventListener('dragover', (e) => {
            e.preventDefault();
            dropZone.classList.add('drag-over');
        });
        
        dropZone.addEventListener('dragleave', () => {
            dropZone.classList.remove('drag-over');
        });
        
        dropZone.addEventListener('drop', (e) => {
            e.preventDefault();
            dropZone.classList.remove('drag-over');
            this.handleFiles(e.dataTransfer.files);
        });
        
        // File input events
        uploadBtn.addEventListener('click', () => {
            fileInput.click();
        });
        
        fileInput.addEventListener('change', (e) => {
            this.handleFiles(e.target.files);
        });
    }
    
    handleFiles(fileList) {
        const files = Array.from(fileList);
        
        // Validate file count
        if (this.files.length + files.length > this.options.maxFiles) {
            this.showError(`Maksimum ${this.options.maxFiles} dosya yükleyebilirsiniz.`);
            return;
        }
        
        // Validate and add files
        files.forEach(file => {
            if (this.validateFile(file)) {
                this.addFile(file);
            }
        });
        
        this.updatePreview();
    }
    
    validateFile(file) {
        // Check file type
        if (!this.options.allowedTypes.includes(file.type)) {
            this.showError(`${file.name}: Desteklenmeyen dosya türü.`);
            return false;
        }
        
        // Check file size
        if (file.size > this.options.maxFileSize) {
            this.showError(`${file.name}: Dosya boyutu çok büyük (Max: ${this.formatFileSize(this.options.maxFileSize)}).`);
            return false;
        }
        
        return true;
    }
    
    addFile(file) {
        const fileObj = {
            id: Date.now() + Math.random(),
            file: file,
            name: file.name,
            size: file.size,
            type: file.type,
            status: 'pending'
        };
        
        this.files.push(fileObj);
    }
    
    removeFile(fileId) {
        this.files = this.files.filter(f => f.id !== fileId);
        this.updatePreview();
    }
    
    updatePreview() {
        const previewContainer = this.container.querySelector('#file-preview');
        
        if (this.files.length === 0) {
            previewContainer.innerHTML = '';
            return;
        }
        
        const previewHTML = this.files.map(file => `
            <div class="file-preview-item" data-file-id="${file.id}">
                <div class="file-info">
                    <div class="file-name">${file.name}</div>
                    <div class="file-size">${this.formatFileSize(file.size)}</div>
                    <div class="file-status status-${file.status}">${this.getStatusText(file.status)}</div>
                </div>
                <div class="file-actions">
                    <button type="button" class="remove-btn" onclick="multiUpload.removeFile(${file.id})">❌</button>
                </div>
            </div>
        `).join('');
        
        previewContainer.innerHTML = previewHTML;
    }
    
    async uploadFiles() {
        if (this.files.length === 0) {
            this.showError('Yüklenecek dosya seçilmedi.');
            return;
        }
        
        const progressContainer = this.container.querySelector('#upload-progress');
        const progressFill = progressContainer.querySelector('.progress-fill');
        const progressText = progressContainer.querySelector('.progress-text');
        
        progressContainer.style.display = 'block';
        
        let uploadedCount = 0;
        const totalFiles = this.files.length;
        
        for (const fileObj of this.files) {
            try {
                fileObj.status = 'uploading';
                this.updatePreview();
                
                const result = await this.uploadSingleFile(fileObj);
                
                if (result.success) {
                    fileObj.status = 'completed';
                    this.uploadedFiles.push(result.data);
                } else {
                    fileObj.status = 'error';
                    this.showError(`${fileObj.name}: ${result.error}`);
                }
                
                uploadedCount++;
                const progress = (uploadedCount / totalFiles) * 100;
                progressFill.style.width = `${progress}%`;
                progressText.textContent = `${uploadedCount}/${totalFiles} dosya yüklendi`;
                
            } catch (error) {
                fileObj.status = 'error';
                this.showError(`${fileObj.name}: Yükleme hatası`);
            }
            
            this.updatePreview();
        }
        
        progressContainer.style.display = 'none';
        
        if (this.options.onComplete) {
            this.options.onComplete(this.uploadedFiles);
        }
    }
    
    async uploadSingleFile(fileObj) {
        const formData = new FormData();
        formData.append('image', fileObj.file);
        formData.append('csrfmiddlewaretoken', this.getCSRFToken());
        
        const response = await fetch(this.options.uploadUrl, {
            method: 'POST',
            body: formData,
            headers: {
                'X-Requested-With': 'XMLHttpRequest'
            }
        });
        
        return await response.json();
    }
    
    getCSRFToken() {
        const cookieValue = document.cookie
            .split('; ')
            .find(row => row.startsWith('csrftoken='))
            ?.split('=')[1];
        return cookieValue || '';
    }
    
    formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }
    
    getStatusText(status) {
        const statusMap = {
            'pending': 'Bekliyor',
            'uploading': 'Yükleniyor...',
            'completed': 'Tamamlandı',
            'error': 'Hata'
        };
        return statusMap[status] || status;
    }
    
    showError(message) {
        // Create or update error message
        let errorDiv = this.container.querySelector('.upload-error');
        if (!errorDiv) {
            errorDiv = document.createElement('div');
            errorDiv.className = 'upload-error';
            this.container.appendChild(errorDiv);
        }
        
        errorDiv.innerHTML = `<p>❌ ${message}</p>`;
        
        // Auto-hide after 5 seconds
        setTimeout(() => {
            if (errorDiv) {
                errorDiv.remove();
            }
        }, 5000);
    }
    
    reset() {
        this.files = [];
        this.uploadedFiles = [];
        this.updatePreview();
        
        const progressContainer = this.container.querySelector('#upload-progress');
        if (progressContainer) {
            progressContainer.style.display = 'none';
        }
    }
}

// CSS Styles (can be included in separate CSS file)
const multiUploadStyles = `
<style>
.multi-upload-area {
    border: 2px dashed #ddd;
    border-radius: 8px;
    padding: 20px;
    background: #fafafa;
    margin: 20px 0;
}

.upload-drop-zone {
    text-align: center;
    padding: 40px 20px;
    cursor: pointer;
    transition: all 0.3s ease;
}

.upload-drop-zone:hover,
.upload-drop-zone.drag-over {
    border-color: #007cba;
    background: #f0f8ff;
}

.upload-icon {
    font-size: 48px;
    margin-bottom: 20px;
}

.upload-btn {
    background: #007cba;
    color: white;
    border: none;
    padding: 8px 16px;
    border-radius: 4px;
    cursor: pointer;
}

.upload-btn:hover {
    background: #005a87;
}

.file-preview-container {
    margin-top: 20px;
}

.file-preview-item {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 10px;
    border: 1px solid #ddd;
    border-radius: 4px;
    margin-bottom: 8px;
    background: white;
}

.file-info {
    flex: 1;
}

.file-name {
    font-weight: bold;
    margin-bottom: 4px;
}

.file-size {
    font-size: 12px;
    color: #666;
}

.file-status {
    font-size: 12px;
    margin-top: 4px;
}

.status-pending { color: #666; }
.status-uploading { color: #ff9800; }
.status-completed { color: #4caf50; }
.status-error { color: #f44336; }

.remove-btn {
    background: none;
    border: none;
    cursor: pointer;
    font-size: 16px;
}

.upload-progress {
    margin-top: 20px;
    text-align: center;
}

.progress-bar {
    width: 100%;
    height: 20px;
    background: #f0f0f0;
    border-radius: 10px;
    overflow: hidden;
    margin-bottom: 10px;
}

.progress-fill {
    height: 100%;
    background: linear-gradient(90deg, #4caf50, #45a049);
    width: 0%;
    transition: width 0.3s ease;
}

.upload-error {
    margin-top: 10px;
    padding: 10px;
    background: #ffebee;
    border: 1px solid #ffcdd2;
    border-radius: 4px;
    color: #c62828;
}
</style>
`;

// Add styles to document if not already present
if (!document.querySelector('#multi-upload-styles')) {
    const styleElement = document.createElement('div');
    styleElement.id = 'multi-upload-styles';
    styleElement.innerHTML = multiUploadStyles;
    document.head.appendChild(styleElement);
}

// Global instance for easy access
let multiUpload = null;

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    const uploadContainer = document.getElementById('multi-upload-container');
    if (uploadContainer) {
        multiUpload = new MultiUpload('multi-upload-container', {
            maxFiles: 5,
            maxFileSize: 10 * 1024 * 1024, // 10MB
            allowedTypes: ['image/jpeg', 'image/png', 'image/gif', 'image/webp'],
            uploadUrl: '/api/upload-item-image/',
            onComplete: function(uploadedFiles) {
                console.log('Upload completed:', uploadedFiles);
                // Handle completion (e.g., update form, show success message)
            }
        });
    }
});

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = MultiUpload;
}