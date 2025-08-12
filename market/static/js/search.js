/**
 * 🔍 Search JavaScript Module
 * Advanced search functionality with autocomplete
 */

class SearchManager {
    constructor(options = {}) {
        this.options = {
            searchInput: options.searchInput || '#search-input',
            autocompleteContainer: options.autocompleteContainer || '#autocomplete-container',
            searchForm: options.searchForm || '#search-form',
            autocompleteUrl: options.autocompleteUrl || '/api/search/autocomplete/',
            searchUrl: options.searchUrl || '/search/',
            minChars: options.minChars || 2,
            debounceDelay: options.debounceDelay || 300,
            maxSuggestions: options.maxSuggestions || 10,
            ...options
        };
        
        this.searchInput = null;
        this.autocompleteContainer = null;
        this.searchForm = null;
        this.debounceTimer = null;
        this.selectedIndex = -1;
        this.suggestions = [];
        this.isVisible = false;
        
        this.init();
    }
    
    init() {
        this.bindElements();
        this.bindEvents();
        this.setupUI();
    }
    
    bindElements() {
        this.searchInput = document.querySelector(this.options.searchInput);
        this.autocompleteContainer = document.querySelector(this.options.autocompleteContainer);
        this.searchForm = document.querySelector(this.options.searchForm);
        
        // Create autocomplete container if it doesn't exist
        if (!this.autocompleteContainer && this.searchInput) {
            this.createAutocompleteContainer();
        }
    }
    
    createAutocompleteContainer() {
        this.autocompleteContainer = document.createElement('div');
        this.autocompleteContainer.id = 'autocomplete-container';
        this.autocompleteContainer.className = 'autocomplete-container';
        this.autocompleteContainer.style.display = 'none';
        
        // Insert after search input
        this.searchInput.parentNode.insertBefore(
            this.autocompleteContainer, 
            this.searchInput.nextSibling
        );
    }
    
    bindEvents() {
        if (!this.searchInput) return;
        
        // Input events
        this.searchInput.addEventListener('input', (e) => {
            this.handleInput(e.target.value);
        });
        
        this.searchInput.addEventListener('keydown', (e) => {
            this.handleKeyDown(e);
        });
        
        this.searchInput.addEventListener('focus', () => {
            if (this.suggestions.length > 0) {
                this.showAutocomplete();
            }
        });
        
        this.searchInput.addEventListener('blur', () => {
            // Delay hiding to allow for suggestion clicks
            setTimeout(() => {
                this.hideAutocomplete();
            }, 200);
        });
        
        // Form submission
        if (this.searchForm) {
            this.searchForm.addEventListener('submit', (e) => {
                this.handleSubmit(e);
            });
        }
        
        // Click outside to close
        document.addEventListener('click', (e) => {
            if (!this.searchInput.contains(e.target) && 
                !this.autocompleteContainer.contains(e.target)) {
                this.hideAutocomplete();
            }
        });
    }
    
    setupUI() {
        if (this.searchInput) {
            // Add search icon and clear button
            const searchWrapper = document.createElement('div');
            searchWrapper.className = 'search-input-wrapper';
            
            const searchIcon = document.createElement('span');
            searchIcon.className = 'search-icon';
            searchIcon.innerHTML = '🔍';
            
            const clearButton = document.createElement('button');
            clearButton.type = 'button';
            clearButton.className = 'search-clear';
            clearButton.innerHTML = '×';
            clearButton.style.display = 'none';
            clearButton.addEventListener('click', () => {
                this.clearSearch();
            });
            
            // Wrap input
            this.searchInput.parentNode.insertBefore(searchWrapper, this.searchInput);
            searchWrapper.appendChild(searchIcon);
            searchWrapper.appendChild(this.searchInput);
            searchWrapper.appendChild(clearButton);
            
            // Show/hide clear button based on input
            this.searchInput.addEventListener('input', () => {
                clearButton.style.display = this.searchInput.value ? 'block' : 'none';
            });
        }
    }
    
    handleInput(query) {
        // Clear previous timer
        if (this.debounceTimer) {
            clearTimeout(this.debounceTimer);
        }
        
        // Reset selection
        this.selectedIndex = -1;
        
        if (query.length < this.options.minChars) {
            this.hideAutocomplete();
            return;
        }
        
        // Debounce the search
        this.debounceTimer = setTimeout(() => {
            this.fetchSuggestions(query);
        }, this.options.debounceDelay);
    }
    
