from django.contrib import messages
from django.conf import settings
from django.core.mail import EmailMessage
from smtplib import SMTPException
from django.contrib.auth.views import (
    LoginView,
    LogoutView,
    PasswordResetCompleteView,
    PasswordResetConfirmView,
    PasswordResetDoneView,
    PasswordResetView,
)
from django.shortcuts import redirect
from django.template.loader import render_to_string
from django.urls import reverse, reverse_lazy
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from django.views import View
from django.views.generic import CreateView, FormView, TemplateView, UpdateView

from core.mixins import DoctorRequiredMixin

from .forms import (
    DoctorProfileForm,
    EmailAuthenticationForm,
    ManualEmailForm,
    StyledPasswordResetForm,
    StyledSetPasswordForm,
    UserRegistrationForm,
)
from .email_tracking import send_tracked_email_message, send_tracked_mail
from .models import EmailLog
from .models import User
from .tokens import email_verification_token


class RegisterView(CreateView):
    model = User
    form_class = UserRegistrationForm
    template_name = 'users/register.html'
    success_url = reverse_lazy('users:verification-sent')

    def form_valid(self, form):
        self.object = form.save(commit=False)
        user = self.object
        user.is_active = False
        user.role = User.Role.PACIENTE
        user.email_verified = False
        user.save()
        self.send_verification_email(user)
        return redirect(self.get_success_url())

    def send_verification_email(self, user):
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = email_verification_token.make_token(user)
        verify_url = self.request.build_absolute_uri(reverse('users:verify-email', args=[uid, token]))
        subject = render_to_string('users/email/verify_email_subject.txt').strip()
        body = render_to_string('users/email/verify_email_body.txt', {'user': user, 'verify_url': verify_url})
        send_tracked_mail(
            subject=subject,
            message=body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            context_type='register_verification',
            triggered_by=user,
        )


class UserLoginView(LoginView):
    template_name = 'users/login.html'
    authentication_form = EmailAuthenticationForm


class VerificationSentView(TemplateView):
    template_name = 'users/verification_sent.html'


class VerifyEmailView(View):
    def get(self, request, uidb64, token, *args, **kwargs):
        try:
            user_id = force_str(urlsafe_base64_decode(uidb64))
            user = User.objects.get(pk=user_id)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            user = None

        if user and email_verification_token.check_token(user, token):
            user.email_verified = True
            user.is_active = True
            user.save(update_fields=['email_verified', 'is_active'])
            messages.success(request, 'Tu correo fue verificado. Ya puedes iniciar sesion.')
        else:
            messages.error(request, 'El enlace de verificacion no es valido o ya expiro.')
        return redirect('users:login')


class UserLogoutView(LogoutView):
    next_page = reverse_lazy('core:home')


class UserPasswordResetView(PasswordResetView):
    form_class = StyledPasswordResetForm
    template_name = 'users/password_reset_form.html'
    email_template_name = 'users/email/password_reset_body.txt'
    subject_template_name = 'users/email/password_reset_subject.txt'
    success_url = reverse_lazy('users:password-reset-done')


class UserPasswordResetDoneView(PasswordResetDoneView):
    template_name = 'users/password_reset_done.html'


class UserPasswordResetConfirmView(PasswordResetConfirmView):
    form_class = StyledSetPasswordForm
    template_name = 'users/password_reset_confirm.html'
    success_url = reverse_lazy('users:password-reset-complete')


class UserPasswordResetCompleteView(PasswordResetCompleteView):
    template_name = 'users/password_reset_complete.html'


class ManualEmailSendView(DoctorRequiredMixin, FormView):
    form_class = ManualEmailForm
    template_name = 'users/manual_email_form.html'
    success_url = reverse_lazy('users:manual-email')

    def get_initial(self):
        initial = super().get_initial()
        initial['recipient'] = self.request.user.email
        initial['subject'] = 'Mensaje desde Agenda Consultorio'
        return initial

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['recent_email_logs'] = EmailLog.objects.filter(triggered_by=self.request.user)[:10]
        return context

    def form_valid(self, form):
        try:
            email = EmailMessage(
                form.cleaned_data['subject'],
                form.cleaned_data['message'],
                settings.DEFAULT_FROM_EMAIL,
                [form.cleaned_data['recipient']],
            )
            send_tracked_email_message(
                email,
                context_type='manual_email',
                triggered_by=self.request.user,
            )
        except (OSError, SMTPException) as error:
            form.add_error(None, f'No fue posible enviar el correo: {error}')
            return self.form_invalid(form)

        messages.success(self.request, f"Correo enviado a {form.cleaned_data['recipient']}.")
        return super().form_valid(form)


class DoctorProfileUpdateView(DoctorRequiredMixin, UpdateView):
    form_class = DoctorProfileForm
    template_name = 'users/doctor_profile_form.html'
    success_url = reverse_lazy('users:doctor-profile')

    def get_object(self, queryset=None):
        return self.request.user

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['files'] = self.request.FILES or None
        return kwargs

    def form_valid(self, form):
        messages.success(self.request, 'El perfil del medico fue actualizado.')
        return super().form_valid(form)
