/**
 * Location Autocomplete Component
 * Maneja la funcionalidad de búsqueda jerárquica de ubicaciones (País, Provincia, Ciudad, Barrio)
 * con autocomplete y creación de nuevos elementos
 */

class LocationAutocomplete {
    constructor(options = {}) {
        this.options = {
            countryFieldSelector: '.country-autocomplete',
            stateFieldSelector: '.state-autocomplete', 
            cityFieldSelector: '.city-autocomplete',
            neighborhoodFieldSelector: '.neighborhood-autocomplete',
            minLength: 2,
            delay: 300,
            maxResults: 10,
            noResultsText: 'No se encontraron resultados',
            createText: 'Crear nuevo',
            urls: {
                countries: '/locations/ajax/countries/autocomplete/',
                states: '/locations/ajax/states/autocomplete/',
                cities: '/locations/ajax/cities/autocomplete/',
                createCountry: '/locations/ajax/countries/create/',
                createState: '/locations/ajax/states/create/',
                createCity: '/locations/ajax/cities/create/'
            },
            ...options
        };
        
        this.elements = {};
        this.modals = {};
        this.selectedValues = {
            country: null,
            state: null,
            city: null
        };
        
        this.init();
    }
    
    init() {
        this.findElements();
        this.setupElements();
        this.setupModals();
        this.bindEvents();
    }
    
    findElements() {
        // Encontrar todos los campos de ubicación
        this.elements.country = document.querySelectorAll(this.options.countryFieldSelector);
        this.elements.state = document.querySelectorAll(this.options.stateFieldSelector);
        this.elements.city = document.querySelectorAll(this.options.cityFieldSelector);
        this.elements.neighborhood = document.querySelectorAll(this.options.neighborhoodFieldSelector);
    }
    
    setupElements() {
        // Configurar campos de país
        this.elements.country.forEach(input => {
            this.setupAutocompleteField(input, 'country');
        });
        
        // Configurar campos de provincia/estado
        this.elements.state.forEach(input => {
            this.setupAutocompleteField(input, 'state');
        });
        
        // Configurar campos de ciudad
        this.elements.city.forEach(input => {
            this.setupAutocompleteField(input, 'city');
        });
        
        // Configurar campos de barrio (solo autocompletado, no hay jerarquía)
        this.elements.neighborhood.forEach(input => {
            this.setupNeighborhoodField(input);
        });
    }
    
    setupAutocompleteField(input, type) {
        // Crear estructura para autocomplete
        const container = this.createAutocompleteContainer(input);
        const hiddenInput = this.createHiddenInput(input);
        const dropdown = this.createDropdown();
        
        container.appendChild(input);
        container.appendChild(dropdown);
        container.appendChild(hiddenInput);
        
        // Almacenar referencias
        input._autocomplete = {
            type: type,
            container: container,
            dropdown: dropdown,
            hiddenInput: hiddenInput,
            searchTimeout: null,
            selectedValue: null
        };
        
        // Configurar eventos específicos
        this.bindAutocompleteEvents(input);
    }
    
    setupNeighborhoodField(input) {
        // Para el barrio, solo configuramos un campo de texto simple sin jerarquía
        input.setAttribute('placeholder', 'Escriba el nombre del barrio...');
        
        // Opcional: podríamos agregar autocompletado basado en barrios existentes
        // Por ahora lo dejamos como campo de texto libre
    }
    
    createAutocompleteContainer(input) {
        const container = document.createElement('div');
        container.style.cssText = `
            position: relative;
            display: inline-block;
            width: 100%;
        `;
        
        input.parentNode.insertBefore(container, input);
        return container;
    }
    
    createHiddenInput(input) {
        const hiddenInput = document.createElement('input');
        hiddenInput.type = 'hidden';
        hiddenInput.name = input.name;
        hiddenInput.id = input.id;
        
        // Cambiar el name y id del input visible
        input.name = input.name + '_display';
        input.id = input.id + '_display';
        input.setAttribute('autocomplete', 'off');
        
        return hiddenInput;
    }
    
