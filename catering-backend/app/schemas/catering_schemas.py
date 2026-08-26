import re
from datetime import datetime, time, timezone
from typing import Any, Generic, Literal, TypeVar
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from app.rbac import VALID_ROLES


def _ensure_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def _validate_not_past(v: datetime) -> datetime:
    dt = _ensure_utc(v)
    if dt < datetime.now(timezone.utc):
        raise ValueError("Date must not be in the past")
    return dt


T = TypeVar("T")


class Page(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    page_size: int
    total_pages: int


class AuditLogOut(BaseModel):
    id: UUID
    organization_id: UUID
    entity_type: str
    entity_id: UUID | None = None
    entity_reference: str | None = None
    action: str
    actor_id: UUID | None = None
    actor_role: str | None = None
    actor_email: str | None = None
    summary: str | None = None
    created_at: datetime


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


class LoginIn(BaseModel):
    email: str
    password: str

    @field_validator("email")
    @classmethod
    def _validate_email(cls, v: str) -> str:
        v = v.strip().lower()
        if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", v):
            raise ValueError("Invalid email format")
        return v

    @field_validator("password")
    @classmethod
    def _validate_password(cls, v: str) -> str:
        if len(v) < 1:
            raise ValueError("Password must not be empty")
        return v


class UserOut(BaseModel):
    id: UUID
    email: str
    full_name: str | None = None
    role: str
    is_active: bool = True
    organization_id: UUID | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    last_login_at: datetime | None = None
    permissions: list[str] = []


class UserCreateIn(BaseModel):
    email: str
    full_name: str | None = None
    role: str

    @field_validator("email")
    @classmethod
    def _validate_email(cls, v: str) -> str:
        v = v.strip().lower()
        if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", v):
            raise ValueError("Invalid email format")
        return v

    @field_validator("role")
    @classmethod
    def _validate_role(cls, v: str) -> str:
        v = v.strip().lower()
        if v not in VALID_ROLES:
            raise ValueError("Invalid role")
        return v


class UserUpdateIn(BaseModel):
    full_name: str | None = None
    role: str | None = None
    verification_code: str | None = None

    @field_validator("role")
    @classmethod
    def _validate_role(cls, v: str | None) -> str | None:
        if v is None:
            return None
        v = v.strip().lower()
        if v not in VALID_ROLES:
            raise ValueError("Invalid role")
        return v

    @field_validator("verification_code")
    @classmethod
    def _strip_code(cls, v: str | None) -> str | None:
        if v is None:
            return None
        v = v.strip()
        if not v.isdigit() or len(v) != 6:
            raise ValueError("Verification code must be a 6-digit number")
        return v


class VerificationCodeIn(BaseModel):
    verification_code: str = Field(min_length=6, max_length=6)

    @field_validator("verification_code")
    @classmethod
    def _strip_code(cls, v: str) -> str:
        v = v.strip()
        if not v.isdigit() or len(v) != 6:
            raise ValueError("Verification code must be a 6-digit number")
        return v


class VerificationCodeRequestOut(BaseModel):
    detail: str = "If the account exists, a verification code has been sent."


class UserCreatedOut(BaseModel):
    id: UUID
    email: str
    full_name: str | None = None
    role: str
    is_active: bool = True
    temporary_password: str


class UserResetOut(BaseModel):
    id: UUID
    email: str
    temporary_password: str


class OrganizationOut(BaseModel):
    id: UUID
    name: str


class PackageGroupIn(BaseModel):
    name: str = Field(min_length=1)
    min_select: int = Field(default=0, ge=0)
    max_select: int = Field(default=1, ge=1)
    sort_order: int = Field(default=0, ge=0)
    key: str | None = None

    @field_validator("name")
    @classmethod
    def _strip_name(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Group name must not be blank")
        return v

    @field_validator("max_select")
    @classmethod
    def _max_ge_min(cls, v: int, info) -> int:
        min_sel = info.data.get("min_select", 0)
        if v < min_sel:
            raise ValueError("max_select must be >= min_select")
        return v


class PackageItemIn(BaseModel):
    menu_item_id: UUID
    kind: str = Field(default="included")
    group_key: str | None = None
    quantity: int = Field(default=1, ge=1)
    unit: str = Field(default="serving", min_length=1)
    sort_order: int = Field(default=0, ge=0)

    @field_validator("kind")
    @classmethod
    def _valid_kind(cls, v: str) -> str:
        if v not in ("included", "default", "option"):
            raise ValueError("Invalid package item kind")
        return v

    @field_validator("unit")
    @classmethod
    def _strip_unit(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Unit must not be blank")
        return v


class DerivedRatioIn(BaseModel):
    item_key: str = Field(min_length=1, max_length=50)
    per_guests: int = Field(ge=1)
    minimum: int = Field(ge=0, default=0)

    @field_validator("item_key")
    @classmethod
    def _strip_key(cls, v: str) -> str:
        v = v.strip().lower().replace(" ", "_")
        if not v:
            raise ValueError("item_key must not be blank")
        return v


class DerivedRatioOut(BaseModel):
    id: UUID
    item_key: str
    per_guests: int
    minimum: int

    class Config:
        from_attributes = True


class CateringPackageCreate(BaseModel):
    name: str = Field(min_length=1)
    description: str | None = None
    base_price: float = Field(ge=0)
    pricing_method: str = Field(default="per_guest")
    has_customization: bool = False
    is_active: bool = True
    groups: list[PackageGroupIn] = []
    items: list[PackageItemIn] = []
    derived_ratios: list[DerivedRatioIn] = []
    min_pax: int | None = Field(default=None, ge=0)
    max_pax: int | None = None
    service_style: str | None = Field(default=None)

    @field_validator("name")
    @classmethod
    def _strip_name(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Name must not be blank")
        return v

    @field_validator("pricing_method")
    @classmethod
    def _valid_pricing(cls, v: str) -> str:
        if v not in ("per_guest", "fixed"):
            raise ValueError("Invalid pricing method")
        return v


class CateringPackageUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1)
    description: str | None = None
    base_price: float | None = Field(default=None, ge=0)
    pricing_method: str | None = None
    has_customization: bool | None = None
    is_active: bool | None = None
    groups: list[PackageGroupIn] | None = None
    items: list[PackageItemIn] | None = None
    derived_ratios: list[DerivedRatioIn] | None = None
    min_pax: int | None = Field(default=None, ge=0)
    max_pax: int | None = None
    service_style: str | None = None

    @field_validator("name")
    @classmethod
    def _strip_name(cls, v: str | None) -> str | None:
        if v is None:
            return v
        v = v.strip()
        if not v:
            raise ValueError("Name must not be blank")
        return v

    @field_validator("pricing_method")
    @classmethod
    def _valid_pricing(cls, v: str | None) -> str | None:
        if v is not None and v not in ("per_guest", "fixed"):
            raise ValueError("Invalid pricing method")
        return v


class PackageItemOut(BaseModel):
    id: UUID
    menu_item_id: UUID
    item_name: str | None = None
    kind: str
    group_id: UUID | None = None
    quantity: int
    unit: str
    sort_order: int

    class Config:
        from_attributes = True


class PackageGroupOut(BaseModel):
    id: UUID
    name: str
    min_select: int
    max_select: int
    sort_order: int
    options: list[PackageItemOut] = []

    class Config:
        from_attributes = True


class PackageDetailOut(BaseModel):
    id: UUID
    organization_id: UUID
    name: str
    description: str | None = None
    base_price: float
    pricing_method: str
    has_customization: bool
    is_active: bool
    min_pax: int | None = None
    max_pax: int | None = None
    service_style: str | None = None
    groups: list[PackageGroupOut] = []
    items: list[PackageItemOut] = []
    derived_ratios: list[DerivedRatioOut] = []
    created_at: datetime
    updated_at: datetime
    created_by: UUID | None = None
    updated_by: UUID | None = None
    deleted_at: datetime | None = None

    class Config:
        from_attributes = True


class CateringPackageOut(BaseModel):
    id: UUID
    organization_id: UUID
    name: str
    description: str | None = None
    base_price: float
    pricing_method: str = "per_guest"
    has_customization: bool = False
    min_pax: int | None = None
    max_pax: int | None = None
    service_style: str | None = None
    is_active: bool
    created_at: datetime
    updated_at: datetime
    created_by: UUID | None = None
    updated_by: UUID | None = None
    deleted_at: datetime | None = None

    class Config:
        from_attributes = True


class FoodItemOut(BaseModel):
    id: UUID
    menu_id: UUID
    menu_name: str
    name: str
    description: str | None = None
    category: str
    dietary_tags: str | None = None
    is_active: bool
    sort_order: int

    class Config:
        from_attributes = True


class FoodRequirementIn(BaseModel):
    type: str = Field(default="food", min_length=1)
    description: str = Field(min_length=1)
    guest_count: int | None = Field(default=None, ge=1, le=5000)

    @field_validator("type", "description")
    @classmethod
    def _strip_text(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Field must not be blank")
        return v


class FoodRequirementOut(FoodRequirementIn):
    pass


class StaffingRequestIn(BaseModel):
    waiter_count: int = Field(default=0, ge=0)
    bartender_count: int = Field(default=0, ge=0)
    chef_count: int = Field(default=0, ge=0)
    kitchen_staff_count: int = Field(default=0, ge=0)
    support_crew_count: int = Field(default=0, ge=0)


class InquiryItemIn(BaseModel):
    menu_item_id: UUID
    item_name: str = Field(min_length=1)
    category: str | None = None
    group_name: str | None = None
    kind: str = Field(default="custom")
    quantity: int = Field(default=1, ge=1)
    unit: str = Field(default="serving", min_length=1)
    sort_order: int = Field(default=0, ge=0)

    @field_validator("item_name")
    @classmethod
    def _strip_name(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Item name must not be blank")
        return v

    @field_validator("kind")
    @classmethod
    def _valid_kind(cls, v: str) -> str:
        if v not in ("default", "custom", "included"):
            raise ValueError("Invalid inquiry item kind")
        return v


class CateringInquiryCreate(BaseModel):
    customer_name: str = Field(min_length=1)
    customer_contact: str = Field(min_length=1)
    event_date: datetime
    event_time: time | None = None
    event_type: str | None = None
    event_address: str = Field(min_length=1)
    venue_name: str | None = None
    location_floor: str | None = None
    room_hall: str | None = None
    landmark: str | None = None
    delivery_instructions: str | None = None
    guest_count: int = Field(ge=1, le=5000)
    catering_package_id: UUID | None = None
    package_mode: str | None = None
    food_requirements: list[FoodRequirementIn] = []
    staff: StaffingRequestIn | None = None
    items: list[InquiryItemIn] = []
    notes: str | None = None
    additional_notes: str | None = None
    dietary_notes: str | None = None
    setup_notes: str | None = None

    @field_validator("customer_name", "customer_contact", "event_address")
    @classmethod
    def _strip_text(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Field must not be blank")
        return v

    @field_validator("venue_name", "location_floor", "room_hall", "landmark", "delivery_instructions")
    @classmethod
    def _strip_optional_text(cls, v: str | None) -> str | None:
        if v is None:
            return v
        v = v.strip()
        return v or None

    @field_validator("event_date")
    @classmethod
    def _not_past(cls, v: datetime) -> datetime:
        return _validate_not_past(v)

    @field_validator("package_mode")
    @classmethod
    def _valid_mode(cls, v: str | None) -> str | None:
        if v is not None and v not in ("default", "custom"):
            raise ValueError("Invalid package mode")
        return v


class CateringInquiryOut(BaseModel):
    id: UUID
    organization_id: UUID
    customer_name: str
    customer_contact: str
    event_date: datetime
    event_time: time | None = None
    event_type: str | None = None
    event_address: str | None = None
    venue_name: str | None = None
    location_floor: str | None = None
    room_hall: str | None = None
    landmark: str | None = None
    delivery_instructions: str | None = None
    guest_count: int
    catering_package_id: UUID | None = None
    package_mode: str | None = None
    food_requirements_json: str | None = None
    waiter_count: int = 0
    bartender_count: int = 0
    chef_count: int = 0
    kitchen_staff_count: int = 0
    support_crew_count: int = 0
    flag_note: str | None = None
    notes: str | None = None
    status: str
    short_reference: str | None = None
    review_status: str = "auto_approved"
    review_reason: str | None = None
    created_at: datetime
    updated_at: datetime
    created_by: UUID | None = None
    updated_by: UUID | None = None
    deleted_at: datetime | None = None

    class Config:
        from_attributes = True


class InquiryItemOut(BaseModel):
    id: UUID
    menu_item_id: UUID | None = None
    item_name: str
    category: str | None = None
    group_name: str | None = None
    kind: str
    quantity: int
    unit: str
    sort_order: int

    class Config:
        from_attributes = True


class StaffingOut(BaseModel):
    waiter_count: int = 0
    bartender_count: int = 0
    chef_count: int = 0
    kitchen_staff_count: int = 0
    support_crew_count: int = 0


class CateringInquiryDetailOut(CateringInquiryOut):
    food_requirements: list[FoodRequirementOut] = []
    items: list[InquiryItemOut] = []
    staffing: StaffingOut | None = None


class CateringQuotationCreate(BaseModel):
    inquiry_id: UUID
    catering_package_id: UUID | None = None
    guest_count: int = Field(ge=1, le=5000)
    total_price: float | None = Field(default=None, ge=0)
    valid_until: datetime | None = None

    @field_validator("valid_until")
    @classmethod
    def _not_past_valid(cls, v: datetime | None) -> datetime | None:
        return _validate_not_past(v) if v is not None else None


class CateringQuotationUpdate(BaseModel):
    catering_package_id: UUID | None = None
    guest_count: int | None = Field(default=None, ge=1, le=5000)
    total_price: float | None = Field(default=None, ge=0)
    valid_until: datetime | None = None

    @field_validator("valid_until")
    @classmethod
    def _not_past_valid(cls, v: datetime | None) -> datetime | None:
        return _validate_not_past(v) if v is not None else None


class CateringQuotationFromInquiryIn(BaseModel):
    guest_count: int | None = Field(default=None, ge=1, le=5000)
    total_price: float | None = Field(default=None, ge=0)
    valid_until: datetime | None = None

    @field_validator("valid_until")
    @classmethod
    def _not_past_valid(cls, v: datetime | None) -> datetime | None:
        return _validate_not_past(v) if v is not None else None


class CateringQuotationPrefillOut(BaseModel):
    inquiry_id: UUID
    inquiry_status: str
    customer_name: str
    customer_contact: str
    event_date: datetime
    event_time: time | None = None
    event_type: str | None = None
    event_address: str | None = None
    venue_name: str | None = None
    location_floor: str | None = None
    room_hall: str | None = None
    landmark: str | None = None
    delivery_instructions: str | None = None
    guest_count: int
    catering_package_id: UUID | None = None
    package_name: str | None = None
    package_mode: str | None = None
    pricing_method: str | None = None
    base_price: float | None = None
    suggested_total: float | None = None
    food_requirements: list[FoodRequirementOut] = []
    items: list[InquiryItemOut] = []
    staffing: StaffingOut | None = None
    flag_note: str | None = None
    notes: str | None = None


class CateringQuotationOut(BaseModel):
    id: UUID
    organization_id: UUID
    inquiry_id: UUID
    catering_package_id: UUID | None = None
    guest_count: int
    total_price: float
    status: str
    valid_until: datetime | None = None
    created_at: datetime
    updated_at: datetime
    created_by: UUID | None = None
    updated_by: UUID | None = None
    deleted_at: datetime | None = None

    class Config:
        from_attributes = True


class CateringQuotationDetailOut(CateringQuotationOut):
    package_name: str | None = None
    package_mode: str | None = None
    pricing_method: str | None = None
    base_price: float | None = None
    customer_name: str | None = None
    customer_contact: str | None = None
    event_date: datetime | None = None
    event_time: time | None = None
    event_type: str | None = None
    event_address: str | None = None
    venue_name: str | None = None
    location_floor: str | None = None
    room_hall: str | None = None
    landmark: str | None = None
    delivery_instructions: str | None = None
    food_requirements: list[FoodRequirementOut] = []
    items: list[InquiryItemOut] = []
    staffing: StaffingOut | None = None


class CateringBookingOut(BaseModel):
    id: UUID
    organization_id: UUID
    quotation_id: UUID
    event_date: datetime
    event_location: str | None = None
    event_time: time | None = None
    guest_count: int
    total_amount: float
    amount_paid: float = 0
    remaining_balance: float = 0
    payment_status: str
    status: str
    service_style: str | None = None
    event_duration_hours: float | None = None
    selected_venue_id: UUID | None = None
    additional_notes: str | None = None
    dietary_notes: str | None = None
    setup_notes: str | None = None
    coordinator_name: str | None = None
    coordinator_contact: str | None = None
    created_at: datetime
    updated_at: datetime
    created_by: UUID | None = None
    updated_by: UUID | None = None
    deleted_at: datetime | None = None

    class Config:
        from_attributes = True


class DerivedInclusionOut(BaseModel):
    item_key: str
    quantity: int


class CateringBookingDetailOut(CateringBookingOut):
    customer_name: str | None = None
    customer_contact: str | None = None
    event_type: str | None = None
    event_address: str | None = None
    venue_name: str | None = None
    location_floor: str | None = None
    room_hall: str | None = None
    landmark: str | None = None
    delivery_instructions: str | None = None
    package_name: str | None = None
    package_mode: str | None = None
    food_requirements: list[FoodRequirementOut] = []
    items: list[InquiryItemOut] = []
    staffing: StaffingOut | None = None
    staffing_available: StaffingOut | None = None
    staffing_warning: str | None = None
    derived_inclusions: list[DerivedInclusionOut] = []
    recent_activity: list[AuditLogOut] = []


class CateringBookingTransition(BaseModel):
    pass


class CateringBookingUpdate(BaseModel):
    coordinator_name: str | None = None
    coordinator_contact: str | None = None
    selected_venue_id: UUID | None = None
    additional_notes: str | None = None
    dietary_notes: str | None = None
    setup_notes: str | None = None


class CateringInquiryUpdate(BaseModel):
    customer_name: str | None = Field(default=None, min_length=1)
    customer_contact: str | None = Field(default=None, min_length=1)
    event_date: datetime | None = None
    event_time: time | None = None
    event_type: str | None = None
    event_address: str | None = Field(default=None, min_length=1)
    venue_name: str | None = None
    location_floor: str | None = None
    room_hall: str | None = None
    landmark: str | None = None
    delivery_instructions: str | None = None
    guest_count: int | None = Field(default=None, ge=1, le=5000)
    catering_package_id: UUID | None = None
    package_mode: str | None = None
    food_requirements: list[FoodRequirementIn] | None = None
    staff: StaffingRequestIn | None = None
    items: list[InquiryItemIn] | None = None
    notes: str | None = None
    additional_notes: str | None = None
    dietary_notes: str | None = None
    setup_notes: str | None = None

    @field_validator("customer_name", "customer_contact")
    @classmethod
    def _strip_text(cls, v: str | None) -> str | None:
        if v is None:
            return v
        v = v.strip()
        if not v:
            raise ValueError("Field must not be blank")
        return v

    @field_validator("event_address")
    @classmethod
    def _strip_address(cls, v: str | None) -> str | None:
        if v is None:
            return v
        v = v.strip()
        if not v:
            raise ValueError("Field must not be blank")
        return v

    @field_validator("venue_name", "location_floor", "room_hall", "landmark", "delivery_instructions")
    @classmethod
    def _strip_optional_text(cls, v: str | None) -> str | None:
        if v is None:
            return v
        v = v.strip()
        return v or None

    @field_validator("event_date")
    @classmethod
    def _not_past(cls, v: datetime | None) -> datetime | None:
        return _validate_not_past(v) if v is not None else None

    @field_validator("package_mode")
    @classmethod
    def _valid_mode(cls, v: str | None) -> str | None:
        if v is not None and v not in ("default", "custom"):
            raise ValueError("Invalid package mode")
        return v


class CateringMenuItemCreate(BaseModel):
    name: str = Field(min_length=1)
    description: str | None = None
    category: str = Field(default="main")
    dietary_tags: str | None = None
    price: float = Field(default=0, ge=0)
    pricing_unit: str = Field(default="per_guest")
    is_active: bool = True
    sort_order: int = Field(default=0, ge=0)

    @field_validator("name")
    @classmethod
    def _strip_name(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Name must not be blank")
        return v

    @field_validator("category")
    @classmethod
    def _valid_category(cls, v: str) -> str:
        if v not in ("starter", "main", "dessert", "beverage", "other"):
            raise ValueError("Invalid item category")
        return v

    @field_validator("pricing_unit")
    @classmethod
    def _valid_pricing_unit(cls, v: str) -> str:
        if v not in ("per_guest", "flat"):
            raise ValueError("Invalid pricing unit")
        return v


class CateringMenuItemUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1)
    description: str | None = None
    category: str | None = None
    dietary_tags: str | None = None
    price: float | None = Field(default=None, ge=0)
    pricing_unit: str | None = None
    is_active: bool | None = None
    sort_order: int | None = Field(default=None, ge=0)

    @field_validator("name")
    @classmethod
    def _strip_name(cls, v: str | None) -> str | None:
        if v is None:
            return v
        v = v.strip()
        if not v:
            raise ValueError("Name must not be blank")
        return v

    @field_validator("category")
    @classmethod
    def _valid_category(cls, v: str | None) -> str | None:
        if v is not None and v not in ("starter", "main", "dessert", "beverage", "other"):
            raise ValueError("Invalid item category")
        return v

    @field_validator("pricing_unit")
    @classmethod
    def _valid_pricing_unit(cls, v: str | None) -> str | None:
        if v is not None and v not in ("per_guest", "flat"):
            raise ValueError("Invalid pricing unit")
        return v


class CateringMenuItemOut(BaseModel):
    id: UUID
    organization_id: UUID
    menu_id: UUID
    name: str
    description: str | None = None
    category: str
    dietary_tags: str | None = None
    price: float = 0
    pricing_unit: str = "per_guest"
    is_active: bool
    sort_order: int
    created_at: datetime
    updated_at: datetime
    created_by: UUID | None = None
    updated_by: UUID | None = None
    deleted_at: datetime | None = None

    class Config:
        from_attributes = True


class CateringMenuCreate(BaseModel):
    name: str = Field(min_length=1)
    description: str | None = None
    category: str = Field(default="lunch")
    is_active: bool = True
    items: list[CateringMenuItemCreate] = []

    @field_validator("name")
    @classmethod
    def _strip_name(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Name must not be blank")
        return v

    @field_validator("category")
    @classmethod
    def _valid_category(cls, v: str) -> str:
        if v not in ("lunch", "dinner", "breakfast", "cocktail", "custom"):
            raise ValueError("Invalid menu category")
        return v


class CateringMenuUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1)
    description: str | None = None
    category: str | None = None
    is_active: bool | None = None
    items: list[CateringMenuItemCreate] | None = None

    @field_validator("name")
    @classmethod
    def _strip_name(cls, v: str | None) -> str | None:
        if v is None:
            return v
        v = v.strip()
        if not v:
            raise ValueError("Name must not be blank")
        return v

    @field_validator("category")
    @classmethod
    def _valid_category(cls, v: str | None) -> str | None:
        if v is not None and v not in ("lunch", "dinner", "breakfast", "cocktail", "custom"):
            raise ValueError("Invalid menu category")
        return v


class CateringMenuOut(BaseModel):
    id: UUID
    organization_id: UUID
    name: str
    description: str | None = None
    category: str
    is_active: bool
    item_count: int = 0
    created_at: datetime
    updated_at: datetime
    created_by: UUID | None = None
    updated_by: UUID | None = None
    deleted_at: datetime | None = None

    class Config:
        from_attributes = True


class CateringGuestCountCreate(BaseModel):
    booking_id: UUID
    count_type: str = Field(default="estimated")
    count: int = Field(ge=1)
    recorded_at: datetime | None = None
    notes: str | None = None

    @field_validator("count_type")
    @classmethod
    def _valid_type(cls, v: str) -> str:
        if v not in ("estimated", "guaranteed", "actual"):
            raise ValueError("Invalid count type")
        return v


class CateringGuestCountUpdate(BaseModel):
    count_type: str | None = None
    count: int | None = Field(default=None, ge=1)
    recorded_at: datetime | None = None
    notes: str | None = None

    @field_validator("count_type")
    @classmethod
    def _valid_type(cls, v: str | None) -> str | None:
        if v is not None and v not in ("estimated", "guaranteed", "actual"):
            raise ValueError("Invalid count type")
        return v


class CateringGuestCountOut(BaseModel):
    id: UUID
    organization_id: UUID
    booking_id: UUID
    count_type: str
    count: int
    recorded_at: datetime
    notes: str | None = None
    created_at: datetime
    updated_at: datetime
    created_by: UUID | None = None
    updated_by: UUID | None = None
    deleted_at: datetime | None = None

    class Config:
        from_attributes = True


class CateringFoodRequirementCreate(BaseModel):
    booking_id: UUID
    requirement_type: str = Field(default="other")
    description: str = Field(min_length=1)
    guest_count: int | None = Field(default=None, ge=1, le=5000)
    notes: str | None = None

    @field_validator("description")
    @classmethod
    def _strip_desc(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Description must not be blank")
        return v

    @field_validator("requirement_type")
    @classmethod
    def _valid_type(cls, v: str) -> str:
        if v not in ("vegetarian", "vegan", "halal", "gluten_free", "allergy", "other"):
            raise ValueError("Invalid requirement type")
        return v


class CateringFoodRequirementUpdate(BaseModel):
    requirement_type: str | None = None
    description: str | None = Field(default=None, min_length=1)
    guest_count: int | None = Field(default=None, ge=1, le=5000)
    notes: str | None = None

    @field_validator("description")
    @classmethod
    def _strip_desc(cls, v: str | None) -> str | None:
        if v is None:
            return v
        v = v.strip()
        if not v:
            raise ValueError("Description must not be blank")
        return v

    @field_validator("requirement_type")
    @classmethod
    def _valid_type(cls, v: str | None) -> str | None:
        if v is not None and v not in ("vegetarian", "vegan", "halal", "gluten_free", "allergy", "other"):
            raise ValueError("Invalid requirement type")
        return v


class CateringFoodRequirementOut(BaseModel):
    id: UUID
    organization_id: UUID
    booking_id: UUID
    requirement_type: str
    description: str
    guest_count: int | None = None
    notes: str | None = None
    created_at: datetime
    updated_at: datetime
    created_by: UUID | None = None
    updated_by: UUID | None = None
    deleted_at: datetime | None = None

    class Config:
        from_attributes = True


class CateringStaffMemberCreate(BaseModel):
    name: str = Field(min_length=1)
    role: str = Field(default="server")
    phone: str | None = None
    rate: float = Field(default=0, ge=0)
    pricing_unit: str = Field(default="per_guest")
    is_active: bool = True

    @field_validator("name")
    @classmethod
    def _strip_name(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Name must not be blank")
        return v

    @field_validator("role")
    @classmethod
    def _valid_role(cls, v: str) -> str:
        if v not in ("chef", "server", "crew", "supervisor", "driver", "bartender", "kitchen_staff", "support"):
            raise ValueError("Invalid staff role")
        return v

    @field_validator("pricing_unit")
    @classmethod
    def _valid_pricing_unit(cls, v: str) -> str:
        if v not in ("per_guest", "flat"):
            raise ValueError("Invalid pricing unit")
        return v


class CateringStaffMemberUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1)
    role: str | None = None
    phone: str | None = None
    rate: float | None = Field(default=None, ge=0)
    pricing_unit: str | None = None
    is_active: bool | None = None

    @field_validator("name")
    @classmethod
    def _strip_name(cls, v: str | None) -> str | None:
        if v is None:
            return v
        v = v.strip()
        if not v:
            raise ValueError("Name must not be blank")
        return v

    @field_validator("role")
    @classmethod
    def _valid_role(cls, v: str | None) -> str | None:
        if v is not None and v not in ("chef", "server", "crew", "supervisor", "driver", "bartender", "kitchen_staff", "support"):
            raise ValueError("Invalid staff role")
        return v

    @field_validator("pricing_unit")
    @classmethod
    def _valid_pricing_unit(cls, v: str | None) -> str | None:
        if v is not None and v not in ("per_guest", "flat"):
            raise ValueError("Invalid pricing unit")
        return v


class CateringStaffMemberOut(BaseModel):
    id: UUID
    organization_id: UUID
    name: str
    role: str
    phone: str | None = None
    rate: float = 0
    pricing_unit: str = "per_guest"
    is_active: bool
    created_at: datetime
    updated_at: datetime
    created_by: UUID | None = None
    updated_by: UUID | None = None
    deleted_at: datetime | None = None

    class Config:
        from_attributes = True


class CateringStaffAssignmentCreate(BaseModel):
    booking_id: UUID
    staff_id: UUID
    shift_start: datetime
    shift_end: datetime | None = None
    role: str | None = None
    notes: str | None = None

    @field_validator("role")
    @classmethod
    def _valid_role(cls, v: str | None) -> str | None:
        if v is not None and v not in ("chef", "server", "crew", "supervisor", "driver", "bartender", "kitchen_staff", "support"):
            raise ValueError("Invalid role")
        return v


class CateringStaffAssignmentUpdate(BaseModel):
    staff_id: UUID | None = None
    shift_start: datetime | None = None
    shift_end: datetime | None = None
    role: str | None = None
    notes: str | None = None

    @field_validator("role")
    @classmethod
    def _valid_role(cls, v: str | None) -> str | None:
        if v is not None and v not in ("chef", "server", "crew", "supervisor", "driver", "bartender", "kitchen_staff", "support"):
            raise ValueError("Invalid role")
        return v


class CateringStaffAssignmentOut(BaseModel):
    id: UUID
    organization_id: UUID
    booking_id: UUID
    staff_id: UUID
    staff_name: str | None = None
    shift_start: datetime
    shift_end: datetime | None = None
    role: str | None = None
    notes: str | None = None
    created_at: datetime
    updated_at: datetime
    created_by: UUID | None = None
    updated_by: UUID | None = None
    deleted_at: datetime | None = None

    class Config:
        from_attributes = True


class CateringEquipmentCreate(BaseModel):
    name: str = Field(min_length=1)
    category: str = Field(default="kitchen")
    quantity: int = Field(default=1, ge=0)
    unit_cost: float = Field(default=0, ge=0)
    pricing_unit: str = Field(default="flat")
    is_active: bool = True

    @field_validator("name")
    @classmethod
    def _strip_name(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Name must not be blank")
        return v

    @field_validator("category")
    @classmethod
    def _valid_category(cls, v: str) -> str:
        if v not in ("kitchen", "service", "venue", "transport", "other"):
            raise ValueError("Invalid equipment category")
        return v

    @field_validator("pricing_unit")
    @classmethod
    def _valid_pricing_unit(cls, v: str) -> str:
        if v not in ("per_guest", "flat"):
            raise ValueError("Invalid pricing unit")
        return v


class CateringEquipmentUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1)
    category: str | None = None
    quantity: int | None = Field(default=None, ge=0)
    unit_cost: float | None = Field(default=None, ge=0)
    pricing_unit: str | None = None
    is_active: bool | None = None

    @field_validator("name")
    @classmethod
    def _strip_name(cls, v: str | None) -> str | None:
        if v is None:
            return v
        v = v.strip()
        if not v:
            raise ValueError("Name must not be blank")
        return v

    @field_validator("category")
    @classmethod
    def _valid_category(cls, v: str | None) -> str | None:
        if v is not None and v not in ("kitchen", "service", "venue", "transport", "other"):
            raise ValueError("Invalid equipment category")
        return v

    @field_validator("pricing_unit")
    @classmethod
    def _valid_pricing_unit(cls, v: str | None) -> str | None:
        if v is not None and v not in ("per_guest", "flat"):
            raise ValueError("Invalid pricing unit")
        return v


class CateringEquipmentOut(BaseModel):
    id: UUID
    organization_id: UUID
    name: str
    category: str
    quantity: int
    unit_cost: float
    pricing_unit: str = "flat"
    is_active: bool
    created_at: datetime
    updated_at: datetime
    created_by: UUID | None = None
    updated_by: UUID | None = None
    deleted_at: datetime | None = None

    class Config:
        from_attributes = True


class CateringEquipmentAssignmentCreate(BaseModel):
    booking_id: UUID
    equipment_id: UUID
    quantity: int = Field(default=1, ge=1)
    notes: str | None = None


class CateringEquipmentAssignmentUpdate(BaseModel):
    equipment_id: UUID | None = None
    quantity: int | None = Field(default=None, ge=1)
    notes: str | None = None


class CateringEquipmentAssignmentOut(BaseModel):
    id: UUID
    organization_id: UUID
    booking_id: UUID
    equipment_id: UUID
    equipment_name: str | None = None
    quantity: int
    notes: str | None = None
    created_at: datetime
    updated_at: datetime
    created_by: UUID | None = None
    updated_by: UUID | None = None
    deleted_at: datetime | None = None

    class Config:
        from_attributes = True


class CateringDeliveryCreate(BaseModel):
    booking_id: UUID
    scheduled_at: datetime
    delivery_address: str | None = None
    contact_name: str | None = None
    contact_phone: str | None = None
    status: str = Field(default="scheduled")
    notes: str | None = None

    @field_validator("scheduled_at")
    @classmethod
    def _not_past(cls, v: datetime) -> datetime:
        return _validate_not_past(v)

    @field_validator("status")
    @classmethod
    def _valid_status(cls, v: str) -> str:
        if v not in ("scheduled", "in_transit", "delivered", "delayed", "cancelled"):
            raise ValueError("Invalid delivery status")
        return v


class CateringDeliveryUpdate(BaseModel):
    scheduled_at: datetime | None = None
    delivery_address: str | None = None
    contact_name: str | None = None
    contact_phone: str | None = None
    status: str | None = None
    notes: str | None = None

    @field_validator("scheduled_at")
    @classmethod
    def _not_past(cls, v: datetime | None) -> datetime | None:
        return _validate_not_past(v) if v is not None else None

    @field_validator("status")
    @classmethod
    def _valid_status(cls, v: str | None) -> str | None:
        if v is not None and v not in ("scheduled", "in_transit", "delivered", "delayed", "cancelled"):
            raise ValueError("Invalid delivery status")
        return v


class CateringDeliveryOut(BaseModel):
    id: UUID
    organization_id: UUID
    booking_id: UUID
    scheduled_at: datetime
    delivery_address: str | None = None
    contact_name: str | None = None
    contact_phone: str | None = None
    status: str
    notes: str | None = None
    created_at: datetime
    updated_at: datetime
    created_by: UUID | None = None
    updated_by: UUID | None = None
    deleted_at: datetime | None = None

    class Config:
        from_attributes = True


class CateringPaymentCreate(BaseModel):
    booking_id: UUID
    amount: float = Field(ge=0)
    method: str = Field(default="cash")
    reference: str | None = None
    paid_at: datetime | None = None
    payment_date: datetime | None = None
    customer_reference: str | None = None
    notes: str | None = None

    @field_validator("method")
    @classmethod
    def _valid_method(cls, v: str) -> str:
        if v not in ("cash", "bank_transfer", "card", "gcash", "check", "other", "maya"):
            raise ValueError("Invalid payment method")
        return v


class CateringPaymentUpdate(BaseModel):
    amount: float | None = Field(default=None, ge=0)
    method: str | None = None
    reference: str | None = None
    paid_at: datetime | None = None
    payment_date: datetime | None = None
    customer_reference: str | None = None
    notes: str | None = None

    @field_validator("method")
    @classmethod
    def _valid_method(cls, v: str | None) -> str | None:
        if v is not None and v not in ("cash", "bank_transfer", "card", "gcash", "check", "other", "maya"):
            raise ValueError("Invalid payment method")
        return v


class CateringPaymentOut(BaseModel):
    id: UUID
    organization_id: UUID
    booking_id: UUID
    amount: float
    method: str
    reference: str | None = None
    paid_at: datetime
    notes: str | None = None
    proof_url: str | None = None
    proof_image_path: str | None = None
    verification_status: str = "pending"
    verified_by: UUID | None = None
    verified_at: datetime | None = None
    payment_date: datetime | None = None
    customer_reference: str | None = None
    created_at: datetime
    updated_at: datetime
    created_by: UUID | None = None
    updated_by: UUID | None = None
    deleted_at: datetime | None = None

    class Config:
        from_attributes = True


class CateringBillItemCreate(BaseModel):
    description: str = Field(min_length=1)
    quantity: int = Field(default=1, ge=0)
    unit_price: float = Field(default=0, ge=0)

    @field_validator("description")
    @classmethod
    def _strip_desc(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Description must not be blank")
        return v


class CateringBillItemUpdate(BaseModel):
    description: str | None = Field(default=None, min_length=1)
    quantity: int | None = Field(default=None, ge=0)
    unit_price: float | None = Field(default=None, ge=0)

    @field_validator("description")
    @classmethod
    def _strip_desc(cls, v: str | None) -> str | None:
        if v is None:
            return v
        v = v.strip()
        if not v:
            raise ValueError("Description must not be blank")
        return v


class CateringBillItemOut(BaseModel):
    id: UUID
    organization_id: UUID
    bill_id: UUID
    description: str
    quantity: int
    unit_price: float
    amount: float
    created_at: datetime
    updated_at: datetime
    created_by: UUID | None = None
    updated_by: UUID | None = None
    deleted_at: datetime | None = None

    class Config:
        from_attributes = True


class CateringBillCreate(BaseModel):
    booking_id: UUID
    issue_date: datetime
    due_date: datetime | None = None
    tax: float = Field(default=0, ge=0)
    discount: float = Field(default=0, ge=0)
    notes: str | None = None
    items: list[CateringBillItemCreate] = []


class CateringBillUpdate(BaseModel):
    issue_date: datetime | None = None
    due_date: datetime | None = None
    tax: float | None = Field(default=None, ge=0)
    discount: float | None = Field(default=None, ge=0)
    notes: str | None = None
    items: list[CateringBillItemCreate] | None = None


class CateringBillOut(BaseModel):
    id: UUID
    organization_id: UUID
    booking_id: UUID
    bill_number: str
    issue_date: datetime
    due_date: datetime | None = None
    subtotal: float
    tax: float
    discount: float
    total: float
    status: str
    notes: str | None = None
    created_at: datetime
    updated_at: datetime
    created_by: UUID | None = None
    updated_by: UUID | None = None
    deleted_at: datetime | None = None

    class Config:
        from_attributes = True


# =========================================================================
# Dashboard "needs attention" schemas.
#
# Groups are role-aware: the base groups (needs_quotation, awaiting_customer,
# happening_soon, deliveries) are shared by staff, manager, administrator, and
# viewer; manager/administrator additionally receive pending_approval,
# missing_resources, balance_due, and overdue_bills. Each group carries an
# ``actionable`` flag so the frontend can render items read-only for roles
# that can only view.
# =========================================================================


class DashboardAttentionItem(BaseModel):
    kind: str
    reference: str
    title: str
    subtitle: str | None = None
    at: datetime | None = None
    status: str | None = None
    meta: dict[str, Any] = {}


class DashboardAttentionGroup(BaseModel):
    key: str
    title: str
    icon: str | None = None
    description: str | None = None
    actionable: bool = True
    items: list[DashboardAttentionItem] = []
    total: int = 0


class DashboardAttentionOut(BaseModel):
    groups: list[DashboardAttentionGroup] = []


# ---- Booking requirements (pre-event checklist) ----

RequirementCategory = Literal["venue", "equipment", "other"]
RequirementStatus = Literal["pending", "done", "overdue"]


class BookingRequirementCreate(BaseModel):
    description: str = Field(min_length=1, max_length=255)
    category: RequirementCategory = "other"
    due_date: datetime | None = None


class BookingRequirementUpdate(BaseModel):
    description: str | None = Field(default=None, max_length=255)
    category: RequirementCategory | None = None
    due_date: datetime | None = None
    status: RequirementStatus | None = None

    @field_validator("description")
    @classmethod
    def _desc_not_blank(cls, v):
        if v is not None and not v.strip():
            raise ValueError("description must not be blank")
        return v


class BookingRequirementOut(BaseModel):
    id: UUID
    booking_id: UUID
    description: str
    category: RequirementCategory
    due_date: str | None = None
    status: RequirementStatus
    completed_by: UUID | None = None
    completed_at: str | None = None
    created_at: str | None = None
    # Booking context (populated on the cross-booking list)
    booking_reference: str | None = None
    customer_name: str | None = None
    event_date: str | None = None


class BookingRequirementListOut(BaseModel):
    items: list[BookingRequirementOut] = []
    total: int = 0


class DashboardStatsOut(BaseModel):
    total_inquiries: int = 0
    total_quotations: int = 0
    quotations_by_status: dict[str, int] = {}
    total_bookings: int = 0
    bookings_by_status: dict[str, int] = {}
    total_revenue: float = 0.0
    upcoming_bookings_30d: int = 0


class DashboardActivityItem(BaseModel):
    id: UUID
    entity_type: str
    entity_reference: str | None = None
    action: str
    actor_email: str | None = None
    actor_role: str | None = None
    summary: str | None = None
    created_at: datetime


class DashboardActivityOut(BaseModel):
    items: list[DashboardActivityItem] = []


# =========================================================================
# Public customer portal schemas.
#
# The customer portal is a capability-based, reference-driven public surface:
# each inquiry, quotation, and booking is addressed by a non-guessable
# reference (the record's UUIDv4 rendered as "INQ-<uuid>" / "QUO-<uuid>" /
# "BK-<uuid>"). No internal ids, organization ids, audit fields, or staff
# data are ever exposed to customers.
# =========================================================================


def _fmt_reference(prefix: str, record_id: UUID | None) -> str:
    return f"{prefix}-{record_id}" if record_id else ""


class CustomerPackageOut(BaseModel):
    id: UUID
    name: str
    description: str | None = None
    base_price: float
    pricing_method: str = "per_guest"
    has_customization: bool = False
    min_pax: int | None = None
    max_pax: int | None = None
    service_style: str | None = None
    dish_names: list[str] = []


class CustomerPackageItemOut(BaseModel):
    item_id: UUID
    name: str
    quantity: int
    unit: str
    available: bool


class CustomerPackageGroupOut(BaseModel):
    id: UUID
    name: str
    min_select: int
    max_select: int
    options: list[CustomerPackageItemOut] = []


class CustomerDerivedRatioOut(BaseModel):
    item_key: str
    per_guests: int
    minimum: int


class CustomerCatalogItemOut(BaseModel):
    id: UUID
    name: str
    category: str | None = None
    price: float
    pricing_unit: str
    item_type: str


class CustomerCatalogOut(BaseModel):
    dishes: list[CustomerCatalogItemOut] = []
    equipment: list[CustomerCatalogItemOut] = []
    staff: list[CustomerCatalogItemOut] = []


class CustomerPackageDetailOut(BaseModel):
    id: UUID
    name: str
    description: str | None = None
    base_price: float
    pricing_method: str
    has_customization: bool
    min_pax: int | None = None
    max_pax: int | None = None
    service_style: str | None = None
    default_items: list[CustomerPackageItemOut] = []
    included_items: list[CustomerPackageItemOut] = []
    groups: list[CustomerPackageGroupOut] = []
    derived_ratios: list[CustomerDerivedRatioOut] = []


class CustomerItemIn(BaseModel):
    menu_item_id: UUID
    quantity: int = Field(default=1, ge=1)
    unit: str = Field(default="serving", min_length=1)
    group_name: str | None = None


class CustomerItemOut(BaseModel):
    name: str
    category: str | None = None
    group_name: str | None = None
    quantity: int
    unit: str
    kind: str


class AddonSelectionIn(BaseModel):
    catalog_item_id: UUID
    quantity: int = Field(default=1, ge=1, le=500)


class CustomerAddonLineOut(BaseModel):
    name: str
    item_type: str
    quantity: int
    pricing_unit: str
    line_total: float


class CustomerResendLinkRequest(BaseModel):
    """Body for POST /public/inquiries/resend-link — email recovery for lost links."""

    email: str = Field(min_length=1)

    @field_validator("email")
    @classmethod
    def _valid_email(cls, v: str) -> str:
        v = v.strip()
        if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", v):
            raise ValueError("Enter a valid email address")
        return v.lower()


class CustomerInquirySubmit(BaseModel):
    customer_name: str = Field(min_length=1)
    customer_contact: str = Field(min_length=1)
    customer_email: str = Field(min_length=1)
    event_date: datetime
    event_time: time | None = None
    event_type: str | None = None
    event_address: str = Field(min_length=1)
    venue_name: str | None = None
    venue_mode: str | None = None
    selected_venue_id: UUID | None = None
    venue_fee: float = Field(default=0, ge=0)
    location_floor: str | None = None
    room_hall: str | None = None
    landmark: str | None = None
    delivery_instructions: str | None = None
    guest_count: int = Field(ge=1, le=5000)
    event_duration_hours: float | None = Field(default=None, ge=0.5, le=24)
    catering_package_id: UUID | None = None
    package_mode: str | None = None
    service_style: str | None = None
    food_requirements: list[FoodRequirementIn] = []
    staff: StaffingRequestIn | None = None
    items: list[CustomerItemIn] = []
    selected_catalog_ids: list[UUID] = []
    addon_catalog_ids: list[AddonSelectionIn] = []
    requested_service_style: str | None = None
    estimated_total: float | None = None
    notes: str | None = None
    additional_notes: str | None = None
    dietary_notes: str | None = None
    setup_notes: str | None = None

    @field_validator("customer_name", "customer_contact", "customer_email", "event_address")
    @classmethod
    def _strip_text(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Field must not be blank")
        return v

    @field_validator("customer_contact")
    @classmethod
    def _valid_contact(cls, v: str) -> str:
        if not re.fullmatch(r"(09\d{9}|\+639\d{9})", v):
            raise ValueError("Enter a valid contact number (09XXXXXXXXX or +639XXXXXXXXX)")
        return v

    @field_validator("customer_email")
    @classmethod
    def _valid_email(cls, v: str) -> str:
        if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", v):
            raise ValueError("Enter a valid email address")
        return v

    @field_validator("venue_name", "location_floor", "room_hall", "landmark", "delivery_instructions")
    @classmethod
    def _strip_optional_text(cls, v: str | None) -> str | None:
        if v is None:
            return v
        v = v.strip()
        return v or None

    @field_validator("event_date")
    @classmethod
    def _not_past(cls, v: datetime) -> datetime:
        return _validate_not_past(v)

    @field_validator("package_mode")
    @classmethod
    def _valid_mode(cls, v: str | None) -> str | None:
        if v is not None and v not in ("default", "custom"):
            raise ValueError("Invalid package mode")
        return v

    @field_validator("venue_mode")
    @classmethod
    def _valid_venue_mode(cls, v: str | None) -> str | None:
        if v is not None and v not in ("own", "need"):
            raise ValueError("Invalid venue mode")
        return v

    @field_validator("requested_service_style")
    @classmethod
    def _valid_requested_style(cls, v: str | None) -> str | None:
        if v is not None and v not in ("buffet", "plated", "cocktail", "banquet"):
            raise ValueError("Invalid service style")
        return v


class CustomerInquiryCreatedOut(BaseModel):
    reference: str
    access_token: str
    created_at: datetime


class InquiryReviewRejectIn(BaseModel):
    reason: str | None = None


class CustomerInquirySummary(BaseModel):
    reference: str
    customer_name: str
    event_date: datetime
    event_time: time | None = None
    event_type: str | None = None
    event_address: str | None = None
    venue_name: str | None = None
    venue_mode: str | None = None
    location_floor: str | None = None
    room_hall: str | None = None
    landmark: str | None = None
    delivery_instructions: str | None = None
    guest_count: int
    event_duration_hours: float | None = None
    package_name: str | None = None
    package_mode: str | None = None
    items: list[CustomerItemOut] = []
    addons: list[CustomerAddonLineOut] = []
    food_requirements: list[FoodRequirementOut] = []
    staffing: StaffingOut | None = None
    notes: str | None = None
    estimated_total: float | None = None
    venue_fee: float = 0
    status: str
    review_status: str = "auto_approved"
    review_reason: str | None = None
    created_at: datetime


class CustomerQuotationOut(BaseModel):
    reference: str
    inquiry_reference: str
    guest_count: int
    total_price: float
    pricing_method: str | None = None
    package_name: str | None = None
    package_description: str | None = None
    event_date: datetime | None = None
    event_time: time | None = None
    event_type: str | None = None
    event_address: str | None = None
    venue_name: str | None = None
    location_floor: str | None = None
    room_hall: str | None = None
    landmark: str | None = None
    delivery_instructions: str | None = None
    items: list[CustomerItemOut] = []
    addons: list[CustomerAddonLineOut] = []
    derived_inclusions: list[DerivedInclusionOut] = []
    service_style: str | None = None
    requested_service_style: str | None = None
    package_base_price: float | None = None
    food_requirements: list[FoodRequirementOut] = []
    staffing: StaffingOut | None = None
    status: str
    valid_until: datetime | None = None
    created_at: datetime
    updated_at: datetime | None = None


class CustomerBookingOut(BaseModel):
    reference: str
    event_date: datetime
    event_location: str | None = None
    event_time: time | None = None
    guest_count: int
    total_amount: float
    status: str
    service_style: str | None = None
    coordinator_name: str | None = None
    coordinator_contact: str | None = None
    created_at: datetime


class CustomerQuotationAcceptIn(BaseModel):
    version: str | None = None


class CustomerBookingBillingOut(BaseModel):
    total_amount: float
    amount_paid: float = 0
    remaining_balance: float = 0
    payment_status: str
    status: str


class CustomerBillingCodeRequestOut(BaseModel):
    message: str
    masked_email: str


class CustomerBillingVerifyOut(BaseModel):
    token: str
    expires_in: int


class CustomerStatusOut(BaseModel):
    inquiry: CustomerInquirySummary
    quotation: CustomerQuotationOut | None = None
    booking: CustomerBookingOut | None = None


# =========================================================================
# Public venue catalog.
# =========================================================================

class CustomerVenueOut(BaseModel):
    id: UUID
    name: str
    capacity: int
    fee: float
    description: str | None = None
    address: str | None = None
    parking_capacity: int | None = None
    status: str = "active"
    available: bool | None = None


# =========================================================================
# Admin venue CRUD.
# =========================================================================

class VenueCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    capacity: int = Field(ge=0)
    fee: float = Field(ge=0)
    description: str | None = None
    address: str | None = None
    parking_capacity: int | None = None
    status: str = "active"

    @field_validator("status")
    @classmethod
    def _valid_status(cls, v: str) -> str:
        if v not in ("active", "inactive"):
            raise ValueError("Status must be 'active' or 'inactive'")
        return v


class VenueUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    capacity: int | None = Field(default=None, ge=0)
    fee: float | None = Field(default=None, ge=0)
    description: str | None = None
    address: str | None = None
    parking_capacity: int | None = None
    status: str | None = None

    @field_validator("status")
    @classmethod
    def _valid_status(cls, v: str | None) -> str | None:
        if v is not None and v not in ("active", "inactive"):
            raise ValueError("Status must be 'active' or 'inactive'")
        return v


class VenueOut(BaseModel):
    id: UUID
    organization_id: UUID
    name: str
    capacity: int
    fee: float
    description: str | None = None
    address: str | None = None
    parking_capacity: int | None = None
    status: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
    created_by: UUID | None = None
    updated_by: UUID | None = None


# =========================================================================
# Public payment submission.
# =========================================================================

class CustomerPaymentSubmit(BaseModel):
    method: str = Field(min_length=1)
    amount: float = Field(gt=0)
    payment_date: datetime | None = None
    customer_reference: str | None = None
    notes: str | None = None

    @field_validator("method")
    @classmethod
    def _valid_method(cls, v: str) -> str:
        v = v.strip().lower()
        if v not in ("gcash", "maya", "bank_transfer", "cash"):
            raise ValueError("Invalid payment method")
        return v

    @field_validator("customer_reference")
    @classmethod
    def _strip_ref(cls, v: str | None) -> str | None:
        if v is None:
            return None
        v = v.strip()
        return v or None

    @field_validator("notes")
    @classmethod
    def _strip_notes(cls, v: str | None) -> str | None:
        if v is None:
            return None
        v = v.strip()
        return v or None


class CustomerPaymentOut(BaseModel):
    id: UUID
    amount: float
    method: str
    customer_reference: str | None = None
    payment_date: datetime | None = None
    verified: bool = False
    proof_url: str | None = None
    created_at: datetime

    class Config:
        from_attributes = True


# =========================================================================
# Public cancellation.
# =========================================================================

class CustomerCancellationOut(BaseModel):
    message: str
    status: str
