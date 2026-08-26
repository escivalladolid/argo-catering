import uuid
from datetime import date, datetime, time, timezone

from sqlalchemy import Date, String, Numeric, Integer, DateTime, Time, Boolean, ForeignKey, UniqueConstraint, Text, CheckConstraint, Index, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def utcnow():
    return datetime.now(timezone.utc)


class OrganizationStub(Base):
    __tablename__ = "organizations"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)


class UserStub(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    role: Mapped[str] = mapped_column(String(50), nullable=False, default="viewer")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    organization_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), nullable=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class CateringPackage(Base):
    __tablename__ = "catering_packages"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    base_price: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, comment="All-inclusive rate covering food, service, and taxes")
    pricing_method: Mapped[str] = mapped_column(String(20), nullable=False, default="per_guest")
    has_customization: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    min_pax: Mapped[int | None] = mapped_column(Integer, nullable=True)
    max_pax: Mapped[int | None] = mapped_column(Integer, nullable=True)
    service_style: Mapped[str | None] = mapped_column(String(20), nullable=True, comment="buffet, plated, cocktail, or banquet")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)
    created_by: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    updated_by: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    groups: Mapped[list["CateringPackageGroup"]] = relationship(back_populates="package", cascade="all, delete-orphan", order_by="CateringPackageGroup.sort_order")
    items: Mapped[list["CateringPackageItem"]] = relationship(back_populates="package", cascade="all, delete-orphan", order_by="CateringPackageItem.sort_order")
    derived_ratios: Mapped[list["PackageDerivedRatio"]] = relationship(back_populates="package", cascade="all, delete-orphan", order_by="PackageDerivedRatio.item_key")

    __table_args__ = (
        Index("uq_package_org_name", "organization_id", "name", unique=True, postgresql_where=text("deleted_at IS NULL"), sqlite_where=text("deleted_at IS NULL")),
        CheckConstraint("pricing_method IN ('per_guest', 'fixed')", name="ck_packages_pricing_method"),
        CheckConstraint("service_style IS NULL OR service_style IN ('buffet', 'plated', 'cocktail', 'banquet')", name="ck_packages_service_style"),
    )


class CateringPackageGroup(Base):
    __tablename__ = "catering_package_groups"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    package_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("catering_packages.id", ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    min_select: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    max_select: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)
    created_by: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    updated_by: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    package: Mapped["CateringPackage"] = relationship(back_populates="groups")
    options: Mapped[list["CateringPackageItem"]] = relationship(back_populates="group", order_by="CateringPackageItem.sort_order")

    __table_args__ = (
        CheckConstraint("min_select >= 0 AND max_select >= min_select", name="ck_package_groups_select_bounds"),
    )


class CateringPackageItem(Base):
    __tablename__ = "catering_package_items"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    package_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("catering_packages.id", ondelete="CASCADE"), nullable=False, index=True)
    menu_item_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("catering_menu_items.id", ondelete="CASCADE"), nullable=False, index=True)
    kind: Mapped[str] = mapped_column(String(20), nullable=False, default="included")
    group_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("catering_package_groups.id", ondelete="SET NULL"), nullable=True, index=True)
    quantity: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    unit: Mapped[str] = mapped_column(String(30), nullable=False, default="serving")
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)
    created_by: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    updated_by: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    package: Mapped["CateringPackage"] = relationship(back_populates="items")
    group: Mapped["CateringPackageGroup | None"] = relationship(back_populates="options")
    menu_item: Mapped["CateringMenuItem | None"] = relationship()

    @property
    def item_name(self) -> str | None:
        return self.menu_item.name if self.menu_item else None

    __table_args__ = (
        CheckConstraint("kind IN ('included', 'default', 'option')", name="ck_package_items_kind"),
        CheckConstraint("quantity > 0", name="ck_package_items_quantity_pos"),
    )


