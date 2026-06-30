from django import forms
from django.contrib.auth import authenticate
from django.contrib.auth.tokens import default_token_generator
from django.contrib.auth.forms import AuthenticationForm, PasswordResetForm, SetPasswordForm, UserCreationForm
from django.contrib.sites.shortcuts import get_current_site
from django.core.mail import EmailMultiAlternatives
from django.forms.utils import flatatt
from django.template import loader
from django.forms.widgets import ClearableFileInput
from django.utils.encoding import force_bytes
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.utils.http import urlsafe_base64_encode
from PIL import Image

from .email_tracking import send_tracked_email_message
from .models import User


class DoctorPhotoWidget(ClearableFileInput):
    def render(self, name, value, attrs=None, renderer=None):
        attrs = attrs or {}
        input_html = format_html(
            '<input type="file" name="{}"{}>',
            name,
            mark_safe(flatatt(attrs)),
        )

        if not self.is_initial(value):
            return input_html

        image_url = getattr(value, 'url', '')
        clear_html = ''
        if not self.is_required:
            clear_html = format_html(
                '<div class="form-check mb-2">'
                '<input class="form-check-input" type="checkbox" name="{}" id="{}">'
                '<label class="form-check-label" for="{}">Borrar foto actual</label>'
                '</div>',
                self.clear_checkbox_name(name),
                self.clear_checkbox_id(self.attrs.get('id', attrs.get('id', name))),
                self.clear_checkbox_id(self.attrs.get('id', attrs.get('id', name))),
            )

        return format_html(
            '<div class="rounded-4 border p-3 mb-3">'
            '<div class="d-flex flex-column flex-md-row gap-3 align-items-md-center">'
            '<img src="{}" alt="Foto actual del medico" class="doctor-photo">'
            '<div>'
            '<p class="mb-2"><strong>Foto actual</strong></p>'
            '{}'
            '<div class="small text-secondary">Puedes reemplazarla seleccionando otra imagen abajo.</div>'
            '</div>'
            '</div>'
            '</div>'
            '{}',
            image_url,
            mark_safe(clear_html),
            input_html,
        )


class UserRegistrationForm(UserCreationForm):
    email = forms.EmailField(label='Correo electronico', help_text='Este correo sera tu usuario para entrar al sistema.')
    full_name = forms.CharField(label='Nombre completo', max_length=255)
    phone = forms.CharField(label='Celular', max_length=20)

    class Meta:
        model = User
        fields = ('full_name', 'phone', 'email')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['full_name'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Escribe tu nombre completo',
            'autocomplete': 'name',
        })
        self.fields['phone'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Ej. 5551234567',
            'autocomplete': 'tel',
        })
        self.fields['email'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'nombre@correo.com',
            'autocomplete': 'email',
        })
        self.fields['password1'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Crea una contrasena segura',
            'autocomplete': 'new-password',
        })
        self.fields['password2'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Repite tu contrasena',
            'autocomplete': 'new-password',
        })
        self.fields['password1'].help_text = (
            'La contrasena debe tener al menos 8 caracteres, no puede ser totalmente numerica '
            'y debe evitar datos personales faciles de adivinar.'
        )
        self.fields['password2'].help_text = 'Repite la contrasena para confirmar.'


class EmailAuthenticationForm(AuthenticationForm):
    username = forms.CharField(label='Correo electronico o usuario')

    def __init__(self, request=None, *args, **kwargs):
        super().__init__(request=request, *args, **kwargs)
        self.fields['username'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Correo electronico o usuario',
            'autocomplete': 'username',
        })
        self.fields['password'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Contrasena',
            'autocomplete': 'current-password',
        })

    def clean(self):
        email = self.cleaned_data.get('username')
        password = self.cleaned_data.get('password')

        if email and password:
            self.user_cache = authenticate(self.request, username=email, password=password)
            if self.user_cache is None:
                raise forms.ValidationError('Correo o contrasena invalidos.', code='invalid_login')
            self.confirm_login_allowed(self.user_cache)

        return self.cleaned_data

    def confirm_login_allowed(self, user):
        if not user.email_verified and not user.is_superuser:
            raise forms.ValidationError('Debes verificar tu correo antes de iniciar sesion.', code='inactive')
        super().confirm_login_allowed(user)


