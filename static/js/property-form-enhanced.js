/**
 * Enhanced Property Form JavaScript
 * Provides advanced form functionality including:
 * - Real-time validation with visual feedback
 * - Progress tracking and section completion
 * - Drag and drop file upload
 * - Auto-save functionality
 * - Smooth scrolling navigation
 */

class PropertyFormEnhancer {
  constructor() {
    this.form = document.getElementById('propertyForm');
    this.progressSteps = document.querySelectorAll('.progress-step');
    this.progressBar = document.getElementById('form-progress');
    this.progressText = document.getElementById('progress-text');
    this.completionPercentage = document.getElementById('completion-percentage');
    
    this.formSections = [
      { id: 'section-basic', fields: ['title', 'property_type', 'description'], weight: 0.2 },
      { id: 'section-location', fields: ['street', 'number', 'country', 'province', 'locality'], weight: 0.15 },
      { id: 'section-physical', fields: ['total_surface', 'bedrooms', 'bathrooms'], weight: 0.15 },
      { id: 'section-financial', fields: ['sale_price', 'rental_price'], weight: 0.2 },
      { id: 'section-features', fields: ['features'], weight: 0.1 },
      { id: 'section-images', fields: ['images'], weight: 0.2 }
    ];
    
    this.validationRules = {
      title: { required: true, minLength: 5, maxLength: 200 },
      property_type: { required: true },
      description: { minLength: 20, maxLength: 2000 },
      street: { required: true, minLength: 3 },
      total_surface: { required: true, min: 1, max: 10000 },
      bedrooms: { min: 0, max: 20 },
      bathrooms: { min: 0, max: 10 }
    };
    
    this.init();
  }
  
  init() {
    this.setupProgressNavigation();
    this.setupFormValidation();
    this.setupDragAndDrop();
    this.setupAutoSave();
    this.setupSectionObserver();
    this.updateProgress();
    
    console.log('Property Form Enhancer initialized');
  }
  
  setupProgressNavigation() {
    this.progressSteps.forEach(step => {
      step.addEventListener('click', (e) => {
        e.preventDefault();
        const targetId = step.getAttribute('href');
        const targetElement = document.querySelector(targetId);
        
        if (targetElement) {
          this.scrollToSection(targetElement);
          this.setActiveStep(step);
        }
      });
    });
  }
  
  scrollToSection(element) {
    const headerOffset = 100;
    const elementPosition = element.getBoundingClientRect().top;
    const offsetPosition = elementPosition + window.pageYOffset - headerOffset;
    
    window.scrollTo({
      top: offsetPosition,
      behavior: 'smooth'
    });
  }
  
  setActiveStep(activeStep) {
    this.progressSteps.forEach(step => step.classList.remove('active'));
    activeStep.classList.add('active');
  }
  
  setupFormValidation() {
    // Real-time validation
    document.querySelectorAll('.enhanced-form-control').forEach(input => {
      input.addEventListener('input', () => {
        this.validateField(input);
        this.updateProgress();
      });
      
      input.addEventListener('blur', () => {
        this.validateField(input);
      });
    });
    
    // Form submission validation
    if (this.form) {
      this.form.addEventListener('submit', (e) => {
        if (!this.validateForm()) {
          e.preventDefault();
        }
      });
    }
  }
  
  validateField(field) {
    const fieldName = field.name;
    const value = field.value.trim();
    const rules = this.validationRules[fieldName];
    
    if (!rules) return true;
    
    const errors = [];
    
    // Required validation
    if (rules.required && !value) {
      errors.push(`${this.getFieldLabel(fieldName)} es requerido`);
    }
    
    // Length validations
    if (value && rules.minLength && value.length < rules.minLength) {
      errors.push(`Mínimo ${rules.minLength} caracteres`);
    }
    
    if (value && rules.maxLength && value.length > rules.maxLength) {
      errors.push(`Máximo ${rules.maxLength} caracteres`);
    }
    
    // Numeric validations
    if (value && rules.min !== undefined) {
      const numValue = parseFloat(value);
      if (isNaN(numValue) || numValue < rules.min) {
        errors.push(`Valor mínimo: ${rules.min}`);
      }
    }
    
    if (value && rules.max !== undefined) {
      const numValue = parseFloat(value);
      if (isNaN(numValue) || numValue > rules.max) {
        errors.push(`Valor máximo: ${rules.max}`);
      }
    }
    
    this.updateFieldValidationState(field, errors);
    return errors.length === 0;
  }
  
