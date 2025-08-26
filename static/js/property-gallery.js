/**
 * Property Gallery Enhanced Functionality
 * Implements smooth transitions, lightbox modal, and improved UX
 */

class PropertyGallery {
    constructor() {
        this.currentView = 'grid';
        this.currentImageIndex = 0;
        this.images = [];
        this.modal = null;
        this.isModalOpen = false;
        
        this.init();
    }
    
    init() {
        this.loadImages();
        this.setupViewToggle();
        this.setupModal();
        this.setupKeyboardNavigation();
        this.setupTouchNavigation();
        this.loadSavedView();
        this.setupImageLoading();
    }
    
    loadImages() {
        // Extract image data from the DOM
        const imageElements = document.querySelectorAll('[data-image-url]');
        this.images = Array.from(imageElements).map((el, index) => ({
            id: el.dataset.imageId,
            url: el.dataset.imageUrl,
            description: el.dataset.imageDescription || 'Sin descripción',
            index: index
        }));
    }
    
    setupViewToggle() {
        const gridBtn = document.getElementById('btn-grid');
        const listBtn = document.getElementById('btn-list');
        
        if (gridBtn && listBtn) {
            gridBtn.addEventListener('click', () => this.toggleView('grid'));
            listBtn.addEventListener('click', () => this.toggleView('list'));
        }
    }
    
    toggleView(view) {
        const gridView = document.getElementById('grid-view');
        const listView = document.getElementById('list-view');
        const btnGrid = document.getElementById('btn-grid');
        const btnList = document.getElementById('btn-list');
        
        if (!gridView || !listView) return;
        
        // Add transition classes
        gridView.style.transition = 'opacity 0.3s ease-in-out, transform 0.3s ease-in-out';
        listView.style.transition = 'opacity 0.3s ease-in-out, transform 0.3s ease-in-out';
        
        if (view === 'grid') {
            this.animateViewTransition(listView, gridView);
            btnGrid?.classList.add('active');
            btnList?.classList.remove('active');
        } else {
            this.animateViewTransition(gridView, listView);
            btnGrid?.classList.remove('active');
            btnList?.classList.add('active');
        }
        
        this.currentView = view;
        localStorage.setItem('gallery-view', view);
    }
    
    animateViewTransition(hideView, showView) {
        // Fade out current view
        hideView.style.opacity = '0';
        hideView.style.transform = 'translateY(-10px)';
        
        setTimeout(() => {
            hideView.classList.add('d-none');
            showView.classList.remove('d-none');
            
            // Fade in new view
            showView.style.opacity = '0';
            showView.style.transform = 'translateY(10px)';
            
            requestAnimationFrame(() => {
                showView.style.opacity = '1';
                showView.style.transform = 'translateY(0)';
            });
        }, 150);
    }
    
    setupModal() {
        const modalElement = document.getElementById('imageModal');
        if (modalElement) {
            this.modal = new bootstrap.Modal(modalElement);
            
            // Setup modal event listeners
            modalElement.addEventListener('shown.bs.modal', () => {
                this.isModalOpen = true;
                document.body.classList.add('modal-keyboard-nav');
            });
            
            modalElement.addEventListener('hidden.bs.modal', () => {
                this.isModalOpen = false;
                document.body.classList.remove('modal-keyboard-nav');
            });
        }
    }
    
    openImageModal(imageUrl, description, imageId) {
        const modalImage = document.getElementById('modalImage');
        const imageDescription = document.getElementById('imageDescription');
        const deleteBtn = document.getElementById('deleteImageBtn');
        
        if (!modalImage) return;
        
        // Find current image index
        this.currentImageIndex = this.images.findIndex(img => img.id == imageId);
        if (this.currentImageIndex === -1) this.currentImageIndex = 0;
        
        // Show loading state
        modalImage.style.opacity = '0.5';
        modalImage.src = '';
        
        // Load image with fade-in effect
        const img = new Image();
        img.onload = () => {
            modalImage.src = imageUrl;
            modalImage.style.opacity = '1';
            modalImage.style.transition = 'opacity 0.3s ease-in-out';
        };
        img.src = imageUrl;
        
        // Update modal content
        if (imageDescription) {
            imageDescription.textContent = description || 'Sin descripción';
        }
        
        if (deleteBtn && imageId) {
            const baseUrl = deleteBtn.dataset.baseUrl || '';
            deleteBtn.href = baseUrl.replace('0', imageId);
        }
        
        // Update counter
        this.updateImageCounter();
        
        // Show modal
        if (this.modal) {
            this.modal.show();
        }
    }
    
