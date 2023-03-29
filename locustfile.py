# locustfile.py
from locust import HttpUser, between, task


class WebsiteTestUser(HttpUser):
    wait_time = between(1, 2)

    @task
    def my_task(self):
        self.client.verify = False
        self.client.post(
            "/auth/signin/", json={"username": "test@test.com", "password": "test"}
        )