class PackageDerivedRatio(Base):
    __tablename__ = "package_derived_ratios"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    package_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("catering_packages.id", ondelete="CASCADE"), nullable=False, index=True)
    item_key: Mapped[str] = mapped_column(String(50), nullable=False)
    per_guests: Mapped[int] = mapped_column(Integer, nullable=False)
    minimum: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)
    created_by: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    updated_by: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    package: Mapped["CateringPackage"] = relationship(back_populates="derived_ratios")

    __table_args__ = (
        Index("uq_derived_ratio_pkg_key", "package_id", "item_key", unique=True, postgresql_where=text("deleted_at IS NULL"), sqlite_where=text("deleted_at IS NULL")),
        CheckConstraint("per_guests > 0", name="ck_derived_ratio_per_guests_pos"),
        CheckConstraint("minimum >= 0", name="ck_derived_ratio_minimum_nonneg"),
    )


class CateringVenue(Base):
    __tablename__ = "catering_venues"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    capacity: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    fee: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0, comment="All-inclusive flat rental fee covering venue, setup, and taxes")
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    address: Mapped[str | None] = mapped_column(Text, nullable=True)
    parking_capacity: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)
    created_by: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    updated_by: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("uq_venue_org_name", "organization_id", "name", unique=True, postgresql_where=text("deleted_at IS NULL"), sqlite_where=text("deleted_at IS NULL")),
        CheckConstraint("capacity >= 0", name="ck_venues_capacity_nonneg"),
        CheckConstraint("fee >= 0", name="ck_venues_fee_nonneg"),
        CheckConstraint("status IN ('active', 'inactive')", name="ck_venues_status"),
    )


class VenueBooking(Base):
    __tablename__ = "venue_bookings"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    venue_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("catering_venues.id", ondelete="CASCADE"), nullable=False, index=True)
    inquiry_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("catering_inquiries.id", ondelete="CASCADE"), nullable=False, unique=True)
    event_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("uq_venue_booking_date", "venue_id", "event_date", unique=True, postgresql_where=text("deleted_at IS NULL"), sqlite_where=text("deleted_at IS NULL")),
    )


class CateringInquiry(Base):
    __tablename__ = "catering_inquiries"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    customer_name: Mapped[str] = mapped_column(String(255), nullable=False)
    customer_contact: Mapped[str] = mapped_column(String(255), nullable=False)
    customer_email: Mapped[str] = mapped_column(String(255), nullable=False)
    access_token: Mapped[str] = mapped_column(String(64), nullable=False, index=True, comment="Secret token for public status/write access")
    short_reference: Mapped[str | None] = mapped_column(String(20), nullable=True, unique=True, index=True, comment="Human-friendly reference e.g. INQ-2026-4837")
    event_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    event_time: Mapped[time | None] = mapped_column(Time(timezone=False), nullable=True)
    event_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    event_address: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    venue_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    venue_mode: Mapped[str | None] = mapped_column(String(20), nullable=True)
    selected_venue_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("catering_venues.id", ondelete="SET NULL"), nullable=True, index=True)
    venue_fee: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    location_floor: Mapped[str | None] = mapped_column(String(100), nullable=True)
    room_hall: Mapped[str | None] = mapped_column(String(255), nullable=True)
    landmark: Mapped[str | None] = mapped_column(String(255), nullable=True)
    delivery_instructions: Mapped[str | None] = mapped_column(Text, nullable=True)
    guest_count: Mapped[int] = mapped_column(Integer, nullable=False)
    event_duration_hours: Mapped[float | None] = mapped_column(Numeric(4, 1), nullable=True, comment="Customer-specified event duration in hours")
    catering_package_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("catering_packages.id", ondelete="SET NULL"), nullable=True, index=True)
    package_mode: Mapped[str | None] = mapped_column(String(20), nullable=True)
    service_style: Mapped[str | None] = mapped_column(String(20), nullable=True, comment="Set from package for premade, from customer for custom")
    requested_service_style: Mapped[str | None] = mapped_column(String(20), nullable=True, comment="Customer-requested override of package default service style")
    food_requirements_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    waiter_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    bartender_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    chef_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    kitchen_staff_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    support_crew_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    flag_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    additional_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    dietary_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    setup_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    estimated_total: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    server_calculated_total: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    price_mismatch: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    selected_catalog_ids: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="new")
    review_status: Mapped[str] = mapped_column(String(20), nullable=False, default="auto_approved", server_default="auto_approved")
    review_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)
    created_by: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    updated_by: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    package: Mapped["CateringPackage | None"] = relationship()
    selected_venue: Mapped["CateringVenue | None"] = relationship()
    quotations: Mapped[list["CateringQuotation"]] = relationship(back_populates="inquiry", cascade="all, delete-orphan")
    items: Mapped[list["CateringInquiryItem"]] = relationship(back_populates="inquiry", cascade="all, delete-orphan", order_by="CateringInquiryItem.sort_order")

    __table_args__ = (
        CheckConstraint("package_mode IS NULL OR package_mode IN ('default', 'custom')", name="ck_inquiries_package_mode"),
        CheckConstraint("venue_mode IS NULL OR venue_mode IN ('own', 'need')", name="ck_inquiries_venue_mode"),
        CheckConstraint("service_style IS NULL OR service_style IN ('buffet', 'plated', 'cocktail', 'banquet')", name="ck_inquiries_service_style"),
        CheckConstraint("waiter_count >= 0 AND bartender_count >= 0 AND chef_count >= 0 AND kitchen_staff_count >= 0 AND support_crew_count >= 0", name="ck_inquiries_staff_counts_nonneg"),
    )