    setupKeyboardNavigation() {
        document.addEventListener('keydown', (e) => {
            if (!this.isModalOpen || this.images.length <= 1) return;
            
            switch(e.key) {
                case 'ArrowLeft':
                    e.preventDefault();
                    this.navigateImage('prev');
                    break;
                case 'ArrowRight':
                    e.preventDefault();
                    this.navigateImage('next');
                    break;
                case 'Escape':
                    if (this.modal) {
                        this.modal.hide();
                    }
                    break;
            }
        });
    }
    
    setupTouchNavigation() {
        let startX = 0;
        let startY = 0;
        
        const modalImage = document.getElementById('modalImage');
        if (!modalImage) return;
        
        modalImage.addEventListener('touchstart', (e) => {
            if (!this.isModalOpen || this.images.length <= 1) return;
            
            startX = e.touches[0].clientX;
            startY = e.touches[0].clientY;
        });
        
        modalImage.addEventListener('touchend', (e) => {
            if (!this.isModalOpen || this.images.length <= 1) return;
            
            const endX = e.changedTouches[0].clientX;
            const endY = e.changedTouches[0].clientY;
            
            const deltaX = endX - startX;
            const deltaY = endY - startY;
            
            // Only trigger if horizontal swipe is more significant than vertical
            if (Math.abs(deltaX) > Math.abs(deltaY) && Math.abs(deltaX) > 50) {
                if (deltaX > 0) {
                    this.navigateImage('prev');
                } else {
                    this.navigateImage('next');
                }
            }
        });
    }
    
    navigateImage(direction) {
        if (this.images.length === 0) return;
        
        if (direction === 'next') {
            this.currentImageIndex = (this.currentImageIndex + 1) % this.images.length;
        } else {
            this.currentImageIndex = this.currentImageIndex === 0 
                ? this.images.length - 1 
                : this.currentImageIndex - 1;
        }
        
        const currentImage = this.images[this.currentImageIndex];
        if (currentImage) {
            this.updateModalImage(currentImage);
            this.updateImageCounter();
        }
    }
    
    updateModalImage(image) {
        const modalImage = document.getElementById('modalImage');
        const imageDescription = document.getElementById('imageDescription');
        const deleteBtn = document.getElementById('deleteImageBtn');
        
        if (!modalImage) return;
        
        // Show loading state
        modalImage.style.opacity = '0.5';
        
        // Load new image
        const img = new Image();
        img.onload = () => {
            modalImage.src = image.url;
            modalImage.style.opacity = '1';
        };
        img.src = image.url;
        
        // Update description
        if (imageDescription) {
            imageDescription.textContent = image.description || 'Sin descripción';
        }
        
        // Update delete button
        if (deleteBtn && image.id) {
            const baseUrl = deleteBtn.dataset.baseUrl || '';
            deleteBtn.href = baseUrl.replace('0', image.id);
        }
    }
    
    updateImageCounter() {
        const counter = document.getElementById('imageCounter');
        if (counter && this.images.length > 1) {
            counter.textContent = `${this.currentImageIndex + 1} de ${this.images.length}`;
        }
    }
    
    loadSavedView() {
        const savedView = localStorage.getItem('gallery-view') || 'grid';
        this.toggleView(savedView);
    }
    
    setupImageLoading() {
        // Setup lazy loading and loading states for images
        const images = document.querySelectorAll('.property-gallery-image');
        
        images.forEach(img => {
            // Add loading placeholder
            const placeholder = this.createImagePlaceholder();
            img.parentNode.insertBefore(placeholder, img);
            
            img.addEventListener('load', () => {
                img.style.opacity = '1';
                placeholder.remove();
            });
            
            img.addEventListener('error', () => {
                this.handleImageError(img);
                placeholder.remove();
            });
            
            // Initially hide image until loaded
            img.style.opacity = '0';
            img.style.transition = 'opacity 0.3s ease-in-out';
        });
    }
    
    createImagePlaceholder() {
        const placeholder = document.createElement('div');
        placeholder.className = 'image-placeholder';
        placeholder.innerHTML = `
            <div class="placeholder-content">
                <div class="spinner-border spinner-border-sm text-primary" role="status">
                    <span class="visually-hidden">Cargando...</span>
                </div>
            </div>
        `;
        return placeholder;
    }
    
