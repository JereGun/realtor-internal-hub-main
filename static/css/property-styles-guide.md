# Property Styles Design System Guide

## Overview

The `property-styles.css` file provides a comprehensive design system for property templates with consistent styling, animations, and responsive utilities.

## Usage

### Including the Stylesheet

Add the following to your template's `extra_css` block:

```html
{% block extra_css %}
    {% load static %}
    <link rel="stylesheet" href="{% static 'css/property-styles.css' %}">
{% endblock %}
```

### CSS Custom Properties (Design Tokens)

The system uses CSS custom properties for consistent theming:

```css
/* Colors */
--property-primary: #2563eb
--property-success: #059669
--property-warning: #d97706
--property-danger: #dc2626
--property-info: #0891b2

/* Spacing */
--property-spacing-xs: 0.25rem
--property-spacing-sm: 0.5rem
--property-spacing-md: 1rem
--property-spacing-lg: 1.5rem
--property-spacing-xl: 2rem

/* Shadows, transitions, border radius, typography, etc. */
```

### Component Classes

#### Property Cards
```html
<div class="property-card">
    <div class="property-card-header">Header</div>
    <div class="property-card-body">Content</div>
    <div class="property-card-footer">Footer</div>
</div>

<!-- Variants -->
<div class="property-card property-card-elevated">Enhanced shadow</div>
<div class="property-card property-card-compact">Smaller padding</div>
```

#### Buttons
```html
<!-- Primary button -->
<button class="property-btn property-btn-primary">Primary</button>

<!-- Variants -->
<button class="property-btn property-btn-success">Success</button>
<button class="property-btn property-btn-warning">Warning</button>
<button class="property-btn property-btn-danger">Danger</button>
<button class="property-btn property-btn-info">Info</button>

<!-- Outline variants -->
<button class="property-btn property-btn-outline-primary">Outline</button>

<!-- Sizes -->
<button class="property-btn property-btn-primary property-btn-sm">Small</button>
<button class="property-btn property-btn-primary property-btn-lg">Large</button>
```

#### Form Elements
```html
<div class="property-form-group">
    <label class="property-form-label">Label</label>
    <input type="text" class="property-form-control">
    <div class="property-form-feedback invalid-feedback">Error message</div>
</div>

<!-- Validation states -->
<input type="text" class="property-form-control is-invalid">
<input type="text" class="property-form-control is-valid">
```

### Animation Classes

#### Entrance Animations
```html
<div class="property-fade-in">Fade in animation</div>
<div class="property-slide-in-left">Slide from left</div>
<div class="property-slide-in-right">Slide from right</div>
<div class="property-scale-in">Scale in animation</div>
<div class="property-bounce-in">Bounce in animation</div>
```

#### Loading States
```html
<div class="property-pulse">Pulsing element</div>
<div class="property-spin">Spinning element</div>
<div class="property-skeleton" style="height: 20px; width: 100%;"></div>
```

#### Hover Effects
```html
<div class="property-hover-lift">Lifts on hover</div>
<div class="property-hover-scale">Scales on hover</div>
<div class="property-hover-shadow">Shadow on hover</div>
```

### Utility Classes

#### Spacing
```html
<div class="property-p-md">Medium padding</div>
<div class="property-m-lg">Large margin</div>
```

#### Colors
```html
<span class="property-text-primary">Primary text</span>
<div class="property-bg-success">Success background</div>
```

#### Shadows and Borders
```html
<div class="property-shadow-md property-rounded-lg">Card with shadow and rounded corners</div>
```

### Responsive Utilities

```html
<div class="property-md-hidden">Hidden on medium screens and up</div>
<div class="property-lg-flex">Flex display on large screens and up</div>
```

### Accessibility Features

- Respects `prefers-reduced-motion` for users who prefer less animation
- High contrast mode support
- Focus-visible support for keyboard navigation
- WCAG compliant color contrast ratios

### Integration with Bootstrap

This design system is designed to work alongside Bootstrap 5. It uses the same breakpoint system and can be used together with Bootstrap classes.

## Examples

### Property Card Example
```html
<div class="property-card property-hover-lift property-transition-all">
    <div class="property-card-body">
        <h5 class="property-text-dark property-font-semibold">Property Title</h5>
        <p class="property-text-muted property-text-sm">Property description</p>
        <div class="d-flex justify-content-between align-items-center">
            <span class="property-text-success property-font-bold property-text-lg">$250,000</span>
            <button class="property-btn property-btn-primary property-btn-sm">View Details</button>
        </div>
    </div>
</div>
```

### Form Example
```html
<form>
    <div class="property-form-group">
        <label class="property-form-label">Property Name</label>
        <input type="text" class="property-form-control property-focus-ring">
    </div>
    <div class="property-form-group">
        <label class="property-form-label">Property Type</label>
        <select class="property-form-control property-form-select">
            <option>Select type...</option>
            <option>House</option>
            <option>Apartment</option>
        </select>
    </div>
    <button type="submit" class="property-btn property-btn-primary property-btn-lg">
        Save Property
    </button>
</form>
```