    createDropdown() {
        const dropdown = document.createElement('div');
        dropdown.className = 'location-autocomplete-dropdown';
        dropdown.style.cssText = `
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
        return dropdown;
    }
    
    bindAutocompleteEvents(input) {
        const autocomplete = input._autocomplete;
        
        // Búsqueda con debounce
        input.addEventListener('input', (e) => {
            const query = e.target.value.trim();
            
            if (autocomplete.searchTimeout) {
                clearTimeout(autocomplete.searchTimeout);
            }
            
            if (query.length < this.options.minLength) {
                this.hideDropdown(autocomplete.dropdown);
                this.clearSelection(input);
                return;
            }
            
            autocomplete.searchTimeout = setTimeout(() => {
                this.search(input, query);
            }, this.options.delay);
        });
        
        // Ocultar dropdown cuando se hace clic fuera
        document.addEventListener('click', (e) => {
            if (!e.target.closest('.location-autocomplete-dropdown') && 
                e.target !== input) {
                this.hideDropdown(autocomplete.dropdown);
            }
        });
        
        // Manejar teclas
        input.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                this.hideDropdown(autocomplete.dropdown);
            }
        });
        
        // Limpiar selección cuando se modifica manualmente
        input.addEventListener('focus', () => {
            if (autocomplete.selectedValue && input.value !== autocomplete.selectedValue.text) {
                this.clearSelection(input);
            }
        });
    }
    
    bindEvents() {
        // Eventos globales ya están manejados en bindAutocompleteEvents
        // Aquí podríamos agregar eventos adicionales si fuera necesario
    }
    
    search(input, query) {
        const autocomplete = input._autocomplete;
        const type = autocomplete.type;
        
        let url = this.options.urls[type === 'state' ? 'states' : type === 'city' ? 'cities' : 'countries'];
        url += `?term=${encodeURIComponent(query)}`;
        
        // Agregar filtros jerárquicos
        if (type === 'state' && this.selectedValues.country) {
            url += `&country_id=${this.selectedValues.country.id}`;
        } else if (type === 'city' && this.selectedValues.state) {
            url += `&state_id=${this.selectedValues.state.id}`;
        }
        
        fetch(url, {
            headers: {
                'X-Requested-With': 'XMLHttpRequest',
                'X-CSRFToken': this.getCSRFToken()
            }
        })
        .then(response => response.json())
        .then(data => {
            this.showResults(input, data.results || [], query);
        })
        .catch(error => {
            console.error('Error en búsqueda de ubicación:', error);
            this.showError(autocomplete.dropdown, 'Error al buscar ubicación');
        });
    }
    
    showResults(input, results, query) {
        const autocomplete = input._autocomplete;
        const dropdown = autocomplete.dropdown;
        const type = autocomplete.type;
        
        dropdown.innerHTML = '';
        
        if (results.length === 0) {
            dropdown.innerHTML = `
                <div class="dropdown-item no-results">
                    <i class="bi bi-search me-2"></i>
                    ${this.options.noResultsText}
                </div>
                <div class="dropdown-item create-new" data-query="${query}" data-type="${type}">
                    <i class="bi bi-plus-circle me-2"></i>
                    ${this.options.createText} ${this.getTypeLabel(type)}: "${query}"
                </div>
            `;
        } else {
            results.forEach(result => {
                const item = document.createElement('div');
                item.className = 'dropdown-item';
                item.innerHTML = `
                    <i class="${this.getTypeIcon(type)} me-2"></i>
                    <div>
                        <div class="fw-semibold">${result.text}</div>
                    </div>
                `;
                
                // Almacenar datos completos
                item._data = result;
                
                item.addEventListener('click', () => {
                    this.selectLocation(input, result);
                });
                
                dropdown.appendChild(item);
            });
            
            // Agregar opción para crear nuevo
            const createItem = document.createElement('div');
            createItem.className = 'dropdown-item create-new border-top';
            createItem.innerHTML = `
                <i class="bi bi-plus-circle me-2"></i>
                ${this.options.createText} ${this.getTypeLabel(type)}
            `;
            createItem.dataset.query = query;
            createItem.dataset.type = type;
            
            createItem.addEventListener('click', () => {
                this.showCreateModal(type, query);
            });
            
            dropdown.appendChild(createItem);
        }
        
        // Agregar estilos
        this.styleDropdownItems(dropdown);
        this.showDropdown(dropdown);
    }
    
    selectLocation(input, location) {
        const autocomplete = input._autocomplete;
        const type = autocomplete.type;
        
        autocomplete.selectedValue = location;
        input.value = location.name; // Mostrar solo el nombre, no la descripción completa
        autocomplete.hiddenInput.value = location.id;
        this.hideDropdown(autocomplete.dropdown);
        
        // Actualizar valores seleccionados para jerarquía
        this.selectedValues[type] = location;
        
        // Limpiar campos dependientes
        this.clearDependentFields(type);
        
        // Disparar evento personalizado
        const event = new CustomEvent('locationSelected', { 
            detail: { type, location },
            bubbles: true 
        });
        input.dispatchEvent(event);
    }
    
    clearSelection(input) {
        const autocomplete = input._autocomplete;
        const type = autocomplete.type;
        
        autocomplete.selectedValue = null;
        autocomplete.hiddenInput.value = '';
        this.selectedValues[type] = null;
        
        // Limpiar campos dependientes
        this.clearDependentFields(type);
    }
    
    clearDependentFields(type) {
        if (type === 'country') {
            // Si cambia el país, limpiar provincia y ciudad
            this.clearFieldsByType('state');
            this.clearFieldsByType('city');
            this.selectedValues.state = null;
            this.selectedValues.city = null;
        } else if (type === 'state') {
            // Si cambia la provincia, limpiar ciudad
            this.clearFieldsByType('city');
            this.selectedValues.city = null;
        }
    }
    
    clearFieldsByType(type) {
        const selector = this.options[type + 'FieldSelector'];
        const fields = document.querySelectorAll(selector);
        
        fields.forEach(field => {
            if (field._autocomplete) {
                field.value = '';
                field._autocomplete.hiddenInput.value = '';
                field._autocomplete.selectedValue = null;
            }
        });
    }
    
    getTypeLabel(type) {
        const labels = {
            'country': 'país',
            'state': 'provincia',
            'city': 'ciudad'
        };
        return labels[type] || type;
    }
    
    getTypeIcon(type) {
        const icons = {
            'country': 'bi bi-globe',
            'state': 'bi bi-map',
            'city': 'bi bi-geo-alt'
        };
        return icons[type] || 'bi bi-geo';
    }
    
    styleDropdownItems(dropdown) {
        dropdown.querySelectorAll('.dropdown-item').forEach(item => {
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
    }
    
    showDropdown(dropdown) {
        dropdown.style.display = 'block';
    }
    
    hideDropdown(dropdown) {
        dropdown.style.display = 'none';
    }
    
    showError(dropdown, message) {
        dropdown.innerHTML = `
            <div class="dropdown-item">
                <i class="bi bi-exclamation-triangle text-danger me-2"></i>
                <span class="text-danger">${message}</span>
            </div>
        `;
        this.showDropdown(dropdown);
    }
    
    setupModals() {
        this.createLocationModal();
    }
    
    createLocationModal() {
        const modalHtml = `
            <div class="modal fade" id="createLocationModal" tabindex="-1" aria-labelledby="createLocationModalLabel" aria-hidden="true">
                <div class="modal-dialog">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title" id="createLocationModalLabel">
                                <i class="bi bi-geo-alt-fill me-2"></i><span id="modalTitle">Crear Nueva Ubicación</span>
                            </h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                        </div>
                        <div class="modal-body">
                            <form id="createLocationForm">
                                <div id="countryFields" style="display: none;">
                                    <div class="mb-3">
                                        <label for="newLocationCountryName" class="form-label">Nombre del País *</label>
                                        <input type="text" class="form-control" id="newLocationCountryName" required>
                                    </div>
                                </div>
                                
                                <div id="stateFields" style="display: none;">
                                    <div class="mb-3">
                                        <label for="newLocationStateName" class="form-label">Nombre de la Provincia *</label>
                                        <input type="text" class="form-control" id="newLocationStateName" required>
                                    </div>
                                    <div class="mb-3">
                                        <label class="form-label">País seleccionado</label>
                                        <div class="form-control-plaintext" id="selectedCountryDisplay">-</div>
                                    </div>
                                </div>
                                
                                <div id="cityFields" style="display: none;">
                                    <div class="mb-3">
                                        <label for="newLocationCityName" class="form-label">Nombre de la Ciudad *</label>
                                        <input type="text" class="form-control" id="newLocationCityName" required>
                                    </div>
                                    <div class="mb-3">
                                        <label class="form-label">Provincia seleccionada</label>
                                        <div class="form-control-plaintext" id="selectedStateDisplay">-</div>
                                    </div>
                                </div>
                                
                                <div class="alert alert-info">
                                    <i class="bi bi-info-circle me-2"></i>
                                    <small>Los campos marcados con * son obligatorios.</small>
                                </div>
                                <div id="createLocationError" class="alert alert-danger d-none"></div>
                            </form>
                        </div>
                        <div class="modal-footer">
                            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancelar</button>
                            <button type="button" class="btn btn-primary" id="saveLocationBtn">
                                <i class="bi bi-check-circle me-1"></i>Crear Ubicación
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        // Agregar modal al DOM si no existe
        if (!document.getElementById('createLocationModal')) {
            document.body.insertAdjacentHTML('beforeend', modalHtml);
        }
        
        this.modals.location = new bootstrap.Modal(document.getElementById('createLocationModal'));
        
        // Bind eventos del modal
        document.getElementById('saveLocationBtn').addEventListener('click', () => {
            this.createLocation();
        });
        
        // Limpiar formulario al cerrar modal
        document.getElementById('createLocationModal').addEventListener('hidden.bs.modal', () => {
            this.resetCreateForm();
        });
    }
    
