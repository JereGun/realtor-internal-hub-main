/**
 * Property Detail Template JavaScript
 * Enhanced functionality for property detail page
 */

document.addEventListener('DOMContentLoaded', function() {
    initializePropertyDetail();
});

function initializePropertyDetail() {
    initializeImageGallery();
    initializeAnimations();
    initializeInteractions();
    initializeResponsiveEnhancements();
}

/**
 * Enhanced Image Gallery Functionality
 */
function initializeImageGallery() {
    const carousel = document.getElementById('propertyCarousel');
    if (!carousel) return;

    const thumbnails = document.querySelectorAll('.property-thumbnail');
    const carouselItems = document.querySelectorAll('.property-carousel-item');
    const indicators = document.querySelectorAll('.property-carousel-indicator');

    // Thumbnail navigation
    thumbnails.forEach((thumbnail, index) => {
        thumbnail.addEventListener('click', function() {
            // Update active thumbnail
            thumbnails.forEach(t => t.classList.remove('active'));
            this.classList.add('active');

            // Update carousel
            const bsCarousel = bootstrap.Carousel.getInstance(carousel) || new bootstrap.Carousel(carousel);
            bsCarousel.to(index);
        });
    });

    // Sync indicators with thumbnails
    carousel.addEventListener('slide.bs.carousel', function(event) {
        const activeIndex = event.to;
        
        // Update thumbnails
        thumbnails.forEach((thumbnail, index) => {
            thumbnail.classList.toggle('active', index === activeIndex);
        });
        
        // Update indicators
        indicators.forEach((indicator, index) => {
            indicator.classList.toggle('active', index === activeIndex);
        });
    });

    // Keyboard navigation
    document.addEventListener('keydown', function(event) {
        if (!isCarouselFocused()) return;

        const bsCarousel = bootstrap.Carousel.getInstance(carousel);
        if (!bsCarousel) return;

        switch(event.key) {
            case 'ArrowLeft':
                event.preventDefault();
                bsCarousel.prev();
                break;
            case 'ArrowRight':
                event.preventDefault();
                bsCarousel.next();
                break;
            case 'Home':
                event.preventDefault();
                bsCarousel.to(0);
                break;
            case 'End':
                event.preventDefault();
                bsCarousel.to(carouselItems.length - 1);
                break;
        }
    });

    // Touch/swipe support for mobile
    let startX = 0;
    let endX = 0;

    carousel.addEventListener('touchstart', function(event) {
        startX = event.touches[0].clientX;
    });

    carousel.addEventListener('touchend', function(event) {
        endX = event.changedTouches[0].clientX;
        handleSwipe();
    });

    function handleSwipe() {
        const threshold = 50;
        const diff = startX - endX;

        if (Math.abs(diff) > threshold) {
            const bsCarousel = bootstrap.Carousel.getInstance(carousel);
            if (!bsCarousel) return;

            if (diff > 0) {
                bsCarousel.next();
            } else {
                bsCarousel.prev();
            }
        }
    }

    function isCarouselFocused() {
        return carousel.contains(document.activeElement) || 
               document.activeElement === carousel;
    }
}

/**
 * Initialize animations and transitions
 */
function initializeAnimations() {
    // Animate cards on scroll
    const observerOptions = {
        threshold: 0.1,
        rootMargin: '0px 0px -50px 0px'
    };

    const observer = new IntersectionObserver(function(entries) {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('property-fade-in');
                observer.unobserve(entry.target);
            }
        });
    }, observerOptions);

    // Observe all info cards
    document.querySelectorAll('.property-info-card, .property-pricing-container, .property-status-container, .property-contracts-container, .property-agent-container').forEach(card => {
        observer.observe(card);
    });

    // Animate feature items with stagger
    const featureItems = document.querySelectorAll('.property-feature-item');
    featureItems.forEach((item, index) => {
        setTimeout(() => {
            item.classList.add('property-fade-in');
        }, index * 100);
    });

    // Animate price cards
    const priceCards = document.querySelectorAll('.property-price-card');
    priceCards.forEach((card, index) => {
        setTimeout(() => {
            card.classList.add('property-scale-in');
        }, index * 200);
    });
}

