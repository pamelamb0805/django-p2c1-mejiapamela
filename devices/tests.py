from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from . import services


class ServicesTests(TestCase):
    def test_load_json_returns_a_list(self):
        self.assertIsInstance(services.load_json("zones.json"), list)

    def test_find_by_id_returns_item_or_none(self):
        zones = services.load_json("zones.json")
        self.assertEqual(services.find_by_id(zones, 1)["name"], "Norte")
        self.assertIsNone(services.find_by_id(zones, 999))

    def test_every_device_points_to_existing_zone_and_category(self):
        zones = services.load_json("zones.json")
        categories = services.load_json("categories.json")
        for device in services.load_json("devices.json"):
            self.assertIsNotNone(services.find_by_id(zones, device["zone_id"]))
            self.assertIsNotNone(services.find_by_id(categories, device["category_id"]))


class ZoneViewsTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user("ana", password="x")

    def setUp(self):
        self.client.force_login(self.user)

    def test_login_is_required(self):
        self.client.logout()
        response = self.client.get(reverse("devices:zone_list"))
        self.assertEqual(response.status_code, 302)

    def test_zone_list(self):
        response = self.client.get(reverse("devices:zone_list"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Austral")

    def test_zone_with_alert_status(self):
        # Norte: 18.4 + 12.5 + 65.7 = 96.6 kWh, límite 23.0
        response = self.client.get(reverse("devices:zone_detail", args=[1]))
        self.assertEqual(response.context["status"], "ALERTA")
        self.assertEqual(response.context["total_kwh"], 96.6)
        self.assertEqual(response.context["count"], 3)

    def test_zone_with_normal_status(self):
        # Sur: 0.5 + 22.9 = 23.4 kWh, límite 79.5
        response = self.client.get(reverse("devices:zone_detail", args=[3]))
        self.assertEqual(response.context["status"], "NORMAL")

    def test_zone_without_devices_shows_empty_message(self):
        response = self.client.get(reverse("devices:zone_detail", args=[4]))
        self.assertEqual(response.context["count"], 0)
        self.assertContains(response, "no tiene dispositivos")

    def test_unknown_zone_returns_404(self):
        response = self.client.get(reverse("devices:zone_detail", args=[999]))
        self.assertEqual(response.status_code, 404)