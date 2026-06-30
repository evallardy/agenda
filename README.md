# Agenda Consultorio

Sistema de agenda para consultorio medico construido con Django, MySQL y Bootstrap.

## Requisitos

- Python 3.12
- MySQL en ejecucion
- Base de datos disponible para las credenciales definidas en `.env`

## Instalacion

1. Crear entorno virtual.
2. Instalar dependencias de desarrollo desde [requirements-dev.txt](requirements-dev.txt).
3. Crear `.env.development` a partir de [ .env.development.example ](.env.development.example).
4. Aplicar migraciones.
5. Iniciar el servidor.

En Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements-dev.txt
Copy-Item .env.development.example .env.development
python manage.py migrate
python manage.py runserver
```

## Variables principales

La configuracion se carga desde archivos de entorno en [agenda/settings.py](agenda/settings.py).

Orden de carga:

- `DJANGO_ENV_FILE` si esta definido
- `.env.production` cuando `DJANGO_ENV=production`
- `.env.development` en cualquier otro caso
- `.env` al final como sobreescritura local opcional

Variables base:

- `DJANGO_ENV`
- `DJANGO_SECRET_KEY`
- `DJANGO_DEBUG`
- `DJANGO_ALLOWED_HOSTS`
- `DJANGO_CSRF_TRUSTED_ORIGINS`
- `DJANGO_USE_WHITENOISE`
- `DB_NAME`
- `DB_USER`
- `DB_PASSWORD`
- `DB_HOST`
- `DB_PORT`
- `EMAIL_BACKEND`
- `EMAIL_HOST`
- `EMAIL_HOST_USER`
- `EMAIL_HOST_PASSWORD`
- `EMAIL_PORT`
- `EMAIL_USE_TLS`

## Archivos de entorno

- Desarrollo: [ .env.development.example ](.env.development.example)
- Produccion: [ .env.production.example ](.env.production.example)
- Base generica: [ .env.example ](.env.example)

## Deploy

Dependencias de produccion:

```powershell
pip install -r requirements-prod.txt
```

Configuracion minima en servidor:

```powershell
Copy-Item .env.production.example .env.production
python manage.py migrate
python manage.py collectstatic --noinput
gunicorn agenda.wsgi:application --config gunicorn.conf.py
```

Tambien puedes usar [Procfile](Procfile) si tu plataforma lo soporta.

## Comandos utiles

Aplicar migraciones:

```powershell
python manage.py migrate
```

Crear datos base del consultorio:

```powershell
python manage.py bootstrap_consultorio
```

Ejecutar pruebas principales:

```powershell
python manage.py test users citas clinico
```

Verificacion rapida:

```powershell
python manage.py check
```

## Funcionalidades principales

- Registro y acceso con usuario personalizado por correo
- Verificacion de cuenta y recuperacion de contrasena por correo
- Agenda de citas para paciente y medico
- Cardex clinico por cita
- Historial clinico por paciente con filtros
- Receta imprimible y descarga PDF
- Envio manual de correos y bitacora de envios

## Notas

- Para desarrollo local puedes usar la guia de [CONFIGURACION_ENTORNOS.md](CONFIGURACION_ENTORNOS.md).
- El proyecto usa MySQL y PyMySQL.
- Las recetas PDF requieren `reportlab`, ya incluido en [requirements.txt](requirements.txt).
- Para deploy simple sin Nginx se incluyo WhiteNoise en [requirements-prod.txt](requirements-prod.txt).
