from django.core import mail
from django.contrib.auth.tokens import default_token_generator
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from smtplib import SMTPServerDisconnected
from unittest.mock import patch

from .models import EmailLog, User
from .tokens import email_verification_token


@override_settings(
    EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
    ALLOWED_HOSTS=['testserver', 'localhost', '127.0.0.1'],
)
class RegistrationFlowTests(TestCase):
    def test_register_creates_inactive_patient_and_sends_verification_email(self):
        email = 'registro.unico@correo.test'
        response = self.client.post(
            reverse('users:register'),
            {
                'full_name': 'Paciente Demo',
                'phone': '5551234567',
                'email': email,
                'password1': 'ClaveSegura789!X',
                'password2': 'ClaveSegura789!X',
            },
        )

        self.assertRedirects(response, reverse('users:verification-sent'))
        user = User.objects.get(email=email)
        self.assertEqual(user.role, User.Role.PACIENTE)
        self.assertFalse(user.is_active)
        self.assertFalse(user.email_verified)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('/usuarios/verificar/', mail.outbox[0].body)
        self.assertTrue(EmailLog.objects.filter(recipient=email, context_type='register_verification', status='sent').exists())

    def test_verify_email_activates_account_and_allows_login_with_email(self):
        user = User.objects.create_user(
            email='paciente.verificar@example.com',
            password='Paciente123!',
            full_name='Paciente Verificar',
            phone='5557654321',
            role=User.Role.PACIENTE,
            is_active=False,
            email_verified=False,
        )

        verify_url = reverse(
            'users:verify-email',
            args=[urlsafe_base64_encode(force_bytes(user.pk)), email_verification_token.make_token(user)],
        )
        response = self.client.get(verify_url, follow=True)

        self.assertRedirects(response, reverse('users:login'))
        user.refresh_from_db()
        self.assertTrue(user.is_active)
        self.assertTrue(user.email_verified)

        login_response = self.client.post(
            reverse('users:login'),
            {'username': user.email, 'password': 'Paciente123!'},
            follow=True,
        )
        self.assertEqual(login_response.status_code, 200)
        self.assertTrue(login_response.wsgi_request.user.is_authenticated)

    def test_register_verify_and_login_end_to_end(self):
        email = 'flujo.registro@example.com'

        response = self.client.post(
            reverse('users:register'),
            {
                'full_name': 'Paciente Flujo Completo',
                'phone': '5551230000',
                'email': email,
                'password1': 'ClaveFuerte123!Z',
                'password2': 'ClaveFuerte123!Z',
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        user = User.objects.get(email=email)
        self.assertFalse(user.is_active)
        self.assertFalse(user.email_verified)
        self.assertEqual(len(mail.outbox), 1)

        verify_url = reverse(
            'users:verify-email',
            args=[urlsafe_base64_encode(force_bytes(user.pk)), email_verification_token.make_token(user)],
        )
        verify_response = self.client.get(verify_url, follow=True)

        self.assertRedirects(verify_response, reverse('users:login'))
        user.refresh_from_db()
        self.assertTrue(user.is_active)
        self.assertTrue(user.email_verified)

        login_response = self.client.post(
            reverse('users:login'),
            {'username': email, 'password': 'ClaveFuerte123!Z'},
            follow=True,
        )

        self.assertEqual(login_response.status_code, 200)
        self.assertTrue(login_response.wsgi_request.user.is_authenticated)


@override_settings(
    EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
    ALLOWED_HOSTS=['testserver', 'localhost', '127.0.0.1'],
)
class PasswordResetFlowTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='paciente.reset@example.com',
            password='Paciente123!',
            full_name='Paciente Reset',
            phone='5551112233',
            role=User.Role.PACIENTE,
            is_active=True,
            email_verified=True,
        )

    def test_password_reset_sends_email_and_updates_password(self):
        response = self.client.post(
            reverse('users:password-reset'),
            {'email': self.user.email},
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('/usuarios/recuperar-contrasena/', mail.outbox[0].body)
        self.assertTrue(
            EmailLog.objects.filter(
                recipient=self.user.email,
                context_type='password_reset',
                status='sent',
            ).exists()
        )

        confirm_url = reverse(
            'users:password-reset-confirm',
            args=[urlsafe_base64_encode(force_bytes(self.user.pk)), default_token_generator.make_token(self.user)],
        )
        confirm_get_response = self.client.get(confirm_url, follow=True)
        confirm_post_url = confirm_get_response.request['PATH_INFO']

        confirm_response = self.client.post(
            confirm_post_url,
            {
                'new_password1': 'NuevaClave789!X',
                'new_password2': 'NuevaClave789!X',
            },
            follow=True,
        )

        self.assertEqual(confirm_response.status_code, 200)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('NuevaClave789!X'))

        login_response = self.client.post(
            reverse('users:login'),
            {'username': self.user.email, 'password': 'NuevaClave789!X'},
            follow=True,
        )

        self.assertEqual(login_response.status_code, 200)
        self.assertTrue(login_response.wsgi_request.user.is_authenticated)


@override_settings(
    EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
    ALLOWED_HOSTS=['testserver', 'localhost', '127.0.0.1'],
)
class ManualEmailViewTests(TestCase):
    def setUp(self):
        self.doctor = User.objects.create_user(
            email='doctor.mail@example.com',
            password='Admin12345!',
            full_name='Doctor Mail',
            phone='5558889999',
            role=User.Role.MEDICO,
            is_active=True,
            email_verified=True,
            is_staff=True,
        )

    def test_doctor_can_open_manual_email_view(self):
        self.client.force_login(self.doctor)

        response = self.client.get(reverse('users:manual-email'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Nuevo mensaje')

    def test_doctor_can_send_manual_email(self):
        self.client.force_login(self.doctor)

        response = self.client.post(
            reverse('users:manual-email'),
            {
                'recipient': 'destino@example.com',
                'subject': 'Correo de prueba',
                'message': 'Mensaje enviado desde la nueva vista.',
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ['destino@example.com'])
        self.assertEqual(mail.outbox[0].subject, 'Correo de prueba')
        self.assertTrue(EmailLog.objects.filter(recipient='destino@example.com', context_type='manual_email', status='sent').exists())

    def test_manual_email_view_handles_smtp_errors_without_500(self):
        self.client.force_login(self.doctor)

        with patch('users.views.EmailMessage.send', side_effect=SMTPServerDisconnected('Connection unexpectedly closed')):
            response = self.client.post(
                reverse('users:manual-email'),
                {
                    'recipient': 'destino@example.com',
                    'subject': 'Correo de prueba',
                    'message': 'Mensaje enviado desde la nueva vista.',
                },
            )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'No fue posible enviar el correo')