    handleKeyDown(e) {
        if (!this.isVisible || this.suggestions.length === 0) {
            return;
        }
        
        switch (e.key) {
            case 'ArrowDown':
                e.preventDefault();
                this.selectedIndex = Math.min(
                    this.selectedIndex + 1, 
                    this.suggestions.length - 1
                );
                this.updateSelection();
                break;
                
            case 'ArrowUp':
                e.preventDefault();
                this.selectedIndex = Math.max(this.selectedIndex - 1, -1);
                this.updateSelection();
                break;
                
            case 'Enter':
                e.preventDefault();
                if (this.selectedIndex >= 0) {
                    this.selectSuggestion(this.suggestions[this.selectedIndex]);
                } else {
                    this.performSearch();
                }
                break;
                
            case 'Escape':
                this.hideAutocomplete();
                this.searchInput.blur();
                break;
        }
    }
    
    handleSubmit(e) {
        e.preventDefault();
        this.performSearch();
    }
    
    async fetchSuggestions(query) {
        try {
            const response = await fetch(
                `${this.options.autocompleteUrl}?q=${encodeURIComponent(query)}`,
                {
                    headers: {
                        'X-Requested-With': 'XMLHttpRequest'
                    }
                }
            );
            
            if (response.ok) {
                const data = await response.json();
                this.suggestions = data.suggestions || [];
                this.renderSuggestions();
                
                if (this.suggestions.length > 0) {
                    this.showAutocomplete();
                } else {
                    this.hideAutocomplete();
                }
            }
        } catch (error) {
            console.error('Search autocomplete error:', error);
            this.hideAutocomplete();
        }
    }
    
    renderSuggestions() {
        if (!this.autocompleteContainer) return;
        
        const html = this.suggestions.map((suggestion, index) => {
            const isSelected = index === this.selectedIndex;
            return `
                <div class="autocomplete-item ${isSelected ? 'selected' : ''}" 
                     data-index="${index}">
                    <div class="suggestion-icon">${this.getSuggestionIcon(suggestion.type)}</div>
                    <div class="suggestion-content">
                        <div class="suggestion-text">${this.highlightMatch(suggestion.text, this.searchInput.value)}</div>
                        ${suggestion.description ? `<div class="suggestion-description">${suggestion.description}</div>` : ''}
                    </div>
                    ${suggestion.category ? `<div class="suggestion-category">${suggestion.category}</div>` : ''}
                </div>
            `;
        }).join('');
        
        this.autocompleteContainer.innerHTML = html;
        
        // Bind click events
        this.autocompleteContainer.querySelectorAll('.autocomplete-item').forEach(item => {
            item.addEventListener('click', () => {
                const index = parseInt(item.dataset.index);
                this.selectSuggestion(this.suggestions[index]);
            });
        });
    }
    
    getSuggestionIcon(type) {
        const icons = {
            'item': '📦',
            'category': '🏷️',
            'user': '👤',
            'location': '📍',
            'recent': '🕒',
            'popular': '🔥'
        };
        return icons[type] || '🔍';
    }
    
    highlightMatch(text, query) {
        if (!query) return text;
        
        const regex = new RegExp(`(${query.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')})`, 'gi');
        return text.replace(regex, '<strong>$1</strong>');
    }
    
    updateSelection() {
        const items = this.autocompleteContainer.querySelectorAll('.autocomplete-item');
        
        items.forEach((item, index) => {
            if (index === this.selectedIndex) {
                item.classList.add('selected');
                item.scrollIntoView({ block: 'nearest' });
            } else {
                item.classList.remove('selected');
            }
        });
    }
    
    selectSuggestion(suggestion) {
        this.searchInput.value = suggestion.text;
        this.hideAutocomplete();
        
        // Trigger search or navigation based on suggestion type
        if (suggestion.url) {
            window.location.href = suggestion.url;
        } else {
            this.performSearch(suggestion.text);
        }
        
        // Track selection for analytics
        this.trackSelection(suggestion);
    }
    
    performSearch(query = null) {
        const searchQuery = query || this.searchInput.value.trim();
        
        if (!searchQuery) return;
        
        // Track search
        this.trackSearch(searchQuery);
        
        // Navigate to search results
        const searchUrl = new URL(this.options.searchUrl, window.location.origin);
        searchUrl.searchParams.set('q', searchQuery);
        window.location.href = searchUrl.toString();
    }
    
    clearSearch() {
        this.searchInput.value = '';
        this.hideAutocomplete();
        this.searchInput.focus();
        
        // Clear button visibility
        const clearButton = this.searchInput.parentNode.querySelector('.search-clear');
        if (clearButton) {
            clearButton.style.display = 'none';
        }
    }
    