/**
 * Initialize interactive elements
 */
function initializeInteractions() {
    // Enhanced hover effects for feature items
    const featureItems = document.querySelectorAll('.property-feature-item');
    featureItems.forEach(item => {
        item.addEventListener('mouseenter', function() {
            this.style.transform = 'translateX(8px) scale(1.02)';
        });

        item.addEventListener('mouseleave', function() {
            this.style.transform = '';
        });
    });

    // Price card interactions
    const priceCards = document.querySelectorAll('.property-price-card');
    priceCards.forEach(card => {
        card.addEventListener('mouseenter', function() {
            this.style.transform = 'translateY(-4px) scale(1.02)';
        });

        card.addEventListener('mouseleave', function() {
            this.style.transform = '';
        });
    });

    // Contract item interactions
    const contractItems = document.querySelectorAll('.property-contract-item');
    contractItems.forEach(item => {
        item.addEventListener('mouseenter', function() {
            this.style.backgroundColor = 'var(--property-light)';
            this.style.transform = 'translateX(4px)';
        });

        item.addEventListener('mouseleave', function() {
            this.style.backgroundColor = '';
            this.style.transform = '';
        });
    });

    // Button hover enhancements
    const buttons = document.querySelectorAll('.property-btn');
    buttons.forEach(button => {
        button.addEventListener('mouseenter', function() {
            if (!this.classList.contains('property-btn-outline-primary') && 
                !this.classList.contains('property-btn-outline-secondary') &&
                !this.classList.contains('property-btn-outline-danger')) {
                this.style.transform = 'translateY(-2px)';
                this.style.boxShadow = 'var(--property-shadow-lg)';
            }
        });

        button.addEventListener('mouseleave', function() {
            this.style.transform = '';
            this.style.boxShadow = '';
        });
    });

    // Smooth scrolling for internal links
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function(e) {
            e.preventDefault();
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                target.scrollIntoView({
                    behavior: 'smooth',
                    block: 'start'
                });
            }
        });
    });
}

/**
 * Utility functions
 */

// Debounce function for performance
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

// Throttle function for scroll events
function throttle(func, limit) {
    let inThrottle;
    return function() {
        const args = arguments;
        const context = this;
        if (!inThrottle) {
            func.apply(context, args);
            inThrottle = true;
            setTimeout(() => inThrottle = false, limit);
        }
    }
}

// Check if element is in viewport
function isInViewport(element) {
    const rect = element.getBoundingClientRect();
    return (
        rect.top >= 0 &&
        rect.left >= 0 &&
        rect.bottom <= (window.innerHeight || document.documentElement.clientHeight) &&
        rect.right <= (window.innerWidth || document.documentElement.clientWidth)
    );
}

// Add loading state to buttons
function addLoadingState(button, text = 'Cargando...') {
    const originalText = button.innerHTML;
    button.innerHTML = `<i class="bi bi-arrow-repeat property-spin me-1"></i>${text}`;
    button.disabled = true;
    
    return function removeLoadingState() {
        button.innerHTML = originalText;
        button.disabled = false;
    };
}

// Show notification
function showNotification(message, type = 'info') {
    const notification = document.createElement('div');
    notification.className = `alert alert-${type} alert-dismissible fade show position-fixed`;
    notification.style.cssText = 'top: 20px; right: 20px; z-index: 9999; min-width: 300px;';
    notification.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    document.body.appendChild(notification);
    
    // Auto remove after 5 seconds
    setTimeout(() => {
        if (notification.parentNode) {
            notification.remove();
        }
    }, 5000);
}

/**
 * Initialize responsive enhancements for property detail
 */
function initializeResponsiveEnhancements() {
    initializeTouchGallery();
    initializeResponsiveLayout();
    initializeMobileOptimizations();
    initializeTabletEnhancements();
}

/**
 * Touch-friendly gallery enhancements
 */
