"""Seed script: creates one organization, users for each role, and
reference data (menus with prices, packages with derived ratios,
staff with rates, equipment with pricing, and catalog items)
for the catering module.

Usage: venv\Scripts\python seed.py
"""
import uuid

from app.database import SessionLocal
from app.models.catering_models import (
    OrganizationStub,
    UserStub,
    CateringMenu,
    CateringMenuItem,
    CateringPackage,
    CateringPackageGroup,
    CateringPackageItem,
    CateringStaffMember,
    CateringEquipment,
    CateringVenue,
    PackageDerivedRatio,
)
from app.auth.auth import hash_password


def seed():
    db = SessionLocal()
    try:
        org = db.query(OrganizationStub).first()
        if not org:
            org_id = uuid.uuid4()
            org = OrganizationStub(id=org_id, name="Default Organization")
            db.add(org)
            db.flush()

            users = [
                UserStub(id=uuid.uuid4(), email="escivalladolid@gmail.com", hashed_password=hash_password("admin123"), role="administrator", organization_id=org_id),
                UserStub(id=uuid.uuid4(), email="manager@example.com", hashed_password=hash_password("manager123"), role="manager", organization_id=org_id),
                UserStub(id=uuid.uuid4(), email="staff@example.com", hashed_password=hash_password("staff123"), role="staff", organization_id=org_id),
                UserStub(id=uuid.uuid4(), email="viewer@example.com", hashed_password=hash_password("viewer123"), role="viewer", organization_id=org_id),
            ]
            for user in users:
                db.add(user)
            print("Seeded org_id=" + str(org_id))
            for user in users:
                print("  User: " + user.email + " / role=" + user.role)
        else:
            org_id = org.id
            print("Organization already exists; seeding reference data.")

        has_menu = db.query(CateringMenu).filter(CateringMenu.organization_id == org_id, CateringMenu.deleted_at.is_(None)).count() > 0
        has_staff = db.query(CateringStaffMember).filter(CateringStaffMember.organization_id == org_id, CateringStaffMember.deleted_at.is_(None)).count() > 0
        has_equip = db.query(CateringEquipment).filter(CateringEquipment.organization_id == org_id, CateringEquipment.deleted_at.is_(None)).count() > 0
        has_pkgs = db.query(CateringPackage).filter(CateringPackage.organization_id == org_id, CateringPackage.deleted_at.is_(None)).count() > 0

        if not has_menu:
            menu = CateringMenu(organization_id=org_id, name="Classic Filipino Buffet", category="lunch", is_active=True, description="Rice, viands, soup, dessert, and beverages.")
            db.add(menu)
            db.flush()
            menu_items_data = [
                ("Chicken BBQ", "main", "grilled", 60.00, "per_guest"),
                ("Beef Caldereta", "main", "spicy", 90.00, "per_guest"),
                ("Fish Fillet", "main", "", 80.00, "per_guest"),
                ("Pork Sisig", "main", "sizzling", 75.00, "per_guest"),
                ("Pancit Bihon", "main", "vegetarian", 40.00, "per_guest"),
                ("Steamed Rice", "main", "vegetarian", 15.00, "per_guest"),
                ("Lumpia Shanghai", "starter", "", 50.00, "per_guest"),
                ("Fresh Fruit Salad", "dessert", "vegetarian", 35.00, "per_guest"),
                ("Leche Flan", "dessert", "vegetarian", 30.00, "per_guest"),
                ("Iced Tea", "beverage", "vegetarian", 10.00, "per_guest"),
                ("Mineral Water", "beverage", "", 5.00, "per_guest"),
                ("Buko Juice", "beverage", "vegetarian", 15.00, "per_guest"),
            ]
            for name, category, tags, price, unit in menu_items_data:
                db.add(CateringMenuItem(
                    organization_id=org_id, menu_id=menu.id, name=name,
                    category=category, dietary_tags=tags or None,
                    price=price, pricing_unit=unit, is_active=True,
                ))
            db.flush()
            print("  Seeded menu: " + menu.name + " (" + str(len(menu_items_data)) + " items)")

        if not has_staff:
            staff_data = [
                ("Server (per guest)", "server", 500.00, "per_guest"),
                ("Bartender", "bartender", 800.00, "flat"),
                ("Chef", "chef", 1500.00, "flat"),
                ("Kitchen Staff", "kitchen_staff", 600.00, "flat"),
                ("Setup Crew", "support", 400.00, "flat"),
                ("Event Coordinator", "supervisor", 2000.00, "flat"),
            ]
            for name, role, rate, unit in staff_data:
                db.add(CateringStaffMember(
                    organization_id=org_id, name=name, role=role,
                    rate=rate, pricing_unit=unit, is_active=True,
                ))
            print("  Seeded " + str(len(staff_data)) + " staff members with rates")

        if not has_equip:
            equipment_data = [
                ("Chafing Dish", "kitchen", 150.00, "flat"),
                ("Buffet Table", "service", 200.00, "flat"),
                ("Round Table (10 pax)", "service", 100.00, "flat"),
                ("Chairs (set of 10)", "service", 80.00, "flat"),
                ("Plates & Utensils Set", "service", 20.00, "per_guest"),
                ("Glassware Set", "service", 15.00, "per_guest"),
            ]
            for name, category, cost, unit in equipment_data:
                db.add(CateringEquipment(
                    organization_id=org_id, name=name, category=category,
                    quantity=10, unit_cost=cost, pricing_unit=unit, is_active=True,
                ))
            print("  Seeded " + str(len(equipment_data)) + " equipment items with pricing")

        if not has_pkgs:
            mi_lookup = {
                mi.name: mi.id for mi in
                db.query(CateringMenuItem).filter(
                    CateringMenuItem.organization_id == org_id,
                    CateringMenuItem.deleted_at.is_(None),
                ).all()
            }

            packages_def = [
                {
                    "name": "Basic",
                    "desc": "Essential catering for small to medium events. Includes a selection of viands, rice, dessert, and beverages with basic service staff.",
                    "price": 350,
                    "min": 30,
                    "max": 100,
                    "service_style": "buffet",
                    "dishes": ["Chicken BBQ", "Pancit Bihon", "Steamed Rice", "Fresh Fruit Salad", "Iced Tea"],
                    "ratios": [("chafing_dish", 25, 2), ("table", 10, 1), ("server", 20, 2), ("setup_staff", 40, 1)],
                },
                {
                    "name": "Standard",
                    "desc": "Our most popular package. More viands, upgraded service, and dedicated event coordination for a memorable experience.",
                    "price": 550,
                    "min": 50,
                    "max": 200,
                    "service_style": "buffet",
                    "dishes": ["Chicken BBQ", "Beef Caldereta", "Fish Fillet", "Pancit Bihon", "Steamed Rice", "Lumpia Shanghai", "Fresh Fruit Salad", "Leche Flan", "Iced Tea", "Buko Juice"],
                    "ratios": [("chafing_dish", 20, 3), ("table", 8, 2), ("server", 15, 3), ("setup_staff", 30, 2)],
                },
                {
                    "name": "Premium",
                    "desc": "Full-service premium catering. Extensive menu, professional staff, and complete event management for grand celebrations.",
                    "price": 800,
                    "min": 80,
                    "max": 500,
                    "service_style": "buffet",
                    "dishes": ["Chicken BBQ", "Beef Caldereta", "Fish Fillet", "Pork Sisig", "Pancit Bihon", "Steamed Rice", "Lumpia Shanghai", "Fresh Fruit Salad", "Leche Flan", "Iced Tea", "Mineral Water", "Buko Juice"],
                    "ratios": [("chafing_dish", 15, 4), ("table", 8, 3), ("server", 12, 4), ("setup_staff", 25, 2)],
                },
            ]

            for pdef in packages_def:
                pkg_id = uuid.uuid4()
                pkg = CateringPackage(
                    id=pkg_id, organization_id=org_id, name=pdef["name"],
                    description=pdef["desc"], base_price=pdef["price"],
                    pricing_method="per_guest", has_customization=False,
                    min_pax=pdef["min"], max_pax=pdef["max"],
                    service_style=pdef.get("service_style"), is_active=True,
                )
                db.add(pkg)
                db.flush()

                for i, dish_name in enumerate(pdef["dishes"]):
                    mi_id = mi_lookup.get(dish_name)
                    if mi_id:
                        db.add(CateringPackageItem(
                            organization_id=org_id, package_id=pkg_id,
                            menu_item_id=mi_id, kind="included",
                            quantity=1, unit="serving", sort_order=i,
                        ))

                for item_key, per_guests, minimum in pdef["ratios"]:
                    db.add(PackageDerivedRatio(
                        organization_id=org_id, package_id=pkg_id,
                        item_key=item_key, per_guests=per_guests, minimum=minimum,
                    ))

                db.flush()

            print("  Seeded " + str(len(packages_def)) + " premade packages with items and derived ratios")

        if not db.query(CateringVenue).filter(CateringVenue.organization_id == org_id, CateringVenue.deleted_at.is_(None)).first():
            venues_def = [
                {"name": "Garden Pavilion", "capacity": 80, "fee": 15000, "description": "Open-air garden venue with lush greenery and ambient lighting", "address": "12 Garden Ave, Quezon City"},
                {"name": "Poolside Function Hall", "capacity": 120, "fee": 25000, "description": "Indoor-outdoor venue beside the pool, ideal for cocktail receptions", "address": "45 Resort Drive, Taguig"},
                {"name": "Grand Events Hall", "capacity": 250, "fee": 45000, "description": "Spacious air-conditioned hall for large celebrations and corporate events", "address": "100 Events Blvd, Makati"},
                {"name": "Rooftop Lounge", "capacity": 60, "fee": 20000, "description": "Intimate rooftop space with city views, best for evening events", "address": "88 Sky Tower, BGC, Taguig"},
            ]
            for vdef in venues_def:
                db.add(CateringVenue(
                    organization_id=org_id,
                    name=vdef["name"],
                    capacity=vdef["capacity"],
                    fee=vdef["fee"],
                    description=vdef["description"],
                    address=vdef["address"],
                    status="active",
                    is_active=True,
                ))
            db.flush()
            print("  Seeded " + str(len(venues_def)) + " venues")
        else:
            print("  Venues already exist, skipping")

        db.commit()
        print("Done.")
    except Exception as e:
        db.rollback()
        print("ERROR: " + str(e))
        import traceback
        traceback.print_exc()
    finally:
        db.close()


if __name__ == "__main__":
    seed()
