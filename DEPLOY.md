# Deploy en servidor

Este repositorio incluye un paquete de deploy compatible con tu shell de despliegue basado en Supervisor y Nginx.

## Archivos incluidos

- `agenda/settings_prod.py`: settings compatibles con las variables `BAR_*` que genera tu shell.
- `deploy/gunicorn.sh` y `deploy/gunicorn_start.sh`: arranque de Gunicorn leyendo `deploy/.env.deploy`.
- `deploy/supervisor/bar.conf`: plantilla que tu shell renderiza hacia `/etc/supervisor/conf.d/`.
- `deploy/nginx/bar.conf`: plantilla que tu shell renderiza hacia `/etc/nginx/sites-available/`.

## Preparacion del repo

1. Ejecuta tu shell con el nombre del repo `agenda`.
2. Edita `deploy/.env.deploy` cuando el script deje los placeholders obligatorios.
3. Reejecuta el shell para completar migraciones, `collectstatic` y reinicio.

## Contrato que espera tu shell

Este proyecto ya expone exactamente los archivos que tu shell usa:

1. `agenda.settings_prod` para `python manage.py ... --settings=agenda.settings_prod`
2. `deploy/gunicorn.sh`
3. `deploy/gunicorn_start.sh`
4. `deploy/supervisor/bar.conf`
5. `deploy/nginx/bar.conf`
6. Variables `BAR_*` desde `deploy/.env.deploy`

## Comandos manuales equivalentes

```bash
sudo bash deploy/tu_shell.sh produccion agenda agenda.tu-dominio.com usuario_supervisor
```