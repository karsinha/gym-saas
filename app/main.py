from fastapi import FastAPI, Request, Depends
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

from app.config import SECRET_KEY
from app.database import Base, engine
from app.dependencies import get_current_user
from app.routers import auth, user, admin

# Crea las tablas en la base de datos si no existen.
# (Más adelante, cuando el proyecto crezca, conviene migrar a Alembic
# para manejar cambios de esquema de forma controlada.)
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Gym SaaS")

# Sesiones basadas en cookie firmada (para el login)
app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY)

app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")

app.include_router(auth.router)
app.include_router(user.router)
app.include_router(admin.router)


@app.get("/", response_class=HTMLResponse)
def home(request: Request, current_user=Depends(get_current_user)):
    if not current_user:
        return RedirectResponse("/login")
    if current_user.role.value == "admin":
        return RedirectResponse("/admin")
    return RedirectResponse("/dashboard")
