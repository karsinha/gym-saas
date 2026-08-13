# Gym SaaS — Base del proyecto

Base inicial de un sistema de gestión de gimnasios. Incluye:

- Registro/login con sesión (el primer usuario registrado queda como **admin**, el resto son **socios**)
- Panel del socio: estado de membresía, días restantes, historial de pagos
- Panel del admin: KPIs (socios activos, ingresos del mes, vencimientos próximos), listado de socios, alta de membresías y pagos

**Stack:** FastAPI + Jinja2 + HTMX + Tailwind (CDN) + SQLAlchemy + PostgreSQL (con SQLite de respaldo).

## 1. Instalar dependencias

```bash
python -m venv venv
source venv/bin/activate    # en Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## 2. Configurar variables de entorno

```bash
cp .env.example .env
```

Por defecto, si no configurás `DATABASE_URL`, el proyecto usa **SQLite** (`gym.db`)
automáticamente. Así podés arrancar sin instalar nada.

### Opción recomendada: usar PostgreSQL con Docker

```bash
docker compose up -d
```

Esto levanta un Postgres en `localhost:5432` con las credenciales que ya están
en `.env.example`. Solo descomentá/dejá esa línea de `DATABASE_URL` en tu `.env`.

## 3. Correr el proyecto

```bash
uvicorn app.main:app --reload
```

Abrí [http://localhost:8000](http://localhost:8000)

## 4. Primer uso

1. Andá a `/register` y creá tu primer usuario → queda como **administrador**.
2. Desde `/admin/socios`, para probar el flujo completo, registrate con otro
   email (o pedile a alguien) para crear un socio, y desde el detalle del
   socio (`/admin/socios/{id}`) cargale una membresía y un pago.
3. Iniciá sesión con ese socio para ver `/dashboard`.

## Estructura del proyecto

```
app/
  main.py              punto de entrada, arma la app y registra rutas
  config.py            lee variables de entorno
  database.py          conexión a la base de datos (SQLAlchemy)
  models.py            tablas: User, Membership, Payment, GymClass, ClassBooking
  security.py          hash de contraseñas
  dependencies.py      usuario actual / control de acceso (admin vs socio)
  routers/
    auth.py            login, registro, logout
    user.py            panel del socio
    admin.py           panel del admin + gestión de socios
  templates/           HTML (Jinja2) + Tailwind + HTMX
  static/              CSS/JS propios (vacío por ahora)
```

## Qué falta / próximos pasos sugeridos

Esto es una base funcional, no un producto terminado. Ideas para seguir, en orden:

1. **Validaciones y mensajes de error** más prolijos (con Pydantic schemas)
2. **Editar/eliminar** socios, membresías y pagos (hoy solo se pueden crear)
3. **Clases grupales**: crear `GymClass`, que los socios se anoten (`ClassBooking`) y ver cupos
4. **Check-in** de socios al entrar al gimnasio
5. **Notificaciones** (recordatorio de vencimiento) — al principio puede ser solo visual en el dashboard, después por email
6. **Alembic** para manejar migraciones de la base de datos en vez de recrear tablas
7. **Tests** básicos con `pytest` para las rutas críticas (login, alta de socio)
8. Reemplazar Tailwind por CDN con un build real (Tailwind CLI o Vite) cuando el proyecto crezca

## Notas para vos que estás aprendiendo

- No hay JWT ni tokens: se usa **sesión con cookie firmada** (`SessionMiddleware`), que es más simple de entender al principio. Cuando quieras exponer una API para un futuro frontend en React o una app mobile, ahí sí conviene migrar a JWT.
- Las contraseñas nunca se guardan en texto plano: se hashean con `bcrypt` (ver `security.py`).
- `Base.metadata.create_all()` crea las tablas automáticamente al arrancar. Sirve para desarrollo, pero en un proyecto real vas a querer **Alembic** para versionar cambios de esquema sin perder datos.
