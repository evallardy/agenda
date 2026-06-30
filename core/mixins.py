from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin

from users.models import User


class RoleRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    allowed_roles = ()

    def test_func(self):
        user = self.request.user
        return user.is_authenticated and (user.is_superuser or user.role in self.allowed_roles)


class PatientRequiredMixin(RoleRequiredMixin):
    allowed_roles = (User.Role.PACIENTE,)


class DoctorRequiredMixin(RoleRequiredMixin):
    allowed_roles = (User.Role.MEDICO,)
