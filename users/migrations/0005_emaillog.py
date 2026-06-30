from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0004_remove_user_photo_url_user_photo'),
    ]

    operations = [
        migrations.CreateModel(
            name='EmailLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('recipient', models.EmailField(max_length=254, verbose_name='destinatario')),
                ('subject', models.CharField(max_length=255, verbose_name='asunto')),
                ('from_email', models.CharField(max_length=255, verbose_name='remitente')),
                ('body', models.TextField(blank=True, verbose_name='contenido')),
                ('context_type', models.CharField(blank=True, max_length=60, verbose_name='tipo de envio')),
                ('status', models.CharField(choices=[('sent', 'Enviado'), ('failed', 'Fallido')], default='sent', max_length=20)),
                ('error_message', models.TextField(blank=True, verbose_name='detalle del error')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='fecha de envio')),
                ('triggered_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='email_logs', to='users.user', verbose_name='enviado por')),
            ],
            options={
                'verbose_name': 'Bitacora de correo',
                'verbose_name_plural': 'Bitacoras de correo',
                'ordering': ('-created_at',),
            },
        ),
    ]
