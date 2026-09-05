from io import StringIO

from django.core.management import call_command, CommandError
from django.test import TestCase

from .models import FactorAmbiental, VersionFactorAmbiental


class ImportHuellaChileFactorsRetirementTests(TestCase):
    def test_legacy_command_is_retired_and_cannot_seed_versions(self):
        before = VersionFactorAmbiental.objects.count()
        with self.assertRaisesMessage(CommandError, "Comando retirado"):
            call_command("import_huellachile_factors", stdout=StringIO())
        self.assertEqual(VersionFactorAmbiental.objects.count(), before)

    def test_system_shells_remain_global_without_seeded_versions(self):
        fuels = FactorAmbiental.objects.filter(
            organizacion__isnull=True, codigo__startswith="huellachile-"
        )
        self.assertEqual(fuels.count(), 6)
        self.assertEqual(
            VersionFactorAmbiental.objects.filter(factor__in=fuels).count(), 0
        )
