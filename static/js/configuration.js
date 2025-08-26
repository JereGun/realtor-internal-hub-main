/**
 * Configuration Management JavaScript Components
 * 
 * Provides advanced functionality for the company configuration system including:
 * - Real-time template preview
 * - Form validation
 * - File upload with preview
 * - Confirmation dialogs for critical operations
 */

class ConfigurationManager {
    constructor() {
        this.init();
    }

    init() {
        this.setupEventListeners();
        this.initializeComponents();
    }

    setupEventListeners() {
        document.addEventListener('DOMContentLoaded', () => {
            this.initializeFormValidation();
            this.initializeFileUploads();
            this.initializeConfirmationDialogs();
        });
    }

    initializeComponents() {
        // Initialize all configuration components
        if (typeof TemplatePreview !== 'undefined') {
            this.templatePreview = new TemplatePreview();
        }
        
        if (typeof FormValidator !== 'undefined') {
            this.formValidator = new FormValidator();
        }
        
        if (typeof FileUploadHandler !== 'undefined') {
            this.fileUploadHandler = new FileUploadHandler();
        }
    }

    initializeFormValidation() {
        const forms = document.querySelectorAll('form[data-validate="true"]');
        forms.forEach(form => {
            new FormValidator(form);
        });
    }

    initializeFileUploads() {
        const fileInputs = document.querySelectorAll('input[type="file"][data-preview="true"]');
        fileInputs.forEach(input => {
            new FileUploadHandler(input);
        });
    }

    initializeConfirmationDialogs() {
        const confirmButtons = document.querySelectorAll('[data-confirm]');
        confirmButtons.forEach(button => {
            button.addEventListener('click', (e) => {
                e.preventDefault();
                const message = button.dataset.confirm;
                if (confirm(message)) {
                    // Proceed with the action
                    if (button.href) {
                        window.location.href = button.href;
                    } else if (button.onclick) {
                        button.onclick();
                    }
                }
            });
        });
    }
}

/**
 * Template Preview Component
 * Handles real-time preview generation for document templates
 */
class TemplatePreview {
    constructor(options = {}) {
        this.options = {
            previewContainer: '#previewPanel',
            templateContentSelector: '.template-editor',
            templateTypeSelector: '#id_template_type',
            previewButton: '[data-action="preview"]',
            apiEndpoint: '/api/template-preview/',
            ...options
        };
        
        this.previewContainer = document.querySelector(this.options.previewContainer);
        this.templateTypeSelector = document.querySelector(this.options.templateTypeSelector);
        
        this.init();
    }

    init() {
        this.setupEventListeners();
        this.loadVariables();
    }

    setupEventListeners() {
        // Preview button click
        const previewButtons = document.querySelectorAll(this.options.previewButton);
        previewButtons.forEach(button => {
            button.addEventListener('click', () => this.generatePreview());
        });

        // Auto-preview on template type change
        if (this.templateTypeSelector) {
            this.templateTypeSelector.addEventListener('change', () => {
                this.loadVariables();
                this.generatePreview();
            });
        }

        // Auto-preview on content change (debounced)
        const templateEditors = document.querySelectorAll(this.options.templateContentSelector);
        templateEditors.forEach(editor => {
            let timeout;
            editor.addEventListener('input', () => {
                clearTimeout(timeout);
                timeout = setTimeout(() => this.generatePreview(), 1000);
            });
        });
    }

    async generatePreview() {
        if (!this.previewContainer) return;

        this.showLoading();

        try {
            const templateContent = this.getTemplateContent();
            const templateType = this.getTemplateType();

            const response = await fetch(this.options.apiEndpoint, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                },
                body: JSON.stringify({
                    template_content: templateContent,
                    template_type: templateType
                })
            });

            const data = await response.json();