    showAutocomplete() {
        if (this.autocompleteContainer && this.suggestions.length > 0) {
            this.autocompleteContainer.style.display = 'block';
            this.isVisible = true;
        }
    }
    
    hideAutocomplete() {
        if (this.autocompleteContainer) {
            this.autocompleteContainer.style.display = 'none';
            this.isVisible = false;
            this.selectedIndex = -1;
        }
    }
    
    trackSearch(query) {
        // Send search analytics
        if (navigator.sendBeacon && typeof gtag !== 'undefined') {
            gtag('event', 'search', {
                search_term: query,
                source: 'autocomplete'
            });
        }
        
        // Save to recent searches
        this.saveRecentSearch(query);
    }
    
    trackSelection(suggestion) {
        // Track suggestion selection
        if (navigator.sendBeacon && typeof gtag !== 'undefined') {
            gtag('event', 'autocomplete_selection', {
                suggestion_type: suggestion.type,
                suggestion_text: suggestion.text
            });
        }
    }
    
    saveRecentSearch(query) {
        try {
            let recentSearches = JSON.parse(localStorage.getItem('recentSearches') || '[]');
            
            // Remove if already exists
            recentSearches = recentSearches.filter(search => search !== query);
            
            // Add to beginning
            recentSearches.unshift(query);
            
            // Keep only last 10
            recentSearches = recentSearches.slice(0, 10);
            
            localStorage.setItem('recentSearches', JSON.stringify(recentSearches));
        } catch (error) {
            console.warn('Could not save recent search:', error);
        }
    }
    
    getRecentSearches() {
        try {
            return JSON.parse(localStorage.getItem('recentSearches') || '[]');
        } catch (error) {
            return [];
        }
    }
}

// Advanced Search Form Handler
class AdvancedSearchForm {
    constructor(formId = '#advanced-search-form') {
        this.form = document.querySelector(formId);
        this.init();
    }
    
    init() {
        if (!this.form) return;
        
        this.bindEvents();
        this.setupFilters();
        this.loadSavedSearches();
    }
    
    bindEvents() {
        // Form submission
        this.form.addEventListener('submit', (e) => {
            this.handleSubmit(e);
        });
        
        // Reset button
        const resetBtn = this.form.querySelector('.reset-btn');
        if (resetBtn) {
            resetBtn.addEventListener('click', () => {
                this.resetForm();
            });
        }
        
        // Save search button
        const saveBtn = this.form.querySelector('.save-search-btn');
        if (saveBtn) {
            saveBtn.addEventListener('click', () => {
                this.saveSearch();
            });
        }
        
        // Price range inputs
        this.setupPriceRange();
        
        // Location filter
        this.setupLocationFilter();
    }
    
    setupFilters() {
        // Category filter with subcategories
        const categorySelect = this.form.querySelector('#category');
        if (categorySelect) {
            categorySelect.addEventListener('change', () => {
                this.updateSubcategories();
            });
        }
        
        // Condition filter
        const conditionInputs = this.form.querySelectorAll('input[name="condition"]');
        conditionInputs.forEach(input => {
            input.addEventListener('change', () => {
                this.updateConditionPreview();
            });
        });
    }
    
    setupPriceRange() {
        const minPrice = this.form.querySelector('#min_price');
        const maxPrice = this.form.querySelector('#max_price');
        const priceDisplay = this.form.querySelector('#price-range-display');
        
        if (minPrice && maxPrice && priceDisplay) {
            const updateDisplay = () => {
                const min = minPrice.value || '0';
                const max = maxPrice.value || '∞';
                priceDisplay.textContent = `₺${min} - ₺${max}`;
            };
            
            minPrice.addEventListener('input', updateDisplay);
            maxPrice.addEventListener('input', updateDisplay);
            updateDisplay();
        }
    }
    
    setupLocationFilter() {
        const citySelect = this.form.querySelector('#city');
        const districtSelect = this.form.querySelector('#district');
        
        if (citySelect && districtSelect) {
            citySelect.addEventListener('change', () => {
                this.updateDistricts(citySelect.value);
            });
        }
    }
    
