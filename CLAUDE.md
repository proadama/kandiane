# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Kandiane** is a Django 5.1.8 application for managing a French association (members, subscriptions, payments, events, and accounting). The codebase has undergone extensive refactoring (Phase 3 completed) to improve architecture and maintainability.

## Development Commands

### Environment Setup

```bash
# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate  # Linux/macOS
# venv\Scripts\activate   # Windows

# Install dependencies
pip install -r requirements.txt

# Create .env file from example
cp .env.example .env
# Edit .env with appropriate values

# Create static directory
mkdir -p static

# Apply migrations
python manage.py migrate

# Create superuser (for testing)
python create_superuser.py
# Creates: username=admin, password=admin123
```

### Running the Application

```bash
# Start development server
python manage.py runserver

# Access at: http://localhost:8000
# Admin: http://localhost:8000/admin/
```

### Database & Migrations

```bash
# Create new migrations
python manage.py makemigrations

# Apply migrations
python manage.py migrate

# Check for migration issues
python manage.py makemigrations --dry-run --check

# Show migration status
python manage.py showmigrations
```

### Testing

```bash
# Run all tests
python manage.py test

# Run specific app tests
python manage.py test apps.cotisations

# Using pytest (recommended)
pytest

# Run specific test file
pytest apps/cotisations/tests/test_models.py

# Run with coverage
pytest --cov=apps
```

### Code Quality

```bash
# Check Django configuration
python manage.py check

# Validate all settings
python manage.py check --deploy
```

### Utility Scripts

```bash
# Fix relative imports (converts to absolute)
python fix_relative_imports.py

# Reset development environment
./reset_dev_env.sh

# Setup after reset
./setup_after_reset.sh
```

## Architecture Overview

### Django Settings Structure

Settings are split across three files in `config/settings/`:

- **`base.py`**: Common settings for all environments
- **`development.py`**: Development-specific (DEBUG=True, console email backend)
- **`production.py`**: Production settings (security enabled, HTTPS)
- **`test.py`**: Test environment settings

Default: `config.settings.development` (set in `manage.py`)

### Application Structure

Five Django apps under `apps/`:

1. **`core`**: Base models, managers, and utilities
   - `BaseModel`: Abstract model with soft delete capability
   - `BaseManager`: Filters out soft-deleted objects by default
   - `Statut`: Flexible status system for all entities
   - `Log`: User action logging system

2. **`accounts`**: User authentication and authorization
   - `CustomUser`: Extended user model with phone, role, etc.
   - Custom middlewares for session management and permissions
   - Password validators

3. **`membres`**: Member management
   - `Membre`: Member profiles (delegates personal info to CustomUser)
   - `TypeMembre`: Member categories with temporal tracking
   - `MembreTypeMembre`: Many-to-many with history (date_debut, date_fin)
   - `HistoriqueMembre`: Change tracking

4. **`cotisations`**: Subscription and payment management (REFACTORED)
   - `Cotisation`: Subscriptions with payment status tracking
   - `Paiement`: Multiple payments per subscription
   - `BaremeCotisation`: Pricing schedules with validity periods
   - `ModePaiement`: Payment methods (cash, check, transfer, card)
   - `Rappel`: Multi-channel reminders (email, SMS, mail, phone)
   - Views split into 8 modules (see below)

5. **`evenements`**: Event management
   - Event creation and planning
   - Registrations with participant tracking
   - Integration with cotisations for event payments

### Soft Delete Pattern (CRITICAL)

All models inheriting from `BaseModel` use **logical deletion**:

```python
# Soft delete (default)
membre.delete()  # Sets deleted_at = now(), object remains in DB

# Hard delete (physical removal)
membre.delete(hard=True)  # Actually removes from DB

# Querying
Membre.objects.all()           # Excludes soft-deleted
Membre.objects.with_deleted()  # Includes soft-deleted
Membre.objects.only_deleted()  # Only soft-deleted

# Restore
membre.restore()  # Sets deleted_at = None
```

**Key managers methods**:
- `.with_deleted()` - Include soft-deleted objects
- `.only_deleted()` - Only soft-deleted objects
- `.recent_deleted(days=30)` - Recently deleted objects

### Cotisations Module Architecture (Phase 3 Refactoring)

The cotisations views were refactored from a monolithic 3972-line file into 8 modules:

```
apps/cotisations/views/
├── __init__.py          # Imports and .as_view() aliases
├── utils.py             # Base classes, mixins, common imports
├── dashboard.py         # DashboardView, StatistiquesView
├── cotisations.py       # CRUD for Cotisation model
├── paiements.py         # CRUD for Paiement model
├── rappels.py           # CRUD for Rappel model
├── baremes.py           # CRUD for BaremeCotisation model
└── api.py               # JSON API endpoints
```