function initializeTouchGallery() {
    const carousel = document.getElementById('propertyCarousel');
    if (!carousel) return;

    // Improve touch sensitivity
    let touchStartX = 0;
    let touchStartY = 0;
    let touchEndX = 0;
    let touchEndY = 0;
    let isSwiping = false;

    carousel.addEventListener('touchstart', function(e) {
        touchStartX = e.touches[0].clientX;
        touchStartY = e.touches[0].clientY;
        isSwiping = false;
    }, { passive: true });

    carousel.addEventListener('touchmove', function(e) {
        if (!isSwiping) {
            const deltaX = Math.abs(e.touches[0].clientX - touchStartX);
            const deltaY = Math.abs(e.touches[0].clientY - touchStartY);
            
            // Determine if this is a horizontal swipe
            if (deltaX > deltaY && deltaX > 10) {
                isSwiping = true;
                e.preventDefault(); // Prevent vertical scrolling
            }
        }
    }, { passive: false });

    carousel.addEventListener('touchend', function(e) {
        if (!isSwiping) return;
        
        touchEndX = e.changedTouches[0].clientX;
        touchEndY = e.changedTouches[0].clientY;
        
        const deltaX = touchStartX - touchEndX;
        const deltaY = Math.abs(touchStartY - touchEndY);
        
        // Only trigger if horizontal movement is greater than vertical
        if (Math.abs(deltaX) > 50 && Math.abs(deltaX) > deltaY) {
            const bsCarousel = bootstrap.Carousel.getInstance(carousel);
            if (bsCarousel) {
                if (deltaX > 0) {
                    bsCarousel.next();
                } else {
                    bsCarousel.prev();
                }
            }
        }
    }, { passive: true });

    // Add touch indicators for mobile
    if (window.innerWidth <= 767) {
        const addTouchIndicator = () => {
            const indicator = document.createElement('div');
            indicator.className = 'touch-indicator';
            indicator.innerHTML = '<i class="bi bi-arrow-left-right"></i> Desliza para navegar';
            indicator.style.cssText = `
                position: absolute;
                bottom: 60px;
                left: 50%;
                transform: translateX(-50%);
                background: var(--property-primary);
                color: white;
                padding: 8px 16px;
                border-radius: 20px;
                font-size: 12px;
                z-index: 10;
                animation: fadeInOut 3s ease-in-out;
                pointer-events: none;
                box-shadow: 0 2px 8px rgba(0,0,0,0.2);
                border: 1px solid white;
            `;
            
            carousel.appendChild(indicator);
            
            // Remove after animation
            setTimeout(() => {
                if (indicator.parentNode) {
                    indicator.remove();
                }
            }, 3000);
        };

        // Show indicator after a short delay
        setTimeout(addTouchIndicator, 1000);
    }
}

/**
 * Responsive layout adjustments
 */
function initializeResponsiveLayout() {
    const adjustLayout = () => {
        const viewport = {
            width: window.innerWidth,
            height: window.innerHeight
        };

        // Adjust sidebar position on tablets
        const sidebar = document.querySelector('.col-lg-4');
        const mainContent = document.querySelector('.col-lg-8');
        
        if (sidebar && mainContent) {
            if (viewport.width >= 768 && viewport.width < 992) {
                // Tablet layout adjustments
                sidebar.style.order = '2';
                mainContent.style.order = '1';
            } else {
                sidebar.style.order = '';
                mainContent.style.order = '';
            }
        }

        // Adjust gallery height for landscape mobile
        const gallery = document.querySelector('.property-gallery-main');
        if (gallery && viewport.width <= 767 && viewport.width > viewport.height) {
            gallery.style.maxHeight = '60vh';
        } else if (gallery) {
            gallery.style.maxHeight = '';
        }

        // Adjust feature grid for different screen sizes
        const featureGrid = document.querySelector('.property-features-grid');
        if (featureGrid) {
            if (viewport.width <= 575) {
                featureGrid.style.gridTemplateColumns = '1fr';
            } else if (viewport.width <= 991) {
                featureGrid.style.gridTemplateColumns = '1fr';
            } else {
                featureGrid.style.gridTemplateColumns = 'repeat(2, 1fr)';
            }
        }
    };

    // Initial adjustment
    adjustLayout();

    // Adjust on resize
    window.addEventListener('resize', debounce(adjustLayout, 250));
    window.addEventListener('orientationchange', () => {
        setTimeout(adjustLayout, 100);
    });
}

