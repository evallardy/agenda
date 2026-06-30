# Configuracion de entornos

Este proyecto usa variables de entorno en `agenda/settings.py`.

Orden de carga:

- `DJANGO_ENV_FILE` si quieres apuntar a un archivo concreto
- `.env.production` cuando `DJANGO_ENV=production`
- `.env.development` para desarrollo por defecto
- `.env` como sobreescritura local opcional

## Local

Usa Mailtrap para desarrollo local. Los correos no se entregan a pacientes reales; aparecen dentro del inbox de Mailtrap.

Archivo sugerido: `.env.development`
Base recomendada: `.env.development.example`

Valores clave para local:
- `DJANGO_ENV=development`
- `DJANGO_DEBUG=true`
- `EMAIL_HOST=sandbox.smtp.mailtrap.io`
- `EMAIL_PORT=2525`
- `EMAIL_USE_TLS=true`
- `EMAIL_USE_SSL=false`
- `DJANGO_USE_WHITENOISE=false`

## Produccion

Usa el servidor SMTP real del consultorio o del hosting.

Archivo sugerido en servidor: variables de entorno del sistema o un `.env.production`.
Base recomendada: `.env.production.example`

Valores clave para produccion:
- `DJANGO_ENV=production`
- `DJANGO_DEBUG=false`
- `DJANGO_ALLOWED_HOSTS` con tus dominios reales
- `DJANGO_CSRF_TRUSTED_ORIGINS` con URLs HTTPS reales
- `EMAIL_HOST` y credenciales reales del servidor de correo
- `DJANGO_USE_WHITENOISE=true` si Django servira estaticos
- cookies seguras y HSTS activados

## Flujo recomendado

- En tu maquina local usa Mailtrap.
- En el servidor usa SMTP real.
- No reutilices las credenciales de Mailtrap en produccion.
- Manten `.env`, `.env.development` y `.env.production` fuera del repositorio.

## Prueba local de correo

Con Mailtrap configurado en `.env`, puedes probar el envio con Django. Si el envio es correcto, el correo aparecera en el inbox de Mailtrap.