            if (data.success) {
                this.showPreview(data.preview_html);
            } else {
                this.showError(data.error);
            }
        } catch (error) {
            console.error('Preview generation error:', error);
            this.showError('Error generando vista previa');
        }
    }

    getTemplateContent() {
        const editors = document.querySelectorAll(this.options.templateContentSelector);
        let content = '';
        
        editors.forEach(editor => {
            if (editor.style.display !== 'none') {
                // Check if it's a CodeMirror instance
                if (editor.nextSibling && editor.nextSibling.classList && 
                    editor.nextSibling.classList.contains('CodeMirror')) {
                    const cm = editor.nextSibling.CodeMirror;
                    content += cm.getValue() + '\n';
                } else {
                    content += editor.value + '\n';
                }
            }
        });
        
        return content.trim();
    }

    getTemplateType() {
        return this.templateTypeSelector ? this.templateTypeSelector.value : 'invoice';
    }

    showLoading() {
        this.previewContainer.innerHTML = `
            <div class="text-center p-4">
                <div class="spinner-border text-primary" role="status">
                    <span class="visually-hidden">Generando vista previa...</span>
                </div>
                <p class="mt-2 text-muted">Generando vista previa...</p>
            </div>
        `;
    }

    showPreview(html) {
        this.previewContainer.innerHTML = html;
    }

    showError(error) {
        this.previewContainer.innerHTML = `
            <div class="alert alert-danger">
                <i class="fas fa-exclamation-triangle me-2"></i>
                ${error}
            </div>
        `;
    }

    async loadVariables() {
        const templateType = this.getTemplateType();
        const variablesPanel = document.getElementById('variablesPanel');
        
        if (!variablesPanel) return;

        try {
            const response = await fetch(`/api/template-variables/?type=${templateType}`);
            const data = await response.json();

            if (data.success) {
                this.renderVariables(data.variables, variablesPanel);
            }
        } catch (error) {
            console.error('Error loading variables:', error);
        }
    }

    renderVariables(variables, container) {
        container.innerHTML = '';
        variables.forEach(variable => {
            const tag = document.createElement('span');
            tag.className = 'variable-tag';
            tag.textContent = variable;
            tag.onclick = () => this.insertVariable(variable);
            container.appendChild(tag);
        });
    }

    insertVariable(variable) {
        // This method should be overridden or extended based on the editor type
        const activeElement = document.activeElement;
        if (activeElement && (activeElement.tagName === 'TEXTAREA' || activeElement.tagName === 'INPUT')) {
            const cursorPos = activeElement.selectionStart;
            const textBefore = activeElement.value.substring(0, cursorPos);
            const textAfter = activeElement.value.substring(cursorPos);
            activeElement.value = textBefore + variable + textAfter;
            activeElement.focus();
            activeElement.setSelectionRange(cursorPos + variable.length, cursorPos + variable.length);
        }
    }

    getCSRFToken() {
        const token = document.querySelector('[name=csrfmiddlewaretoken]');
        return token ? token.value : '';
    }
}

/**
 * Form Validator Component
 * Provides real-time form validation with custom rules
 */
class FormValidator {
    constructor(form) {
        this.form = form;
        this.rules = {};
        this.init();
    }

    init() {
        this.setupValidationRules();
        this.setupEventListeners();
    }

    setupValidationRules() {
        // Company name validation
        this.addRule('name', {
            required: true,
            minLength: 3,
            pattern: /^[a-zA-ZáéíóúÁÉÍÓÚñÑ0-9\s\.\,\-\_\&]+$/,
            message: 'El nombre debe tener al menos 3 caracteres y solo contener caracteres válidos'
        });

        // Email validation
        this.addRule('email', {
            pattern: /^[^\s@]+@[^\s@]+\.[^\s@]+$/,
            message: 'Formato de email inválido'
        });

        // Phone validation
        this.addRule('phone', {
            pattern: /^\+?[\d\s\-\(\)]+$/,
            message: 'Formato de teléfono inválido'
        });

        // Tax ID validation
        this.addRule('tax_id', {
            pattern: /^[A-Z]\d{8}$|^\d{8}[A-Z]$/,
            message: 'Formato de NIF/CIF inválido'
        });

        // URL validation
        this.addRule('website', {
            pattern: /^https?:\/\/.+/,
            message: 'La URL debe comenzar con http:// o https://'
        });
    }

    addRule(fieldName, rule) {
        this.rules[fieldName] = rule;
    }

    setupEventListeners() {
        Object.keys(this.rules).forEach(fieldName => {
            const field = this.form.querySelector(`[name="${fieldName}"], #id_${fieldName}`);
            if (field) {
                field.addEventListener('blur', () => this.validateField(field, fieldName));
                field.addEventListener('input', () => this.clearValidation(field));
            }
        });

        this.form.addEventListener('submit', (e) => {
            if (!this.validateForm()) {
                e.preventDefault();
            }
        });
    }

