"""
Dependencias de FastAPI reutilizables para manejar autenticación por sesión
(cookie firmada), sin necesidad de JWT: más simple para empezar a aprender.
"""
from fastapi import Request, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app import models


def get_current_user(request: Request, db: Session = Depends(get_db)):
    """
    Devuelve el usuario logueado (según la sesión) o None si no hay nadie logueado.
    No lanza error: se usa para páginas que se ven distinto si estás logueado o no.
    """
    user_id = request.session.get("user_id")
    if not user_id:
        return None
    return db.query(models.User).filter(models.User.id == user_id).first()


def require_login(request: Request, db: Session = Depends(get_db)):
    """
    Igual que get_current_user, pero corta con un redirect/error si no hay sesión.
    Usar en rutas que exigen estar logueado.
    """
    user = get_current_user(request, db)
    if not user:
        raise HTTPException(status_code=status.HTTP_303_SEE_OTHER, headers={"Location": "/login"})
    return user


def require_admin(request: Request, db: Session = Depends(get_db)):
    """
    Igual que require_login, pero además exige rol admin.
    """
    user = require_login(request, db)
    if user.role != models.UserRole.admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acceso solo para administradores")
    return user
