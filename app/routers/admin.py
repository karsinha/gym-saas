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

@router.get("/socios/{socio_id}/editar", response_class=HTMLResponse)
def editar_socio_form(socio_id: int, request: Request, admin=Depends(require_admin), db: Session = Depends(get_db)):
    socio = db.query(models.User).filter(models.User.id == socio_id).first()
    return templates.TemplateResponse(
        "admin_socio_editar.html", {"request": request, "admin": admin, "socio": socio, "error": None}
    )


@router.post("/socios/{socio_id}/editar")
def editar_socio_submit(
    socio_id: int,
    request: Request,
    full_name: str = Form(...),
    email: str = Form(...),
    admin=Depends(require_admin),
    db: Session = Depends(get_db),
):
    socio = db.query(models.User).filter(models.User.id == socio_id).first()

    # Si el email cambió, verificamos que no lo esté usando otro usuario
    email_en_uso = (
        db.query(models.User)
        .filter(models.User.email == email, models.User.id != socio_id)
        .first()
    )
    if email_en_uso:
        return templates.TemplateResponse(
            "admin_socio_editar.html",
            {"request": request, "admin": admin, "socio": socio, "error": "Ese email ya lo usa otro usuario."},
            status_code=400,
        )

    socio.full_name = full_name
    socio.email = email
    db.commit()
    return RedirectResponse(f"/admin/socios/{socio_id}", status_code=303)


@router.post("/socios/{socio_id}/eliminar")
def eliminar_socio(socio_id: int, admin=Depends(require_admin), db: Session = Depends(get_db)):
    socio = db.query(models.User).filter(models.User.id == socio_id).first()
    if socio:
        # Gracias a cascade="all, delete-orphan" en el modelo User,
        # esto borra también sus membresías, pagos y reservas asociadas.
        db.delete(socio)
        db.commit()
    return RedirectResponse("/admin/socios", status_code=303)


@router.post("/socios/{socio_id}/membership/{membership_id}/eliminar")
def eliminar_membresia(
    socio_id: int, membership_id: int, admin=Depends(require_admin), db: Session = Depends(get_db)
):
    membership = db.query(models.Membership).filter(models.Membership.id == membership_id).first()
    if membership:
        db.delete(membership)
        db.commit()
    return RedirectResponse(f"/admin/socios/{socio_id}", status_code=303)


@router.post("/socios/{socio_id}/payment/{payment_id}/eliminar")
def eliminar_pago(
    socio_id: int, payment_id: int, admin=Depends(require_admin), db: Session = Depends(get_db)
):
    pago = db.query(models.Payment).filter(models.Payment.id == payment_id).first()
    if pago:
        db.delete(pago)
        db.commit()
    return RedirectResponse(f"/admin/socios/{socio_id}", status_code=303)

@router.get("/clases", response_class=HTMLResponse)
def listar_clases(request: Request, admin=Depends(require_admin), db: Session = Depends(get_db)):
    clases = db.query(models.GymClass).order_by(models.GymClass.day_of_week, models.GymClass.start_time).all()
    data = []
    for c in clases:
        anotados = db.query(models.ClassBooking).filter(models.ClassBooking.class_id == c.id).count()
        data.append({"clase": c, "anotados": anotados})
    return templates.TemplateResponse(
        "admin_clases.html", {"request": request, "admin": admin, "data": data}
    )


@router.post("/clases")
def nueva_clase(
    name: str = Form(...),
    instructor: str = Form(""),
    day_of_week: str = Form(...),
    start_time: str = Form(...),
    capacity: int = Form(20),
    admin=Depends(require_admin),
    db: Session = Depends(get_db),
):
    clase = models.GymClass(
        name=name, instructor=instructor, day_of_week=day_of_week,
        start_time=start_time, capacity=capacity,
    )
    db.add(clase)
    db.commit()
    return RedirectResponse("/admin/clases", status_code=303)


@router.post("/clases/{class_id}/eliminar")
def eliminar_clase(class_id: int, admin=Depends(require_admin), db: Session = Depends(get_db)):
    clase = db.query(models.GymClass).filter(models.GymClass.id == class_id).first()
    if clase:
        db.delete(clase)  # cascade borra también las reservas de esa clase
        db.commit()
    return RedirectResponse("/admin/clases", status_code=303)


@router.post("/socios/{socio_id}/membership/{membership_id}/confirmar")
def confirmar_membresia(
    socio_id: int, membership_id: int, admin=Depends(require_admin), db: Session = Depends(get_db)
):
    membership = db.query(models.Membership).filter(models.Membership.id == membership_id).first()
    if membership and membership.status == models.MembershipStatus.pending:
        dias = (membership.end_date - membership.start_date).days
        membership.start_date = date.today()
        membership.end_date = date.today() + timedelta(days=dias)
        membership.status = models.MembershipStatus.active
        db.commit()
    return RedirectResponse(f"/admin/socios/{socio_id}", status_code=303)