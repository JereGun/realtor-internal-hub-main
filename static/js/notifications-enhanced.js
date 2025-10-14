/**
 * Enhanced Notifications JavaScript
 * Provides modern interactions for notification system
 */

document.addEventListener('DOMContentLoaded', function() {
    
    // Auto-hide alerts after 5 seconds
    const alerts = document.querySelectorAll('.alert-modern');
    alerts.forEach(alert => {
        if (!alert.classList.contains('alert-danger') && !alert.classList.contains('alert-error')) {
            setTimeout(() => {
                if (alert && alert.parentNode) {
                    alert.classList.add('fade');
                    setTimeout(() => {
                        if (alert && alert.parentNode) {
                            alert.remove();
                        }
                    }, 300);
                }
            }, 5000);
        }
    });

    // Enhanced close button behavior
    const closeButtons = document.querySelectorAll('.alert-modern .btn-close');
    closeButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            e.preventDefault();
            const alert = this.closest('.alert-modern');
            if (alert) {
                alert.style.transform = 'translateX(100%)';
                alert.style.opacity = '0';
                setTimeout(() => {
                    if (alert && alert.parentNode) {
                        alert.remove();
                    }
                }, 300);
            }
        });
    });

    // Notification card hover effects
    const notificationCards = document.querySelectorAll('.notification-card, .notification-list-item');
    notificationCards.forEach(card => {
        card.addEventListener('mouseenter', function() {
            this.style.transform = 'translateY(-2px)';
        });
        
        card.addEventListener('mouseleave', function() {
            this.style.transform = 'translateY(0)';
        });
    });

    // Mark notification as read on click and handle smooth scrolling
    const notificationReadLinks = document.querySelectorAll('.notification-list-item a, .notification-card a');
    notificationReadLinks.forEach(link => {
        link.addEventListener('click', function() {
            const notificationItem = this.closest('.notification-list-item, .notification-card');
            if (notificationItem && notificationItem.classList.contains('unread')) {
                // Add a subtle animation to indicate the change
                notificationItem.style.transition = 'all 0.3s ease';
                notificationItem.classList.remove('unread');
            }
        });
    });

    // Enhanced form interactions
    const formControls = document.querySelectorAll('.notification-filters .form-control, .notification-filters .form-select');
    formControls.forEach(control => {
        control.addEventListener('focus', function() {
            this.parentElement.style.transform = 'scale(1.02)';
        });
        
        control.addEventListener('blur', function() {
            this.parentElement.style.transform = 'scale(1)';
        });
    });

    // Smooth scroll to notifications
    const notificationScrollLinks = document.querySelectorAll('a[href*="notification"]');
    notificationScrollLinks.forEach(link => {
        link.addEventListener('click', function(e) {
            const href = this.getAttribute('href');
            if (href.includes('#')) {
                e.preventDefault();
                const target = document.querySelector(href.split('#')[1]);
                if (target) {
                    target.scrollIntoView({
                        behavior: 'smooth',
                        block: 'start'
                    });
                }
            }
        });
    });

    // Toast notification system for dynamic alerts
    window.showToast = function(message, type = 'info', duration = 5000) {
        const toast = document.createElement('div');
        toast.className = `alert-modern alert-${type} alert-toast fade show`;
        toast.innerHTML = `
            <div class="d-flex align-items-center">
                <i class="bi bi-${getIconForType(type)} me-2"></i>
                <div class="flex-grow-1">${message}</div>
                <button type="button" class="btn-close" aria-label="Cerrar"></button>
            </div>
        `;
        
        document.body.appendChild(toast);
        
        // Auto remove
        setTimeout(() => {
            toast.classList.add('hide');
            setTimeout(() => {
                if (toast && toast.parentNode) {
                    toast.remove();
                }
            }, 300);
        }, duration);
        
        // Manual close
        const closeBtn = toast.querySelector('.btn-close');
        closeBtn.addEventListener('click', () => {
            toast.classList.add('hide');
            setTimeout(() => {
                if (toast && toast.parentNode) {
                    toast.remove();
                }
            }, 300);
        });
    };

    function getIconForType(type) {
        const icons = {
            'success': 'check-circle-fill',
            'danger': 'exclamation-triangle-fill',
            'error': 'exclamation-triangle-fill',
            'warning': 'exclamation-circle-fill',
            'info': 'info-circle-fill'
        };
        return icons[type] || 'info-circle';
    }

    // Enhanced pagination
    const paginationLinks = document.querySelectorAll('.pagination .page-link');
    paginationLinks.forEach(link => {
        link.addEventListener('click', function(e) {
            // Add loading state
            this.style.opacity = '0.6';
            this.innerHTML = '<i class="bi bi-arrow-clockwise"></i>';
        });
    });

    // Keyboard shortcuts
    document.addEventListener('keydown', function(e) {
        // Ctrl/Cmd + M to mark all as read
        if ((e.ctrlKey || e.metaKey) && e.key === 'm') {
            e.preventDefault();
            const markAllBtn = document.getElementById('mark-all-read-btn');
            if (markAllBtn) {
                markAllBtn.click();
            }
        }
        
        // Escape to close modals/alerts
        if (e.key === 'Escape') {
            const alerts = document.querySelectorAll('.alert-modern');
            alerts.forEach(alert => {
                const closeBtn = alert.querySelector('.btn-close');
                if (closeBtn) {
                    closeBtn.click();
                }
            });
        }
    });

    // Initialize tooltips for notification actions
    const tooltipElements = document.querySelectorAll('[title]');
    tooltipElements.forEach(element => {
        element.addEventListener('mouseenter', function() {
            const title = this.getAttribute('title');
            if (title) {
                const tooltip = document.createElement('div');
                tooltip.className = 'tooltip-modern';
                tooltip.textContent = title;
                tooltip.style.position = 'absolute';
                tooltip.style.background = 'var(--gray-800)';
                tooltip.style.color = 'white';
                tooltip.style.padding = 'var(--space-2) var(--space-3)';
                tooltip.style.borderRadius = 'var(--radius)';
                tooltip.style.fontSize = 'var(--text-sm)';
                tooltip.style.zIndex = '1000';
                tooltip.style.pointerEvents = 'none';
                tooltip.style.opacity = '0';
                tooltip.style.transition = 'opacity 0.2s ease';
                
                document.body.appendChild(tooltip);
                
                const rect = this.getBoundingClientRect();
                tooltip.style.left = rect.left + (rect.width / 2) - (tooltip.offsetWidth / 2) + 'px';
                tooltip.style.top = rect.top - tooltip.offsetHeight - 8 + 'px';
                
                setTimeout(() => {
                    tooltip.style.opacity = '1';
                }, 10);
                
                this._tooltip = tooltip;
            }
        });
        
        element.addEventListener('mouseleave', function() {
            if (this._tooltip) {
                this._tooltip.style.opacity = '0';
                setTimeout(() => {
                    if (this._tooltip && this._tooltip.parentNode) {
                        this._tooltip.remove();
                    }
                }, 200);
            }
        });
    });
});