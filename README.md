# Cotizador Interno de Fletes de Importación — CINTAC

Aplicación web en **Django (monolito)** con **PostgreSQL**, roles (Administrador / Analista), política de contraseñas,
bloqueo por intentos fallidos y **tabla de auditoría**. Lista para desplegar en **Render**.

## 1. Estructura del proyecto

```
cotizador_cintac/
├── manage.py
├── requirements.txt          # dependencias
├── build.sh                  # script de construcción para Render
├── render.yaml               # Blueprint de Render (web + PostgreSQL)
├── .env.example              # variables de entorno de ejemplo
├── config/                   # settings (django-environ), urls, wsgi
├── apps/
│   ├── usuarios/             # Usuario (RBAC), login seguro, primer ingreso, gestión de usuarios
│   │   ├── models.py         #   rol, primer_ingreso, intentos_fallidos, bloqueado
│   │   ├── reglas_clave.py   #   política de contraseña con expresiones regulares
│   │   ├── validators.py     #   validador conectado a AUTH_PASSWORD_VALIDATORS
│   │   ├── forms.py          #   LoginForm (intentos/bloqueo) y CambioClaveForm
│   │   ├── middleware.py     #   obliga el cambio de clave en el primer ingreso
│   │   └── permisos.py       #   mixins por rol (403 + auditoría)
│   ├── tarifas/              # Puerto, Embarcador, Tarifa (normalizadas) + CRUD solo Administrador
│   ├── cotizaciones/         # Cotizacion (historial), simulador, comparador
│   │   └── services.py       #   reglas COMEX en Python puro (Decreto 75, contingencia, TLC, IVA)
│   └── auditoria/            # AuditLog inmutable, señales de login/logout, vista con filtros
├── templates/                # pantallas (base, usuarios, tarifas, cotizaciones, auditoria)
└── static/css/app.css        # estilos con la paleta CINTAC
```

## 2. Instalación local (Windows PowerShell)

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env          # y edita SECRET_KEY y las claves

# IMPORTANTE: el repositorio no trae migraciones; se generan una vez y se suben a Git
python manage.py makemigrations usuarios tarifas cotizaciones auditoria
python manage.py migrate

python manage.py crear_admin_inicial                      # usa ADMIN_USERNAME / ADMIN_PASSWORD del .env
python manage.py cargar_datos_ejemplo                     # tarifas de ejemplo
python manage.py cargar_datos_ejemplo --usuarios-demo     # (opcional, SOLO local) admin_cintac, analista1, analista2
python manage.py runserver
```

Sin `DATABASE_URL` se usa SQLite. Para PostgreSQL local agrega en `.env`:
`DATABASE_URL=postgres://usuario:clave@localhost:5432/cintac`.

> Las carpetas `apps/*/migrations/` deben **subirse a Git** (no están en `.gitignore`): Render solo ejecuta `migrate`.

## 3. Pruebas

```powershell
python manage.py test                                    # todas (unitarias + Django)
python -m unittest apps.cotizaciones.tests.test_services apps.usuarios.tests.test_reglas_clave   # solo las puras (sin BD)
```

| Archivo | Qué cubre |
|---|---|
| `cotizaciones/tests/test_services.py` | Contingencia, Decreto 75, TLC, IVA sobre CIF + arancel, redondeos, validaciones, comparador |
| `usuarios/tests/test_reglas_clave.py` | Regex de contraseña (cada regla), clave temporal aleatoria |
| `usuarios/tests/test_autenticacion.py` | CP01: intentos, bloqueo, primer ingreso, cambio de clave, roles, gestión de usuarios |
| `tarifas/tests/test_tarifas.py` | Restricciones de BD, CRUD, normalización, permisos |
| `cotizaciones/tests/test_cotizaciones.py` | Simulador, historial por rol, comparador |
| `auditoria/tests/test_auditoria.py` | Inmutabilidad, IP, login/logout, filtros |

## 4. Variables de entorno