    async updateSubcategories() {
        const categorySelect = this.form.querySelector('#category');
        const subcategorySelect = this.form.querySelector('#subcategory');
        
        if (!categorySelect || !subcategorySelect) return;
        
        const category = categorySelect.value;
        subcategorySelect.innerHTML = '<option value="">Tüm Alt Kategoriler</option>';
        
        if (!category) return;
        
        try {
            const response = await fetch(`/api/subcategories/?category=${category}`);
            if (response.ok) {
                const data = await response.json();
                data.subcategories.forEach(sub => {
                    const option = document.createElement('option');
                    option.value = sub.value;
                    option.textContent = sub.label;
                    subcategorySelect.appendChild(option);
                });
            }
        } catch (error) {
            console.error('Error loading subcategories:', error);
        }
    }
    
    async updateDistricts(city) {
        const districtSelect = this.form.querySelector('#district');
        if (!districtSelect) return;
        
        districtSelect.innerHTML = '<option value="">Tüm İlçeler</option>';
        
        if (!city) return;
        
        try {
            const response = await fetch(`/api/districts/?city=${city}`);
            if (response.ok) {
                const data = await response.json();
                data.districts.forEach(district => {
                    const option = document.createElement('option');
                    option.value = district.value;
                    option.textContent = district.label;
                    districtSelect.appendChild(option);
                });
            }
        } catch (error) {
            console.error('Error loading districts:', error);
        }
    }
    
    updateConditionPreview() {
        const selectedConditions = Array.from(
            this.form.querySelectorAll('input[name="condition"]:checked')
        ).map(input => input.nextElementSibling.textContent);
        
        const preview = this.form.querySelector('#condition-preview');
        if (preview) {
            preview.textContent = selectedConditions.length > 0 
                ? selectedConditions.join(', ') 
                : 'Tüm Durumlar';
        }
    }
    
    handleSubmit(e) {
        e.preventDefault();
        
        const formData = new FormData(this.form);
        const params = new URLSearchParams();
        
        // Build search parameters
        for (const [key, value] of formData.entries()) {
            if (value && value.trim()) {
                params.append(key, value);
            }
        }
        
        // Navigate to search results
        window.location.href = `/search/?${params.toString()}`;
    }
    
    resetForm() {
        this.form.reset();
        this.updateConditionPreview();
        
        // Clear dynamic selects
        const subcategorySelect = this.form.querySelector('#subcategory');
        const districtSelect = this.form.querySelector('#district');
        
        if (subcategorySelect) {
            subcategorySelect.innerHTML = '<option value="">Tüm Alt Kategoriler</option>';
        }
        
        if (districtSelect) {
            districtSelect.innerHTML = '<option value="">Tüm İlçeler</option>';
        }
        
        // Update price display
        const priceDisplay = this.form.querySelector('#price-range-display');
        if (priceDisplay) {
            priceDisplay.textContent = '₺0 - ₺∞';
        }
    }
    
    async saveSearch() {
        const searchName = prompt('Bu aramayı kaydetmek için bir isim girin:');
        if (!searchName) return;
        
        const formData = new FormData(this.form);
        const searchData = {};
        
        for (const [key, value] of formData.entries()) {
            if (value && value.trim()) {
                searchData[key] = value;
            }
        }
        
        try {
            const response = await fetch('/api/search/save/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                },
                body: JSON.stringify({
                    name: searchName,
                    filters: searchData
                })
            });
            
            if (response.ok) {
                alert('Arama başarıyla kaydedildi!');
                this.loadSavedSearches();
            } else {
                alert('Arama kaydedilirken hata oluştu.');
            }
        } catch (error) {
            console.error('Error saving search:', error);
            alert('Arama kaydedilirken hata oluştu.');
        }
    }
    
    async loadSavedSearches() {
        const savedSearchContainer = this.form.querySelector('#saved-searches');
        if (!savedSearchContainer) return;
        
        try {
            const response = await fetch('/api/search/saved/');
            if (response.ok) {
                const data = await response.json();
                this.renderSavedSearches(data.searches, savedSearchContainer);
            }
        } catch (error) {
            console.error('Error loading saved searches:', error);
        }
    }
    
    renderSavedSearches(searches, container) {
        if (searches.length === 0) {
            container.innerHTML = '<p>Kayıtlı arama bulunamadı.</p>';
            return;
        }
        
        const html = searches.map(search => `
            <div class="saved-search-item">
                <div class="search-name">${search.name}</div>
                <div class="search-actions">
                    <button type="button" onclick="advancedSearch.loadSearch(${search.id})">Yükle</button>
                    <button type="button" onclick="advancedSearch.deleteSearch(${search.id})">Sil</button>
                </div>
            </div>
        `).join('');
        
        container.innerHTML = html;
    }
    
    async loadSearch(searchId) {
        try {
            const response = await fetch(`/api/search/saved/${searchId}/`);
            if (response.ok) {
                const data = await response.json();
                this.populateForm(data.filters);
            }
        } catch (error) {
            console.error('Error loading search:', error);
        }
    }
    
    async deleteSearch(searchId) {
        if (!confirm('Bu aramayı silmek istediğinizden emin misiniz?')) return;
        
        try {
            const response = await fetch(`/api/search/saved/${searchId}/`, {
                method: 'DELETE',
                headers: {
                    'X-CSRFToken': this.getCSRFToken()
                }
            });
            
            if (response.ok) {
                this.loadSavedSearches();
            }
        } catch (error) {
            console.error('Error deleting search:', error);
        }
    }
    
    populateForm(filters) {
        for (const [key, value] of Object.entries(filters)) {
            const field = this.form.querySelector(`[name="${key}"]`);
            if (field) {
                if (field.type === 'checkbox' || field.type === 'radio') {
                    field.checked = field.value === value;
                } else {
                    field.value = value;
                }
            }
        }
        
        // Trigger change events to update dependent fields
        this.form.querySelector('#category')?.dispatchEvent(new Event('change'));
        this.form.querySelector('#city')?.dispatchEvent(new Event('change'));
        this.updateConditionPreview();
    }
    
    getCSRFToken() {
        const cookieValue = document.cookie
            .split('; ')
            .find(row => row.startsWith('csrftoken='))
            ?.split('=')[1];
        return cookieValue || '';
    }
}