**Legacy**: `views_old.py` contains not-yet-migrated export/import functions.

**IMPORTANT**: Always use **absolute imports** in views:

```python
# ✅ CORRECT
from apps.cotisations.views.utils import StaffRequiredMixin

# ❌ INCORRECT (will fail in Django)
from .utils import StaffRequiredMixin
```

### Custom Managers Pattern

Most models have custom managers with domain-specific queries:

```python
# MembreManager examples
Membre.objects.recherche("query")           # Search by name/email/phone
Membre.objects.par_type(type_id)            # Filter by active member type
Membre.objects.adhesions_recentes(days=30)  # Recent members
Membre.objects.avec_cotisations_impayees()  # Members with unpaid subscriptions
Membre.objects.actifs()                     # Members with active type
Membre.objects.sans_compte_utilisateur()    # No linked user account

# CotisationManager examples
Cotisation.objects.en_retard()              # Overdue subscriptions
Cotisation.objects.par_membre(membre_id)    # By member
Cotisation.objects.par_annee(2025)          # By year
```

### Membre-CustomUser Relationship

**Key Pattern**: `Membre` delegates personal fields to `CustomUser`:

```python
# Fields stored in CustomUser:
- first_name (prenom)
- last_name (nom)
- email
- telephone

# Accessed via properties on Membre:
membre.nom        # @property -> utilisateur.last_name
membre.prenom     # @property -> utilisateur.first_name
membre.email      # @property -> utilisateur.email
membre.telephone  # @property -> utilisateur.telephone
```

**Implication**: When creating/updating members, ensure the CustomUser is created first and linked via `utilisateur` field.

### Middleware Stack

Four custom middlewares in `config/settings/base.py`:

1. **`LastUserActivityMiddleware`** (accounts): Tracks user activity
2. **`SessionExpiryMiddleware`** (accounts): Auto-logout after inactivity
3. **`RolePermissionMiddleware`** (accounts): Role-based access control
4. **`MaintenanceModeMiddleware`** (core): Site maintenance mode
5. **`NoCacheMiddleware`** (core): Prevent caching of sensitive pages

### URL Routing Pattern

Each app has its own `urls.py` with namespace:

```python
# In app's urls.py
app_name = 'cotisations'  # Namespace

# Usage in templates/views
{% url 'cotisations:dashboard' %}
reverse('cotisations:dashboard')
```

### Template Context Processors

Custom context processor in `apps.core.context_processors`:

- `trash_counters`: Adds soft-deleted counts to all templates

## Important Patterns & Conventions

### Import Style

**Always use absolute imports** throughout the codebase:

```python
# ✅ CORRECT
from apps.cotisations.models import Cotisation
from apps.membres.models import Membre
from apps.core.models import BaseModel

# ❌ INCORRECT
from ..models import Cotisation
from .models import Membre
```

**Reason**: Django's module loading can fail with relative imports in certain contexts (URL routing, management commands).

### Reference Generation

Models with unique references (Cotisation, Paiement) auto-generate them in `save()`:

```python
# Cotisation reference format
COT-YYYYMM-MEMBID-XXXXX   # Standard subscription
EVENT-YYYYMM-MEMBID-XXXXX # Event subscription

# Paiement reference format
PAI-YYYYMMDD-COTID-XXXX    # Payment
RMB-YYYYMMDD-COTID-XXXX    # Refund
REJ-YYYYMMDD-COTID-XXXX    # Rejection
```

### JSONField Usage

Models use `JSONField` for flexible metadata storage:

```python
cotisation.metadata = {
    'evenement_titre': 'Conférence 2025',
    'nombre_accompagnants': 2,
    'tarif_membre': 25.00
}
```

**Use `ExtendedJSONEncoder`** from `apps.cotisations.views.utils` for serializing Decimal and datetime objects.

### Audit Trail Pattern

Three levels of logging:

1. **`core.Log`**: Global user actions (login, config changes)
2. **`membres.HistoriqueMembre`**: Member-specific changes
3. **`cotisations.HistoriqueCotisation`**: Subscription transaction history

All use JSONField for `donnees_avant` and `donnees_apres`.

### Date Handling

- All dates use `timezone.now()` from `django.utils.timezone`
- Settings: `USE_TZ = True`, `TIME_ZONE = 'Europe/Paris'`
- Store DateTimeFields with timezone, DateFields without

### Model Validation

Override `clean()` for validation, call from `save()`:

```python
def clean(self):
    if self.date_fin and self.date_fin < self.date_debut:
        raise ValidationError("Date fin must be after date debut")

def save(self, *args, **kwargs):
    self.clean()
    super().save(*args, **kwargs)
```

## Migration Gotchas

### Squashed Migrations

The project uses squashed migrations to resolve conflicts (see `apps/evenements/migrations/0002_0003_squashed_noop.py`).

**If encountering migration conflicts**:
1. Check for duplicate table creations across apps
2. Create a squashed migration with empty `operations = []`
3. Set `replaces = [('app', 'migration1'), ('app', 'migration2')]`

### Migration Dependencies

Pay attention to `core_log` table - it's created in `core.0006_log` but was temporarily created/deleted in evenements migrations.

## Testing Conventions

Tests follow Django's standard structure:

```
apps/<appname>/tests/
├── __init__.py
├── test_models.py
├── test_views.py
├── test_forms.py
├── test_api.py
└── test_integration.py
```

**Running specific tests**:
```bash
# Single test method
python manage.py test apps.cotisations.tests.test_models.CotisationModelTest.test_reference_generation

# Test class
python manage.py test apps.cotisations.tests.test_models.CotisationModelTest
```

## Security Considerations

### Production Checklist

From `config/settings/base.py`, ensure in production:

```python
DEBUG = False
SECRET_KEY = '<unique-secret-key>'
ALLOWED_HOSTS = ['yourdomain.com']

# Enable these in production.py:
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 31536000
```

### Password Validation

Custom validator in `apps.accounts.validators.StrongPasswordValidator` enforces:
- Minimum 8 characters
- At least one uppercase
- At least one lowercase
- At least one digit

### Session Security

- Auto-logout after 30 minutes inactivity (`SESSION_IDLE_TIMEOUT`)
- 2-hour absolute session lifetime (`SESSION_COOKIE_AGE`)
- Sessions expire on browser close

## Environment Variables

Copy `.env.example` to `.env` and configure:

**Required**:
- `SECRET_KEY`: Django secret (generate new for each environment)
- `DATABASE_URL`: Database connection string
- `DEBUG`: True/False

**Optional**:
- `EMAIL_*`: SMTP configuration
- `SITE_NAME`: Association name
- `SITE_URL`: Base URL
- `MAINTENANCE_MODE`: Enable maintenance page

## Common Workflows

### Adding a New Model

1. Create model in `apps/<appname>/models.py`
2. Inherit from `BaseModel` for soft delete
3. Create custom manager if needed (inherit from `BaseManager`)
4. Add indexes for foreign keys and frequently filtered fields
5. Run `makemigrations` and `migrate`
6. Add to admin.py if needed

### Creating Class-Based Views

1. Create view in appropriate module under `views/`
2. Use absolute imports from `apps.<appname>.views.utils`
3. Create `.as_view()` alias in `views/__init__.py`
4. Add to `urls.py` with namespace

### Adding API Endpoints

Add to `apps/cotisations/views/api.py`:

```python
from django.http import JsonResponse
from apps.cotisations.views.utils import ExtendedJSONEncoder
import json

@require_http_methods(["GET", "POST"])
def api_your_endpoint(request):
    data = {'key': 'value'}
    return JsonResponse(
        data,
        encoder=ExtendedJSONEncoder,
        safe=False
    )
```

## Key Files Reference

- **Settings**: `config/settings/base.py`, `development.py`, `production.py`
- **Root URLs**: `config/urls.py`
- **Main models**:
  - `apps/core/models.py` (BaseModel, Statut, Log)
  - `apps/membres/models.py` (Membre, TypeMembre)
  - `apps/cotisations/models.py` (Cotisation, Paiement, Rappel)
- **Managers**: `apps/*/managers.py` in each app
- **Middlewares**: `apps/accounts/middleware.py`, `apps/core/middleware.py`

## Documentation References

- **README.md**: Installation and quick start
- **INSTALLATION_ET_TESTS.md**: Detailed installation and testing guide
- **REFACTORING_PHASE3_NOTES.md**: Technical notes on views refactoring
- **REFACTORING_TRACKER.md**: Overall refactoring progress tracker
- **SOLUTION_DUPLICATION_COMPTES.md**: Account duplication solution
- **PLAN_REFONTE_MEMBRE_USER.md**: Member-user workflow plan

## Language & Locale

- Primary language: **French** (fr-fr)
- Timezone: **Europe/Paris**
- Use Django's `gettext_lazy` (_) for all user-facing strings
- Date format: DD/MM/YYYY (European)
