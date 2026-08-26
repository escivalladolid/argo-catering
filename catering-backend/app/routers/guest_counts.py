from app.booking_scoped import make_booking_router
from app.models.catering_models import CateringGuestCount, CateringInquiry
from app.rbac import Perm
from app.schemas.catering_schemas import (
    CateringGuestCountCreate,
    CateringGuestCountOut,
    CateringGuestCountUpdate,
)

router = make_booking_router(
    prefix="/guest-counts",
    tag="Guest Counts",
    model=CateringGuestCount,
    create_schema=CateringGuestCountCreate,
    update_schema=CateringGuestCountUpdate,
    out_schema=CateringGuestCountOut,
    search_columns=[CateringInquiry.customer_name, CateringGuestCount.notes],
    sort_map={
        "name": CateringInquiry.customer_name,
        "count_type": CateringGuestCount.count_type,
        "count": CateringGuestCount.count,
        "recorded_at": CateringGuestCount.recorded_at,
        "created_at": CateringGuestCount.created_at,
    },
    status_column=CateringGuestCount.count_type,
    perm_view=Perm.GUEST_COUNT_VIEW,
    perm_create=Perm.GUEST_COUNT_CREATE,
    perm_update=Perm.GUEST_COUNT_UPDATE,
    perm_delete=Perm.GUEST_COUNT_DELETE,
)
