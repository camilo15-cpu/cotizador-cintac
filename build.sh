#!/usr/bin/env bash
# Script de construcción para Render: se ejecuta en cada despliegue.
set -o errexit   # detener el despliegue si algún comando falla

pip install -r requirements.txt

python manage.py collectstatic --no-input
python manage.py migrate --no-input

# Crea el administrador inicial si ADMIN_USERNAME y ADMIN_PASSWORD están definidos (idempotente)
python manage.py crear_admin_inicial