    handleImageError(img) {
        const errorPlaceholder = document.createElement('div');
        errorPlaceholder.className = 'image-error-placeholder';
        errorPlaceholder.innerHTML = `
            <div class="error-content">
                <i class="bi bi-image text-muted"></i>
                <small class="text-muted">Error al cargar imagen</small>
            </div>
        `;
        
        img.parentNode.replaceChild(errorPlaceholder, img);
    }
}

/**
 * Initialize responsive gallery enhancements
 */
function initializeResponsiveGallery() {
    initializeMobileGalleryOptimizations();
    initializeTabletGalleryEnhancements();
    initializeTouchGalleryControls();
    initializeResponsiveModal();
    initializeViewportAdjustments();
}

/**
 * Mobile gallery optimizations
 */
function initializeMobileGalleryOptimizations() {
    if (window.innerWidth > 767) return;

    // Mobile-optimized gallery grid
    const galleryGrid = document.querySelector('.property-gallery-grid');
    if (galleryGrid) {
        galleryGrid.style.gridTemplateColumns = '1fr';
        galleryGrid.style.gap = '16px';
        galleryGrid.style.padding = '16px';
    }

    // Mobile view toggle
    const viewToggle = document.querySelector('.view-toggle-buttons');
    if (viewToggle) {
        viewToggle.style.position = 'sticky';
        viewToggle.style.top = '10px';
        viewToggle.style.zIndex = '10';
        viewToggle.style.backgroundColor = 'white';
        viewToggle.style.padding = '8px';
        viewToggle.style.borderRadius = '8px';
        viewToggle.style.boxShadow = '0 2px 8px rgba(0,0,0,0.1)';
        viewToggle.style.margin = '0 -16px 16px -16px';
    }

    // Mobile gallery cards
    const galleryCards = document.querySelectorAll('.property-gallery-card');
    galleryCards.forEach(card => {
        card.style.borderRadius = '8px';
        card.style.marginBottom = '16px';
    });

    // Mobile image containers
    const imageContainers = document.querySelectorAll('.property-image-container');
    imageContainers.forEach(container => {
        container.style.aspectRatio = '4/3'; // Better for mobile viewing
    });

    // Mobile-friendly image actions
    const imageActions = document.querySelectorAll('.property-image-actions');
    imageActions.forEach(actions => {
        actions.style.padding = '12px';
        actions.style.gap = '8px';
    });

    const actionButtons = document.querySelectorAll('.property-image-actions .btn');
    actionButtons.forEach(button => {
        button.style.minHeight = '44px';
        button.style.minWidth = '44px';
        button.style.padding = '8px 12px';
    });
}

/**
 * Tablet gallery enhancements
 */
function initializeTabletGalleryEnhancements() {
    if (window.innerWidth < 768 || window.innerWidth >= 992) return;

    // Tablet-optimized gallery grid
    const galleryGrid = document.querySelector('.property-gallery-grid');
    if (galleryGrid) {
        galleryGrid.style.gridTemplateColumns = 'repeat(2, 1fr)';
        galleryGrid.style.gap = '20px';
        galleryGrid.style.padding = '20px';
    }

    // Tablet view toggle
    const viewToggle = document.querySelector('.view-toggle-buttons');
    if (viewToggle) {
        viewToggle.style.position = 'sticky';
        viewToggle.style.top = '20px';
        viewToggle.style.marginBottom = '24px';
    }

    // Tablet gallery cards
    const galleryCards = document.querySelectorAll('.property-gallery-card');
    galleryCards.forEach(card => {
        card.style.borderRadius = '12px';
    });

    // Tablet image actions
    const imageActions = document.querySelectorAll('.property-image-actions');
    imageActions.forEach(actions => {
        actions.style.padding = '16px';
        actions.style.gap = '12px';
    });
}

/**
 * Touch-friendly gallery controls
 */
