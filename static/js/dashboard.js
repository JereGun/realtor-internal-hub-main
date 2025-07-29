/**
 * Dashboard JavaScript - Enhanced Functionality
 * Sistema de Gestión Inmobiliaria
 */

class DashboardManager {
    constructor() {
        this.init();
        this.setupEventListeners();
        this.startAutoRefresh();
    }

    init() {
        this.animateMetricCards();
        this.setupTooltips();
        this.initializeCounters();
    }

    setupEventListeners() {
        // Refresh button functionality
        const refreshBtn = document.getElementById('refreshDashboard');
        if (refreshBtn) {
            refreshBtn.addEventListener('click', () => this.refreshDashboard());
        }

        // Metric card click handlers
        document.querySelectorAll('.metric-card').forEach(card => {
            card.addEventListener('click', (e) => this.handleMetricCardClick(e));
        });

        // Quick action analytics
        document.querySelectorAll('.quick-action').forEach(action => {
            action.addEventListener('click', (e) => this.trackQuickAction(e));
        });

        // Table row hover effects
        document.querySelectorAll('.table-modern tbody tr').forEach(row => {
            row.addEventListener('mouseenter', (e) => this.highlightRelatedData(e));
            row.addEventListener('mouseleave', (e) => this.removeHighlight(e));
        });
    }

    animateMetricCards() {
        const cards = document.querySelectorAll('.metric-card');
        cards.forEach((card, index) => {
            card.style.opacity = '0';
            card.style.transform = 'translateY(30px)';

            setTimeout(() => {
                card.style.transition = 'all 0.6s cubic-bezier(0.4, 0, 0.2, 1)';
                card.style.opacity = '1';
                card.style.transform = 'translateY(0)';
            }, index * 150);
        });
    }

    initializeCounters() {
        const counters = document.querySelectorAll('.metric-value');

        counters.forEach(counter => {
            const target = parseInt(counter.textContent.replace(/[^0-9]/g, ''));
            if (isNaN(target)) return;

            let current = 0;
            const increment = target / 50;
            const timer = setInterval(() => {
                current += increment;
                if (current >= target) {
                    current = target;
                    clearInterval(timer);
                }

                // Format number with commas and currency symbol if needed
                const formatted = this.formatNumber(Math.floor(current), counter.textContent);
                counter.textContent = formatted;
            }, 30);
        });
    }

    formatNumber(num, originalText) {
        const hasCurrency = originalText.includes('$');
        const formatted = num.toLocaleString();
        return hasCurrency ? `$${formatted}` : formatted;
    }

    setupTooltips() {
        // Initialize Bootstrap tooltips if available
        if (typeof bootstrap !== 'undefined') {
            const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
            tooltipTriggerList.map(function (tooltipTriggerEl) {
                return new bootstrap.Tooltip(tooltipTriggerEl);
            });
        }
    }

    handleMetricCardClick(event) {
        const card = event.currentTarget;
        const cardType = this.getCardType(card);

        // Add click animation
        card.style.transform = 'scale(0.95)';
        setTimeout(() => {
            card.style.transform = '';
        }, 150);

        // Navigate to relevant section based on card type
        this.navigateToSection(cardType);
    }

    getCardType(card) {
        if (card.classList.contains('success')) return 'sales';
        if (card.classList.contains('info')) return 'rentals';
        if (card.classList.contains('warning')) return 'payments';
        if (card.classList.contains('primary')) return 'properties';
        return 'general';
    }

    navigateToSection(type) {
        const routes = {
            'sales': '/contracts/?status=finished',
            'rentals': '/contracts/?status=active',
            'payments': '/payments/?status=pending',
            'properties': '/properties/'
        };

        if (routes[type]) {
            // Add loading state
            this.showLoadingState();
            window.location.href = routes[type];
        }
    }