class CateringInquiryItem(Base):
    __tablename__ = "catering_inquiry_items"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    inquiry_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("catering_inquiries.id", ondelete="CASCADE"), nullable=False, index=True)
    menu_item_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("catering_menu_items.id", ondelete="SET NULL"), nullable=True, index=True)
    catalog_item_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True, index=True, comment="Original dish/equipment/staff catalog UUID for customer-added extras")
    item_name: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[str | None] = mapped_column(String(50), nullable=True)
    group_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    kind: Mapped[str] = mapped_column(String(20), nullable=False, default="default")
    quantity: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    unit: Mapped[str] = mapped_column(String(30), nullable=False, default="serving")
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)
    created_by: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    updated_by: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    inquiry: Mapped["CateringInquiry"] = relationship(back_populates="items")

    __table_args__ = (
        CheckConstraint("kind IN ('default', 'custom', 'included', 'addon')", name="ck_inquiry_items_kind"),
        CheckConstraint("quantity > 0", name="ck_inquiry_items_quantity_pos"),
    )


class CateringQuotation(Base):
    __tablename__ = "catering_quotations"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    inquiry_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("catering_inquiries.id", ondelete="CASCADE"), nullable=False, index=True)
    catering_package_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("catering_packages.id", ondelete="SET NULL"), nullable=True)
    guest_count: Mapped[int] = mapped_column(Integer, nullable=False)
    total_price: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="draft")
    valid_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)
    created_by: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    updated_by: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    inquiry: Mapped["CateringInquiry"] = relationship(back_populates="quotations")
    booking: Mapped["CateringBooking | None"] = relationship(back_populates="quotation", uselist=False)


class CateringBooking(Base):
    __tablename__ = "catering_bookings"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    quotation_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("catering_quotations.id", ondelete="CASCADE"), nullable=False, unique=True)
    event_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    event_location: Mapped[str | None] = mapped_column(Text, nullable=True)
    event_time: Mapped[time | None] = mapped_column(Time(timezone=False), nullable=True)
    guest_count: Mapped[int] = mapped_column(Integer, nullable=False)
    total_amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    payment_status: Mapped[str] = mapped_column(String(50), nullable=False, default="unpaid")
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="pending")
    coordinator_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    coordinator_contact: Mapped[str | None] = mapped_column(String(255), nullable=True)
    service_style: Mapped[str | None] = mapped_column(String(20), nullable=True, comment="Denormalized from package at booking creation")
    event_duration_hours: Mapped[float | None] = mapped_column(Numeric(4, 1), nullable=True, comment="Event duration in hours from inquiry")
    selected_venue_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("catering_venues.id", ondelete="SET NULL"), nullable=True, index=True)
    additional_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    dietary_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    setup_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)
    created_by: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    updated_by: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    quotation: Mapped["CateringQuotation"] = relationship(back_populates="booking")
    selected_venue: Mapped["CateringVenue | None"] = relationship()

    __table_args__ = (
        CheckConstraint("service_style IS NULL OR service_style IN ('buffet', 'plated', 'cocktail', 'banquet')", name="ck_bookings_service_style"),
    )


