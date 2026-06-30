from django.urls import path

from .views import (
    ManualEmailSendView,
    RegisterView,
    DoctorProfileUpdateView,
    UserLoginView,
    UserLogoutView,
    UserPasswordResetCompleteView,
    UserPasswordResetConfirmView,
    UserPasswordResetDoneView,
    UserPasswordResetView,
    VerificationSentView,
    VerifyEmailView,
)

app_name = 'users'

urlpatterns = [
    path('registro/', RegisterView.as_view(), name='register'),
    path('ingresar/', UserLoginView.as_view(), name='login'),
    path('salir/', UserLogoutView.as_view(), name='logout'),
    path('correo/manual/', ManualEmailSendView.as_view(), name='manual-email'),
    path('perfil-medico/', DoctorProfileUpdateView.as_view(), name='doctor-profile'),
    path('recuperar-contrasena/', UserPasswordResetView.as_view(), name='password-reset'),
    path('recuperar-contrasena/enviado/', UserPasswordResetDoneView.as_view(), name='password-reset-done'),
    path('recuperar-contrasena/<uidb64>/<token>/', UserPasswordResetConfirmView.as_view(), name='password-reset-confirm'),
    path('recuperar-contrasena/completa/', UserPasswordResetCompleteView.as_view(), name='password-reset-complete'),
    path('verificacion-enviada/', VerificationSentView.as_view(), name='verification-sent'),
    path('verificar/<uidb64>/<token>/', VerifyEmailView.as_view(), name='verify-email'),
]
