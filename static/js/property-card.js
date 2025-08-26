/**
 * Property Card Interactive Functions
 * Handles property card interactions and quick actions
 */

// Toggle favorite status for a property
function toggleFavorite(propertyId) {
    const button = event.target.closest('.property-quick-action');
    const icon = button.querySelector('i');
    
    // Toggle icon state
    if (icon.classList.contains('bi-heart')) {
        icon.classList.remove('bi-heart');
        icon.classList.add('bi-heart-fill');
        button.style.color = 'var(--property-danger)';
    } else {
        icon.classList.remove('bi-heart-fill');
        icon.classList.add('bi-heart');
        button.style.color = '';
    }
    
    // Here you would typically make an AJAX call to update the favorite status
    // Example:
    // fetch(`/api/properties/${propertyId}/toggle-favorite/`, {
    //     method: 'POST',
    //     headers: {
    //         'X-CSRFToken': getCookie('csrftoken'),
    //         'Content-Type': 'application/json',
    //     },
    // })
    // .then(response => response.json())
    // .then(data => {
    //     if (data.success) {
    //         // Handle success
    //     }
    // })
    // .catch(error => {
    //     console.error('Error:', error);
    //     // Revert the icon change on error
    // });
}

/**
 * Initialize responsive property card enhancements
 */
function initializeResponsiveCards() {
    initializeTouchInteractions();
    initializeResponsiveGrid();
    initializeMobileCardOptimizations();
}

/**
 * Touch-friendly interactions for property cards
 */
function initializeTouchInteractions() {
    const propertyCards = document.querySelectorAll('.property-card-enhanced');
    
    propertyCards.forEach(card => {
        // Touch feedback for cards
        card.addEventListener('touchstart', function() {
            if (window.innerWidth <= 767) {
                this.style.transform = 'scale(0.98)';
                this.style.transition = 'transform 0.1s ease';
            }
        });
        
        card.addEventListener('touchend', function() {
            if (window.innerWidth <= 767) {
                setTimeout(() => {
                    this.style.transform = '';
                    this.style.transition = '';
                }, 150);
            }
        });

        // Prevent hover effects on touch devices
        if ('ontouchstart' in window) {
            card.addEventListener('touchstart', function() {
                this.classList.add('touch-active');
            });
            
            card.addEventListener('touchend', function() {
                setTimeout(() => {
                    this.classList.remove('touch-active');
                }, 300);
            });
        }
    });

    // Touch-friendly quick actions
    const quickActions = document.querySelectorAll('.property-quick-action');
    quickActions.forEach(action => {
        action.addEventListener('touchstart', function(e) {
            e.stopPropagation();
            this.style.transform = 'scale(0.9)';
            this.style.backgroundColor = 'rgba(255, 255, 255, 1)';
        });
        
        action.addEventListener('touchend', function(e) {
            e.stopPropagation();
            setTimeout(() => {
                this.style.transform = '';
                this.style.backgroundColor = '';
            }, 150);
        });
    });
}

/**
 * Responsive grid adjustments
 */
function initializeResponsiveGrid() {
    const adjustGrid = () => {
        const propertyGrid = document.querySelector('.property-grid, .row.row-cols-1.row-cols-md-2.row-cols-lg-3.row-cols-xl-4');
        if (!propertyGrid) return;

        const viewport = window.innerWidth;
        
        // Adjust grid based on viewport
        if (viewport <= 575) {
            propertyGrid.className = propertyGrid.className.replace(/row-cols-\w+-\d+/g, '');
            propertyGrid.classList.add('row-cols-1');
        } else if (viewport <= 767) {
            propertyGrid.className = propertyGrid.className.replace(/row-cols-\w+-\d+/g, '');
            propertyGrid.classList.add('row-cols-1', 'row-cols-sm-2');
        } else if (viewport <= 991) {
            propertyGrid.className = propertyGrid.className.replace(/row-cols-\w+-\d+/g, '');
            propertyGrid.classList.add('row-cols-1', 'row-cols-sm-2', 'row-cols-md-2');
        } else if (viewport <= 1199) {
            propertyGrid.className = propertyGrid.className.replace(/row-cols-\w+-\d+/g, '');
            propertyGrid.classList.add('row-cols-1', 'row-cols-sm-2', 'row-cols-md-2', 'row-cols-lg-3');
        } else {
            propertyGrid.className = propertyGrid.className.replace(/row-cols-\w+-\d+/g, '');
            propertyGrid.classList.add('row-cols-1', 'row-cols-sm-2', 'row-cols-md-2', 'row-cols-lg-3', 'row-cols-xl-4');
        }
    };

    // Initial adjustment
    adjustGrid();

    // Adjust on resize
    window.addEventListener('resize', debounce(adjustGrid, 250));
}

