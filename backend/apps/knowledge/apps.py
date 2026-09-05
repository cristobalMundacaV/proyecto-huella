from django.apps import AppConfig


class KnowledgeConfig(AppConfig):
    default_auto_field = "django.db.models.AutoField"
    name = "apps.knowledge"
    label = "knowledge"

    def ready(self):
        from django.db.models.signals import post_migrate
        from .bootstrap import ensure_source_registry_after_migrate
        post_migrate.connect(ensure_source_registry_after_migrate, sender=self, dispatch_uid="knowledge.ensure_source_registry")
