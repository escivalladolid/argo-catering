from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from app.routers import (
    auth_router,
    packages,
    venues,
    inquiries,
    quotations,
    bookings,
    menus,
    guest_counts,
    food_requirements,
    staffing,
    equipment,
    deliveries,
    payments,
    billing,
    public_portal,
    audit_log,
    users,
    dashboard,
)

from app.config import get_settings
from app.email_service import EmailService
import app.email_service as _email_svc_mod

app = FastAPI(
    title="Catering Management System",
    description="Backend API for the Catering Management module",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_email_svc_mod.email_service = EmailService(get_settings())

app.include_router(auth_router.router)
app.include_router(packages.router)
app.include_router(venues.router)
app.include_router(inquiries.router)
app.include_router(quotations.router)
app.include_router(bookings.router)
app.include_router(menus.router)
app.include_router(guest_counts.router)
app.include_router(food_requirements.router)
app.include_router(staffing.staff_router)
app.include_router(staffing.assignment_router)
app.include_router(equipment.equipment_router)
app.include_router(equipment.assignment_router)
app.include_router(deliveries.router)
app.include_router(payments.router)
app.include_router(billing.router)
app.include_router(public_portal.router)
app.include_router(audit_log.router)
app.include_router(users.router)
app.include_router(dashboard.router)


@app.get("/")
def root():
    return {"message": "Catering Management System API"}

@app.get("/app", response_class=HTMLResponse)
def serve_app():
    html_path = Path(__file__).parent.parent / "catering-mockup.html"
    return HTMLResponse(content=html_path.read_text(encoding="utf-8"))

@app.get("/customer", response_class=HTMLResponse)
def serve_customer_portal():
    html_path = Path(__file__).parent.parent / "customer-portal.html"
    return HTMLResponse(content=html_path.read_text(encoding="utf-8"))

@app.get("/customer-portal.html", response_class=HTMLResponse)
def serve_customer_portal_file_alias():
    """Alias matching the exact path used in emailed tracking links
    (PUBLIC_BASE_URL + /customer-portal.html?ref=...&token=...)."""
    return serve_customer_portal()

# Mount uploads directory for serving payment proofs and other files
uploads_dir = Path(__file__).parent.parent / "uploads"
uploads_dir.mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=str(uploads_dir)), name="uploads")