class BookingRequirement(Base):
    __tablename__ = "booking_requirements"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    booking_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("catering_bookings.id", ondelete="CASCADE"), nullable=False, index=True)
    description: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[str] = mapped_column(String(20), nullable=False, default="other")
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    completed_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)
    created_by: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    updated_by: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    booking: Mapped["CateringBooking"] = relationship()

    __table_args__ = (
        CheckConstraint("category IN ('venue', 'equipment', 'other')", name="ck_booking_requirements_category"),
        CheckConstraint("status IN ('pending', 'done', 'overdue')", name="ck_booking_requirements_status"),
        Index("ix_booking_requirements_org_status", "organization_id", "status"),
    )


class CateringMenu(Base):
    __tablename__ = "catering_menus"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    category: Mapped[str] = mapped_column(String(50), nullable=False, default="lunch")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)
    created_by: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    updated_by: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    item_count: int = 0

    items: Mapped[list["CateringMenuItem"]] = relationship(back_populates="menu", cascade="all, delete-orphan")

    __table_args__ = (
        Index("uq_menu_org_name", "organization_id", "name", unique=True, postgresql_where=text("deleted_at IS NULL"), sqlite_where=text("deleted_at IS NULL")),
        CheckConstraint("category IN ('lunch', 'dinner', 'breakfast', 'cocktail', 'custom')", name="ck_menus_category"),
    )


class CateringMenuItem(Base):
    __tablename__ = "catering_menu_items"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    menu_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("catering_menus.id", ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    category: Mapped[str] = mapped_column(String(50), nullable=False, default="main")
    dietary_tags: Mapped[str | None] = mapped_column(String(255), nullable=True)
    price: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    pricing_unit: Mapped[str] = mapped_column(String(20), nullable=False, default="per_guest")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_test_data: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=text("false"), comment="Seeded by automated tests; excluded from customer-facing reads")
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)
    created_by: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    updated_by: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    menu: Mapped["CateringMenu"] = relationship(back_populates="items")

    __table_args__ = (
        Index("uq_menu_item_name", "menu_id", "name", unique=True, postgresql_where=text("deleted_at IS NULL"), sqlite_where=text("deleted_at IS NULL")),
        CheckConstraint("category IN ('starter', 'main', 'dessert', 'beverage', 'other')", name="ck_menu_items_category"),
        CheckConstraint("price >= 0", name="ck_menu_items_price_nonneg"),
        CheckConstraint("pricing_unit IN ('per_guest', 'flat')", name="ck_menu_items_pricing_unit"),
    )


class CateringGuestCount(Base):
    __tablename__ = "catering_guest_counts"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    booking_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("catering_bookings.id", ondelete="CASCADE"), nullable=False, index=True)
    count_type: Mapped[str] = mapped_column(String(30), nullable=False, default="estimated")
    count: Mapped[int] = mapped_column(Integer, nullable=False)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)
    created_by: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    updated_by: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        CheckConstraint("count >= 1", name="ck_guest_counts_count_pos"),
        CheckConstraint("count_type IN ('estimated', 'guaranteed', 'actual')", name="ck_guest_counts_type"),
    )


