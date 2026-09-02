from django.apps import AppConfig


class AnalyticsConfig(AppConfig):
    name = "apps.analytics"
    label = "analytics"

    def ready(self):
        from django.db.models.signals import post_migrate

        from .signals import ensure_environmental_catalog_after_migrate

        post_migrate.connect(
            ensure_environmental_catalog_after_migrate,
            sender=self,
            dispatch_uid="analytics.ensure_system_environmental_catalog",
        )
