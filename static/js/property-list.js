/**
 * Property List Template Enhancements
 * Handles interactive features for the property list page
 */

class PropertyListEnhancer {
    constructor() {
        this.init();
    }

    init() {
        this.initAnimatedCounters();
        this.initFilterEnhancements();
        this.initTableEnhancements();
        this.initSearchStateHandling();
    }

    /**
     * Initialize animated counters for statistics cards
     */
    initAnimatedCounters() {
        const counters = document.querySelectorAll('.property-stat-number[data-count]');
        
        const animateCounter = (element) => {
            const target = parseInt(element.getAttribute('data-count'));
            const duration = 1500; // 1.5 seconds
            const increment = target / (duration / 16); // 60fps
            let current = 0;
            
            const updateCounter = () => {
                current += increment;
                if (current < target) {
                    element.textContent = Math.floor(current).toLocaleString();
                    requestAnimationFrame(updateCounter);
                } else {
                    element.textContent = target.toLocaleString();
                }
            };
            
            updateCounter();
        };

        // Use Intersection Observer to trigger animation when cards come into view
        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting && !entry.target.classList.contains('animated')) {
                    entry.target.classList.add('animated');
                    animateCounter(entry.target);
                }
            });
        }, { threshold: 0.5 });

        counters.forEach(counter => {
            observer.observe(counter);
        });
    }

    /**
     * Initialize filter enhancements
     */
    initFilterEnhancements() {
        this.initActiveFilterDisplay();
        this.initFilterStateTracking();
        this.initAdvancedFiltersToggle();
        this.initFilterFormEnhancements();
    }

    /**
     * Display active filters as tags
     */
    initActiveFilterDisplay() {
        const filterForm = document.getElementById('filterForm');
        if (!filterForm) return;

        const createActiveFiltersDisplay = () => {
            const activeFilters = this.getActiveFilters();
            const existingDisplay = document.querySelector('.property-active-filters');
            
            if (activeFilters.length === 0) {
                if (existingDisplay) {
                    existingDisplay.remove();
                }
                return;
            }

            let filtersHTML = `
                <div class="property-active-filters">
                    <div class="property-active-filters-title">
                        <i class="bi bi-funnel-fill"></i>
                        Filtros Activos (${activeFilters.length})
                    </div>
                    <div class="property-active-filters-list">
            `;

            activeFilters.forEach(filter => {
                const removeUrl = this.buildRemoveFilterUrl(filter.name);
                filtersHTML += `
                    <a href="${removeUrl}" class="property-active-filter-tag" title="Remover filtro: ${filter.label}">
                        ${filter.label}: ${filter.value}
                        <button type="button" class="property-active-filter-remove" aria-label="Remover">
                            <i class="bi bi-x"></i>
                        </button>
                    </a>
                `;
            });

            filtersHTML += `
                    </div>
                </div>
            `;

            if (existingDisplay) {
                existingDisplay.outerHTML = filtersHTML;
            } else {
                const filtersCard = document.getElementById('filtersCard');
                if (filtersCard) {
                    filtersCard.insertAdjacentHTML('afterend', filtersHTML);
                }
            }
        };

        // Create initial display
        createActiveFiltersDisplay();

        // Update on form changes
        filterForm.addEventListener('change', () => {
            setTimeout(createActiveFiltersDisplay, 100);
        });
    }

    /**
     * Get active filters from the form
     */
    getActiveFilters() {
        const filters = [];
        const form = document.getElementById('filterForm');
        if (!form) return filters;

        const formData = new FormData(form);
        const filterLabels = {
            'search': 'Búsqueda',
            'property_type': 'Tipo',
            'property_status': 'Estado',
            'sort': 'Ordenar',
            'min_sale_price': 'Precio mín. venta',
            'max_sale_price': 'Precio máx. venta',
            'min_rental_price': 'Precio mín. alquiler',
            'max_rental_price': 'Precio máx. alquiler',
            'bedrooms': 'Dormitorios',
            'bathrooms': 'Baños',
            'agent': 'Agente',
            'garage': 'Garage',
            'furnished': 'Amueblado',
            'year_built': 'Año construcción'
        };

        for (const [name, value] of formData.entries()) {
            if (value && value.trim() !== '' && filterLabels[name]) {
                let displayValue = value;
                
                // Format specific values
                if (name.includes('price') && !isNaN(value)) {
                    displayValue = '$' + parseInt(value).toLocaleString();
                } else if (name === 'garage' || name === 'furnished') {
                    displayValue = value === 'true' ? 'Sí' : 'No';
                } else if (name === 'sort') {
                    const sortOptions = {
                        '-created_at': 'Más recientes',
                        'created_at': 'Más antiguos',
                        'title': 'Título (A-Z)',
                        '-title': 'Título (Z-A)',
                        'sale_price': 'Precio venta (menor)',
                        '-sale_price': 'Precio venta (mayor)',
                        'rental_price': 'Precio alquiler (menor)',
                        '-rental_price': 'Precio alquiler (mayor)',
                        '-total_surface': 'Superficie (mayor)',
                        'total_surface': 'Superficie (menor)',
                        '-bedrooms': 'Más dormitorios',
                        'bedrooms': 'Menos dormitorios'
                    };
                    displayValue = sortOptions[value] || value;
                }

                filters.push({
                    name: name,
                    label: filterLabels[name],
                    value: displayValue
                });
            }
        }

        return filters;
    }

    /**
     * Build URL to remove a specific filter
     */
    buildRemoveFilterUrl(filterName) {
        const url = new URL(window.location);
        url.searchParams.delete(filterName);
        return url.toString();
    }

    /**
     * Track filter state and add visual feedback
     */
    initFilterStateTracking() {
        const filterInputs = document.querySelectorAll('#filterForm input, #filterForm select');
        
        filterInputs.forEach(input => {
            const updateFilterState = () => {
                if (input.value && input.value.trim() !== '') {
                    input.classList.add('has-value');
                } else {
                    input.classList.remove('has-value');
                }
            };

            // Initial state
            updateFilterState();

            // Update on change
            input.addEventListener('input', updateFilterState);
            input.addEventListener('change', updateFilterState);
        });
    }

    /**
     * Initialize advanced filters toggle
     */
    initAdvancedFiltersToggle() {
        const toggleButton = document.querySelector('[data-bs-target="#advancedFilters"]');
        const advancedSection = document.getElementById('advancedFilters');
        
        if (!toggleButton || !advancedSection) return;

        const updateToggleState = () => {
            const isExpanded = advancedSection.classList.contains('show');
            toggleButton.setAttribute('aria-expanded', isExpanded);
            
            const icon = toggleButton.querySelector('.property-advanced-icon');
            if (icon) {
                icon.style.transform = isExpanded ? 'rotate(180deg)' : 'rotate(0deg)';
            }
        };

        // Listen for Bootstrap collapse events
        advancedSection.addEventListener('shown.bs.collapse', updateToggleState);
        advancedSection.addEventListener('hidden.bs.collapse', updateToggleState);
        
        // Initial state
        updateToggleState();
    }

    /**
     * Initialize form enhancements
     */
    initFilterFormEnhancements() {
        const form = document.getElementById('filterForm');
        if (!form) return;

        // Add loading state to submit button
        form.addEventListener('submit', (e) => {
            const submitButton = form.querySelector('button[type="submit"]');
            if (submitButton) {
                submitButton.disabled = true;
                submitButton.innerHTML = '<i class="bi bi-hourglass-split property-spin me-1"></i>Buscando...';
            }
        });

        // Auto-submit on certain field changes (with debounce)
        const autoSubmitFields = form.querySelectorAll('select[name="sort"], select[name="property_type"], select[name="property_status"]');
        let submitTimeout;

        autoSubmitFields.forEach(field => {
            field.addEventListener('change', () => {
                clearTimeout(submitTimeout);
                submitTimeout = setTimeout(() => {
                    form.submit();
                }, 300);
            });
        });
    }

    /**
     * Initialize table enhancements
     */
    initTableEnhancements() {
        this.initTableRowHoverEffects();
        this.initTableImagePreview();
        this.initTableActionTooltips();
    }

    /**
     * Enhanced table row hover effects
     */
    initTableRowHoverEffects() {
        const tableRows = document.querySelectorAll('.property-table tbody tr');
        
        tableRows.forEach(row => {
            row.addEventListener('mouseenter', () => {
                row.style.transform = 'translateX(4px)';
                row.style.boxShadow = 'inset 4px 0 0 var(--property-primary)';
            });

            row.addEventListener('mouseleave', () => {
                row.style.transform = '';
                row.style.boxShadow = '';
            });
        });
    }

    /**
     * Initialize table image preview on hover
     */
    initTableImagePreview() {
        const tableImages = document.querySelectorAll('.property-table-image');
        
        tableImages.forEach(img => {
            img.addEventListener('mouseenter', () => {
                img.style.transform = 'scale(1.1)';
                img.style.zIndex = '10';
            });

            img.addEventListener('mouseleave', () => {
                img.style.transform = '';
                img.style.zIndex = '';
            });
        });
    }

    /**
     * Initialize action button tooltips
     */
    initTableActionTooltips() {
        const actionButtons = document.querySelectorAll('.property-table-action');
        
        actionButtons.forEach(button => {
            // Add tooltip based on button class
            let tooltipText = '';
            if (button.classList.contains('property-table-action-view')) {
                tooltipText = 'Ver detalles';
            } else if (button.classList.contains('property-table-action-edit')) {
                tooltipText = 'Editar propiedad';
            } else if (button.classList.contains('property-table-action-delete')) {
                tooltipText = 'Eliminar propiedad';
            }

            if (tooltipText) {
                button.setAttribute('title', tooltipText);
                button.setAttribute('data-bs-toggle', 'tooltip');
            }
        });

        // Initialize Bootstrap tooltips if available
        if (typeof bootstrap !== 'undefined' && bootstrap.Tooltip) {
            const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
            tooltipTriggerList.map(function (tooltipTriggerEl) {
                return new bootstrap.Tooltip(tooltipTriggerEl);
            });
        }
    }

    /**
     * Initialize search state handling
     */
    initSearchStateHandling() {
        const searchInput = document.getElementById('searchQuery');
        if (!searchInput) return;

        let searchTimeout;
        
        searchInput.addEventListener('input', (e) => {
            clearTimeout(searchTimeout);
            const query = e.target.value.trim();
            
            // Add visual feedback for active search
            if (query.length > 0) {
                searchInput.classList.add('has-value');
            } else {
                searchInput.classList.remove('has-value');
            }

            // Auto-search with debounce (optional)
            if (query.length >= 3) {
                searchTimeout = setTimeout(() => {
                    // Could trigger auto-search here
                    console.log('Auto-search for:', query);
                }, 500);
            }
        });

        // Clear search functionality
        const clearSearchButton = document.createElement('button');
        clearSearchButton.type = 'button';
        clearSearchButton.className = 'btn btn-sm btn-outline-secondary position-absolute';
        clearSearchButton.style.cssText = 'right: 8px; top: 50%; transform: translateY(-50%); z-index: 5; display: none;';
        clearSearchButton.innerHTML = '<i class="bi bi-x"></i>';
        clearSearchButton.title = 'Limpiar búsqueda';

        const searchContainer = searchInput.parentElement;
        searchContainer.style.position = 'relative';
        searchContainer.appendChild(clearSearchButton);

        const updateClearButton = () => {
            if (searchInput.value.trim().length > 0) {
                clearSearchButton.style.display = 'block';
            } else {
                clearSearchButton.style.display = 'none';
            }
        };

        searchInput.addEventListener('input', updateClearButton);
        updateClearButton(); // Initial state

        clearSearchButton.addEventListener('click', () => {
            searchInput.value = '';
            searchInput.classList.remove('has-value');
            updateClearButton();
            searchInput.focus();
        });
    }
}

    /**
     * Initialize responsive enhancements
     */
    initResponsiveEnhancements() {
        this.initTouchFriendlyInteractions();
        this.initResponsiveTableHandling();
        this.initMobileFilterEnhancements();
        this.initViewportAdjustments();
    }

    /**
     * Touch-friendly interactions for mobile devices
     */
    initTouchFriendlyInteractions() {
        // Add touch feedback to buttons
        const buttons = document.querySelectorAll('.property-btn, .property-table-action');
        
        buttons.forEach(button => {
            button.addEventListener('touchstart', function() {
                this.style.transform = 'scale(0.95)';
            });
            
            button.addEventListener('touchend', function() {
                setTimeout(() => {
                    this.style.transform = '';
                }, 150);
            });
        });

        // Improve touch scrolling for horizontal tables
        const tableContainer = document.querySelector('.table-responsive');
        if (tableContainer) {
            let isScrolling = false;
            
            tableContainer.addEventListener('touchstart', () => {
                isScrolling = false;
            });
            
            tableContainer.addEventListener('touchmove', () => {
                isScrolling = true;
            });
            
            // Prevent accidental clicks while scrolling
            tableContainer.addEventListener('touchend', (e) => {
                if (isScrolling) {
                    e.preventDefault();
                }
            });
        }
    }

    /**
     * Responsive table handling
     */
    initResponsiveTableHandling() {
        const table = document.querySelector('.property-table');
        const tableContainer = document.querySelector('.table-responsive');
        
        if (!table || !tableContainer) return;

        // Add scroll indicators for mobile
        const addScrollIndicators = () => {
            if (window.innerWidth <= 575) {
                const scrollIndicator = document.createElement('div');
                scrollIndicator.className = 'table-scroll-indicator';
                scrollIndicator.innerHTML = '<i class="bi bi-arrow-left-right"></i> Desliza para ver más';
                scrollIndicator.style.cssText = `
                    position: absolute;
                    top: 10px;
                    right: 10px;
                    background: var(--property-primary);
                    color: white;
                    padding: 4px 8px;
                    border-radius: 4px;
                    font-size: 12px;
                    z-index: 10;
                    animation: pulse 2s infinite;
                `;
                
                tableContainer.style.position = 'relative';
                tableContainer.appendChild(scrollIndicator);
                
                // Hide indicator after first scroll
                tableContainer.addEventListener('scroll', () => {
                    scrollIndicator.style.display = 'none';
                }, { once: true });
            }
        };

        addScrollIndicators();
        
        // Update on resize
        window.addEventListener('resize', debounce(() => {
            const existingIndicator = tableContainer.querySelector('.table-scroll-indicator');
            if (existingIndicator) {
                existingIndicator.remove();
            }
            addScrollIndicators();
        }, 250));
    }

    /**
     * Mobile filter enhancements
     */
    initMobileFilterEnhancements() {
        const filterToggle = document.querySelector('[data-bs-target="#filtersCard"]');
        const filtersCard = document.getElementById('filtersCard');
        
        if (!filterToggle || !filtersCard) return;

        // Add mobile-specific filter behavior
        if (window.innerWidth <= 767) {
            // Auto-collapse filters after applying on mobile
            const filterForm = document.getElementById('filterForm');
            if (filterForm) {
                filterForm.addEventListener('submit', () => {
                    if (filtersCard.classList.contains('show')) {
                        const bsCollapse = bootstrap.Collapse.getInstance(filtersCard);
                        if (bsCollapse) {
                            bsCollapse.hide();
                        }
                    }
                });
            }

            // Improve filter toggle button text for mobile
            const updateToggleText = () => {
                const isExpanded = filtersCard.classList.contains('show');
                const icon = filterToggle.querySelector('i');
                const text = filterToggle.childNodes[filterToggle.childNodes.length - 1];
                
                if (icon) {
                    icon.className = isExpanded ? 'bi bi-x me-1' : 'bi bi-funnel me-1';
                }
                if (text && text.nodeType === Node.TEXT_NODE) {
                    text.textContent = isExpanded ? 'Cerrar' : 'Filtros';
                }
            };

            filtersCard.addEventListener('shown.bs.collapse', updateToggleText);
            filtersCard.addEventListener('hidden.bs.collapse', updateToggleText);
        }
    }

    /**
     * Viewport-based adjustments
     */
    initViewportAdjustments() {
        const adjustForViewport = () => {
            const viewport = {
                width: window.innerWidth,
                height: window.innerHeight
            };

            // Adjust stats grid based on viewport
            const statsGrid = document.querySelector('.property-stats-grid');
            if (statsGrid) {
                if (viewport.width <= 575) {
                    statsGrid.style.gridTemplateColumns = '1fr';
                } else if (viewport.width <= 767) {
                    statsGrid.style.gridTemplateColumns = 'repeat(2, 1fr)';
                } else {
                    statsGrid.style.gridTemplateColumns = 'repeat(4, 1fr)';
                }
            }

            // Adjust table font size for very small screens
            const table = document.querySelector('.property-table');
            if (table && viewport.width <= 480) {
                table.style.fontSize = '11px';
            } else if (table) {
                table.style.fontSize = '';
            }

            // Handle landscape orientation on mobile
            if (viewport.width <= 767 && viewport.width > viewport.height) {
                document.body.classList.add('mobile-landscape');
            } else {
                document.body.classList.remove('mobile-landscape');
            }
        };

        // Initial adjustment
        adjustForViewport();

        // Adjust on resize with debounce
        window.addEventListener('resize', debounce(adjustForViewport, 250));
        
        // Adjust on orientation change
        window.addEventListener('orientationchange', () => {
            setTimeout(adjustForViewport, 100);
        });
    }
}

// Debounce utility function
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

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    const enhancer = new PropertyListEnhancer();
    enhancer.initResponsiveEnhancements();
});

// Export for potential external use
if (typeof module !== 'undefined' && module.exports) {
    module.exports = PropertyListEnhancer;
}