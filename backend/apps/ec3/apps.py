from django.apps import AppConfig


class Ec3Config(AppConfig):
    name = "apps.ec3"
    default_auto_field = "django.db.models.AutoField"

    def ready(self):
        from . import checks  # noqa: F401 - register Django deployment checks
        from apps.knowledge.connectors.registry import CONNECTOR_REGISTRY
        from .connector import Ec3Connector

        CONNECTOR_REGISTRY["ec3_openepd"] = Ec3Connector
