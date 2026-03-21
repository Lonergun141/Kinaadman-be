# Kinaadman Backend

Kinaadman is a multi-tenant SaaS platform for universities to manage, archive, and publish thesis and capstone research in a centralized digital repository. This repository contains the backend API and Admin panel built with **Django**.

## Tech Stack

- **Framework:** Django 5.x
- **API Engine:** Django Ninja (REST / OpenAPI)
- **Admin Interface:** Django Unfold (Tailwind CSS powered admin)
- **Database:** PostgreSQL
- **Multi-Tenancy:** Custom tenant resolution via HTTP headers and Host aliases
- **Authentication:** JWT & OTP Session Management

## Project Structure

```text
Kinaadman-be/
├── apps/                   # Django applications (domain logic)
│   ├── authentication/     # Auth, OTP, JWT session management
│   ├── core/               # Shared models, templates, utils
│   ├── repository/         # Theses, Departments, Programs, File processing
│   ├── tenants/            # Tenant management, branding, domains
│   └── users/              # Users, TenantMemberships, RBAC
├── config/                 # Django settings and main URL routing
│   ├── settings/           # Modularized settings (base, local, production)
│   ├── api.py              # Main Django Ninja API router registration
│   └── urls.py             # Root URL conf
├── core/templates/         # Global template overrides (e.g. Redoc, Login, Portal)
├── requirements/           # Python dependencies split by environment
```

## Developer Setup

### Prerequisites
- Python 3.11+
- PostgreSQL (Running locally)

### 1. Clone & Environment Setup
```bash
git clone <repo_url>
cd Kinaadman-be

# Create a virtual environment
python -m venv .venv

# Activate the virtual environment
source .venv/Scripts/activate  # Windows (Git Bash)
# or
.venv\Scripts\activate         # Windows (CMD/PowerShell)
# or
source .venv/bin/activate      # Linux/macOS
```

### 2. Install Dependencies
```bash
pip install -r requirements/local.txt
```

### 3. Environment Variables
Create a `.env` file in the project root containing your local configurations:
```ini
DEBUG=True
SECRET_KEY=generate_a_secure_random_key_here

# Local PostgreSQL Connection
DATABASE_URL=postgres://postgres:qwerty@localhost:5434/kinaadman
```

### 4. Database Migrations
Provision the schema to your local database:
```bash
python manage.py makemigrations
python manage.py migrate
```

### 5. Create Superuser (Admin Access)
```bash
python manage.py createsuperuser
```

### 6. Populate Mock Data (Recommended for Local Dev)
To quickly seed the database with tenants, universities, departments, programs, and mock theses:
```bash
python manage.py populate_mock
```

### 7. Run the Development Server
```bash
python manage.py runserver
```

## Accessing Interfaces

### Admin Dashboard (Django Unfold)
Access the beautifully themed backend administration panel at:
- **Admin URL:** `http://127.0.0.1:8000/admin/`

### API Documentation (Django Ninja)
The API leverages Django Ninja to auto-generate OpenAPI documentation. Kinaadman uses a custom branded override of Redoc.
- **Redoc UI:** `http://127.0.0.1:8000/v1/docs/`

## Development Notes

### Tenant Context Isolation
Because Kinaadman is a multi-tenant platform, most API endpoints (like those in `apps/repository`) enforce strict data isolation. 

For local API testing via `curl` or Postman, you must pass an explicit **`X-Tenant-ID`** header to resolve the tenant context:
```bash
curl -H "X-Tenant-ID: <tenant_uuid_here>" http://127.0.0.1:8000/v1/theses/
```
*(You can retrieve a valid Tenant ID from the Django Admin or by running `python manage.py shell -c "from apps.tenants.models import Tenant; print(Tenant.objects.first().id)"`).*

### Authentication Pipeline
The backend specifies a custom OTP and Token refresh pipeline:
1. `POST /v1/auth/login` - Resolves tenant and verifies password. Can enforce Tenant OTP policies.
2. `POST /v1/auth/otp/verify` - Verifies the generated email OTP challege.
3. `POST /v1/auth/refresh` - Stateless rotatable token refresh family.

### Full Text Search (FTS) Integration for Frontend
The `GET /v1/theses/` endpoint supports powerful Postgres Full Text Search (FTS). It uses linguistic lexemes to intelligently match root words and scores/ranks results based on whether the match was found in the thesis title (higher priority) or the abstract (lower priority).

To implement a "Google-like" search bar in your Next.js frontend, simply pass the user's input to the `search` query parameter:
```javascript
// Next.js Frontend Example
const searchQuery = "neural networks";
const res = await fetch(`http://127.0.0.1:8000/v1/theses/?search=${encodeURIComponent(searchQuery)}`, {
    headers: {
        "X-Tenant-ID": currentTenantId
    }
});
const theses = await res.json();
// The resulting payload is already ranked by relevance and ordered automatically by the backend!
```
