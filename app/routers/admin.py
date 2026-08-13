from datetime import date, timedelta, datetime

from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database import get_db
from app import models
from app.dependencies import require_admin

router = APIRouter(prefix="/admin")
templates = Jinja2Templates(directory="app/templates")


def _actualizar_estados_membresia(db: Session):
    """Marca como 'expired' las membresías cuya fecha de fin ya pasó."""
    hoy = date.today()
    (
        db.query(models.Membership)
        .filter(models.Membership.end_date < hoy, models.Membership.status == models.MembershipStatus.active)
        .update({models.Membership.status: models.MembershipStatus.expired})
    )
    db.commit()


@router.get("", response_class=HTMLResponse)
def admin_dashboard(request: Request, admin=Depends(require_admin), db: Session = Depends(get_db)):
    _actualizar_estados_membresia(db)
    hoy = date.today()

    total_socios = db.query(models.User).filter(models.User.role == models.UserRole.user).count()

    socios_activos = (
        db.query(models.Membership.user_id)
        .filter(models.Membership.status == models.MembershipStatus.active)
        .distinct()
        .count()
    )

    inicio_mes = hoy.replace(day=1)
    ingresos_mes = (
        db.query(func.coalesce(func.sum(models.Payment.amount), 0))
        .filter(models.Payment.payment_date >= inicio_mes)
        .scalar()
    )

    proximos_vencimientos = (
        db.query(models.Membership)
        .join(models.User)
        .filter(
            models.Membership.status == models.MembershipStatus.active,
            models.Membership.end_date >= hoy,
            models.Membership.end_date <= hoy + timedelta(days=7),
        )
        .order_by(models.Membership.end_date.asc())
        .all()
    )

    return templates.TemplateResponse(
        "admin_dashboard.html",
        {
            "request": request,
            "admin": admin,
            "total_socios": total_socios,
            "socios_activos": socios_activos,
            "ingresos_mes": ingresos_mes,
            "proximos_vencimientos": proximos_vencimientos,
        },
    )


@router.get("/socios", response_class=HTMLResponse)
def listar_socios(request: Request, admin=Depends(require_admin), db: Session = Depends(get_db)):
    _actualizar_estados_membresia(db)
    socios = db.query(models.User).filter(models.User.role == models.UserRole.user).all()

    # Para cada socio, buscamos su membresía más reciente para mostrar el estado
    data = []
    for socio in socios:
        membership = (
            db.query(models.Membership)
            .filter(models.Membership.user_id == socio.id)
            .order_by(models.Membership.end_date.desc())
            .first()
        )
        data.append({"socio": socio, "membership": membership})

    return templates.TemplateResponse(
        "admin_socios.html", {"request": request, "admin": admin, "data": data}
    )


@router.get("/socios/{socio_id}", response_class=HTMLResponse)
def detalle_socio(socio_id: int, request: Request, admin=Depends(require_admin), db: Session = Depends(get_db)):
    socio = db.query(models.User).filter(models.User.id == socio_id).first()
    memberships = (
        db.query(models.Membership)
        .filter(models.Membership.user_id == socio_id)
        .order_by(models.Membership.end_date.desc())
        .all()
    )
    pagos = (
        db.query(models.Payment)
        .filter(models.Payment.user_id == socio_id)
        .order_by(models.Payment.payment_date.desc())
        .all()
    )
    return templates.TemplateResponse(
        "admin_socio_detalle.html",
        {"request": request, "admin": admin, "socio": socio, "memberships": memberships, "pagos": pagos},
    )


@router.post("/socios/{socio_id}/membership")
def nueva_membresia(
    socio_id: int,
    plan_name: str = Form(...),
    price: float = Form(...),
    dias: int = Form(30),
    admin=Depends(require_admin),
    db: Session = Depends(get_db),
):
    inicio = date.today()
    fin = inicio + timedelta(days=dias)
    membership = models.Membership(
        user_id=socio_id, plan_name=plan_name, price=price, start_date=inicio, end_date=fin
    )
    db.add(membership)
    db.commit()
    return RedirectResponse(f"/admin/socios/{socio_id}", status_code=303)


@router.post("/socios/{socio_id}/payment")
def nuevo_pago(
    socio_id: int,
    amount: float = Form(...),
    method: str = Form("efectivo"),
    membership_id: int = Form(None),
    admin=Depends(require_admin),
    db: Session = Depends(get_db),
):
    pago = models.Payment(
        user_id=socio_id,
        membership_id=membership_id,
        amount=amount,
        method=method,
        payment_date=datetime.utcnow(),
    )
    db.add(pago)
    db.commit()
    return RedirectResponse(f"/admin/socios/{socio_id}", status_code=303)