class StyledPasswordResetForm(PasswordResetForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['email'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'nombre@correo.com',
            'autocomplete': 'email',
        })

    def save(
        self,
        domain_override=None,
        subject_template_name='registration/password_reset_subject.txt',
        email_template_name='registration/password_reset_email.html',
        use_https=False,
        token_generator=default_token_generator,
        from_email=None,
        request=None,
        html_email_template_name=None,
        extra_email_context=None,
    ):
        email_value = self.cleaned_data['email']
        if not domain_override:
            current_site = get_current_site(request)
            site_name = current_site.name
            domain = current_site.domain
        else:
            site_name = domain = domain_override

        for user in self.get_users(email_value):
            user_email = getattr(user, User.get_email_field_name())
            context = {
                'email': user_email,
                'domain': domain,
                'site_name': site_name,
                'uid': urlsafe_base64_encode(force_bytes(user.pk)),
                'user': user,
                'token': token_generator.make_token(user),
                'protocol': 'https' if use_https else 'http',
                **(extra_email_context or {}),
            }
            subject = loader.render_to_string(subject_template_name, context)
            subject = ''.join(subject.splitlines())
            body = loader.render_to_string(email_template_name, context)
            email_message = EmailMultiAlternatives(subject, body, from_email, [user_email])
            if html_email_template_name:
                html_email = loader.render_to_string(html_email_template_name, context)
                email_message.attach_alternative(html_email, 'text/html')

            send_tracked_email_message(
                email_message,
                context_type='password_reset',
                triggered_by=user,
            )


class StyledSetPasswordForm(SetPasswordForm):
    def __init__(self, user, *args, **kwargs):
        super().__init__(user, *args, **kwargs)
        self.fields['new_password1'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Crea una nueva contrasena',
            'autocomplete': 'new-password',
        })
        self.fields['new_password2'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Repite la nueva contrasena',
            'autocomplete': 'new-password',
        })


class ManualEmailForm(forms.Form):
    recipient = forms.EmailField(label='Destinatario')
    subject = forms.CharField(label='Asunto', max_length=255)
    message = forms.CharField(label='Mensaje', widget=forms.Textarea)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['recipient'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'correo@destino.com',
            'autocomplete': 'email',
        })
        self.fields['subject'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Asunto del correo',
        })
        self.fields['message'].widget.attrs.update({
            'class': 'form-control',
            'rows': 8,
            'placeholder': 'Escribe aqui el contenido del correo.',
        })


class DoctorProfileForm(forms.ModelForm):
    MAX_FILE_SIZE = 2 * 1024 * 1024
    MAX_DIMENSIONS = (2000, 2000)

    class Meta:
        model = User
        fields = (
            'full_name',
            'specialties',
            'professional_license',
            'office_name',
            'office_address',
            'profile_bio',
            'photo',
            'phone',
            'email',
        )
        widgets = {
            'full_name': forms.TextInput(attrs={'class': 'form-control'}),
            'specialties': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej. Medicina general, Pediatria'}),
            'professional_license': forms.TextInput(attrs={'class': 'form-control'}),
            'office_name': forms.TextInput(attrs={'class': 'form-control'}),
            'office_address': forms.TextInput(attrs={'class': 'form-control'}),
            'profile_bio': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'photo': DoctorPhotoWidget(attrs={'class': 'form-control', 'accept': 'image/*'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['photo'].widget.attrs.update({'class': 'form-control'})
        self.fields['photo'].help_text = 'Sube una imagen JPG o PNG de hasta 2 MB. Se ajustara automaticamente.'

    def clean_photo(self):
        photo = self.cleaned_data.get('photo')
        if not photo:
            return photo

        if photo.size > self.MAX_FILE_SIZE:
            raise forms.ValidationError('La foto debe pesar como maximo 2 MB.')

        try:
            with Image.open(photo) as image:
                width, height = image.size
        except OSError as error:
            raise forms.ValidationError('El archivo seleccionado no es una imagen valida.') from error

        photo.seek(0)

        if width > self.MAX_DIMENSIONS[0] or height > self.MAX_DIMENSIONS[1]:
            raise forms.ValidationError('La foto no debe exceder 2000 x 2000 pixeles.')

        return photo
