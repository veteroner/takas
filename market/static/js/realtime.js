/**
 * 🔴 Real-time JavaScript Module
 * WebSocket connections, notifications, and live updates
 */

class RealtimeManager {
    constructor(options = {}) {
        this.options = {
            websocketUrl: options.websocketUrl || this.getWebSocketUrl(),
            reconnectInterval: options.reconnectInterval || 5000,
            maxReconnectAttempts: options.maxReconnectAttempts || 10,
            ...options
        };
        
        this.socket = null;
        this.reconnectAttempts = 0;
        this.isConnected = false;
        this.messageHandlers = new Map();
        this.reconnectTimer = null;
        
        this.init();
    }
    
    init() {
        this.connect();
        this.setupUI();
        this.bindEvents();
    }
    
    getWebSocketUrl() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const host = window.location.host;
        return `${protocol}//${host}/ws/notifications/`;
    }
    
    connect() {
        try {
            this.socket = new WebSocket(this.options.websocketUrl);
            
            this.socket.onopen = (event) => {
                console.log('🔴 WebSocket connected');
                this.isConnected = true;
                this.reconnectAttempts = 0;
                this.updateConnectionStatus('connected');
                this.onConnected(event);
            };
            
            this.socket.onmessage = (event) => {
                const data = JSON.parse(event.data);
                this.handleMessage(data);
            };
            
            this.socket.onclose = (event) => {
                console.log('🔴 WebSocket disconnected');
                this.isConnected = false;
                this.updateConnectionStatus('disconnected');
                this.onDisconnected(event);
                this.scheduleReconnect();
            };
            
            this.socket.onerror = (error) => {
                console.error('🔴 WebSocket error:', error);
                this.updateConnectionStatus('error');
                this.onError(error);
            };
            
        } catch (error) {
            console.error('🔴 Failed to create WebSocket:', error);
            this.scheduleReconnect();
        }
    }
    
    scheduleReconnect() {
        if (this.reconnectAttempts >= this.options.maxReconnectAttempts) {
            console.error('🔴 Max reconnection attempts reached');
            this.updateConnectionStatus('failed');
            return;
        }
        
        this.reconnectAttempts++;
        console.log(`🔴 Reconnecting in ${this.options.reconnectInterval}ms (attempt ${this.reconnectAttempts})`);
        
        this.reconnectTimer = setTimeout(() => {
            this.connect();
        }, this.options.reconnectInterval);
    }
    
    disconnect() {
        if (this.reconnectTimer) {
            clearTimeout(this.reconnectTimer);
            this.reconnectTimer = null;
        }
        
        if (this.socket) {
            this.socket.close();
            this.socket = null;
        }
        
        this.isConnected = false;
        this.updateConnectionStatus('disconnected');
    }
    
    send(message) {
        if (this.isConnected && this.socket) {
            this.socket.send(JSON.stringify(message));
            return true;
        } else {
            console.warn('🔴 Cannot send message: WebSocket not connected');
            return false;
        }
    }
    
    handleMessage(data) {
        const { type, payload } = data;
        
        // Call registered handlers
        if (this.messageHandlers.has(type)) {
            const handlers = this.messageHandlers.get(type);
            handlers.forEach(handler => {
                try {
                    handler(payload);
                } catch (error) {
                    console.error(`🔴 Error in message handler for ${type}:`, error);
                }
            });
        }
        
        // Built-in message handling
        switch (type) {
            case 'notification':
                this.handleNotification(payload);
                break;
            case 'activity_feed':
                this.handleActivityFeed(payload);
                break;
            case 'user_status':
                this.handleUserStatus(payload);
                break;
            case 'system_message':
                this.handleSystemMessage(payload);
                break;
            default:
                console.log('🔴 Unhandled message type:', type, payload);
        }
    }
    
    on(messageType, handler) {
        if (!this.messageHandlers.has(messageType)) {
            this.messageHandlers.set(messageType, []);
        }
        this.messageHandlers.get(messageType).push(handler);
    }
    
    off(messageType, handler) {
        if (this.messageHandlers.has(messageType)) {
            const handlers = this.messageHandlers.get(messageType);
            const index = handlers.indexOf(handler);
            if (index > -1) {
                handlers.splice(index, 1);
            }
        }
    }
    
    handleNotification(notification) {
        this.showNotification(notification);
        this.updateNotificationBadge();
        this.addToNotificationList(notification);
    }
    
    handleActivityFeed(activity) {
        this.addToActivityFeed(activity);
    }
    
    handleUserStatus(userStatus) {
        this.updateUserStatus(userStatus);
    }
    
    handleSystemMessage(message) {
        this.showSystemMessage(message);
    }
    
    showNotification(notification) {
        // Browser notification if permission granted
        if (Notification.permission === 'granted') {
            new Notification(notification.title, {
                body: notification.message,
                icon: '/static/img/logo.png',
                tag: notification.id
            });
        }
        
        // Toast notification
        this.showToast(notification);
    }
    
    showToast(notification) {
        const toast = document.createElement('div');
        toast.className = 'realtime-toast';
        toast.innerHTML = `
            <div class="toast-content">
                <div class="toast-icon">${this.getNotificationIcon(notification.type)}</div>
                <div class="toast-text">
                    <div class="toast-title">${notification.title}</div>
                    <div class="toast-message">${notification.message}</div>
                </div>
                <button class="toast-close" onclick="this.parentElement.parentElement.remove()">×</button>
            </div>
        `;
        
        document.body.appendChild(toast);
        
        // Animate in
        setTimeout(() => toast.classList.add('show'), 100);
        
        // Auto remove after 5 seconds
        setTimeout(() => {
            toast.classList.remove('show');
            setTimeout(() => toast.remove(), 300);
        }, 5000);
    }
    
    getNotificationIcon(type) {
        const icons = {
            'trade_request': '🤝',
            'trade_accepted': '✅',
            'trade_declined': '❌',
            'new_message': '💬',
            'new_favorite': '❤️',
            'item_viewed': '👁️',
            'system': '⚙️',
            'warning': '⚠️',
            'info': 'ℹ️'
        };
        return icons[type] || '🔔';
    }
    
    updateNotificationBadge() {
        const badge = document.querySelector('.notification-badge');
        if (badge) {
            const currentCount = parseInt(badge.textContent) || 0;
            badge.textContent = currentCount + 1;
            badge.style.display = 'inline';
        }
    }
    
    addToNotificationList(notification) {
        const notificationList = document.querySelector('#notification-list');
        if (notificationList) {
            const notificationItem = document.createElement('div');
            notificationItem.className = 'notification-item unread';
            notificationItem.innerHTML = `
                <div class="notification-icon">${this.getNotificationIcon(notification.type)}</div>
                <div class="notification-content">
                    <div class="notification-title">${notification.title}</div>
                    <div class="notification-message">${notification.message}</div>
                    <div class="notification-time">${this.formatTime(notification.timestamp)}</div>
                </div>
            `;
            
            notificationList.insertBefore(notificationItem, notificationList.firstChild);
            
            // Keep only last 50 notifications
            const items = notificationList.querySelectorAll('.notification-item');
            if (items.length > 50) {
                items[items.length - 1].remove();
            }
        }
    }
    
    addToActivityFeed(activity) {
        const activityFeed = document.querySelector('#activity-feed');
        if (activityFeed) {
            const activityItem = document.createElement('div');
            activityItem.className = 'activity-item';
            activityItem.innerHTML = `
                <div class="activity-content">
                    <div class="activity-text">${activity.message}</div>
                    <div class="activity-time">${this.formatTime(activity.timestamp)}</div>
                </div>
            `;
            
            activityFeed.insertBefore(activityItem, activityFeed.firstChild);
            
            // Keep only last 20 activities
            const items = activityFeed.querySelectorAll('.activity-item');
            if (items.length > 20) {
                items[items.length - 1].remove();
            }
        }
    }
    
    updateUserStatus(userStatus) {
        const onlineUsers = document.querySelector('#online-users');
        if (onlineUsers) {
            const userElement = onlineUsers.querySelector(`[data-user-id="${userStatus.user_id}"]`);
            
            if (userStatus.is_online) {
                if (!userElement) {
                    // Add new online user
                    const userDiv = document.createElement('div');
                    userDiv.className = 'online-user';
                    userDiv.setAttribute('data-user-id', userStatus.user_id);
                    userDiv.innerHTML = `
                        <div class="user-avatar">👤</div>
                        <div class="user-name">${userStatus.username}</div>
                        <div class="user-status online">🟢</div>
                    `;
                    onlineUsers.appendChild(userDiv);
                }
            } else {
                if (userElement) {
                    // Remove offline user
                    userElement.remove();
                }
            }
        }
    }
    
    showSystemMessage(message) {
        console.log('🔴 System message:', message);
        
        // Show as toast with system styling
        this.showToast({
            title: 'Sistem Mesajı',
            message: message.text,
            type: 'system'
        });
    }
    
    setupUI() {
        // Add connection status indicator
        if (!document.querySelector('#connection-status')) {
            const statusDiv = document.createElement('div');
            statusDiv.id = 'connection-status';
            statusDiv.className = 'connection-status';
            statusDiv.innerHTML = '<span class="status-indicator"></span> <span class="status-text">Bağlanıyor...</span>';
            document.body.appendChild(statusDiv);
        }
        
        // Request notification permission
        if ('Notification' in window && Notification.permission === 'default') {
            Notification.requestPermission();
        }
    }
    
    updateConnectionStatus(status) {
        const statusElement = document.querySelector('#connection-status');
        if (statusElement) {
            const indicator = statusElement.querySelector('.status-indicator');
            const text = statusElement.querySelector('.status-text');
            
            switch (status) {
                case 'connected':
                    indicator.className = 'status-indicator connected';
                    text.textContent = 'Bağlandı';
                    statusElement.style.display = 'none'; // Hide when connected
                    break;
                case 'disconnected':
                    indicator.className = 'status-indicator disconnected';
                    text.textContent = 'Bağlantı kesildi';
                    statusElement.style.display = 'block';
                    break;
                case 'error':
                    indicator.className = 'status-indicator error';
                    text.textContent = 'Bağlantı hatası';
                    statusElement.style.display = 'block';
                    break;
                case 'failed':
                    indicator.className = 'status-indicator failed';
                    text.textContent = 'Bağlantı başarısız';
                    statusElement.style.display = 'block';
                    break;
            }
        }
    }
    
    bindEvents() {
        // Page visibility change
        document.addEventListener('visibilitychange', () => {
            if (document.hidden) {
                // Page hidden, reduce activity
            } else {
                // Page visible, increase activity
                if (!this.isConnected) {
                    this.connect();
                }
            }
        });
        
        // Window beforeunload
        window.addEventListener('beforeunload', () => {
            this.disconnect();
        });
    }
    
    formatTime(timestamp) {
        const date = new Date(timestamp);
        const now = new Date();
        const diff = now - date;
        
        if (diff < 60000) { // Less than 1 minute
            return 'Şimdi';
        } else if (diff < 3600000) { // Less than 1 hour
            return `${Math.floor(diff / 60000)} dakika önce`;
        } else if (diff < 86400000) { // Less than 1 day
            return `${Math.floor(diff / 3600000)} saat önce`;
        } else {
            return date.toLocaleDateString('tr-TR');
        }
    }
    
    // Event handlers that can be overridden
    onConnected(event) {
        console.log('🔴 Connected to real-time server');
    }
    
    onDisconnected(event) {
        console.log('🔴 Disconnected from real-time server');
    }
    
    onError(error) {
        console.error('🔴 Real-time connection error:', error);
    }
}

