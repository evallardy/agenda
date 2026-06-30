from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend
from django.db.models import Q


class EmailOrUsernameBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        user_model = get_user_model()
        identifier = username or kwargs.get(user_model.USERNAME_FIELD)
        if identifier is None or password is None:
            return None

        try:
            user = user_model.objects.get(Q(email__iexact=identifier) | Q(username__iexact=identifier))
        except user_model.DoesNotExist:
            return None

        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None