  updateFieldValidationState(field, errors) {
    field.classList.remove('is-invalid', 'is-valid');
    
    const validFeedback = field.parentNode.querySelector('.valid-feedback');
    const invalidFeedback = field.parentNode.querySelector('.invalid-feedback');
    
    if (errors.length > 0) {
      field.classList.add('is-invalid');
      if (invalidFeedback) {
        invalidFeedback.textContent = errors[0];
        invalidFeedback.style.display = 'flex';
      }
      if (validFeedback) {
        validFeedback.style.display = 'none';
      }
    } else if (field.value.trim()) {
      field.classList.add('is-valid');
      if (validFeedback) {
        validFeedback.style.display = 'flex';
      }
      if (invalidFeedback) {
        invalidFeedback.style.display = 'none';
      }
    } else {
      if (validFeedback) validFeedback.style.display = 'none';
      if (invalidFeedback) invalidFeedback.style.display = 'none';
    }
  }
  
  validateForm() {
    let isValid = true;
    const errors = [];
    
    document.querySelectorAll('.enhanced-form-control').forEach(field => {
      if (!this.validateField(field)) {
        isValid = false;
      }
    });
    
    // Custom business logic validations
    const listingType = document.getElementById('id_listing_type')?.value;
    const salePrice = parseFloat(document.getElementById('id_sale_price')?.value) || 0;
    const rentalPrice = parseFloat(document.getElementById('id_rental_price')?.value) || 0;
    
    if (listingType === 'sale' && salePrice <= 0) {
      errors.push('Debe definir un precio de venta');
      isValid = false;
    } else if (listingType === 'rent' && rentalPrice <= 0) {
      errors.push('Debe definir un precio de alquiler');
      isValid = false;
    } else if (listingType === 'both' && salePrice <= 0 && rentalPrice <= 0) {
      errors.push('Debe definir al menos un precio');
      isValid = false;
    }
    
    if (!isValid) {
      errors.forEach(error => this.showToast(error, 'error'));
      this.scrollToFirstError();
    }
    
    return isValid;
  }
  
  scrollToFirstError() {
    const firstError = document.querySelector('.is-invalid');
    if (firstError) {
      this.scrollToSection(firstError.closest('.form-section') || firstError);
      firstError.focus();
    }
  }
  
  updateProgress() {
    let totalWeight = 0;
    let completedWeight = 0;
    
    this.formSections.forEach((section, index) => {
      const sectionElement = document.getElementById(section.id);
      const progressStep = this.progressSteps[index];
      
      if (!sectionElement || !progressStep) return;
      
      totalWeight += section.weight;
      
      // Calculate section completion
      const completedFields = section.fields.filter(fieldName => {
        const field = document.getElementById(`id_${fieldName}`);
        return field && field.value.trim() !== '';
      });
      
      const completionRatio = completedFields.length / section.fields.length;
      const isCompleted = completionRatio >= 0.5; // 50% completion threshold
      
      if (isCompleted) {
        completedWeight += section.weight * completionRatio;
        progressStep.classList.add('completed');
      } else {
        progressStep.classList.remove('completed');
        completedWeight += section.weight * completionRatio;
      }
    });
    
    const progressPercentage = Math.round((completedWeight / totalWeight) * 100);
    
    if (this.progressBar) {
      this.progressBar.style.width = `${progressPercentage}%`;
    }
    
    if (this.progressText) {
      const completedSections = document.querySelectorAll('.progress-step.completed').length;
      this.progressText.textContent = `${completedSections} de ${this.formSections.length} secciones completadas`;
    }
    
    if (this.completionPercentage) {
      this.completionPercentage.textContent = `${progressPercentage}%`;
    }
  }
  
