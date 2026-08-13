from datetime import date

from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db
from app import models
from app.dependencies import require_login

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/dashboard", response_class=HTMLResponse)
def user_dashboard(request: Request, user=Depends(require_login), db: Session = Depends(get_db)):
    # Traemos la membresía más reciente del socio
    membership = (
        db.query(models.Membership)
        .filter(models.Membership.user_id == user.id)
        .order_by(models.Membership.end_date.desc())
        .first()
    )

    dias_restantes = None
    if membership:
        dias_restantes = (membership.end_date - date.today()).days

    pagos = (
        db.query(models.Payment)
        .filter(models.Payment.user_id == user.id)
        .order_by(models.Payment.payment_date.desc())
        .limit(5)
        .all()
    )

    return templates.TemplateResponse(
        "user_dashboard.html",
        {
            "request": request,
            "user": user,
            "membership": membership,
            "dias_restantes": dias_restantes,
            "pagos": pagos,
        },
    )