function initializeTouchGalleryControls() {
    // Touch feedback for gallery cards
    const galleryCards = document.querySelectorAll('.property-gallery-card');
    
    galleryCards.forEach(card => {
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
    });

    // Touch-friendly action buttons
    const actionButtons = document.querySelectorAll('.property-image-actions .btn');
    actionButtons.forEach(button => {
        button.addEventListener('touchstart', function(e) {
            e.stopPropagation();
            this.style.transform = 'scale(0.9)';
        });
        
        button.addEventListener('touchend', function(e) {
            e.stopPropagation();
            setTimeout(() => {
                this.style.transform = '';
            }, 150);
        });
    });

    // Touch-friendly view toggle
    const viewToggleButtons = document.querySelectorAll('.view-toggle-buttons .btn');
    viewToggleButtons.forEach(button => {
        button.addEventListener('touchstart', function() {
            this.style.transform = 'scale(0.95)';
        });
        
        button.addEventListener('touchend', function() {
            setTimeout(() => {
                this.style.transform = '';
            }, 150);
        });
    });

    // Swipe gestures for image navigation in modal
    let touchStartX = 0;
    let touchEndX = 0;

    const modal = document.getElementById('imageModal');
    if (modal) {
        modal.addEventListener('touchstart', function(e) {
            touchStartX = e.touches[0].clientX;
        }, { passive: true });

        modal.addEventListener('touchend', function(e) {
            touchEndX = e.changedTouches[0].clientX;
            handleSwipe();
        }, { passive: true });

        function handleSwipe() {
            const threshold = 50;
            const diff = touchStartX - touchEndX;

            if (Math.abs(diff) > threshold) {
                const prevButton = modal.querySelector('.modal-nav-prev');
                const nextButton = modal.querySelector('.modal-nav-next');

                if (diff > 0 && nextButton) {
                    nextButton.click();
                } else if (diff < 0 && prevButton) {
                    prevButton.click();
                }
            }
        }
    }
}

/**
 * Responsive modal enhancements
 */
