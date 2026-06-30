# Deploy en servidor

Este repositorio incluye un paquete de deploy pensado para trabajar con el `crea_proyecto.sh` que ya tienes en el servidor.

## Archivos incluidos

- `deploy/project.conf.example`: variables del proyecto para que el script del servidor no tenga que inferir nombres o rutas.
- `deploy/post_deploy.sh`: instala dependencias de produccion, ejecuta migraciones, `collectstatic` y `check --deploy`.
- `deploy/gunicorn_start.sh`: arranque de Gunicorn para systemd.
- `deploy/systemd/agenda.service`: plantilla de servicio systemd.
- `deploy/nginx/agenda.conf`: plantilla base de Nginx.

## Preparacion del repo

1. Copia `deploy/project.conf.example` a `deploy/project.conf` y ajusta dominio, usuario, rutas y correo.
2. Copia `.env.production.example` a `.env.production` y completa credenciales reales.
3. Asegurate de que el servidor tenga Python 3, `venv`, Nginx y systemd.

## Flujo esperado con `crea_proyecto.sh`

Este proyecto asume que el script del servidor puede:

1. Clonar o actualizar el repositorio en `${APP_SOURCE_DIR}`.
2. Leer `deploy/project.conf`.
3. Ejecutar `deploy/post_deploy.sh`.
4. Instalar o enlazar `deploy/systemd/agenda.service`.
5. Instalar o enlazar `deploy/nginx/agenda.conf`.

Si tu version de `crea_proyecto.sh` usa otros nombres, adapta solo el mapeo en el servidor; los artefactos del proyecto ya estan listos.

## Comandos manuales equivalentes

```bash
cp deploy/project.conf.example deploy/project.conf
cp .env.production.example .env.production
bash deploy/post_deploy.sh
sudo cp deploy/systemd/agenda.service /etc/systemd/system/agenda.service
sudo cp deploy/nginx/agenda.conf /etc/nginx/sites-available/agenda.conf
sudo ln -s /etc/nginx/sites-available/agenda.conf /etc/nginx/sites-enabled/agenda.conf
sudo systemctl daemon-reload
sudo systemctl enable --now agenda
sudo nginx -t
sudo systemctl reload nginx
```