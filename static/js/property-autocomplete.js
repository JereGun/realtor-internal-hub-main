/**
 * Property Autocomplete Component
 * Maneja la funcionalidad de búsqueda de propiedades con autocomplete y creación de nuevas propiedades
 */

class PropertyAutocomplete {
    constructor(inputElement, options = {}) {
        this.input = inputElement;
        this.hiddenInput = null;
        this.dropdown = null;
        this.createModal = null;
        this.options = {
            minLength: 2,
            delay: 300,
            maxResults: 10,
            placeholder: 'Buscar propiedad por título, dirección o código...',
            noResultsText: 'No se encontraron propiedades',
            createText: 'Crear nueva propiedad',
            autocompleteUrl: '/properties/ajax/autocomplete/',
            createUrl: '/properties/ajax/create/',
            ...options
        };
        
        this.searchTimeout = null;
        this.selectedProperty = null;
        
        this.init();
    }
    
    init() {
        this.setupElements();
        this.bindEvents();
        this.setupModal();
        
        // Si hay un valor inicial, establecerlo
        if (this.hiddenInput.value) {
            this.loadInitialValue();
        }
    }
    
    setupElements() {
        // Crear input hidden para almacenar el ID de la propiedad
        this.hiddenInput = document.createElement('input');
        this.hiddenInput.type = 'hidden';
        this.hiddenInput.name = this.input.name;
        this.hiddenInput.id = this.input.id;
        
        // Cambiar el name y id del input visible
        this.input.name = this.input.name + '_display';
        this.input.id = this.input.id + '_display';
        this.input.placeholder = this.options.placeholder;
        this.input.setAttribute('autocomplete', 'off');
        
        // Insertar el hidden input después del visible
        this.input.parentNode.insertBefore(this.hiddenInput, this.input.nextSibling);
        
        // Crear dropdown
        this.dropdown = document.createElement('div');
        this.dropdown.className = 'property-autocomplete-dropdown';
        this.dropdown.style.cssText = `
            position: absolute;
            top: 100%;
            left: 0;
            right: 0;
            background: white;
            border: 1px solid #ddd;
            border-radius: 0.375rem;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            max-height: 400px;
            overflow-y: auto;
            z-index: 1000;
            display: none;
        `;
        
        // Contenedor posicional
        const container = document.createElement('div');
        container.style.position = 'relative';
        container.style.display = 'inline-block';
        container.style.width = '100%';
        
        this.input.parentNode.insertBefore(container, this.input);
        container.appendChild(this.input);
        container.appendChild(this.dropdown);
    }
    
