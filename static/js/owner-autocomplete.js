/**
 * Owner Autocomplete Component
 * Maneja la funcionalidad de búsqueda de dueños con autocomplete y creación de nuevos dueños
 */

class OwnerAutocomplete {
    constructor(inputElement, options = {}) {
        this.input = inputElement;
        this.hiddenInput = null;
        this.dropdown = null;
        this.createModal = null;
        this.options = {
            minLength: 2,
            delay: 300,
            maxResults: 10,
            placeholder: 'Buscar dueño por nombre, apellido o email...',
            noResultsText: 'No se encontraron resultados',
            createText: 'Crear nuevo dueño',
            autocompleteUrl: '/properties/ajax/owners/autocomplete/',
            createUrl: '/customers/ajax/create/',
            ...options
        };
        
        this.searchTimeout = null;
        this.selectedOwner = null;
        
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
        // Crear input hidden para almacenar el ID del dueño
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
        this.dropdown.className = 'owner-autocomplete-dropdown';
        this.dropdown.style.cssText = `
            position: absolute;
            top: 100%;
            left: 0;
            right: 0;
            background: white;
            border: 1px solid #ddd;
            border-radius: 0.375rem;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            max-height: 300px;
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
            if (!e.target.closest('.owner-autocomplete-dropdown') && 
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
            if (this.selectedOwner && this.input.value !== this.selectedOwner.text) {
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
            console.error('Error en búsqueda de dueños:', error);
            this.showError('Error al buscar dueños');
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
                    <i class="bi bi-person me-2"></i>
                    <div>
                        <div class="fw-semibold">${result.text}</div>
                    </div>
                `;
                item.dataset.id = result.id;
                item.dataset.text = result.text;
                
                item.addEventListener('click', () => {
                    this.selectOwner(result);
                });
                
                this.dropdown.appendChild(item);
            });
            
            // Agregar opción para crear nuevo
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
    
    selectOwner(owner) {
        this.selectedOwner = owner;
        this.input.value = owner.text;
        this.hiddenInput.value = owner.id;
        this.hideDropdown();
        
        // Disparar evento personalizado
        const event = new CustomEvent('ownerSelected', { 
            detail: owner,
            bubbles: true 
        });
        this.input.dispatchEvent(event);
    }
    
    clearSelection() {
        this.selectedOwner = null;
        this.hiddenInput.value = '';
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
        // Crear modal HTML
        const modalHtml = `
            <div class="modal fade" id="createOwnerModal" tabindex="-1" aria-labelledby="createOwnerModalLabel" aria-hidden="true">
                <div class="modal-dialog">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title" id="createOwnerModalLabel">
                                <i class="bi bi-person-plus me-2"></i>Crear Nuevo Dueño
                            </h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                        </div>
                        <div class="modal-body">
                            <form id="createOwnerForm">
                                <div class="row">
                                    <div class="col-md-6 mb-3">
                                        <label for="newOwnerFirstName" class="form-label">Nombre *</label>
                                        <input type="text" class="form-control" id="newOwnerFirstName" required>
                                    </div>
                                    <div class="col-md-6 mb-3">
                                        <label for="newOwnerLastName" class="form-label">Apellido *</label>
                                        <input type="text" class="form-control" id="newOwnerLastName" required>
                                    </div>
                                </div>
                                <div class="mb-3">
                                    <label for="newOwnerEmail" class="form-label">Email *</label>
                                    <input type="email" class="form-control" id="newOwnerEmail" required>
                                </div>
                                <div class="row">
                                    <div class="col-md-6 mb-3">
                                        <label for="newOwnerPhone" class="form-label">Teléfono</label>
                                        <input type="text" class="form-control" id="newOwnerPhone">
                                    </div>
                                    <div class="col-md-6 mb-3">
                                        <label for="newOwnerDocument" class="form-label">Documento</label>
                                        <input type="text" class="form-control" id="newOwnerDocument">
                                    </div>
                                </div>
                                <div class="alert alert-info">
                                    <i class="bi bi-info-circle me-2"></i>
                                    <small>Los campos marcados con * son obligatorios.</small>
                                </div>
                                <div id="createOwnerError" class="alert alert-danger d-none"></div>
                            </form>
                        </div>
                        <div class="modal-footer">
                            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancelar</button>
                            <button type="button" class="btn btn-primary" id="saveOwnerBtn">
                                <i class="bi bi-check-circle me-1"></i>Crear Dueño
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        // Agregar modal al DOM si no existe
        if (!document.getElementById('createOwnerModal')) {
            document.body.insertAdjacentHTML('beforeend', modalHtml);
        }
        
        this.createModal = new bootstrap.Modal(document.getElementById('createOwnerModal'));
        
        // Bind eventos del modal
        document.getElementById('saveOwnerBtn').addEventListener('click', () => {
            this.createOwner();
        });
        
        // Limpiar formulario al cerrar modal
        document.getElementById('createOwnerModal').addEventListener('hidden.bs.modal', () => {
            this.resetCreateForm();
        });
    }
    
    showCreateModal(query = '') {
        this.hideDropdown();
        
        // Pre-llenar campos si es posible parsear el query
        const queryParts = query.split(' ');
        if (queryParts.length >= 2) {
            document.getElementById('newOwnerFirstName').value = queryParts[0] || '';
            document.getElementById('newOwnerLastName').value = queryParts.slice(1).join(' ') || '';
        } else if (query.includes('@')) {
            document.getElementById('newOwnerEmail').value = query;
        } else if (queryParts.length === 1) {
            document.getElementById('newOwnerFirstName').value = query;
        }
        
        this.createModal.show();
    }
    
    createOwner() {
        const form = document.getElementById('createOwnerForm');
        const errorDiv = document.getElementById('createOwnerError');
        const saveBtn = document.getElementById('saveOwnerBtn');
        
        // Recopilar datos
        const data = {
            first_name: document.getElementById('newOwnerFirstName').value.trim(),
            last_name: document.getElementById('newOwnerLastName').value.trim(),
            email: document.getElementById('newOwnerEmail').value.trim(),
            phone: document.getElementById('newOwnerPhone').value.trim(),
            document: document.getElementById('newOwnerDocument').value.trim()
        };
        
        // Validaciones básicas
        if (!data.first_name || !data.last_name || !data.email) {
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
                // Seleccionar el nuevo dueño
                this.selectOwner({
                    id: result.customer.id,
                    text: result.customer.text
                });
                
                // Cerrar modal
                this.createModal.hide();
                
                // Mostrar notificación de éxito
                this.showNotification('Dueño creado correctamente', 'success');
            } else {
                this.showCreateError(result.error || 'Error al crear el dueño');
            }
        })
        .catch(error => {
            console.error('Error creando dueño:', error);
            this.showCreateError('Error de conexión al crear el dueño');
        })
        .finally(() => {
            // Rehabilitar botón
            saveBtn.disabled = false;
            saveBtn.innerHTML = '<i class="bi bi-check-circle me-1"></i>Crear Dueño';
        });
    }
    
    showCreateError(message) {
        const errorDiv = document.getElementById('createOwnerError');
        errorDiv.textContent = message;
        errorDiv.classList.remove('d-none');
    }
    
    resetCreateForm() {
        document.getElementById('createOwnerForm').reset();
        document.getElementById('createOwnerError').classList.add('d-none');
    }
    
    loadInitialValue() {
        const ownerId = this.hiddenInput.value;
        if (ownerId) {
            // Hacer petición para obtener datos del dueño
            fetch(`${this.options.autocompleteUrl}?term=&id=${ownerId}`, {
                headers: {
                    'X-Requested-With': 'XMLHttpRequest',
                    'X-CSRFToken': this.getCSRFToken()
                }
            })
            .then(response => response.json())
            .then(data => {
                if (data.results && data.results.length > 0) {
                    const owner = data.results[0];
                    this.input.value = owner.text;
                    this.selectedOwner = owner;
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
    // Inicializar todos los campos con clase 'owner-autocomplete'
    const ownerInputs = document.querySelectorAll('.owner-autocomplete');
    ownerInputs.forEach(input => {
        new OwnerAutocomplete(input);
    });
});

// Exportar para uso global
window.OwnerAutocomplete = OwnerAutocomplete;