function initializeResponsiveModal() {
    const modal = document.getElementById('imageModal');
    if (!modal) return;

    // Mobile modal optimizations
    if (window.innerWidth <= 767) {
        const modalDialog = modal.querySelector('.modal-dialog');
        if (modalDialog) {
            modalDialog.style.maxWidth = '95vw';
            modalDialog.style.margin = '10px auto';
        }

        const modalContent = modal.querySelector('.modal-content');
        if (modalContent) {
            modalContent.style.borderRadius = '8px';
        }

        // Mobile modal navigation
        const modalNavButtons = modal.querySelectorAll('.modal-nav-prev, .modal-nav-next');
        modalNavButtons.forEach(button => {
            button.style.width = '44px';
            button.style.height = '44px';
            button.style.fontSize = '20px';
            button.style.borderRadius = '50%';
            button.style.backgroundColor = 'var(--property-primary)';
            button.style.border = '2px solid white';
            button.style.color = 'white';
            button.style.boxShadow = '0 2px 8px rgba(0,0,0,0.2)';
        });

        // Add touch indicator for mobile modal
        const addModalTouchIndicator = () => {
            const indicator = document.createElement('div');
            indicator.className = 'modal-touch-indicator';
            indicator.innerHTML = '<i class="bi bi-arrow-left-right"></i> Desliza para navegar';
            indicator.style.cssText = `
                position: absolute;
                bottom: 20px;
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
            
            modal.appendChild(indicator);
            
            setTimeout(() => {
                if (indicator.parentNode) {
                    indicator.remove();
                }
            }, 3000);
        };

        // Show touch indicator when modal opens
        modal.addEventListener('shown.bs.modal', () => {
            setTimeout(addModalTouchIndicator, 500);
        });
    }

    // Tablet modal optimizations
    if (window.innerWidth >= 768 && window.innerWidth < 992) {
        const modalDialog = modal.querySelector('.modal-dialog');
        if (modalDialog) {
            modalDialog.style.maxWidth = '90vw';
        }
    }
}

/**
 * Viewport-based adjustments
 */
function initializeViewportAdjustments() {
    const adjustGalleryForViewport = () => {
        const viewport = {
            width: window.innerWidth,
            height: window.innerHeight
        };

        const galleryGrid = document.querySelector('.property-gallery-grid');
        if (!galleryGrid) return;

        // Adjust grid columns based on viewport
        if (viewport.width <= 575) {
            galleryGrid.style.gridTemplateColumns = '1fr';
            galleryGrid.style.gap = '16px';
        } else if (viewport.width <= 767) {
            galleryGrid.style.gridTemplateColumns = '1fr';
            galleryGrid.style.gap = '20px';
        } else if (viewport.width <= 991) {
            galleryGrid.style.gridTemplateColumns = 'repeat(2, 1fr)';
            galleryGrid.style.gap = '24px';
        } else if (viewport.width <= 1199) {
            galleryGrid.style.gridTemplateColumns = 'repeat(3, 1fr)';
            galleryGrid.style.gap = '24px';
        } else {
            galleryGrid.style.gridTemplateColumns = 'repeat(4, 1fr)';
            galleryGrid.style.gap = '24px';
        }

        // Adjust image aspect ratio for mobile landscape
        const imageContainers = document.querySelectorAll('.property-image-container');
        if (viewport.width <= 767 && viewport.width > viewport.height) {
            imageContainers.forEach(container => {
                container.style.aspectRatio = '16/9';
            });
        } else if (viewport.width <= 767) {
            imageContainers.forEach(container => {
                container.style.aspectRatio = '4/3';
            });
        } else {
            imageContainers.forEach(container => {
                container.style.aspectRatio = '16/9';
            });
        }

        // Handle landscape orientation
        if (viewport.width <= 767 && viewport.width > viewport.height) {
            document.body.classList.add('mobile-landscape');
        } else {
            document.body.classList.remove('mobile-landscape');
        }
    };

    // Initial adjustment
    adjustGalleryForViewport();

    // Adjust on resize and orientation change
    window.addEventListener('resize', debounce(adjustGalleryForViewport, 250));
    window.addEventListener('orientationchange', () => {
        setTimeout(adjustGalleryForViewport, 100);
    });
}

// Debounce utility
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

// Add responsive CSS for gallery
const responsiveGalleryStyles = document.createElement('style');
responsiveGalleryStyles.textContent = `
    /* Mobile gallery optimizations */
    @media (max-width: 767px) {
        .property-gallery-container {
            padding: 16px 0;
        }
        
        .view-toggle-buttons {
            position: sticky !important;
            top: 10px !important;
            z-index: 10 !important;
            background: white !important;
            padding: 8px !important;
            border-radius: 8px !important;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1) !important;
            margin: 0 -16px 16px -16px !important;
        }
        
        .property-gallery-grid {
            grid-template-columns: 1fr !important;
            gap: 16px !important;
            padding: 16px !important;
        }
        
        .property-gallery-card {
            border-radius: 8px !important;
            margin-bottom: 16px !important;
        }
        
        .property-image-container {
            aspect-ratio: 4/3 !important;
        }
        
        .property-image-actions {
            padding: 12px !important;
            gap: 8px !important;
        }
        
        .property-image-actions .btn {
            min-height: 44px !important;
            min-width: 44px !important;
            padding: 8px 12px !important;
        }
        
        .modal-dialog {
            max-width: 95vw !important;
            margin: 10px auto !important;
        }
        
        .modal-nav-prev,
        .modal-nav-next {
            width: 44px !important;
            height: 44px !important;
            font-size: 20px !important;
            border-radius: 50% !important;
            background-color: var(--property-primary) !important;
            border: 2px solid white !important;
            color: white !important;
            box-shadow: 0 2px 8px rgba(0,0,0,0.2) !important;
        }
    }
    
    /* Tablet gallery optimizations */
    @media (min-width: 768px) and (max-width: 991px) {
        .property-gallery-grid {
            grid-template-columns: repeat(2, 1fr) !important;
            gap: 20px !important;
            padding: 20px !important;
        }
        
        .view-toggle-buttons {
            position: sticky !important;
            top: 20px !important;
            margin-bottom: 24px !important;
        }
        
        .property-gallery-card {
            border-radius: 12px !important;
        }
        
        .property-image-actions {
            padding: 16px !important;
            gap: 12px !important;
        }
        
        .modal-dialog {
            max-width: 90vw !important;
        }
    }
    
    /* Touch device optimizations */
    @media (hover: none) and (pointer: coarse) {
        .property-image-actions .btn {
            min-height: 44px !important;
            min-width: 44px !important;
        }
        
        .view-toggle-buttons .btn {
            min-height: 44px !important;
            padding: 12px 16px !important;
        }
    }
    
    /* Landscape mobile optimizations */
    @media (max-width: 767px) and (orientation: landscape) {
        .property-image-container {
            aspect-ratio: 16/9 !important;
        }
        
        .view-toggle-buttons {
            position: relative !important;
            top: auto !important;
            margin: 0 0 16px 0 !important;
        }
    }
    
    @keyframes fadeInOut {
        0% { opacity: 0; transform: translateX(-50%) translateY(10px); }
        20% { opacity: 1; transform: translateX(-50%) translateY(0); }
        80% { opacity: 1; transform: translateX(-50%) translateY(0); }
        100% { opacity: 0; transform: translateX(-50%) translateY(-10px); }
    }
`;
document.head.appendChild(responsiveGalleryStyles);

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    new PropertyGallery();
    initializeResponsiveGallery();
});

// Global functions for backward compatibility
function toggleView(view) {
    if (window.propertyGallery) {
        window.propertyGallery.toggleView(view);
    }
}

function openImageModal(imageUrl, description, imageId) {
    if (window.propertyGallery) {
        window.propertyGallery.openImageModal(imageUrl, description, imageId);
    }
}