// CSS Styles for search components
const searchStyles = `
<style>
.search-input-wrapper {
    position: relative;
    display: flex;
    align-items: center;
}

.search-icon {
    position: absolute;
    left: 10px;
    z-index: 1;
    color: #999;
}

.search-input-wrapper input {
    padding-left: 35px;
    padding-right: 35px;
}

.search-clear {
    position: absolute;
    right: 10px;
    background: none;
    border: none;
    font-size: 18px;
    cursor: pointer;
    color: #999;
    z-index: 1;
}

.search-clear:hover {
    color: #333;
}

.autocomplete-container {
    position: absolute;
    top: 100%;
    left: 0;
    right: 0;
    background: white;
    border: 1px solid #ddd;
    border-top: none;
    border-radius: 0 0 4px 4px;
    box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    max-height: 300px;
    overflow-y: auto;
    z-index: 1000;
}

.autocomplete-item {
    display: flex;
    align-items: center;
    padding: 10px;
    cursor: pointer;
    border-bottom: 1px solid #eee;
}

.autocomplete-item:hover,
.autocomplete-item.selected {
    background: #f8f9fa;
}

.suggestion-icon {
    font-size: 16px;
    margin-right: 10px;
    flex-shrink: 0;
}

.suggestion-content {
    flex: 1;
}

.suggestion-text {
    font-size: 14px;
    margin-bottom: 2px;
}

.suggestion-text strong {
    font-weight: bold;
    color: #007cba;
}

.suggestion-description {
    font-size: 12px;
    color: #666;
}

.suggestion-category {
    font-size: 11px;
    color: #999;
    background: #f0f0f0;
    padding: 2px 6px;
    border-radius: 2px;
}

.saved-search-item {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 8px;
    border: 1px solid #ddd;
    border-radius: 4px;
    margin-bottom: 5px;
}

.search-name {
    font-weight: bold;
}

.search-actions button {
    margin-left: 5px;
    padding: 4px 8px;
    border: none;
    border-radius: 2px;
    cursor: pointer;
    font-size: 12px;
}

.search-actions button:first-child {
    background: #007cba;
    color: white;
}

.search-actions button:last-child {
    background: #f44336;
    color: white;
}
</style>
`;

// Add styles to document
if (!document.querySelector('#search-styles')) {
    const styleElement = document.createElement('div');
    styleElement.id = 'search-styles';
    styleElement.innerHTML = searchStyles;
    document.head.appendChild(styleElement);
}

// Global instances
let searchManager = null;
let advancedSearch = null;

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    // Initialize search manager for header search
    const headerSearch = document.querySelector('#header-search');
    if (headerSearch) {
        searchManager = new SearchManager({
            searchInput: '#header-search',
            searchForm: '#header-search-form'
        });
    }
    
    // Initialize advanced search form
    const advancedForm = document.querySelector('#advanced-search-form');
    if (advancedForm) {
        advancedSearch = new AdvancedSearchForm('#advanced-search-form');
    }
});

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { SearchManager, AdvancedSearchForm };
}