    showCreateModal(type, query = '') {
        // Ocultar todos los dropdowns
        document.querySelectorAll('.location-autocomplete-dropdown').forEach(dropdown => {
            this.hideDropdown(dropdown);
        });
        
        // Configurar modal según tipo
        const modalTitle = document.getElementById('modalTitle');
        const countryFields = document.getElementById('countryFields');
        const stateFields = document.getElementById('stateFields');
        const cityFields = document.getElementById('cityFields');
        const selectedCountryDisplay = document.getElementById('selectedCountryDisplay');
        const selectedStateDisplay = document.getElementById('selectedStateDisplay');
        
        // Ocultar todos los campos primero
        countryFields.style.display = 'none';
        stateFields.style.display = 'none';
        cityFields.style.display = 'none';
        
        // Configurar según tipo
        if (type === 'country') {
            modalTitle.textContent = 'Crear Nuevo País';
            countryFields.style.display = 'block';
            document.getElementById('newLocationCountryName').value = query;
        } else if (type === 'state') {
            modalTitle.textContent = 'Crear Nueva Provincia';
            stateFields.style.display = 'block';
            document.getElementById('newLocationStateName').value = query;
            
            if (this.selectedValues.country) {
                selectedCountryDisplay.textContent = this.selectedValues.country.name;
            }
        } else if (type === 'city') {
            modalTitle.textContent = 'Crear Nueva Ciudad';
            cityFields.style.display = 'block';
            document.getElementById('newLocationCityName').value = query;
            
            if (this.selectedValues.state) {
                selectedStateDisplay.textContent = `${this.selectedValues.state.name}, ${this.selectedValues.state.country}`;
            }
        }
        
        // Almacenar el tipo para usar en createLocation()
        this.modals.location._currentType = type;
        this.modals.location.show();
    }
    
