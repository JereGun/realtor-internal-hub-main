/**
 * Owner Receipts JavaScript functionality
 * Handles AJAX operations and UI interactions for owner receipts
 */

// Common functions for owner receipts
const OwnerReceipts = {
    
    /**
     * Show alert message to user with enhanced styling and animations
     */
    showAlert: function(type, message, duration = 5000) {
        // Remove any existing alerts first
        const existingAlerts = document.querySelectorAll('.owner-receipt-alert');
        existingAlerts.forEach(alert => alert.remove());
        
        const alertDiv = document.createElement('div');
        alertDiv.className = `alert alert-${type} alert-dismissible fade show position-fixed owner-receipt-alert`;
        alertDiv.style.cssText = `
            top: 20px; 
            right: 20px; 
            z-index: 9999; 
            min-width: 350px; 
            max-width: 500px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
            border: none;
            animation: slideInRight 0.3s ease-out;
        `;
        
        // Add custom CSS for animation if not already added
        if (!document.getElementById('owner-receipts-styles')) {
            const style = document.createElement('style');
            style.id = 'owner-receipts-styles';
            style.textContent = `
                @keyframes slideInRight {
                    from { transform: translateX(100%); opacity: 0; }
                    to { transform: translateX(0); opacity: 1; }
                }
                @keyframes slideOutRight {
                    from { transform: translateX(0); opacity: 1; }
                    to { transform: translateX(100%); opacity: 0; }
                }
                .owner-receipt-alert.fade-out {
                    animation: slideOutRight 0.3s ease-in;
                }
            `;
            document.head.appendChild(style);
        }
        
        const iconMap = {
            'success': 'bi-check-circle-fill',
            'danger': 'bi-exclamation-triangle-fill',
            'warning': 'bi-exclamation-circle-fill',
            'info': 'bi-info-circle-fill'
        };
        
        const icon = iconMap[type] || 'bi-info-circle-fill';
        
        alertDiv.innerHTML = `
            <div class="d-flex align-items-center">
                <i class="bi ${icon} me-2 fs-5"></i>
                <div class="flex-grow-1">${message}</div>
                <button type="button" class="btn-close ms-2" data-bs-dismiss="alert" aria-label="Close"></button>
            </div>
        `;
        
        document.body.appendChild(alertDiv);
        
        // Auto-remove with animation
        setTimeout(() => {
            if (alertDiv.parentNode) {
                alertDiv.classList.add('fade-out');
                setTimeout(() => {
                    if (alertDiv.parentNode) {
                        alertDiv.remove();
                    }
                }, 300);
            }
        }, duration);
        
        return alertDiv;
    },

    /**
     * Get CSRF token from page
     */
    getCSRFToken: function() {
        const token = document.querySelector('[name=csrfmiddlewaretoken]');
        return token ? token.value : '';
    },

    /**
     * Show loading spinner on button
     */
    setButtonLoading: function(button, loading = true, originalText = '') {
        if (loading) {
            button.dataset.originalText = button.innerHTML;
            button.disabled = true;
            button.innerHTML = '<i class="bi bi-hourglass-split me-1"></i>Enviando...';
        } else {
            button.disabled = false;
            button.innerHTML = originalText || button.dataset.originalText || button.innerHTML;
        }
    },

    /**
     * Enhanced confirmation dialog
     */
    showConfirmation: function(message, title = 'Confirmar acción') {
        return new Promise((resolve) => {
            // Create modal if it doesn't exist
            let modal = document.getElementById('confirmationModal');
            if (!modal) {
                modal = document.createElement('div');
                modal.id = 'confirmationModal';
                modal.className = 'modal fade';
                modal.innerHTML = `
                    <div class="modal-dialog modal-dialog-centered">
                        <div class="modal-content">
                            <div class="modal-header">
                                <h5 class="modal-title" id="confirmationModalLabel">${title}</h5>
                                <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                            </div>
                            <div class="modal-body">
                                <div class="d-flex align-items-center">
                                    <i class="bi bi-question-circle-fill text-warning fs-1 me-3"></i>
                                    <div id="confirmationMessage">${message}</div>
                                </div>
                            </div>
                            <div class="modal-footer">
                                <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancelar</button>
                                <button type="button" class="btn btn-primary" id="confirmButton">Confirmar</button>
                            </div>
                        </div>
                    </div>
                `;
                document.body.appendChild(modal);
            } else {
                modal.querySelector('#confirmationModalLabel').textContent = title;
                modal.querySelector('#confirmationMessage').textContent = message;
            }
            
            const bootstrapModal = new bootstrap.Modal(modal);
            const confirmButton = modal.querySelector('#confirmButton');
            
            // Remove previous event listeners
            const newConfirmButton = confirmButton.cloneNode(true);
            confirmButton.parentNode.replaceChild(newConfirmButton, confirmButton);
            
            newConfirmButton.addEventListener('click', () => {
                bootstrapModal.hide();
                resolve(true);
            });
            
            modal.addEventListener('hidden.bs.modal', () => {
                resolve(false);
            }, { once: true });
            
            bootstrapModal.show();
        });
    },

    /**
     * Resend owner receipt via AJAX with enhanced UX
     */
    resendReceipt: function(receiptId, buttonElement = null) {
        // Find the button if not provided
        if (!buttonElement) {
            buttonElement = document.querySelector(`button[onclick*="resendReceipt(${receiptId})"]`) ||
                           document.querySelector(`[data-receipt-id="${receiptId}"][data-action="resend"]`);
        }
        
        const isResend = buttonElement && buttonElement.textContent.toLowerCase().includes('reenviar');
        const confirmMessage = isResend ? 
            '¿Está seguro de que desea reenviar este comprobante por correo electrónico?' :
            '¿Está seguro de que desea enviar este comprobante por correo electrónico?';
        
        // Use enhanced confirmation dialog if bootstrap is available, otherwise fallback to confirm
        const showConfirm = typeof bootstrap !== 'undefined' ? 
            this.showConfirmation(confirmMessage, 'Confirmar envío') :
            Promise.resolve(confirm(confirmMessage));
            
        showConfirm.then(confirmed => {
            if (!confirmed) return;
            
            // Set button loading state
            if (buttonElement) {
                this.setButtonLoading(buttonElement, true);
            }
            
            // Show initial feedback
            this.showAlert('info', 'Enviando comprobante...', 2000);
            
            fetch(`/accounting/owner-receipt/${receiptId}/resend/`, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': this.getCSRFToken(),
                    'X-Requested-With': 'XMLHttpRequest',
                    'Content-Type': 'application/json',
                },
            })
            .then(response => {
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                return response.json();
            })
            .then(data => {
                if (data.success) {
                    this.showAlert('success', 
                        data.message || 'Comprobante enviado correctamente', 
                        3000
                    );
                    
                    // Update UI elements if they exist
                    this.updateReceiptStatus(receiptId, 'sent');
                    
                    // Reload page after delay to show updated status
                    setTimeout(() => {
                        window.location.reload();
                    }, 2000);
                } else {
                    this.showAlert('danger', 
                        data.error || 'Error al enviar el comprobante', 
                        7000
                    );
                    
                    // Restore button
                    if (buttonElement) {
                        this.setButtonLoading(buttonElement, false);
                    }
                }
            })
            .catch(error => {
                console.error('Error sending receipt:', error);
                
                let errorMessage = 'Error de conexión al enviar el comprobante';
                if (error.message.includes('404')) {
                    errorMessage = 'Comprobante no encontrado';
                } else if (error.message.includes('403')) {
                    errorMessage = 'No tiene permisos para realizar esta acción';
                } else if (error.message.includes('500')) {
                    errorMessage = 'Error interno del servidor. Intente nuevamente';
                }
                
                this.showAlert('danger', errorMessage, 7000);
                
                // Restore button
                if (buttonElement) {
                    this.setButtonLoading(buttonElement, false);
                }
            });
        });
    },

    /**
     * Update receipt status in the UI
     */
    updateReceiptStatus: function(receiptId, newStatus) {
        // Update status badges
        const statusBadges = document.querySelectorAll(`[data-receipt-id="${receiptId}"] .badge`);
        statusBadges.forEach(badge => {
            badge.className = badge.className.replace(/bg-\w+/g, '');
            switch(newStatus) {
                case 'sent':
                    badge.classList.add('bg-success');
                    badge.textContent = 'Enviado';
                    break;
                case 'failed':
                    badge.classList.add('bg-danger');
                    badge.textContent = 'Error';
                    break;
                case 'generated':
                    badge.classList.add('bg-warning', 'text-dark');
                    badge.textContent = 'Generado';
                    break;
            }
        });
        
        // Update action buttons
        const actionButtons = document.querySelectorAll(`[data-receipt-id="${receiptId}"] button`);
        actionButtons.forEach(button => {
            if (button.textContent.includes('Enviar') || button.textContent.includes('Reenviar')) {
                if (newStatus === 'sent') {
                    button.innerHTML = '<i class="bi bi-envelope me-1"></i>Reenviar';
                }
            }
        });
    },

    /**
     * Initialize tooltips for owner receipts
     */
    initTooltips: function() {
        if (typeof bootstrap !== 'undefined') {
            const tooltipTriggerList = [].slice.call(
                document.querySelectorAll('[data-bs-toggle="tooltip"]')
            );
            tooltipTriggerList.map(function (tooltipTriggerEl) {
                return new bootstrap.Tooltip(tooltipTriggerEl);
            });
        }
    },

    /**
     * Initialize form validation and submission
     */
    initFormHandling: function() {
        // Handle filter form submission with loading state
        const filterForm = document.getElementById('filterForm');
        if (filterForm) {
            filterForm.addEventListener('submit', (e) => {
                const submitButton = filterForm.querySelector('button[type="submit"]');
                if (submitButton) {
                    this.setButtonLoading(submitButton, true);
                    submitButton.innerHTML = '<i class="bi bi-hourglass-split me-1"></i>Buscando...';
                }
            });
        }

        // Handle generation form with enhanced confirmation and AJAX
        const generateForm = document.getElementById('generateReceiptForm');
        if (generateForm) {
            generateForm.addEventListener('submit', (e) => {
                e.preventDefault();
                
                const sendEmail = generateForm.querySelector('input[name="send_email"]').checked;
                const confirmMessage = sendEmail ? 
                    '¿Está seguro de que desea generar y enviar el comprobante por correo electrónico?' :
                    '¿Está seguro de que desea generar el comprobante?';
                
                const showConfirm = typeof bootstrap !== 'undefined' ? 
                    this.showConfirmation(confirmMessage, 'Confirmar generación') :
                    Promise.resolve(confirm(confirmMessage));
                
                showConfirm.then(confirmed => {
                    if (confirmed) {
                        // Extract invoice ID from URL or form data
                        const urlParts = window.location.pathname.split('/');
                        const invoiceId = urlParts[urlParts.indexOf('invoice') + 1] || 
                                         generateForm.dataset.invoiceId;
                        
                        this.handleGenerateReceipt(generateForm, invoiceId);
                    }
                });
            });
        }
    },

    /**
     * Initialize AJAX event handlers
     */
    initAjaxHandlers: function() {
        // Handle resend buttons with data attributes
        document.addEventListener('click', (e) => {
            const target = e.target.closest('[data-action="resend"]');
            if (target) {
                e.preventDefault();
                const receiptId = target.dataset.receiptId;
                if (receiptId) {
                    this.resendReceipt(receiptId, target);
                }
            }
            
            // Handle PDF download links
            const pdfLink = e.target.closest('a[href*="pdf"]');
            if (pdfLink) {
                const urlParts = pdfLink.href.split('/');
                const receiptId = urlParts[urlParts.indexOf('owner-receipt') + 1];
                if (receiptId) {
                    this.handlePdfDownload(receiptId, pdfLink);
                }
            }
        });

        // Handle bulk actions if implemented
        const bulkActionForm = document.getElementById('bulkActionForm');
        if (bulkActionForm) {
            bulkActionForm.addEventListener('submit', (e) => {
                e.preventDefault();
                this.handleBulkAction();
            });
        }
    },

    /**
     * Handle bulk actions (future enhancement)
     */
    handleBulkAction: function() {
        const selectedReceipts = document.querySelectorAll('input[name="selected_receipts"]:checked');
        const action = document.querySelector('select[name="bulk_action"]').value;
        
        if (selectedReceipts.length === 0) {
            this.showAlert('warning', 'Seleccione al menos un comprobante');
            return;
        }
        
        if (!action) {
            this.showAlert('warning', 'Seleccione una acción');
            return;
        }
        
        const confirmMessage = `¿Está seguro de que desea ${action} ${selectedReceipts.length} comprobante(s)?`;
        const showConfirm = typeof bootstrap !== 'undefined' ? 
            this.showConfirmation(confirmMessage, 'Confirmar acción masiva') :
            Promise.resolve(confirm(confirmMessage));
        
        showConfirm.then(confirmed => {
            if (confirmed) {
                // Implementation for bulk actions would go here
                this.showAlert('info', 'Funcionalidad de acciones masivas en desarrollo');
            }
        });
    },

    /**
     * Handle receipt generation form submission
     */
    handleGenerateReceipt: function(form, invoiceId) {
        const formData = new FormData(form);
        const submitButton = form.querySelector('button[type="submit"]');
        const sendEmail = form.querySelector('input[name="send_email"]').checked;
        
        // Set loading state
        this.setButtonLoading(submitButton, true);
        
        // Show progress feedback
        this.showAlert('info', 'Generando comprobante...', 3000);
        
        fetch(form.action || window.location.href, {
            method: 'POST',
            body: formData,
            headers: {
                'X-CSRFToken': this.getCSRFToken(),
                'X-Requested-With': 'XMLHttpRequest',
            }
        })
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            if (data.success) {
                const message = sendEmail ? 
                    'Comprobante generado y enviado correctamente' :
                    'Comprobante generado correctamente';
                    
                this.showAlert('success', data.message || message, 4000);
                
                // Redirect after delay
                setTimeout(() => {
                    if (data.redirect_url) {
                        window.location.href = data.redirect_url;
                    } else {
                        window.location.href = `/accounting/invoice/${invoiceId}/`;
                    }
                }, 2500);
            } else {
                this.showAlert('danger', 
                    data.error || 'Error al generar el comprobante', 
                    7000
                );
                this.setButtonLoading(submitButton, false);
            }
        })
        .catch(error => {
            console.error('Error generating receipt:', error);
            
            let errorMessage = 'Error de conexión al generar el comprobante';
            if (error.message.includes('404')) {
                errorMessage = 'Factura no encontrada';
            } else if (error.message.includes('403')) {
                errorMessage = 'No tiene permisos para generar comprobantes';
            } else if (error.message.includes('500')) {
                errorMessage = 'Error interno del servidor. Intente nuevamente';
            }
            
            this.showAlert('danger', errorMessage, 7000);
            this.setButtonLoading(submitButton, false);
        });
    },

    /**
     * Handle PDF download with feedback
     */
    handlePdfDownload: function(receiptId, linkElement) {
        if (linkElement) {
            const icon = linkElement.querySelector('i');
            const originalClass = icon ? icon.className : '';
            
            if (icon) {
                icon.className = 'bi bi-hourglass-split';
            }
            
            // Show feedback
            this.showAlert('info', 'Preparando descarga del PDF...', 2000);
            
            // Restore icon after delay
            setTimeout(() => {
                if (icon) {
                    icon.className = originalClass;
                }
            }, 3000);
        }
    },

    /**
     * Initialize keyboard shortcuts
     */
    initKeyboardShortcuts: function() {
        document.addEventListener('keydown', (e) => {
            // Ctrl+R to refresh (prevent default browser refresh in development)
            if (e.ctrlKey && e.key === 'r' && window.location.hostname === 'localhost') {
                e.preventDefault();
                window.location.reload();
            }
            
            // Escape to close modals
            if (e.key === 'Escape') {
                const openModals = document.querySelectorAll('.modal.show');
                openModals.forEach(modal => {
                    const bootstrapModal = bootstrap.Modal.getInstance(modal);
                    if (bootstrapModal) {
                        bootstrapModal.hide();
                    }
                });
            }
            
            // Ctrl+F to focus search
            if (e.ctrlKey && e.key === 'f') {
                const searchInput = document.getElementById('searchQuery');
                if (searchInput) {
                    e.preventDefault();
                    searchInput.focus();
                    searchInput.select();
                }
            }
        });
    },

    /**
     * Initialize UI enhancements
     */
    initUIEnhancements: function() {
        // Add hover effects to cards
        const cards = document.querySelectorAll('.card');
        cards.forEach(card => {
            card.addEventListener('mouseenter', function() {
                this.style.transform = 'translateY(-2px)';
                this.style.transition = 'transform 0.2s ease';
                this.style.boxShadow = '0 4px 12px rgba(0,0,0,0.15)';
            });
            
            card.addEventListener('mouseleave', function() {
                this.style.transform = 'translateY(0)';
                this.style.boxShadow = '';
            });
        });

        // Auto-collapse filters on mobile
        if (window.innerWidth < 768) {
            const filtersCard = document.getElementById('filtersCard');
            if (filtersCard && filtersCard.classList.contains('show')) {
                filtersCard.classList.remove('show');
            }
        }

        // Add loading states to PDF download links
        const pdfLinks = document.querySelectorAll('a[href*="pdf"]');
        pdfLinks.forEach(link => {
            link.addEventListener('click', function() {
                const icon = this.querySelector('i');
                if (icon) {
                    icon.className = 'bi bi-hourglass-split';
                    setTimeout(() => {
                        icon.className = 'bi bi-file-earmark-pdf';
                    }, 2000);
                }
            });
        });

        // Initialize progress indicators for long operations
        this.initProgressIndicators();
    },

    /**
     * Initialize progress indicators
     */
    initProgressIndicators: function() {
        // Show progress for page loads
        if (document.readyState === 'loading') {
            const progressBar = document.createElement('div');
            progressBar.id = 'pageLoadProgress';
            progressBar.style.cssText = `
                position: fixed;
                top: 0;
                left: 0;
                width: 0%;
                height: 3px;
                background: linear-gradient(90deg, #007bff, #28a745);
                z-index: 10000;
                transition: width 0.3s ease;
            `;
            document.body.appendChild(progressBar);
            
            let progress = 0;
            const interval = setInterval(() => {
                progress += Math.random() * 15;
                if (progress > 90) progress = 90;
                progressBar.style.width = progress + '%';
            }, 100);
            
            document.addEventListener('DOMContentLoaded', () => {
                clearInterval(interval);
                progressBar.style.width = '100%';
                setTimeout(() => {
                    progressBar.remove();
                }, 500);
            });
        }
    },

    /**
     * Initialize owner receipts functionality
     */
    init: function() {
        this.initTooltips();
        this.initFormHandling();
        this.initAjaxHandlers();
        this.initKeyboardShortcuts();
        this.initUIEnhancements();
        
        // Log initialization for debugging
        if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
            console.log('OwnerReceipts initialized successfully');
        }
    }
};

// Global function for backward compatibility
function resendReceipt(receiptId) {
    OwnerReceipts.resendReceipt(receiptId);
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    OwnerReceipts.init();
});