// CSS Styles for real-time components
const realtimeStyles = `
<style>
.connection-status {
    position: fixed;
    top: 10px;
    right: 10px;
    background: #fff;
    border: 1px solid #ddd;
    border-radius: 4px;
    padding: 8px 12px;
    font-size: 12px;
    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    z-index: 10000;
}

.status-indicator {
    display: inline-block;
    width: 8px;
    height: 8px;
    border-radius: 50%;
    margin-right: 5px;
}

.status-indicator.connected { background: #4caf50; }
.status-indicator.disconnected { background: #ff9800; }
.status-indicator.error { background: #f44336; }
.status-indicator.failed { background: #9e9e9e; }

.realtime-toast {
    position: fixed;
    top: 20px;
    right: 20px;
    background: #fff;
    border: 1px solid #ddd;
    border-radius: 8px;
    box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    max-width: 350px;
    z-index: 10001;
    opacity: 0;
    transform: translateX(100%);
    transition: all 0.3s ease;
}

.realtime-toast.show {
    opacity: 1;
    transform: translateX(0);
}

.toast-content {
    display: flex;
    align-items: flex-start;
    padding: 15px;
}

.toast-icon {
    font-size: 20px;
    margin-right: 10px;
    flex-shrink: 0;
}

.toast-text {
    flex: 1;
}

.toast-title {
    font-weight: bold;
    margin-bottom: 5px;
}

.toast-message {
    font-size: 14px;
    color: #666;
}

.toast-close {
    background: none;
    border: none;
    font-size: 18px;
    cursor: pointer;
    color: #999;
    margin-left: 10px;
}

.toast-close:hover {
    color: #333;
}

.notification-badge {
    background: #f44336;
    color: white;
    border-radius: 50%;
    padding: 2px 6px;
    font-size: 11px;
    position: absolute;
    top: -5px;
    right: -5px;
    min-width: 16px;
    text-align: center;
}

.notification-item {
    display: flex;
    align-items: flex-start;
    padding: 10px;
    border-bottom: 1px solid #eee;
    cursor: pointer;
}

.notification-item.unread {
    background: #f8f9fa;
    border-left: 3px solid #007cba;
}

.notification-item:hover {
    background: #f0f0f0;
}

.notification-icon {
    font-size: 18px;
    margin-right: 10px;
    flex-shrink: 0;
}

.notification-content {
    flex: 1;
}

.notification-title {
    font-weight: bold;
    margin-bottom: 5px;
}

.notification-message {
    font-size: 14px;
    color: #666;
    margin-bottom: 5px;
}

.notification-time {
    font-size: 12px;
    color: #999;
}

.activity-item {
    padding: 8px 10px;
    border-bottom: 1px solid #eee;
}

.activity-text {
    font-size: 14px;
    margin-bottom: 5px;
}

.activity-time {
    font-size: 12px;
    color: #999;
}

.online-user {
    display: flex;
    align-items: center;
    padding: 8px;
    margin-bottom: 5px;
    background: #f8f9fa;
    border-radius: 4px;
}

.user-avatar {
    font-size: 18px;
    margin-right: 8px;
}

.user-name {
    flex: 1;
    font-size: 14px;
}

.user-status {
    font-size: 12px;
}
</style>
`;

// Add styles to document
if (!document.querySelector('#realtime-styles')) {
    const styleElement = document.createElement('div');
    styleElement.id = 'realtime-styles';
    styleElement.innerHTML = realtimeStyles;
    document.head.appendChild(styleElement);
}

// Global instance
let realtimeManager = null;

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    try {
        realtimeManager = new RealtimeManager({
            websocketUrl: `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}/ws/notifications/`,
            reconnectInterval: 5000,
            maxReconnectAttempts: 10
        });
        
        // Setup custom handlers
        realtimeManager.on('trade_request', function(data) {
            console.log('🤝 New trade request:', data);
        });
        
        realtimeManager.on('new_message', function(data) {
            console.log('💬 New message:', data);
        });
        
    } catch (error) {
        console.error('🔴 Failed to initialize real-time manager:', error);
    }
});

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = RealtimeManager;
}