class CateringFoodRequirement(Base):
    __tablename__ = "catering_food_requirements"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    booking_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("catering_bookings.id", ondelete="CASCADE"), nullable=False, index=True)
    requirement_type: Mapped[str] = mapped_column(String(30), nullable=False, default="other")
    description: Mapped[str] = mapped_column(String(255), nullable=False)
    guest_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)
    created_by: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    updated_by: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        CheckConstraint("requirement_type IN ('vegetarian', 'vegan', 'halal', 'gluten_free', 'allergy', 'other')", name="ck_food_req_type"),
        CheckConstraint("guest_count IS NULL OR guest_count >= 1", name="ck_food_req_guest_count"),
    )


class CateringStaffMember(Base):
    __tablename__ = "catering_staff_members"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(30), nullable=False, default="server")
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    rate: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    pricing_unit: Mapped[str] = mapped_column(String(20), nullable=False, default="per_guest")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_test_data: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=text("false"), comment="Seeded by automated tests; excluded from customer-facing reads")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)
    created_by: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    updated_by: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("uq_staff_org_name", "organization_id", "name", unique=True, postgresql_where=text("deleted_at IS NULL"), sqlite_where=text("deleted_at IS NULL")),
        CheckConstraint("role IN ('chef', 'server', 'crew', 'supervisor', 'driver', 'bartender', 'kitchen_staff', 'support')", name="ck_staff_role"),
        CheckConstraint("rate >= 0", name="ck_staff_rate_nonneg"),
        CheckConstraint("pricing_unit IN ('per_guest', 'flat')", name="ck_staff_pricing_unit"),
    )


class CateringStaffAssignment(Base):
    __tablename__ = "catering_staff_assignments"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    booking_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("catering_bookings.id", ondelete="CASCADE"), nullable=False, index=True)
    staff_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("catering_staff_members.id", ondelete="CASCADE"), nullable=False, index=True)
    shift_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    shift_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    role: Mapped[str | None] = mapped_column(String(30), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)
    created_by: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    updated_by: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    staff: Mapped["CateringStaffMember"] = relationship()

    @property
    def staff_name(self) -> str | None:
        return self.staff.name if self.staff else None


class CateringEquipment(Base):
    __tablename__ = "catering_equipment"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[str] = mapped_column(String(30), nullable=False, default="kitchen")
    quantity: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    unit_cost: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    pricing_unit: Mapped[str] = mapped_column(String(20), nullable=False, default="flat")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_test_data: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=text("false"), comment="Seeded by automated tests; excluded from customer-facing reads")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)
    created_by: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    updated_by: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("uq_equipment_org_name", "organization_id", "name", unique=True, postgresql_where=text("deleted_at IS NULL"), sqlite_where=text("deleted_at IS NULL")),
        CheckConstraint("quantity >= 0", name="ck_equipment_quantity_nonneg"),
        CheckConstraint("unit_cost >= 0", name="ck_equipment_unit_cost_nonneg"),
        CheckConstraint("category IN ('kitchen', 'service', 'venue', 'transport', 'other')", name="ck_equipment_category"),
        CheckConstraint("pricing_unit IN ('per_guest', 'flat')", name="ck_equipment_pricing_unit"),
    )


class CateringEquipmentAssignment(Base):
    __tablename__ = "catering_equipment_assignments"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    booking_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("catering_bookings.id", ondelete="CASCADE"), nullable=False, index=True)
    equipment_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("catering_equipment.id", ondelete="CASCADE"), nullable=False, index=True)
    quantity: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)
    created_by: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    updated_by: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    equipment: Mapped["CateringEquipment"] = relationship()

    @property
    def equipment_name(self) -> str | None:
        return self.equipment.name if self.equipment else None

    __table_args__ = (
        CheckConstraint("quantity >= 1", name="ck_equip_assign_quantity_pos"),
    )