    createLocation() {
        const type = this.modals.location._currentType;
        const errorDiv = document.getElementById('createLocationError');
        const saveBtn = document.getElementById('saveLocationBtn');
        
        let data = {};
        let nameField = null;
        
        // Recopilar datos según tipo
        if (type === 'country') {
            nameField = document.getElementById('newLocationCountryName');
            data = {
                name: nameField.value.trim()
            };
        } else if (type === 'state') {
            nameField = document.getElementById('newLocationStateName');
            data = {
                name: nameField.value.trim(),
                country_id: this.selectedValues.country ? this.selectedValues.country.id : null
            };
        } else if (type === 'city') {
            nameField = document.getElementById('newLocationCityName');
            data = {
                name: nameField.value.trim(),
                state_id: this.selectedValues.state ? this.selectedValues.state.id : null
            };
        }
        
        // Validaciones básicas
        if (!data.name) {
            this.showCreateError('El nombre es requerido');
            return;
        }
        
        if (type === 'state' && !data.country_id) {
            this.showCreateError('Debe seleccionar un país primero');
            return;
        }
        
        if (type === 'city' && !data.state_id) {
            this.showCreateError('Debe seleccionar una provincia primero');
            return;
        }
        
        // Deshabilitar botón
        saveBtn.disabled = true;
        saveBtn.innerHTML = '<i class="bi bi-hourglass me-1"></i>Creando...';
        errorDiv.classList.add('d-none');
        
        // URL según tipo
        const urlKey = type === 'state' ? 'createState' : type === 'city' ? 'createCity' : 'createCountry';
        const url = this.options.urls[urlKey];
        
        // Enviar petición
        fetch(url, {
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
                // Encontrar el campo apropiado y seleccionar la nueva ubicación
                this.selectNewlyCreatedLocation(type, result.location);
                
                // Cerrar modal
                this.modals.location.hide();
                
                // Mostrar notificación de éxito
                this.showNotification(`${this.getTypeLabel(type).charAt(0).toUpperCase() + this.getTypeLabel(type).slice(1)} creado correctamente`, 'success');
            } else {
                this.showCreateError(result.error || 'Error al crear la ubicación');
            }
        })
        .catch(error => {
            console.error('Error creando ubicación:', error);
            this.showCreateError('Error de conexión al crear la ubicación');
        })
        .finally(() => {
            // Rehabilitar botón
            saveBtn.disabled = false;
            saveBtn.innerHTML = '<i class="bi bi-check-circle me-1"></i>Crear Ubicación';
        });
    }
    
    selectNewlyCreatedLocation(type, location) {
        // Encontrar el campo correcto por tipo
        const selector = this.options[type + 'FieldSelector'];
        const field = document.querySelector(selector);
        
        if (field && field._autocomplete) {
            this.selectLocation(field, location);
        }
    }
    
    showCreateError(message) {
        const errorDiv = document.getElementById('createLocationError');
        errorDiv.textContent = message;
        errorDiv.classList.remove('d-none');
    }
    
    resetCreateForm() {
        document.getElementById('createLocationForm').reset();
        document.getElementById('createLocationError').classList.add('d-none');
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
    // Inicializar el componente de ubicaciones
    window.locationAutocomplete = new LocationAutocomplete();
});

// Exportar para uso global
window.LocationAutocomplete = LocationAutocomplete;