  setupDragAndDrop() {
    const dragDropZone = document.getElementById('dragDropZone');
    const multipleImageInput = document.getElementById('multipleImageInput');
    
    if (!dragDropZone || !multipleImageInput) return;
    
    // Prevent default drag behaviors
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
      dragDropZone.addEventListener(eventName, this.preventDefaults, false);
      document.body.addEventListener(eventName, this.preventDefaults, false);
    });
    
    // Highlight drop zone when item is dragged over it
    ['dragenter', 'dragover'].forEach(eventName => {
      dragDropZone.addEventListener(eventName, () => {
        dragDropZone.classList.add('drag-over');
      }, false);
    });
    
    ['dragleave', 'drop'].forEach(eventName => {
      dragDropZone.addEventListener(eventName, () => {
        dragDropZone.classList.remove('drag-over');
      }, false);
    });
    
    // Handle dropped files
    dragDropZone.addEventListener('drop', (e) => {
      const files = e.dataTransfer.files;
      this.handleFiles(files);
    }, false);
    
    // Handle file input change
    multipleImageInput.addEventListener('change', (e) => {
      this.handleFiles(e.target.files);
    });
  }
  
  preventDefaults(e) {
    e.preventDefault();
    e.stopPropagation();
  }
  
  handleFiles(files) {
    [...files].forEach(file => this.processFile(file));
  }
  
  processFile(file) {
    // Validate file type
    if (!file.type.startsWith('image/')) {
      this.showToast('Solo se permiten archivos de imagen', 'error');
      return;
    }
    
    // Validate file size (5MB limit)
    if (file.size > 5 * 1024 * 1024) {
      this.showToast('El archivo es demasiado grande. Máximo 5MB por imagen.', 'error');
      return;
    }
    
    // Check maximum number of images
    const existingImages = document.querySelectorAll('.image-preview-item').length;
    if (existingImages >= 10) {
      this.showToast('Máximo 10 imágenes permitidas', 'error');
      return;
    }
    
    this.createImagePreview(file);
  }
  
  createImagePreview(file) {
    const reader = new FileReader();
    reader.onload = (e) => {
      const previewHtml = this.generateImagePreviewHTML(e.target.result, file.name);
      this.addImagePreview(previewHtml);
    };
    reader.readAsDataURL(file);
  }
  
  generateImagePreviewHTML(imageSrc, fileName) {
    return `
      <div class="image-preview-item card mb-3 border-light">
        <div class="card-body p-3">
          <div class="row g-3 align-items-start">
            <div class="col-md-3">
              <img src="${imageSrc}" class="img-fluid rounded" alt="Vista previa" 
                   style="max-height: 150px; width: 100%; object-fit: cover;">
            </div>
            <div class="col-md-9">
              <div class="mb-3">
                <label class="form-label fw-semibold">
                  <i class="bi bi-card-text me-1"></i>Descripción
                </label>
                <input type="text" class="form-control enhanced-form-control" 
                       placeholder="Descripción de la imagen..." value="${fileName}">
              </div>
              <div class="d-flex justify-content-between align-items-center">
                <div class="form-check">
                  <input class="form-check-input" type="radio" name="cover_image_preview" value="">
                  <label class="form-check-label">Imagen principal</label>
                </div>
                <button type="button" class="btn btn-outline-danger btn-sm remove-preview">
                  <i class="bi bi-trash me-1"></i>Eliminar
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    `;
  }
  
  addImagePreview(html) {
    let container = document.getElementById('image-forms-container');
    if (!container) {
      container = document.createElement('div');
      container.id = 'image-forms-container';
      container.className = 'mt-4';
      const dragDropZone = document.getElementById('dragDropZone');
      dragDropZone.parentNode.insertBefore(container, dragDropZone.nextSibling);
    }
    
    container.insertAdjacentHTML('beforeend', html);
    
    // Add remove functionality to the new preview
    const removeBtn = container.lastElementChild.querySelector('.remove-preview');
    removeBtn.addEventListener('click', function() {
      this.closest('.image-preview-item').remove();
    });
    
    this.showToast('Imagen agregada correctamente', 'success');
  }
  
  setupAutoSave() {
    let autoSaveTimeout;
    const autoSave = () => {
      clearTimeout(autoSaveTimeout);
      autoSaveTimeout = setTimeout(() => {
        this.saveFormData();
      }, 2000);
    };
    
    document.querySelectorAll('.enhanced-form-control').forEach(input => {
      input.addEventListener('input', autoSave);
    });
  }
  
  saveFormData() {
    const formData = new FormData(this.form);
    const data = {};
    
    for (let [key, value] of formData.entries()) {
      data[key] = value;
    }
    
    localStorage.setItem('property_form_autosave', JSON.stringify(data));
    console.log('Form data auto-saved');
  }
  
  loadFormData() {
    const savedData = localStorage.getItem('property_form_autosave');
    if (savedData) {
      try {
        const data = JSON.parse(savedData);
        Object.keys(data).forEach(key => {
          const field = document.getElementById(`id_${key}`);
          if (field && !field.value) {
            field.value = data[key];
          }
        });
      } catch (e) {
        console.error('Error loading saved form data:', e);
      }
    }
  }
  
  setupSectionObserver() {
    const observer = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          const sectionId = entry.target.id;
          const correspondingStep = document.querySelector(`[href="#${sectionId}"]`);
          
          if (correspondingStep) {
            this.setActiveStep(correspondingStep);
          }
        }
      });
    }, {
      threshold: 0.5,
      rootMargin: '-100px 0px -100px 0px'
    });
    
    document.querySelectorAll('.form-section').forEach(section => {
      observer.observe(section);
    });
  }
  
  getFieldLabel(fieldName) {
    const labelMap = {
      title: 'Título',
      property_type: 'Tipo de propiedad',
      description: 'Descripción',
      street: 'Calle',
      total_surface: 'Superficie total',
      bedrooms: 'Dormitorios',
      bathrooms: 'Baños'
    };
    
    return labelMap[fieldName] || fieldName;
  }
  
  showToast(message, type = 'info') {
    let toastContainer = document.querySelector('.toast-container');
    if (!toastContainer) {
      toastContainer = document.createElement('div');
      toastContainer.className = 'toast-container position-fixed top-0 end-0 p-3';
      toastContainer.style.zIndex = '9999';
      document.body.appendChild(toastContainer);
    }
    
    const iconClass = {
      error: 'bi-exclamation-triangle-fill text-danger',
      success: 'bi-check-circle-fill text-success',
      info: 'bi-info-circle-fill text-info'
    }[type];
    
    const headerText = {
      error: 'Error',
      success: 'Éxito',
      info: 'Información'
    }[type];
    
    const toastHtml = `
      <div class="toast" role="alert" aria-live="assertive" aria-atomic="true">
        <div class="toast-header">
          <i class="${iconClass} me-2"></i>
          <strong class="me-auto">${headerText}</strong>
          <button type="button" class="btn-close" data-bs-dismiss="toast" aria-label="Close"></button>
        </div>
        <div class="toast-body">${message}</div>
      </div>
    `;
    
    toastContainer.insertAdjacentHTML('beforeend', toastHtml);
    const toastElement = toastContainer.lastElementChild;
    const toast = new bootstrap.Toast(toastElement, {
      autohide: true,
      delay: type === 'error' ? 5000 : 3000
    });
    
    toast.show();
    
    toastElement.addEventListener('hidden.bs.toast', function() {
      this.remove();
    });
  }
}