    validateField(field, fieldName) {
        const rule = this.rules[fieldName];
        const value = field.value.trim();

        // Required validation
        if (rule.required && !value) {
            this.showFieldError(field, 'Este campo es obligatorio');
            return false;
        }

        // Skip other validations if field is empty and not required
        if (!value && !rule.required) {
            this.clearFieldError(field);
            return true;
        }

        // Min length validation
        if (rule.minLength && value.length < rule.minLength) {
            this.showFieldError(field, `Debe tener al menos ${rule.minLength} caracteres`);
            return false;
        }

        // Pattern validation
        if (rule.pattern && !rule.pattern.test(value)) {
            this.showFieldError(field, rule.message);
            return false;
        }

        // Custom validation
        if (rule.custom && !rule.custom(value)) {
            this.showFieldError(field, rule.message);
            return false;
        }

        this.showFieldSuccess(field);
        return true;
    }

    validateForm() {
        let isValid = true;
        Object.keys(this.rules).forEach(fieldName => {
            const field = this.form.querySelector(`[name="${fieldName}"], #id_${fieldName}`);
            if (field && !this.validateField(field, fieldName)) {
                isValid = false;
            }
        });
        return isValid;
    }

    showFieldError(field, message) {
        field.classList.add('is-invalid');
        field.classList.remove('is-valid');
        
        let feedback = field.parentNode.querySelector('.invalid-feedback');
        if (!feedback) {
            feedback = document.createElement('div');
            feedback.className = 'invalid-feedback';
            field.parentNode.appendChild(feedback);
        }
        feedback.textContent = message;
    }

    showFieldSuccess(field) {
        field.classList.add('is-valid');
        field.classList.remove('is-invalid');
        
        const feedback = field.parentNode.querySelector('.invalid-feedback');
        if (feedback) {
            feedback.remove();
        }
    }

    clearFieldError(field) {
        field.classList.remove('is-invalid', 'is-valid');
        const feedback = field.parentNode.querySelector('.invalid-feedback');
        if (feedback) {
            feedback.remove();
        }
    }

    clearValidation(field) {
        // Clear validation styling on input (but not errors)
        field.classList.remove('is-valid');
    }
}

/**
 * File Upload Handler Component
 * Handles file uploads with preview and validation
 */
class FileUploadHandler {
    constructor(input, options = {}) {
        this.input = input;
        this.options = {
            maxSize: 2 * 1024 * 1024, // 2MB
            allowedTypes: ['image/jpeg', 'image/png', 'image/svg+xml'],
            previewContainer: null,
            ...options
        };
        
        this.init();
    }

    init() {
        this.setupEventListeners();
        this.findPreviewContainer();
    }

    findPreviewContainer() {
        if (!this.options.previewContainer) {
            // Look for a preview container near the input
            const container = this.input.closest('.form-group, .mb-3');
            if (container) {
                this.options.previewContainer = container.querySelector('.file-preview, .logo-preview, .image-preview');
            }
        }
    }

    setupEventListeners() {
        this.input.addEventListener('change', (e) => {
            if (e.target.files.length > 0) {
                this.handleFileSelect(e.target.files[0]);
            }
        });

        // Drag and drop support
        if (this.options.previewContainer) {
            this.setupDragAndDrop();
        }
    }

    setupDragAndDrop() {
        const container = this.options.previewContainer;
        
        container.addEventListener('dragover', (e) => {
            e.preventDefault();
            container.classList.add('drag-over');
        });

        container.addEventListener('dragleave', (e) => {
            e.preventDefault();
            container.classList.remove('drag-over');
        });

        container.addEventListener('drop', (e) => {
            e.preventDefault();
            container.classList.remove('drag-over');
            
            const files = e.dataTransfer.files;
            if (files.length > 0) {
                this.handleFileSelect(files[0]);
            }
        });
    }

    handleFileSelect(file) {
        if (!this.validateFile(file)) {
            return;
        }

        this.showPreview(file);
        this.updateInput(file);
    }