/**
 * Mobile-specific card optimizations
 */
function initializeMobileCardOptimizations() {
    if (window.innerWidth > 767) return;

    const propertyCards = document.querySelectorAll('.property-card-enhanced');
    
    propertyCards.forEach(card => {
        // Optimize card layout for mobile
        const content = card.querySelector('.property-content');
        if (content) {
            content.style.padding = '16px';
        }

        // Optimize features layout for mobile
        const features = card.querySelector('.property-features');
        if (features) {
            features.style.display = 'flex';
            features.style.flexDirection = 'column';
            features.style.gap = '8px';
        }

        const featureItems = card.querySelectorAll('.property-feature');
        featureItems.forEach(feature => {
            feature.style.display = 'flex';
            feature.style.justifyContent = 'space-between';
            feature.style.alignItems = 'center';
            feature.style.padding = '4px 0';
        });

        // Optimize actions for mobile
        const actions = card.querySelector('.property-actions');
        if (actions) {
            actions.style.display = 'flex';
            actions.style.flexDirection = 'column';
            actions.style.gap = '8px';
        }

        const actionButtons = card.querySelectorAll('.property-actions .property-btn');
        actionButtons.forEach(button => {
            button.style.width = '100%';
            button.style.minHeight = '44px';
            button.style.justifyContent = 'center';
        });

        // Optimize pricing display for mobile
        const pricing = card.querySelector('.property-pricing');
        if (pricing) {
            pricing.style.display = 'flex';
            pricing.style.flexDirection = 'column';
            pricing.style.gap = '4px';
        }

        // Hide overlay on mobile (touch devices)
        const overlay = card.querySelector('.property-overlay');
        if (overlay && 'ontouchstart' in window) {
            overlay.style.display = 'none';
        }
    });
}

/**
 * Debounce utility function
 */
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// Initialize property card interactions
document.addEventListener('DOMContentLoaded', function() {
    // Initialize tooltips for property features
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    if (typeof bootstrap !== 'undefined' && bootstrap.Tooltip) {
        tooltipTriggerList.map(function (tooltipTriggerEl) {
            return new bootstrap.Tooltip(tooltipTriggerEl);
        });
    }
    
    // Add loading states for property images
    const propertyImages = document.querySelectorAll('.property-image');
    propertyImages.forEach(img => {
        img.addEventListener('load', function() {
            this.style.opacity = '1';
        });
        
        img.addEventListener('error', function() {
            // Replace with placeholder if image fails to load
            const placeholder = document.createElement('div');
            placeholder.className = 'property-image-placeholder';
            placeholder.innerHTML = '<i class="bi bi-building property-placeholder-icon"></i>';
            this.parentNode.replaceChild(placeholder, this);
        });
    });
    
    // Add stagger animation to property cards
    const propertyCards = document.querySelectorAll('.property-card-enhanced');
    propertyCards.forEach((card, index) => {
        card.style.animationDelay = `${index * 0.1}s`;
        card.classList.add('property-fade-in');
    });

    // Initialize responsive enhancements
    initializeResponsiveCards();
});

// Utility function to get CSRF token (if needed for AJAX calls)
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}