    trackQuickAction(event) {
        const action = event.currentTarget;
        const actionName = action.querySelector('h6').textContent;

        // Analytics tracking (if implemented)
        console.log(`Quick action clicked: ${actionName}`);

        // Add visual feedback
        action.style.transform = 'scale(0.98)';
        setTimeout(() => {
            action.style.transform = '';
        }, 100);
    }

    highlightRelatedData(event) {
        const row = event.currentTarget;
        const customerName = row.cells[2]?.textContent;

        if (customerName) {
            // Highlight other rows with same customer
            document.querySelectorAll('.table-modern tbody tr').forEach(otherRow => {
                if (otherRow !== row && otherRow.cells[2]?.textContent === customerName) {
                    otherRow.style.backgroundColor = 'rgba(37, 99, 235, 0.1)';
                }
            });
        }
    }

    removeHighlight(event) {
        // Remove all highlights
        document.querySelectorAll('.table-modern tbody tr').forEach(row => {
            row.style.backgroundColor = '';
        });
    }

    refreshDashboard() {
        this.showLoadingState();

        // Simulate API call
        setTimeout(() => {
            location.reload();
        }, 1000);
    }

    showLoadingState() {
        const cards = document.querySelectorAll('.metric-card');
        cards.forEach(card => {
            const value = card.querySelector('.metric-value');
            if (value) {
                value.innerHTML = '<div class="loading-spinner"></div>';
            }
        });
    }

    startAutoRefresh() {
        // Auto-refresh every 5 minutes
        setInterval(() => {
            this.updateDashboardData();
        }, 300000);
    }

    async updateDashboardData() {
        try {
            // This would be an AJAX call to get updated data
            console.log('Checking for dashboard updates...');

            // Example: Update notification badge
            this.updateNotificationBadge();

        } catch (error) {
            console.error('Error updating dashboard data:', error);
        }
    }

    updateNotificationBadge() {
        // Update notification count if needed
        const badge = document.querySelector('.nav-link .badge');
        // This would typically come from an API call
    }

    // Utility methods
    showNotification(message, type = 'info') {
        const notification = document.createElement('div');
        notification.className = `alert alert-${type} alert-dismissible fade show position-fixed`;
        notification.style.cssText = 'top: 20px; right: 20px; z-index: 9999; min-width: 300px;';
        notification.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;

        document.body.appendChild(notification);

        // Auto-remove after 5 seconds
        setTimeout(() => {
            if (notification.parentNode) {
                notification.remove();
            }
        }, 5000);
    }

    formatCurrency(amount) {
        return new Intl.NumberFormat('es-AR', {
            style: 'currency',
            currency: 'ARS'
        }).format(amount);
    }

    formatDate(date) {
        return new Intl.DateTimeFormat('es-AR', {
            year: 'numeric',
            month: 'short',
            day: 'numeric'
        }).format(new Date(date));
    }
}

// Initialize dashboard when DOM is loaded
document.addEventListener('DOMContentLoaded', function () {
    const dashboard = new DashboardManager();

    // Make dashboard instance globally available
    window.dashboard = dashboard;

    // Add keyboard shortcuts
    document.addEventListener('keydown', function (e) {
        // Ctrl/Cmd + R for refresh
        if ((e.ctrlKey || e.metaKey) && e.key === 'r') {
            e.preventDefault();
            dashboard.refreshDashboard();
        }

        // Ctrl/Cmd + N for new property
        if ((e.ctrlKey || e.metaKey) && e.key === 'n') {
            e.preventDefault();
            window.location.href = '/properties/create/';
        }
    });

    // Add responsive behavior
    window.addEventListener('resize', function () {
        // Adjust layout for mobile
        const isMobile = window.innerWidth < 768;
        document.body.classList.toggle('mobile-layout', isMobile);
    });

    // Add print functionality
    window.addEventListener('beforeprint', function () {
        document.body.classList.add('printing');
    });

    window.addEventListener('afterprint', function () {
        document.body.classList.remove('printing');
    });
});

// Export for module systems
if (typeof module !== 'undefined' && module.exports) {
    module.exports = DashboardManager;
}