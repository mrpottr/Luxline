"""Monitoring endpoint URL configuration tests."""

import unittest
from types import SimpleNamespace
from unittest.mock import patch

from backend.app.core.config import settings
from backend.app.routers.admin import get_monitoring_health, get_monitoring_metrics


class TestMonitoringConfig(unittest.TestCase):
    def setUp(self):
        self.prometheus_url = settings.prometheus_internal_url
        self.grafana_url = settings.grafana_internal_url
        object.__setattr__(settings, "prometheus_internal_url", "http://prometheus.test:19090")
        object.__setattr__(settings, "grafana_internal_url", "http://grafana.test:13000")

    def tearDown(self):
        object.__setattr__(settings, "prometheus_internal_url", self.prometheus_url)
        object.__setattr__(settings, "grafana_internal_url", self.grafana_url)

    @patch("backend.app.routers.admin.requests.get")
    def test_metrics_uses_configured_prometheus_url_and_preserves_response_shape(self, get):
        get.return_value = SimpleNamespace(json=lambda: {"status": "success"})
        response = get_monitoring_metrics(_admin=object())
        self.assertEqual(response, {"status": "ok", "data": {"status": "success"}})
        self.assertEqual(get.call_args.args[0], "http://prometheus.test:19090/api/v1/query")

    @patch("backend.app.routers.admin.requests.get")
    def test_health_uses_configured_urls_and_keeps_public_links_stable(self, get):
        get.return_value = SimpleNamespace(status_code=200)
        response = get_monitoring_health(_admin=object())
        self.assertEqual(get.call_args_list[0].args[0], "http://prometheus.test:19090/-/healthy")
        self.assertEqual(get.call_args_list[1].args[0], "http://grafana.test:13000/api/health")
        self.assertEqual(response["grafana_url"], "http://localhost:3000")
        self.assertEqual(response["prometheus_url"], "http://localhost:9090")
