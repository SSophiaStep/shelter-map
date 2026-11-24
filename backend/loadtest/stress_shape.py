"""Stress / spike: сходинки навантаження до точки зламу, різкий пік і спад.

Запуск (з папки backend):
  locust -f loadtest/locustfile.py,loadtest/stress_shape.py --headless \
         --host http://127.0.0.1:8000 --csv loadtest/results/stress \
         --csv-full-history --only-summary
Сходинки по 60 с: 50 → 100 → 150 → 200 → 300 → 400 користувачів, потім spike 600
на 60 с і повернення до 50 користувачів на 90 с (перевірка відновлення).
"""

from locust import LoadTestShape

STEPS = [(60, 50), (120, 100), (180, 150), (240, 200), (300, 300), (360, 400)]
SPIKE = (420, 600)
RECOVERY = (510, 50)


class StressShape(LoadTestShape):
    def tick(self):
        t = self.get_run_time()
        for end, users in [*STEPS, SPIKE, RECOVERY]:
            if t < end:
                return users, 100
        return None
