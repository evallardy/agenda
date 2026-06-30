from django.contrib.auth.base_user import BaseUserManager
from django.contrib.auth.models import AbstractUser
from PIL import Image, ImageOps
from django.db import models


class UserManager(BaseUserManager):
    use_in_migrations = True

    def _create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError('El correo es obligatorio.')
        email = self.normalize_email(email)
        username = extra_fields.pop('username', email)
        user = self.model(email=email, username=username, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', False)
        extra_fields.setdefault('is_superuser', False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        extra_fields.setdefault('email_verified', True)
        extra_fields.setdefault('role', User.Role.MEDICO)
        extra_fields.setdefault('username', 'admin')

        if extra_fields.get('is_staff') is not True:
            raise ValueError('El superusuario debe tener is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('El superusuario debe tener is_superuser=True.')
        return self._create_user(email, password, **extra_fields)


class User(AbstractUser):
    MAX_PHOTO_SIZE = (600, 600)

    class Role(models.TextChoices):
        PACIENTE = 'paciente', 'Paciente'
        MEDICO = 'medico', 'Medico'

    username = models.CharField(max_length=150, unique=True, blank=True)
    first_name = None
    last_name = None
    email = models.EmailField('correo electronico', unique=True)
    full_name = models.CharField('nombre completo', max_length=255)
    phone = models.CharField('celular', max_length=20)
    specialties = models.CharField('especialidades', max_length=255, blank=True)
    professional_license = models.CharField('cedula profesional', max_length=80, blank=True)
    office_name = models.CharField('nombre del consultorio', max_length=150, blank=True)
    office_address = models.CharField('ubicacion del consultorio', max_length=255, blank=True)
    profile_bio = models.TextField('descripcion profesional', blank=True)
    photo = models.ImageField('foto del medico', upload_to='doctors/', blank=True, null=True)
    email_verified = models.BooleanField(default=False)
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.PACIENTE)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    objects = UserManager()

    def save(self, *args, **kwargs):
        if not self.username:
            self.username = self.email
        super().save(*args, **kwargs)
        self._resize_photo()

    def _resize_photo(self):
        if not self.photo or not hasattr(self.photo, 'path'):
            return

        photo_path = self.photo.path
        try:
            with Image.open(photo_path) as image:
                normalized = ImageOps.exif_transpose(image)
                side = min(normalized.width, normalized.height)
                left = (normalized.width - side) // 2
                top = (normalized.height - side) // 2
                cropped = normalized.crop((left, top, left + side, top + side))
                resized = cropped.resize(self.MAX_PHOTO_SIZE, Image.Resampling.LANCZOS)
                resized.save(photo_path, optimize=True)
        except (FileNotFoundError, OSError):
            return

    def __str__(self):
        return self.full_name or self.email


class EmailLog(models.Model):
    class Status(models.TextChoices):
        SENT = 'sent', 'Enviado'
        FAILED = 'failed', 'Fallido'

    recipient = models.EmailField('destinatario')
    subject = models.CharField('asunto', max_length=255)
    from_email = models.CharField('remitente', max_length=255)
    body = models.TextField('contenido', blank=True)
    context_type = models.CharField('tipo de envio', max_length=60, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.SENT)
    error_message = models.TextField('detalle del error', blank=True)
    triggered_by = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        related_name='email_logs',
        null=True,
        blank=True,
        verbose_name='enviado por',
    )
    created_at = models.DateTimeField('fecha de envio', auto_now_add=True)

    class Meta:
        verbose_name = 'Bitacora de correo'
        verbose_name_plural = 'Bitacoras de correo'
        ordering = ('-created_at',)

    def __str__(self):
        return f'{self.recipient} - {self.subject}'