/**
 * Mobile-specific optimizations
 */
function initializeMobileOptimizations() {
    if (window.innerWidth > 767) return;

    // Optimize button sizes for mobile
    const buttons = document.querySelectorAll('.property-btn');
    buttons.forEach(button => {
        if (!button.classList.contains('property-btn-sm')) {
            button.style.minHeight = '44px';
            button.style.padding = '12px 16px';
        }
    });

    // Add mobile-specific interactions
    const priceCards = document.querySelectorAll('.property-price-card');
    priceCards.forEach(card => {
        card.addEventListener('touchstart', function() {
            this.style.transform = 'scale(0.98)';
        });
        
        card.addEventListener('touchend', function() {
            setTimeout(() => {
                this.style.transform = '';
            }, 150);
        });
    });

    // Improve contract items for mobile
    const contractItems = document.querySelectorAll('.property-contract-item');
    contractItems.forEach(item => {
        item.style.padding = '16px';
        item.style.marginBottom = '12px';
        item.style.borderRadius = '8px';
        item.style.border = '1px solid var(--property-gray-200)';
    });

    // Mobile-friendly agent card
    const agentCard = document.querySelector('.property-agent-container');
    if (agentCard) {
        agentCard.style.position = 'sticky';
        agentCard.style.bottom = '0';
        agentCard.style.zIndex = '10';
        agentCard.style.backgroundColor = 'white';
        agentCard.style.borderTop = '1px solid var(--property-gray-200)';
        agentCard.style.padding = '16px';
        agentCard.style.margin = '0 -16px';
    }
}

/**
 * Tablet-specific enhancements
 */
function initializeTabletEnhancements() {
    if (window.innerWidth < 768 || window.innerWidth >= 992) return;

    // Optimize thumbnail navigation for tablets
    const thumbnailNav = document.querySelector('.property-thumbnail-nav');
    if (thumbnailNav) {
        thumbnailNav.style.display = 'flex';
        thumbnailNav.style.overflowX = 'auto';
        thumbnailNav.style.gap = '8px';
        thumbnailNav.style.padding = '8px 0';
        thumbnailNav.style.scrollbarWidth = 'thin';
    }

    // Enhance feature display for tablets
    const featureItems = document.querySelectorAll('.property-feature-item');
    featureItems.forEach(item => {
        item.style.padding = '16px';
        item.style.borderRadius = '8px';
        item.style.backgroundColor = 'var(--property-light)';
        item.style.transition = 'all 0.2s ease';
        
        item.addEventListener('mouseenter', function() {
            this.style.backgroundColor = 'var(--property-primary-light)';
            this.style.transform = 'translateY(-2px)';
        });
        
        item.addEventListener('mouseleave', function() {
            this.style.backgroundColor = 'var(--property-light)';
            this.style.transform = '';
        });
    });

    // Tablet-optimized pricing layout
    const pricingContainer = document.querySelector('.property-pricing-container');
    if (pricingContainer) {
        pricingContainer.style.position = 'sticky';
        pricingContainer.style.top = '20px';
    }
}

// Add CSS animations for touch indicators
const style = document.createElement('style');
style.textContent = `
    @keyframes fadeInOut {
        0% { opacity: 0; transform: translateX(-50%) translateY(10px); }
        20% { opacity: 1; transform: translateX(-50%) translateY(0); }
        80% { opacity: 1; transform: translateX(-50%) translateY(0); }
        100% { opacity: 0; transform: translateX(-50%) translateY(-10px); }
    }
    
    .mobile-landscape .property-detail-header {
        padding: 8px 0;
    }
    
    .mobile-landscape .property-detail-title {
        font-size: 1.25rem;
    }
    
    @media (max-width: 767px) and (orientation: landscape) {
        .property-gallery-main {
            max-height: 60vh;
        }
        
        .property-carousel-inner {
            border-radius: 8px;
        }
    }
`;
document.head.appendChild(style);

// Export functions for external use
window.PropertyDetail = {
    showNotification,
    addLoadingState,
    isInViewport,
    debounce,
    throttle,
    initializeResponsiveEnhancements
};