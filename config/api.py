from ninja import NinjaAPI, Redoc
from apps.authentication.api import router as auth_router
from apps.repository.api import departments_router, programs_router, theses_router

api = NinjaAPI(
    title="Kinaadman API",
    version="1.0.0",
    description="""
### Campus-Only Multi-Tenant Thesis Repository API

All API routes within Kinaadman are strictly tenant-isolated. You must pass a valid `X-Tenant-ID` HTTP header for non-browser integration testing.
    """,
    docs_url="docs/",
    docs=Redoc()
)

api.add_router("/auth/", auth_router)
api.add_router("/departments/", departments_router)
api.add_router("/programs/", programs_router)
api.add_router("/theses/", theses_router)
