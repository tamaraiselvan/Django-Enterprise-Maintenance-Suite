[![Latest on Django Packages](https://img.shields.io/badge/PyPI-django-enterprise-maintenance-suite/tags-8c3c26.svg)](https://djangopackages.org/packages/p/django-enterprise-maintenance-suite/)
                        
# Django Enterprise Maintenance Suite

Enterprise Maintenance Suite is a **Django reusable application** that provides
**enterprise-grade maintenance control** such as:

- Full Maintenance Mode (503)
- Read-Only Mode (No Writes)
- Admin approval workflow
- Time-based maintenance windows
- Audit logging

This package is intended to be installed via **pip** and plugged directly into
any existing Django project.

---

## Features

- Full system maintenance (HTTP 503)
- Read-only mode (blocks POST / PUT / PATCH / DELETE)
- Admin-controlled enable / disable
- Approval workflow
- Time-window based activation
- Middleware based request interception
- Audit trail for maintenance actions
- Production-ready Django app

---

## Installation

### 1. Install Package from PyPI

```python
pip install django_enterprise_maintenance_suite
```

### 2. Add to INSTALLED_APPS

```python
INSTALLED_APPS = [
    ...
    "django_enterprise_maintenance_suite",
    ...
]
```

### 3. Add Middleware

```python
MIDDLEWARE = [
    ...
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django_enterprise_maintenance_suite.middleware.MaintenanceMiddleware',
]

```
### 4. Add to settings.py

```python
MAINTENANCE_SUITE = {
    'ADMIN_URL_NAME': 'admin:index',
    'MAINTENANCE_TEMPLATE': '503.html',
    'READ_ONLY_ALLOWED_METHODS': ["GET", "HEAD"],
}
```

### 5. Run Migrations

```python
python manage.py migrate
```

### 6. Add to urls.py

```python
from django.urls import path, include

urlpatterns = [
    ...
    path("maintenance/", include("django_enterprise_maintenance_suite.urls")),
]

```

### 7. Create SuperUser

```python
python manage.py createsuperuser
```
## Requirements

- Python 3.9+
- Django 4.2+

## How It Works

1. Incoming requests pass through `MaintenanceMiddleware`
2. Active maintenance window is evaluated
3. Mode is applied:
   - **Maintenance Mode** → HTTP 503
   - **Read-Only Mode** → Blocks write methods
4. Admin URLs are ignored by default

## Maintenance Modes

### Full Maintenance Mode
- Blocks all requests
- Returns **503 Service Unavailable**
- Intended for deployments & outages

### Read-Only Mode
- Allows safe HTTP methods
- Blocks:
  - POST
  - PUT
  - PATCH
  - DELETE
- Returns **403 Forbidden**

## Admin Panel Usage

The Django Admin allows you to:

- Create maintenance windows
- Enable / disable maintenance
- Approve or reject maintenance
- Track audit logs

## Custom 503 Page

To override the default maintenance page, create: **templates/503.html**
Django will automatically use this template.

## Use Cases

- Production deployments
- Database migrations
- Emergency maintenance
- Compliance-driven outages
- Enterprise change management

## Supporting

- Star this project on [GitHub](https://github.com/tamaraiselvan/Django-Enterprise-Maintenance-Suite)
- Follow me on [GitHub](https://github.com/tamaraiselvan)
- [![](https://img.shields.io/static/v1?label=Sponsor&message=%E2%9D%A4&logo=GitHub&color=%23fe8e86)](https://github.com/sponsors/tamaraiselvan)

## License

Licensed under the MIT License.
Copyright © 2026 TS Tamarai Selvan [Copy of the license](LICENSE).