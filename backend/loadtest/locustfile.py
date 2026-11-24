"""Сценарій навантаження: типова поведінка людини під час тривоги.

Більшість запитів - пошук найближчих укриттів поруч із кількома містами
(різкі піки читання), решта - перегляд об'єкта, відгуки, профіль і рідкісний запис.
Запуск: locust -f loadtest/locustfile.py --host http://127.0.0.1:8000
"""

import random

from locust import FastHttpUser, between, task

HOTSPOTS = [
    (50.4501, 30.5234),
    (49.8397, 24.0297),
    (46.4825, 30.7233),
    (49.9935, 36.2304),
    (48.4647, 35.0462),
    (48.2915, 25.9403),
    (48.6208, 22.2879),
    (51.4982, 31.2893),
]
PASSWORD = "LoadTest123"
FORM = {"Content-Type": "application/x-www-form-urlencoded"}


def random_point() -> tuple[float, float]:
    lat, lon = random.choice(HOTSPOTS)
    # розкид ~1 км навколо центру міста
    return lat + random.uniform(-0.01, 0.01), lon + random.uniform(-0.015, 0.015)


class CitizenUser(FastHttpUser):
    wait_time = between(0.1, 0.5)

    def on_start(self):
        email = f"load{random.randint(0, 99)}@example.com"
        with self.client.post(
            "/auth/login",
            data=f"username={email}&password={PASSWORD}",
            headers=FORM,
            name="/auth/login",
            catch_response=True,
        ) as response:
            if response.status_code == 200:
                token = response.json()["access_token"]
                self.auth = {"Authorization": f"Bearer {token}"}
            else:
                self.auth = {}
                response.failure(f"login failed: {response.status_code}")

    @task(10)
    def nearby(self):
        lat, lon = random_point()
        radius = random.choice([1000, 2000, 3000])
        self.client.get(
            f"/places/nearby?lat={lat:.5f}&lon={lon:.5f}&radius_m={radius}",
            name="/places/nearby",
        )

    @task(2)
    def nearby_heating(self):
        lat, lon = random_point()
        self.client.get(
            f"/places/nearby?lat={lat:.5f}&lon={lon:.5f}&radius_m=3000&type=heating",
            name="/places/nearby?type=heating",
        )

    @task(3)
    def place_details(self):
        self.client.get(f"/places/{random.randint(1, 100000)}", name="/places/{id}")

    @task(2)
    def place_reports(self):
        self.client.get(
            f"/places/{random.randint(1, 100000)}/reports", name="/places/{id}/reports"
        )

    @task(2)
    def profile(self):
        self.client.get("/auth/me", headers=self.auth, name="/auth/me")

    @task(1)
    def add_report(self):
        self.client.post(
            f"/places/{random.randint(1, 100000)}/reports",
            json={"text": "Укриття відчинене"},
            headers=self.auth,
            name="/places/{id}/reports [POST]",
        )