    validateFile(file) {
        // Size validation
        if (file.size > this.options.maxSize) {
            this.showError(`El archivo es demasiado grande. Máximo ${this.formatFileSize(this.options.maxSize)}`);
            return false;
        }

        // Type validation
        if (this.options.allowedTypes.length > 0 && !this.options.allowedTypes.includes(file.type)) {
            this.showError('Tipo de archivo no válido');
            return false;
        }

        return true;
    }

    showPreview(file) {
        if (!this.options.previewContainer) return;

        if (file.type.startsWith('image/')) {
            const reader = new FileReader();
            reader.onload = (e) => {
                this.options.previewContainer.innerHTML = `
                    <img src="${e.target.result}" alt="Preview" class="img-fluid">
                `;
                this.options.previewContainer.classList.add('has-image');
            };
            reader.readAsDataURL(file);
        }
    }

    updateInput(file) {
        // Create a new FileList with the selected file
        const dt = new DataTransfer();
        dt.items.add(file);
        this.input.files = dt.files;
    }

    showError(message) {
        // Show error message
        let errorDiv = this.input.parentNode.querySelector('.file-error');
        if (!errorDiv) {
            errorDiv = document.createElement('div');
            errorDiv.className = 'file-error text-danger small mt-1';
            this.input.parentNode.appendChild(errorDiv);
        }
        errorDiv.textContent = message;

        // Clear error after 5 seconds
        setTimeout(() => {
            if (errorDiv.parentNode) {
                errorDiv.remove();
            }
        }, 5000);
    }

    formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }
}

/**
 * Notification Manager
 * Handles in-app notifications and alerts
 */
class NotificationManager {
    constructor() {
        this.container = this.createContainer();
    }

    createContainer() {
        let container = document.getElementById('notification-container');
        if (!container) {
            container = document.createElement('div');
            container.id = 'notification-container';
            container.className = 'position-fixed top-0 end-0 p-3';
            container.style.zIndex = '9999';
            document.body.appendChild(container);
        }
        return container;
    }

    show(message, type = 'info', duration = 5000) {
        const notification = document.createElement('div');
        notification.className = `alert alert-${type} alert-dismissible fade show`;
        notification.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;

        this.container.appendChild(notification);

        // Auto-dismiss
        if (duration > 0) {
            setTimeout(() => {
                if (notification.parentNode) {
                    notification.remove();
                }
            }, duration);
        }

        return notification;
    }

    success(message, duration = 5000) {
        return this.show(message, 'success', duration);
    }

    error(message, duration = 8000) {
        return this.show(message, 'danger', duration);
    }

    warning(message, duration = 6000) {
        return this.show(message, 'warning', duration);
    }

    info(message, duration = 5000) {
        return this.show(message, 'info', duration);
    }
}

/**
 * Utility Functions
 */
const ConfigUtils = {
    /**
     * Format phone number to Spanish format
     */
    formatPhoneNumber(phone) {
        const cleaned = phone.replace(/\D/g, '');
        if (cleaned.length === 9 && !cleaned.startsWith('34')) {
            return '+34 ' + cleaned.substring(0, 3) + ' ' + cleaned.substring(3, 6) + ' ' + cleaned.substring(6);
        }
        return phone;
    },

    /**
     * Validate Spanish NIF/CIF
     */
    validateTaxId(taxId) {
        const cleaned = taxId.toUpperCase().trim();
        
        // NIF validation
        if (/^\d{8}[A-Z]$/.test(cleaned)) {
            const letters = 'TRWAGMYFPDXBNJZSQVHLCKE';
            const number = parseInt(cleaned.substring(0, 8));
            const letter = cleaned.charAt(8);
            return letters.charAt(number % 23) === letter;
        }
        
        // CIF validation (basic format check)
        if (/^[A-Z]\d{8}$/.test(cleaned)) {
            return true;
        }
        
        return false;
    },

    /**
     * Debounce function
     */
    debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    },

    /**
     * Get CSRF token
     */
    getCSRFToken() {
        const token = document.querySelector('[name=csrfmiddlewaretoken]');
        return token ? token.value : '';
    }
};

// Initialize configuration manager when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.configManager = new ConfigurationManager();
    window.notificationManager = new NotificationManager();
});

// Export for module usage
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        ConfigurationManager,
        TemplatePreview,
        FormValidator,
        FileUploadHandler,
        NotificationManager,
        ConfigUtils
    };
}