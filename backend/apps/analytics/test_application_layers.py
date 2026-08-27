import ast
import inspect

from django.test import SimpleTestCase

from .policies import activity_core as activity_policies
from .policies import assets as asset_policies
from .policies import ingestion as ingestion_policies
from .policies import platform as platform_policies
from .selectors import activity_core as activity_selectors
from .selectors import assets as asset_selectors
from .selectors import ingestion as ingestion_selectors
from .selectors import operational_context as operational_selectors
from .selectors import platform as platform_selectors
from .selectors import provenance as provenance_selectors
from .services import activity_core as activity_services
from .services import assets as asset_services
from .services import ingestion_v2 as ingestion_services
from .services import operational_context as operational_services
from .services import platform as platform_services


class ApplicationLayerContractTests(SimpleTestCase):
    selector_modules = (
        platform_selectors,
        operational_selectors,
        activity_selectors,
        asset_selectors,
        ingestion_selectors,
        provenance_selectors,
    )
    policy_modules = (
        platform_policies,
        activity_policies,
        asset_policies,
        ingestion_policies,
    )
    service_modules = (
        platform_services,
        operational_services,
        activity_services,
        asset_services,
        ingestion_services,
    )

    def imported_modules(self, module):
        tree = ast.parse(inspect.getsource(module))
        return {
            node.module or ""
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom)
        } | {
            alias.name
            for node in ast.walk(tree)
            if isinstance(node, ast.Import)
            for alias in node.names
        }

    def test_selectors_do_not_expose_mutation_calls(self):
        forbidden = {"save", "create", "update", "delete", "bulk_create"}
        for module in self.selector_modules:
            tree = ast.parse(inspect.getsource(module))
            calls = {
                node.func.attr
                for node in ast.walk(tree)
                if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
            }
            self.assertFalse(calls & forbidden, module.__name__)

    def test_policies_do_not_depend_on_http_drf_or_ai(self):
        for module in self.policy_modules:
            imports = self.imported_modules(module)
            self.assertFalse(
                any(
                    name.startswith(("rest_framework", "django.http")) or "ai" in name
                    for name in imports
                ),
                module.__name__,
            )

    def test_services_do_not_depend_on_drf_response(self):
        for module in self.service_modules:
            imports = self.imported_modules(module)
            self.assertFalse(
                any(name.startswith("rest_framework.response") for name in imports),
                module.__name__,
            )