/**
 * Responsive Form Enhancements
 */
class ResponsiveFormEnhancer {
  constructor() {
    this.init();
  }

  init() {
    this.initializeMobileOptimizations();
    this.initializeTabletEnhancements();
    this.initializeTouchFriendlyControls();
    this.initializeResponsiveValidation();
    this.initializeViewportAdjustments();
  }

  initializeMobileOptimizations() {
    if (window.innerWidth > 767) return;

    // Mobile-specific form adjustments
    const formContainer = document.querySelector('.property-form-container');
    if (formContainer) {
      formContainer.style.padding = '16px 0';
    }

    // Optimize progress indicator for mobile
    const progressIndicator = document.querySelector('.form-progress-indicator');
    if (progressIndicator) {
      progressIndicator.style.position = 'relative';
      progressIndicator.style.top = 'auto';
      progressIndicator.style.margin = '0 -16px 20px -16px';
      progressIndicator.style.borderRadius = '0';
    }

    // Mobile-friendly progress steps
    const progressSteps = document.querySelector('.progress-steps');
    if (progressSteps) {
      progressSteps.style.display = 'flex';
      progressSteps.style.overflowX = 'auto';
      progressSteps.style.gap = '8px';
      progressSteps.style.padding = '8px 16px';
      progressSteps.style.scrollbarWidth = 'thin';
    }

    // Optimize form sections for mobile
    const formSections = document.querySelectorAll('.form-section');
    formSections.forEach(section => {
      section.style.margin = '0 -16px 16px -16px';
      section.style.borderRadius = '0';
      section.style.borderLeft = 'none';
      section.style.borderRight = 'none';
      section.style.padding = '16px';
    });

    // Mobile-friendly form controls
    const formControls = document.querySelectorAll('.form-control, .form-select');
    formControls.forEach(control => {
      control.style.minHeight = '44px';
      control.style.fontSize = '16px'; // Prevents zoom on iOS
      control.style.padding = '12px 16px';
    });

    // Sticky form actions for mobile
    const formActions = document.querySelector('.form-actions');
    if (formActions) {
      formActions.style.position = 'sticky';
      formActions.style.bottom = '0';
      formActions.style.background = 'white';
      formActions.style.padding = '16px';
      formActions.style.margin = '0 -16px';
      formActions.style.borderTop = '1px solid var(--property-gray-200)';
      formActions.style.boxShadow = '0 -2px 8px rgba(0,0,0,0.1)';
      formActions.style.zIndex = '10';
      formActions.style.display = 'flex';
      formActions.style.flexDirection = 'column';
      formActions.style.gap = '12px';
    }

    // Mobile file upload optimization
    const dragDropZone = document.getElementById('dragDropZone');
    if (dragDropZone) {
      dragDropZone.style.minHeight = '120px';
      dragDropZone.style.padding = '20px';
      dragDropZone.style.margin = '0 -16px';
      dragDropZone.style.borderRadius = '0';
      dragDropZone.style.borderLeft = 'none';
      dragDropZone.style.borderRight = 'none';
    }
  }

