from ninja import NinjaAPI
from apps.authentication.api import router as auth_router

api = NinjaAPI(
    title="Kinaadman API",
    version="1.0.0",
    description="Campus-Only Multi-Tenant Thesis Repository API"
)

api.add_router("/auth/", auth_router)
