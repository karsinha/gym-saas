from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db
from app import models
from app.security import hash_password, verify_password
from app.dependencies import get_current_user

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/register", response_class=HTMLResponse)
def register_form(request: Request):
    return templates.TemplateResponse("register.html", {"request": request, "error": None})


@router.post("/register", response_class=HTMLResponse)
def register_submit(
    request: Request,
    full_name: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    existing = db.query(models.User).filter(models.User.email == email).first()
    if existing:
        return templates.TemplateResponse(
            "register.html",
            {"request": request, "error": "Ese email ya está registrado."},
            status_code=400,
        )

    # El primer usuario que se registra queda como admin automáticamente.
    # Los siguientes se registran como socios (user) por defecto.
    is_first_user = db.query(models.User).count() == 0
    role = models.UserRole.admin if is_first_user else models.UserRole.user

    new_user = models.User(
        full_name=full_name,
        email=email,
        password_hash=hash_password(password),
        role=role,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    request.session["user_id"] = new_user.id
    request.session["role"] = role.value
    destino = "/admin" if role == models.UserRole.admin else "/dashboard"
    return RedirectResponse(destino, status_code=303)


@router.get("/login", response_class=HTMLResponse)
def login_form(request: Request):
    return templates.TemplateResponse("login.html", {"request": request, "error": None})


@router.post("/login", response_class=HTMLResponse)
def login_submit(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    user = db.query(models.User).filter(models.User.email == email).first()
    if not user or not verify_password(password, user.password_hash):
        return templates.TemplateResponse(
            "login.html",
            {"request": request, "error": "Email o contraseña incorrectos."},
            status_code=400,
        )

    request.session["user_id"] = user.id
    request.session["role"] = user.role.value
    destino = "/admin" if user.role == models.UserRole.admin else "/dashboard"
    return RedirectResponse(destino, status_code=303)


@router.get("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/login", status_code=303)