  initializeTabletEnhancements() {
    if (window.innerWidth < 768 || window.innerWidth >= 992) return;

    // Tablet-optimized layout
    const formContainer = document.querySelector('.property-form-container');
    if (formContainer) {
      formContainer.style.padding = '24px';
    }

    // Tablet progress indicator
    const progressIndicator = document.querySelector('.form-progress-indicator');
    if (progressIndicator) {
      progressIndicator.style.position = 'sticky';
      progressIndicator.style.top = '20px';
    }

    // Tablet form sections
    const formSections = document.querySelectorAll('.form-section');
    formSections.forEach(section => {
      section.style.padding = '24px';
      section.style.marginBottom = '24px';
    });

    // Tablet form actions
    const formActions = document.querySelector('.form-actions');
    if (formActions) {
      formActions.style.display = 'flex';
      formActions.style.justifyContent = 'space-between';
      formActions.style.gap = '16px';
    }

    const actionButtons = formActions?.querySelectorAll('.btn');
    actionButtons?.forEach(button => {
      button.style.flex = '1';
      button.style.maxWidth = '200px';
    });
  }

  initializeTouchFriendlyControls() {
    // Touch feedback for interactive elements
    const interactiveElements = document.querySelectorAll('.form-control, .form-select, .btn, .form-check-input, .progress-step');
    
    interactiveElements.forEach(element => {
      element.addEventListener('touchstart', function() {
        this.style.transform = 'scale(0.98)';
        this.style.transition = 'transform 0.1s ease';
      });
      
      element.addEventListener('touchend', function() {
        setTimeout(() => {
          this.style.transform = '';
          this.style.transition = '';
        }, 150);
      });
    });

    // Improve checkbox and radio touch targets
    const checkboxes = document.querySelectorAll('.form-check-input');
    checkboxes.forEach(checkbox => {
      const label = checkbox.nextElementSibling;
      if (label) {
        label.style.minHeight = '44px';
        label.style.display = 'flex';
        label.style.alignItems = 'center';
        label.style.padding = '8px';
        label.style.cursor = 'pointer';
      }
    });

    // Touch-friendly drag and drop
    const dragDropZone = document.getElementById('dragDropZone');
    if (dragDropZone) {
      dragDropZone.addEventListener('touchstart', function() {
        this.style.backgroundColor = 'var(--property-light)';
        this.style.borderColor = 'var(--property-primary)';
      });
      
      dragDropZone.addEventListener('touchend', function() {
        setTimeout(() => {
          this.style.backgroundColor = '';
          this.style.borderColor = '';
        }, 200);
      });
    }
  }

