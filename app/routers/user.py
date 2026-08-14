from datetime import date, timedelta

from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import HTMLResponse, RedirectResponse
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

@router.get("/dashboard/editar", response_class=HTMLResponse)
def editar_perfil_form(request: Request, user=Depends(require_login)):
    return templates.TemplateResponse(
        "user_editar.html", {"request": request, "user": user, "error": None}
    )


@router.post("/dashboard/editar")
def editar_perfil_submit(
    request: Request,
    full_name: str = Form(...),
    email: str = Form(...),
    phone: str = Form(""),
    user=Depends(require_login),
    db: Session = Depends(get_db),
):
    email_en_uso = (
        db.query(models.User)
        .filter(models.User.email == email, models.User.id != user.id)
        .first()
    )
    if email_en_uso:
        return templates.TemplateResponse(
            "user_editar.html",
            {"request": request, "user": user, "error": "Ese email ya lo usa otro usuario."},
            status_code=400,
        )

    user.full_name = full_name
    user.email = email
    user.phone = phone
    db.commit()
    return RedirectResponse("/dashboard", status_code=303)

@router.get("/clases", response_class=HTMLResponse)
def listar_clases_socio(request: Request, user=Depends(require_login), db: Session = Depends(get_db)):
    clases = db.query(models.GymClass).order_by(models.GymClass.day_of_week, models.GymClass.start_time).all()
    mis_reservas = {
        b.class_id for b in db.query(models.ClassBooking).filter(models.ClassBooking.user_id == user.id).all()
    }
    data = []
    for c in clases:
        anotados = db.query(models.ClassBooking).filter(models.ClassBooking.class_id == c.id).count()
        data.append({
            "clase": c,
            "cupos_libres": c.capacity - anotados,
            "ya_reservado": c.id in mis_reservas,
        })
    return templates.TemplateResponse(
        "clases.html", {"request": request, "user": user, "data": data}
    )


@router.post("/clases/{class_id}/reservar")
def reservar_clase(class_id: int, user=Depends(require_login), db: Session = Depends(get_db)):
    clase = db.query(models.GymClass).filter(models.GymClass.id == class_id).first()
    if clase:
        ya_reservado = (
            db.query(models.ClassBooking)
            .filter(models.ClassBooking.class_id == class_id, models.ClassBooking.user_id == user.id)
            .first()
        )
        anotados = db.query(models.ClassBooking).filter(models.ClassBooking.class_id == class_id).count()
        if not ya_reservado and anotados < clase.capacity:
            db.add(models.ClassBooking(class_id=class_id, user_id=user.id))
            db.commit()
    return RedirectResponse("/clases", status_code=303)


@router.post("/clases/{class_id}/cancelar")
def cancelar_reserva(class_id: int, user=Depends(require_login), db: Session = Depends(get_db)):
    booking = (
        db.query(models.ClassBooking)
        .filter(models.ClassBooking.class_id == class_id, models.ClassBooking.user_id == user.id)
        .first()
    )
    if booking:
        db.delete(booking)
        db.commit()
    return RedirectResponse("/clases", status_code=303)


@router.post("/dashboard/membresia")
def elegir_membresia(
    plan_name: str = Form(...),
    price: float = Form(...),
    dias: int = Form(...),
    user=Depends(require_login),
    db: Session = Depends(get_db),
):
    inicio = date.today()
    fin = inicio + timedelta(days=dias)
    membership = models.Membership(
        user_id=user.id,
        plan_name=plan_name,
        price=price,
        start_date=inicio,
        end_date=fin,
        status=models.MembershipStatus.pending,
    )
    db.add(membership)
    db.commit()
    return RedirectResponse("/dashboard", status_code=303)