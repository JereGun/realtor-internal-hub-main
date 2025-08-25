/**
 * Notification Management JavaScript
 * Handles AJAX functionality for notification management
 */

class NotificationManager {
    constructor() {
        this.csrfToken = this.getCSRFToken();
        this.init();
    }

    init() {
        // Initialize event listeners
        this.bindEvents();
        // Update notification count on page load
        this.updateNotificationCount();
    }

    bindEvents() {
        // Bind mark all as read button
        const markAllBtn = document.querySelector('#mark-all-read-btn');
        if (markAllBtn) {
            markAllBtn.addEventListener('click', () => this.markAllAsRead());
        }

        // Bind individual notification checkboxes
        document.querySelectorAll('.notification-checkbox').forEach(checkbox => {
            checkbox.addEventListener('change', (e) => {
                const notificationId = e.target.dataset.notificationId;
                this.markAsRead(notificationId);
            });
        });

        // Bind mark as read buttons in detail view
        const markReadBtn = document.querySelector('.mark-read-btn');
        if (markReadBtn) {
            const notificationId = markReadBtn.dataset.notificationId;
            markReadBtn.addEventListener('click', () => this.markAsRead(notificationId));
        }
    }

    getCSRFToken() {
        const csrfInput = document.querySelector('[name=csrfmiddlewaretoken]');
        if (csrfInput) {
            return csrfInput.value;
        }
        
        // Try to get from meta tag
        const csrfMeta = document.querySelector('meta[name=csrf-token]');
        if (csrfMeta) {
            return csrfMeta.getAttribute('content');
        }
        
        // Try to get from cookie
        const cookies = document.cookie.split(';');
        for (let cookie of cookies) {
            const [name, value] = cookie.trim().split('=');
            if (name === 'csrftoken') {
                return value;
            }
        }
        
        return '';
    }

    async markAsRead(notificationId) {
        try {
            const response = await fetch(`/notifications/${notificationId}/mark-as-read/`, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': this.csrfToken,
                    'Content-Type': 'application/json',
                },
            });

            const data = await response.json();

