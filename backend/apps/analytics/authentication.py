from django.contrib.auth.backends import ModelBackend
from django.contrib.auth.models import User

from .services.identity import normalize_email_identity


class EmailAuthenticationBackend(ModelBackend):
    """Authenticate customers by email while preserving legacy superuser access."""

    def authenticate(self, request, username=None, password=None, email=None, **kwargs):
        identity = normalize_email_identity(email or username)
        if not identity or not password:
            return None
        users = User.objects.filter(email__iexact=identity)
        if users.count() == 1:
            user = users.first()
        elif "@" not in identity:
            user = User.objects.filter(username__iexact=identity, is_superuser=True).first()
        else:
            user = None
        if user and user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None
