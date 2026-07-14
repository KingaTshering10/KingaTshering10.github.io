from fastapi import APIRouter

from app.api.v1 import admin, auth, buyers, catalog, farmers, harvests, users

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(catalog.router)
api_router.include_router(farmers.router)
api_router.include_router(harvests.router)
api_router.include_router(buyers.router)
api_router.include_router(admin.router)