            if (data.success) {
                console.log(`Notificación ${notificationId} marcada como leída`);
                
                // Update UI elements
                this.updateNotificationUI(notificationId, true);
                this.updateUnreadCount(data.unread_count);
                this.showMessage('success', data.message);
                
                return true;
            } else {
                console.error('Error:', data.error);
                this.showMessage('error', 'Error al marcar la notificación como leída');
                
                // Revert checkbox state
                const checkbox = document.getElementById(`notification_${notificationId}`);
                if (checkbox) {
                    checkbox.checked = !checkbox.checked;
                }
                
                return false;
            }
        } catch (error) {
            console.error('Error:', error);
            this.showMessage('error', 'Error al marcar la notificación como leída');
            
            // Revert checkbox state
            const checkbox = document.getElementById(`notification_${notificationId}`);
            if (checkbox) {
                checkbox.checked = !checkbox.checked;
            }
            
            return false;
        }
    }

    async markAllAsRead() {
        try {
            const response = await fetch('/notifications/mark-all-as-read/', {
                method: 'POST',
                headers: {
                    'X-CSRFToken': this.csrfToken,
                    'Content-Type': 'application/json',
                },
            });

            const data = await response.json();

            if (data.success) {
                console.log('Todas las notificaciones marcadas como leídas');
                
                // Update all checkboxes
                document.querySelectorAll('.notification-checkbox').forEach(checkbox => {
                    checkbox.checked = true;
                });
                
                // Remove warning highlight from all rows
                document.querySelectorAll('tr.table-warning').forEach(row => {
                    row.classList.remove('table-warning');
                });
                
                // Update unread count
                this.updateUnreadCount(0);
                this.showMessage('success', data.message);
                
                return true;
            } else {
                console.error('Error:', data.error);
                this.showMessage('error', 'Error al marcar las notificaciones como leídas');
                return false;
            }
        } catch (error) {
            console.error('Error:', error);
            this.showMessage('error', 'Error al marcar las notificaciones como leídas');
            return false;
        }
    }

    updateNotificationUI(notificationId, isRead) {
        // Update row highlighting
        const row = document.getElementById(`notification-row-${notificationId}`);
        if (row && isRead) {
            row.classList.remove('table-warning');
        }

        // Update status badge in detail view
        if (window.location.pathname.includes(`/notifications/${notificationId}/`)) {
            const statusElements = document.querySelectorAll('.badge');
            statusElements.forEach(badge => {
                if (badge.textContent.trim() === 'No leída' && isRead) {
                    badge.className = 'badge bg-success';
                    badge.textContent = 'Leída';
                }
            });

            // Hide mark as read button in detail view
            const markReadBtn = document.querySelector('button[onclick*="markAsRead"], .btn:contains("Marcar como leída")');
            if (markReadBtn && isRead) {
                const container = markReadBtn.closest('.d-grid');
                if (container) {
                    container.style.display = 'none';
                }
            }
        }
    }

    updateUnreadCount(newCount) {
        // Update navbar badge
        const navbarBadges = document.querySelectorAll('.navbar .nav-link .badge, .navbar .badge');
        navbarBadges.forEach(badge => {
            if (newCount > 0) {
                badge.textContent = newCount;
                badge.style.display = 'inline';
            } else {
                badge.style.display = 'none';
            }
        });

        // Update summary cards if present
        const unreadCard = document.querySelector('.card .card-title:contains("No leídas")');
        if (unreadCard) {
            const countElement = unreadCard.parentElement.querySelector('.display-6');
            if (countElement) {
                countElement.textContent = newCount;
            }
        }

        // Update page title if it shows count
        if (newCount > 0) {
            document.title = `(${newCount}) Notificaciones - Real Estate Management`;
        } else {
            document.title = 'Notificaciones - Real Estate Management';
        }
    }

    async updateNotificationCount() {
        try {
            const response = await fetch('/notifications/count/', {
                method: 'GET',
                headers: {
                    'X-CSRFToken': this.csrfToken,
                    'Content-Type': 'application/json',
                },
            });

            if (response.ok) {
                const data = await response.json();
                this.updateUnreadCount(data.unread_count);
            }
        } catch (error) {
            console.error('Error updating notification count:', error);
        }
    }

    showMessage(type, message) {
        // Remove existing alerts
        document.querySelectorAll('.alert.notification-alert').forEach(alert => {
            alert.remove();
        });

        // Create new alert element
        const alertDiv = document.createElement('div');
        alertDiv.className = `alert alert-${type === 'success' ? 'success' : 'danger'} alert-dismissible fade show notification-alert`;
        alertDiv.innerHTML = `
            <i class="bi bi-${type === 'success' ? 'check-circle' : 'exclamation-triangle'}"></i>
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
        `;

        // Insert at the top of the content
        const container = document.querySelector('.container-fluid, .container');
        if (container) {
            container.insertBefore(alertDiv, container.firstChild);
        }

        // Auto-dismiss after 5 seconds
        setTimeout(() => {
            if (alertDiv.parentNode) {
                alertDiv.remove();
            }
        }, 5000);
    }

    // Utility method to refresh notification list
    async refreshNotificationList() {
        if (window.location.pathname.includes('/notifications/')) {
            window.location.reload();
        }
    }

    // Method to handle real-time updates (can be extended with WebSockets)
    startRealTimeUpdates() {
        // Poll for updates every 30 seconds
        setInterval(() => {
            this.updateNotificationCount();
        }, 30000);
    }
}

// Initialize notification manager when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    window.notificationManager = new NotificationManager();
    
    // Start real-time updates
    window.notificationManager.startRealTimeUpdates();
});

// Legacy function support for existing templates
function markAsRead(notificationId) {
    if (window.notificationManager) {
        return window.notificationManager.markAsRead(notificationId);
    }
}

function markAllAsRead() {
    if (window.notificationManager) {
        return window.notificationManager.markAllAsRead();
    }
}