    bindEvents() {
        // Búsqueda con debounce
        this.input.addEventListener('input', (e) => {
            const query = e.target.value.trim();
            
            if (this.searchTimeout) {
                clearTimeout(this.searchTimeout);
            }
            
            if (query.length < this.options.minLength) {
                this.hideDropdown();
                this.clearSelection();
                return;
            }
            
            this.searchTimeout = setTimeout(() => {
                this.search(query);
            }, this.options.delay);
        });
        
        // Ocultar dropdown cuando se hace clic fuera
        document.addEventListener('click', (e) => {
            if (!e.target.closest('.property-autocomplete-dropdown') && 
                e.target !== this.input) {
                this.hideDropdown();
            }
        });
        
        // Manejar teclas
        this.input.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                this.hideDropdown();
            }
        });
        
        // Limpiar selección cuando se modifica manualmente
        this.input.addEventListener('focus', () => {
            if (this.selectedProperty && this.input.value !== this.selectedProperty.text) {
                this.clearSelection();
            }
        });
    }
    
    search(query) {
        const url = `${this.options.autocompleteUrl}?term=${encodeURIComponent(query)}`;
        
        fetch(url, {
            headers: {
                'X-Requested-With': 'XMLHttpRequest',
                'X-CSRFToken': this.getCSRFToken()
            }
        })
        .then(response => response.json())
        .then(data => {
            this.showResults(data.results || [], query);
        })
        .catch(error => {
            console.error('Error en búsqueda de propiedades:', error);
            this.showError('Error al buscar propiedades');
        });
    }
    
    showResults(results, query) {
        this.dropdown.innerHTML = '';
        
        if (results.length === 0) {
            this.dropdown.innerHTML = `
                <div class="dropdown-item no-results">
                    <i class="bi bi-search me-2"></i>
                    ${this.options.noResultsText}
                </div>
                <div class="dropdown-item create-new" data-query="${query}">
                    <i class="bi bi-plus-circle me-2"></i>
                    ${this.options.createText}: "${query}"
                </div>
            `;
        } else {
            results.forEach(result => {
                const item = document.createElement('div');
                item.className = 'dropdown-item';
                item.innerHTML = `
                    <div class="d-flex align-items-center">
                        <div class="property-icon me-3">
                            <i class="bi bi-house-door text-primary"></i>
                        </div>
                        <div class="flex-grow-1">
                            <div class="fw-semibold">${result.title}</div>
                            <small class="text-muted">${result.address || 'Sin dirección'}</small>
                            <div class="d-flex gap-2 mt-1">
                                <span class="badge bg-light text-dark">${result.property_type || 'N/A'}</span>
                                <span class="badge bg-${this.getStatusColor(result.status)}">${result.status || 'N/A'}</span>
                            </div>
                        </div>
                        <div class="text-end">
                            <small class="text-muted">${result.surface || 'N/A'} m²</small>
                        </div>
                    </div>
                `;
                item.dataset.id = result.id;
                item.dataset.text = result.title;
                
                item.addEventListener('click', () => {
                    this.selectProperty(result);
                });
                
                this.dropdown.appendChild(item);
            });
            
            // Agregar opción para crear nueva
            const createItem = document.createElement('div');
            createItem.className = 'dropdown-item create-new border-top';
            createItem.innerHTML = `
                <i class="bi bi-plus-circle me-2"></i>
                ${this.options.createText}
            `;
            createItem.dataset.query = query;
            
            createItem.addEventListener('click', () => {
                this.showCreateModal(query);
            });
            
            this.dropdown.appendChild(createItem);
        }
        
        // Agregar estilos
        this.dropdown.querySelectorAll('.dropdown-item').forEach(item => {
            item.style.cssText = `
                padding: 0.75rem 1rem;
                cursor: pointer;
                border-bottom: 1px solid #f0f0f0;
                transition: background-color 0.2s;
            `;
            
            if (item.classList.contains('no-results')) {
                item.style.cursor = 'default';
                item.style.color = '#6c757d';
            }
            
            if (item.classList.contains('create-new')) {
                item.style.backgroundColor = '#f8f9fa';
                item.style.color = '#0d6efd';
                item.style.fontWeight = '500';
            }
            
            item.addEventListener('mouseenter', () => {
                if (!item.classList.contains('no-results')) {
                    item.style.backgroundColor = '#f8f9fa';
                }
            });
            
            item.addEventListener('mouseleave', () => {
                if (!item.classList.contains('create-new')) {
                    item.style.backgroundColor = 'white';
                } else {
                    item.style.backgroundColor = '#f8f9fa';
                }
            });
        });
        
        this.showDropdown();
    }
    
    getStatusColor(status) {
        const statusColors = {
            'disponible': 'success',
            'vendida': 'danger',
            'alquilada': 'warning',
            'reservada': 'info',
            'en_proceso': 'secondary'
        };
        return statusColors[status] || 'secondary';
    }
    
    selectProperty(property) {
        this.selectedProperty = property;
        this.input.value = property.title;
        this.hiddenInput.value = property.id;
        this.hideDropdown();
        
        // Disparar evento personalizado
        const event = new CustomEvent('propertySelected', { 
            detail: property,
            bubbles: true 
        });
        this.input.dispatchEvent(event);
        
        // Actualizar información de la propiedad en el formulario
        this.updatePropertyInfo(property);
    }
    
    updatePropertyInfo(property) {
        // Actualizar elementos de información si existen
        const infoContainer = document.querySelector('.property-info-container');
        if (infoContainer) {
            infoContainer.innerHTML = `
                <div class="card">
                    <div class="card-body">
                        <div class="d-flex align-items-center">
                            <div class="property-icon me-3">
                                <i class="bi bi-house-door text-primary" style="font-size: 2rem;"></i>
                            </div>
                            <div class="flex-grow-1">
                                <h6 class="mb-1">${property.title}</h6>
                                <p class="text-muted mb-1">${property.address || 'Sin dirección'}</p>
                                <div class="d-flex gap-2">
                                    <span class="badge bg-light text-dark">${property.property_type || 'N/A'}</span>
                                    <span class="badge bg-${this.getStatusColor(property.status)}">${property.status || 'N/A'}</span>
                                    <span class="badge bg-secondary">${property.surface || 'N/A'} m²</span>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            `;
        }
    }
    
    clearSelection() {
        this.selectedProperty = null;
        this.hiddenInput.value = '';
        
        // Limpiar información de la propiedad
        const infoContainer = document.querySelector('.property-info-container');
        if (infoContainer) {
            infoContainer.innerHTML = '';
        }
    }
    
    showDropdown() {
        this.dropdown.style.display = 'block';
    }
    
    hideDropdown() {
        this.dropdown.style.display = 'none';
    }
    
    showError(message) {
        this.dropdown.innerHTML = `
            <div class="dropdown-item">
                <i class="bi bi-exclamation-triangle text-danger me-2"></i>
                <span class="text-danger">${message}</span>
            </div>
        `;
        this.showDropdown();
    }
    
    setupModal() {
        // Crear modal HTML para crear nueva propiedad
        const modalHtml = `
            <div class="modal fade" id="createPropertyModal" tabindex="-1" aria-labelledby="createPropertyModalLabel" aria-hidden="true">
                <div class="modal-dialog modal-lg">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title" id="createPropertyModalLabel">
                                <i class="bi bi-house-add me-2"></i>Crear Nueva Propiedad
                            </h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                        </div>
                        <div class="modal-body">
                            <form id="createPropertyForm">
                                <div class="row">
                                    <div class="col-md-8 mb-3">
                                        <label for="newPropertyTitle" class="form-label">Título *</label>
                                        <input type="text" class="form-control" id="newPropertyTitle" required>
                                    </div>
                                    <div class="col-md-4 mb-3">
                                        <label for="newPropertyType" class="form-label">Tipo *</label>
                                        <select class="form-select" id="newPropertyType" required>
                                            <option value="">Seleccionar...</option>
                                            <option value="casa">Casa</option>
                                            <option value="departamento">Departamento</option>
                                            <option value="local">Local Comercial</option>
                                            <option value="oficina">Oficina</option>
                                            <option value="terreno">Terreno</option>
                                            <option value="galpon">Galpón</option>
                                        </select>
                                    </div>
                                </div>
                                <div class="mb-3">
                                    <label for="newPropertyDescription" class="form-label">Descripción</label>
                                    <textarea class="form-control" id="newPropertyDescription" rows="3"></textarea>
                                </div>
                                <div class="row">
                                    <div class="col-md-6 mb-3">
                                        <label for="newPropertyStreet" class="form-label">Calle</label>
                                        <input type="text" class="form-control" id="newPropertyStreet">
                                    </div>
                                    <div class="col-md-3 mb-3">
                                        <label for="newPropertyNumber" class="form-label">Número</label>
                                        <input type="text" class="form-control" id="newPropertyNumber">
                                    </div>
                                    <div class="col-md-3 mb-3">
                                        <label for="newPropertySurface" class="form-label">Superficie (m²)</label>
                                        <input type="number" class="form-control" id="newPropertySurface" step="0.01" min="0">
                                    </div>
                                </div>
                                <div class="row">
                                    <div class="col-md-6 mb-3">
                                        <label for="newPropertyStatus" class="form-label">Estado *</label>
                                        <select class="form-select" id="newPropertyStatus" required>
                                            <option value="">Seleccionar...</option>
                                            <option value="disponible">Disponible</option>
                                            <option value="reservada">Reservada</option>
                                            <option value="vendida">Vendida</option>
                                            <option value="alquilada">Alquilada</option>
                                        </select>
                                    </div>
                                    <div class="col-md-6 mb-3">
                                        <label for="newPropertyListingType" class="form-label">Tipo de Operación</label>
                                        <select class="form-select" id="newPropertyListingType">
                                            <option value="">Seleccionar...</option>
                                            <option value="venta">Venta</option>
                                            <option value="alquiler">Alquiler</option>
                                            <option value="venta_alquiler">Venta y Alquiler</option>
                                        </select>
                                    </div>
                                </div>
                                <div class="alert alert-info">
                                    <i class="bi bi-info-circle me-2"></i>
                                    <small>Los campos marcados con * son obligatorios. Podrás completar más detalles después de crear la propiedad.</small>
                                </div>
                                <div id="createPropertyError" class="alert alert-danger d-none"></div>
                            </form>
                        </div>
                        <div class="modal-footer">
                            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancelar</button>
                            <button type="button" class="btn btn-primary" id="savePropertyBtn">
                                <i class="bi bi-check-circle me-1"></i>Crear Propiedad
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        // Agregar modal al DOM si no existe
        if (!document.getElementById('createPropertyModal')) {
            document.body.insertAdjacentHTML('beforeend', modalHtml);
        }
        
        this.createModal = new bootstrap.Modal(document.getElementById('createPropertyModal'));
        
        // Bind eventos del modal
        document.getElementById('savePropertyBtn').addEventListener('click', () => {
            this.createProperty();
        });
        
        // Limpiar formulario al cerrar modal
        document.getElementById('createPropertyModal').addEventListener('hidden.bs.modal', () => {
            this.resetCreateForm();
        });
    }
    
    showCreateModal(query = '') {
        this.hideDropdown();
        
        // Pre-llenar título si es posible
        if (query) {
            document.getElementById('newPropertyTitle').value = query;
        }
        
        this.createModal.show();
    }
    
    createProperty() {
        const form = document.getElementById('createPropertyForm');
        const errorDiv = document.getElementById('createPropertyError');
        const saveBtn = document.getElementById('savePropertyBtn');
        
        // Recopilar datos
        const data = {
            title: document.getElementById('newPropertyTitle').value.trim(),
            property_type: document.getElementById('newPropertyType').value,
            description: document.getElementById('newPropertyDescription').value.trim(),
            street: document.getElementById('newPropertyStreet').value.trim(),
            number: document.getElementById('newPropertyNumber').value.trim(),
            total_surface: document.getElementById('newPropertySurface').value,
            property_status: document.getElementById('newPropertyStatus').value,
            listing_type: document.getElementById('newPropertyListingType').value
        };
        
        // Validaciones básicas
        if (!data.title || !data.property_type || !data.property_status) {
            this.showCreateError('Todos los campos marcados con * son obligatorios');
            return;
        }
        
        // Deshabilitar botón
        saveBtn.disabled = true;
        saveBtn.innerHTML = '<i class="bi bi-hourglass me-1"></i>Creando...';
        errorDiv.classList.add('d-none');
        
        // Enviar petición
        fetch(this.options.createUrl, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-Requested-With': 'XMLHttpRequest',
                'X-CSRFToken': this.getCSRFToken()
            },
            body: JSON.stringify(data)
        })
        .then(response => response.json())
        .then(result => {
            if (result.success) {
                // Seleccionar la nueva propiedad
                this.selectProperty({
                    id: result.property.id,
                    title: result.property.title,
                    address: result.property.address,
                    property_type: result.property.property_type,
                    status: result.property.status,
                    surface: result.property.surface
                });
                
                // Cerrar modal
                this.createModal.hide();
                
                // Mostrar notificación de éxito
                this.showNotification('Propiedad creada correctamente', 'success');
            } else {
                this.showCreateError(result.error || 'Error al crear la propiedad');
            }
        })
        .catch(error => {
            console.error('Error creando propiedad:', error);
            this.showCreateError('Error de conexión al crear la propiedad');
        })
        .finally(() => {
            // Rehabilitar botón
            saveBtn.disabled = false;
            saveBtn.innerHTML = '<i class="bi bi-check-circle me-1"></i>Crear Propiedad';
        });
    }
    
    showCreateError(message) {
        const errorDiv = document.getElementById('createPropertyError');
        errorDiv.textContent = message;
        errorDiv.classList.remove('d-none');
    }
    
    resetCreateForm() {
        document.getElementById('createPropertyForm').reset();
        document.getElementById('createPropertyError').classList.add('d-none');
    }
    
    loadInitialValue() {
        const propertyId = this.hiddenInput.value;
        if (propertyId) {
            // Hacer petición para obtener datos de la propiedad
            fetch(`${this.options.autocompleteUrl}?term=&id=${propertyId}`, {
                headers: {
                    'X-Requested-With': 'XMLHttpRequest',
                    'X-CSRFToken': this.getCSRFToken()
                }
            })
            .then(response => response.json())
            .then(data => {
                if (data.results && data.results.length > 0) {
                    const property = data.results[0];
                    this.input.value = property.title;
                    this.selectedProperty = property;
                    this.updatePropertyInfo(property);
                }
            })
            .catch(error => {
                console.error('Error cargando valor inicial:', error);
            });
        }
    }
    
    showNotification(message, type = 'info') {
        // Crear notificación Bootstrap toast
        const toastContainer = this.getToastContainer();
        const iconClass = type === 'success' ? 'bi-check-circle-fill text-success' : 'bi-info-circle-fill text-info';
        const headerText = type === 'success' ? 'Éxito' : 'Información';
        
        const toastHtml = `
            <div class="toast" role="alert" aria-live="assertive" aria-atomic="true">
                <div class="toast-header">
                    <i class="${iconClass} me-2"></i>
                    <strong class="me-auto">${headerText}</strong>
                    <button type="button" class="btn-close" data-bs-dismiss="toast" aria-label="Close"></button>
                </div>
                <div class="toast-body">
                    ${message}
                </div>
            </div>
        `;
        
        toastContainer.insertAdjacentHTML('beforeend', toastHtml);
        const toast = new bootstrap.Toast(toastContainer.lastElementChild);
        toast.show();
        
        toastContainer.lastElementChild.addEventListener('hidden.bs.toast', function() {
            this.remove();
        });
    }
    
    getToastContainer() {
        let container = document.querySelector('.toast-container');
        if (!container) {
            container = document.createElement('div');
            container.className = 'toast-container position-fixed top-0 end-0 p-3';
            container.style.zIndex = '9999';
            document.body.appendChild(container);
        }
        return container;
    }
    
    getCSRFToken() {
        return document.querySelector('[name=csrfmiddlewaretoken]')?.value || 
               document.querySelector('meta[name="csrf-token"]')?.content || '';
    }
}

// Auto-inicializar cuando el DOM esté listo
document.addEventListener('DOMContentLoaded', function() {
    // Inicializar todos los campos con clase 'property-autocomplete'
    const propertyInputs = document.querySelectorAll('.property-autocomplete');
    propertyInputs.forEach(input => {
        new PropertyAutocomplete(input);
    });
});

// Exportar para uso global
window.PropertyAutocomplete = PropertyAutocomplete;