  initializeResponsiveValidation() {
    const form = document.querySelector('form');
    if (!form) return;

    // Mobile validation summary
    const showMobileValidationSummary = (errors) => {
      if (window.innerWidth > 767) return;

      const existingSummary = document.querySelector('.mobile-validation-summary');
      if (existingSummary) {
        existingSummary.remove();
      }

      if (errors.length === 0) return;

      const summary = document.createElement('div');
      summary.className = 'mobile-validation-summary alert alert-danger';
      summary.style.cssText = `
        position: fixed;
        top: 20px;
        left: 20px;
        right: 20px;
        z-index: 9999;
        border-radius: 8px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
      `;
      
      summary.innerHTML = `
        <div class="d-flex justify-content-between align-items-start">
          <div>
            <h6 class="alert-heading mb-2">Errores en el formulario:</h6>
            <ul class="mb-0">
              ${errors.map(error => `<li>${error}</li>`).join('')}
            </ul>
          </div>
          <button type="button" class="btn-close" onclick="this.parentElement.parentElement.remove()"></button>
        </div>
      `;
      
      document.body.appendChild(summary);
      
      // Auto-remove after 10 seconds
      setTimeout(() => {
        if (summary.parentNode) {
          summary.remove();
        }
      }, 10000);
    };

    // Enhanced validation for mobile
    form.addEventListener('submit', function(e) {
      const errors = [];
      const requiredFields = form.querySelectorAll('[required]');
      
      requiredFields.forEach(field => {
        if (!field.value.trim()) {
          const label = form.querySelector(`label[for="${field.id}"]`);
          const fieldName = label ? label.textContent : field.name;
          errors.push(`${fieldName} es requerido`);
        }
      });

      if (errors.length > 0) {
        showMobileValidationSummary(errors);
        
        // Scroll to first error field
        const firstErrorField = form.querySelector('.is-invalid, [required]:invalid');
        if (firstErrorField) {
          firstErrorField.scrollIntoView({ 
            behavior: 'smooth', 
            block: 'center' 
          });
          firstErrorField.focus();
        }
      }
    });
  }