| Variable | Uso | Ejemplo |
|---|---|---|
| `SECRET_KEY` | Clave de Django (obligatoria si `DEBUG=False`) | generada por Render |
| `DEBUG` | Modo desarrollo | `False` en producción |
| `DATABASE_URL` | Conexión a PostgreSQL | la entrega Render |
| `ALLOWED_HOSTS` / `CSRF_TRUSTED_ORIGINS` | Dominios permitidos | Render agrega su dominio solo |
| `ADMIN_USERNAME`, `ADMIN_PASSWORD`, `ADMIN_NOMBRE` | Administrador inicial (debe cambiar la clave al ingresar) | tú los defines |
| `COTIZADOR_BLOQUEAR_EXCESO_PESO` | `True` bloquea >25 t/contenedor; `False` solo advierte | `True` |
| `SESSION_COOKIE_AGE` | Segundos de inactividad antes de cerrar sesión | `1800` |

## 5. Despliegue en Render

1. Sube el proyecto a **GitHub** (con las carpetas `migrations/`).
2. En Render: **New → Blueprint**, elige el repositorio. Render lee `render.yaml` y crea la base **PostgreSQL** y el **servicio web**.
3. Cuando lo pida, completa `ADMIN_USERNAME` y `ADMIN_PASSWORD` (clave temporal que cumpla la política).
4. Render ejecuta `build.sh` (instala, `collectstatic`, `migrate`, crea el administrador) y arranca con `gunicorn config.wsgi:application`.
5. Abre la URL pública, ingresa con el administrador y cambia la clave (cambio obligatorio).
6. Carga las tarifas desde el mantenedor, o corre `cargar_datos_ejemplo` desde una terminal local apuntando a la base de Render.

Notas: las bases PostgreSQL del plan gratuito de Render **tienen vencimiento y los servicios gratuitos se suspenden por inactividad**;
revisa los plazos vigentes en la documentación de Render antes de la presentación. Para conectar desde tu PC usa la URL **externa** de la base (con `?sslmode=require`).

## 6. Cumplimiento de la rúbrica

| Criterio | Dónde se cumple |
|---|---|
| Estructura, normalización y optimización de BD | `tarifas/models.py` (3FN: Puerto, Embarcador, Tarifa), restricciones `UniqueConstraint`/`CheckConstraint`, índices en rutas, auditoría y cotizaciones |
| Patrones de seguridad | Hash PBKDF2 con sal, regex de contraseña, bloqueo a 3 intentos, cambio obligatorio, RBAC en servidor, CSRF, sesión HttpOnly con expiración por inactividad, HTTPS/HSTS en producción, escape de HTML en plantillas, auditoría inmutable |
| Interfaz y necesidades del negocio | Simulador, comparador, mantenedor, usuarios, historial e impresión |
| Entorno y documentación | Este README, `.env.example`, `render.yaml`, `build.sh` |
| Plan de pruebas | Carpeta `apps/*/tests/` (y el plan de pruebas entregado aparte) |

## 7. Decisiones de diseño

- **IVA**: 19 % sobre **CIF + arancel** (base imponible de importación).
- **Decreto 75**: superar 25 t por contenedor **bloquea** la cotización (corrige la falla D-01 del prototipo). Con `COTIZADOR_BLOQUEAR_EXCESO_PESO=False` solo advierte.
- **Validaciones** (tipo de cambio > 0, FOB ≥ 0, días ≥ 1, toneladas > 0) se aplican en el formulario y otra vez en `services.py` (corrige D-02).
- **Roles y permisos** viven en la base de datos y se verifican en cada petición (corrige D-03).
- **Cotizacion** guarda una copia de la tarifa usada (desnormalización intencional) para que el historial no cambie si la tarifa se edita o elimina.
- **Auditoría**: escrita siempre por el servidor; el registro no se puede editar ni borrar; guarda el nombre del usuario aunque luego se elimine.
- El **Comparador** está disponible para ambos roles; el **CRUD de tarifas**, la gestión de usuarios y la auditoría son solo del Administrador.
