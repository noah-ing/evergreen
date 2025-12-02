"""
API routes module.
"""

from evergreen.api.routes.auth import router as auth_router
from evergreen.api.routes.tenants import router as tenants_router

__all__ = [
    "auth_router",
    "tenants_router",
]
