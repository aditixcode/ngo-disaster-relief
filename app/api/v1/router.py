"""
Central API Router for Version 1.

Aggregates individual resource routers (health, auth, disasters, volunteers,
donations, inventory, beneficiaries, distributions) into a unified /api/v1 router.
"""

from fastapi import APIRouter
from app.api.v1.endpoints import (
    health,
    auth,
    disasters,
    volunteers,
    donations,
    inventory,
    beneficiaries,
    distribution_centers,
    distributions,
    reports,
)

api_router = APIRouter()

# Include health-check router
api_router.include_router(health.router, tags=["Health"])

# Include authentication & authorization router
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])

# Include disaster management router
api_router.include_router(disasters.router, prefix="/disasters", tags=["Disasters"])

# Include volunteer assignments & task management router
api_router.include_router(volunteers.router, prefix="/volunteers", tags=["Volunteers & Tasks"])

# Include donation management router
api_router.include_router(donations.router, prefix="/donations", tags=["Donations"])

# Include relief inventory router
api_router.include_router(inventory.router, prefix="/inventory", tags=["Relief Inventory"])

# Include beneficiary management router
api_router.include_router(beneficiaries.router, prefix="/beneficiaries", tags=["Beneficiaries"])

# Include distribution center management router
api_router.include_router(distribution_centers.router, prefix="/distribution-centers", tags=["Distribution Centers"])

# Include resource distribution tracking router
api_router.include_router(distributions.router, prefix="/distributions", tags=["Distributions"])

# Include reporting and summary analytics router
api_router.include_router(reports.router, prefix="/reports", tags=["Reports"])


