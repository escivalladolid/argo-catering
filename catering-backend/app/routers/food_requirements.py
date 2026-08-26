from app.booking_scoped import make_booking_router
from app.models.catering_models import CateringFoodRequirement, CateringInquiry
from app.rbac import Perm
from app.schemas.catering_schemas import (
    CateringFoodRequirementCreate,
    CateringFoodRequirementOut,
    CateringFoodRequirementUpdate,
)

router = make_booking_router(
    prefix="/food-requirements",
    tag="Food Requirements",
    model=CateringFoodRequirement,
    create_schema=CateringFoodRequirementCreate,
    update_schema=CateringFoodRequirementUpdate,
    out_schema=CateringFoodRequirementOut,
    search_columns=[CateringInquiry.customer_name, CateringFoodRequirement.description],
    sort_map={
        "name": CateringInquiry.customer_name,
        "requirement_type": CateringFoodRequirement.requirement_type,
        "guest_count": CateringFoodRequirement.guest_count,
        "created_at": CateringFoodRequirement.created_at,
    },
    status_column=CateringFoodRequirement.requirement_type,
    perm_view=Perm.FOOD_REQUIREMENT_VIEW,
    perm_create=Perm.FOOD_REQUIREMENT_CREATE,
    perm_update=Perm.FOOD_REQUIREMENT_UPDATE,
    perm_delete=Perm.FOOD_REQUIREMENT_DELETE,
)