  initializeViewportAdjustments() {
    const adjustForViewport = () => {
      const viewport = {
        width: window.innerWidth,
        height: window.innerHeight
      };

      // Handle landscape orientation on mobile
      if (viewport.width <= 767 && viewport.width > viewport.height) {
        document.body.classList.add('mobile-landscape');
        
        // Hide progress indicator in landscape
        const progressIndicator = document.querySelector('.form-progress-indicator');
        if (progressIndicator) {
          progressIndicator.style.display = 'none';
        }
      } else {
        document.body.classList.remove('mobile-landscape');
        
        // Show progress indicator in portrait
        const progressIndicator = document.querySelector('.form-progress-indicator');
        if (progressIndicator) {
          progressIndicator.style.display = '';
        }
      }

      // Adjust form section spacing
      const formSections = document.querySelectorAll('.form-section');
      if (viewport.width <= 575) {
        formSections.forEach(section => {
          section.style.padding = '16px';
          section.style.marginBottom = '12px';
        });
      } else if (viewport.width <= 767) {
        formSections.forEach(section => {
          section.style.padding = '20px';
          section.style.marginBottom = '16px';
        });
      }
    };

    // Initial adjustment
    adjustForViewport();

    // Adjust on resize and orientation change
    window.addEventListener('resize', debounce(adjustForViewport, 250));
    window.addEventListener('orientationchange', () => {
      setTimeout(adjustForViewport, 100);
    });
  }
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

// Add responsive CSS for forms
const responsiveFormStyles = document.createElement('style');
responsiveFormStyles.textContent = `
  /* Mobile form optimizations */
  @media (max-width: 767px) {
    .property-form-container {
      padding: 16px 0 !important;
    }
    
    .form-progress-indicator {
      position: relative !important;
      top: auto !important;
      margin: 0 -16px 20px -16px !important;
      border-radius: 0 !important;
    }
    
    .progress-steps {
      display: flex !important;
      overflow-x: auto !important;
      gap: 8px !important;
      padding: 8px 16px !important;
      scrollbar-width: thin;
    }
    
    .progress-step {
      flex-shrink: 0 !important;
      min-width: 120px !important;
      font-size: 14px !important;
      padding: 8px 12px !important;
    }
    
    .form-section {
      margin: 0 -16px 16px -16px !important;
      border-radius: 0 !important;
      border-left: none !important;
      border-right: none !important;
      padding: 16px !important;
    }
    
    .form-actions {
      position: sticky !important;
      bottom: 0 !important;
      background: white !important;
      padding: 16px !important;
      margin: 0 -16px !important;
      border-top: 1px solid var(--property-gray-200) !important;
      box-shadow: 0 -2px 8px rgba(0,0,0,0.1) !important;
      z-index: 10 !important;
      display: flex !important;
      flex-direction: column !important;
      gap: 12px !important;
    }
    
    .file-upload-wrapper,
    #dragDropZone {
      margin: 0 -16px !important;
      border-radius: 0 !important;
      border-left: none !important;
      border-right: none !important;
    }
  }
  
  /* Tablet form optimizations */
  @media (min-width: 768px) and (max-width: 991px) {
    .form-progress-indicator {
      position: sticky !important;
      top: 20px !important;
    }
    
    .progress-steps {
      display: grid !important;
      grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)) !important;
      gap: 12px !important;
    }
    
    .form-section {
      padding: 24px !important;
      margin-bottom: 24px !important;
    }
    
    .form-actions {
      display: flex !important;
      justify-content: space-between !important;
      gap: 16px !important;
    }
    
    .form-actions .btn {
      flex: 1 !important;
      max-width: 200px !important;
    }
  }
  
  /* Touch device optimizations */
  @media (hover: none) and (pointer: coarse) {
    .form-control,
    .form-select {
      min-height: 44px !important;
      font-size: 16px !important; /* Prevents zoom on iOS */
    }
    
    .btn {
      min-height: 44px !important;
      min-width: 44px !important;
    }
    
    .form-check-input {
      width: 20px !important;
      height: 20px !important;
    }
    
    .form-check-label {
      min-height: 44px !important;
      display: flex !important;
      align-items: center !important;
      padding-left: 8px !important;
    }
    
    .progress-step {
      min-height: 44px !important;
    }
  }
  
  /* Landscape mobile optimizations */
  @media (max-width: 767px) and (orientation: landscape) {
    .form-progress-indicator {
      display: none !important;
    }
    
    .property-form-container {
      padding: 8px 0 !important;
    }
    
    .form-section {
      padding: 16px !important;
      margin-bottom: 12px !important;
    }
    
    .form-actions {
      position: relative !important;
      bottom: auto !important;
      box-shadow: none !important;
      border-top: none !important;
    }
  }
`;
document.head.appendChild(responsiveFormStyles);

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
  new PropertyFormEnhancer();
  new ResponsiveFormEnhancer();
});