class CateringDelivery(Base):
    __tablename__ = "catering_deliveries"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    booking_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("catering_bookings.id", ondelete="CASCADE"), nullable=False, index=True)
    scheduled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    delivery_address: Mapped[str | None] = mapped_column(String(255), nullable=True)
    contact_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    contact_phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="scheduled")
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)
    created_by: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    updated_by: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        CheckConstraint("status IN ('scheduled', 'in_transit', 'delivered', 'delayed', 'cancelled')", name="ck_deliveries_status"),
    )


class CateringPayment(Base):
    __tablename__ = "catering_payments"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    booking_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("catering_bookings.id", ondelete="CASCADE"), nullable=False, index=True)
    amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    method: Mapped[str] = mapped_column(String(30), nullable=False, default="cash")
    reference: Mapped[str | None] = mapped_column(String(100), nullable=True)
    paid_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    payment_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    customer_reference: Mapped[str | None] = mapped_column(String(255), nullable=True)
    proof_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    proof_image_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    verification_status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    verified_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)
    created_by: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    updated_by: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        CheckConstraint("amount >= 0", name="ck_payments_amount_nonneg"),
        CheckConstraint("method IN ('cash', 'bank_transfer', 'card', 'gcash', 'check', 'other', 'maya')", name="ck_payments_method"),
        CheckConstraint("verification_status IN ('pending', 'approved', 'rejected')", name="ck_payments_verification_status"),
        Index("ix_payments_verification_status", "organization_id", "verification_status"),
    )


class CateringBill(Base):
    __tablename__ = "catering_bills"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    booking_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("catering_bookings.id", ondelete="CASCADE"), nullable=False, index=True)
    bill_number: Mapped[str] = mapped_column(String(50), nullable=False)
    issue_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    due_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    subtotal: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    tax: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    discount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    total: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="draft")
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)
    created_by: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    updated_by: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    items: Mapped[list["CateringBillItem"]] = relationship(back_populates="bill", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("organization_id", "bill_number", name="uq_bill_org_number"),
        CheckConstraint("status IN ('draft', 'sent', 'paid', 'overdue', 'void')", name="ck_bills_status"),
        CheckConstraint("subtotal >= 0 AND tax >= 0 AND discount >= 0 AND total >= 0", name="ck_bills_totals_nonneg"),
    )


class CateringBillItem(Base):
    __tablename__ = "catering_bill_items"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    bill_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("catering_bills.id", ondelete="CASCADE"), nullable=False, index=True)
    description: Mapped[str] = mapped_column(String(255), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    unit_price: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)
    created_by: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    updated_by: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    bill: Mapped["CateringBill"] = relationship(back_populates="items")

    __table_args__ = (
        CheckConstraint("quantity >= 0 AND unit_price >= 0 AND amount >= 0", name="ck_bill_items_nonneg"),
    )


class CateringAuditLog(Base):
    """Append-only audit trail for every mutation across the catering module.

    This is intentionally separate from the existing ``created_by`` /
    ``updated_by`` snapshot columns on each entity — those stay untouched.
    The audit log records status transitions and mutations over time so the
    activity log / booking history can show who did what and when.
    """

    __tablename__ = "catering_audit_log"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False)
    entity_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    entity_reference: Mapped[str | None] = mapped_column(String(255), nullable=True)
    action: Mapped[str] = mapped_column(String(50), nullable=False)
    actor_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    actor_role: Mapped[str | None] = mapped_column(String(50), nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow, index=True)

    __table_args__ = (
        Index("ix_audit_org_entity", "organization_id", "entity_type", "entity_id"),
    )


class CateringVerificationCode(Base):
    """One-time codes emailed to an admin to confirm sensitive actions.

    Only the hash of the code is stored; the plain code is never persisted.
    ``action`` embeds the target, e.g. ``reset_password:<target_user_id>``.
    """

    __tablename__ = "catering_verification_codes"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)
    reference_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    action: Mapped[str] = mapped_column(String(120), nullable=False)
    code_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("now()"))

    __table_args__ = (
        Index("ix_verification_codes_user_action", "user_id", "action"),
        Index("ix_verification_codes_reference_action", "reference_id", "action"),
    )
