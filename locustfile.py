from locust import HttpUser, task, between
import random

# This is a very simple load test
class BasicUser(HttpUser):
    # Wait 1 to 3 seconds between actions (simulates a fast user)
    wait_time = between(1, 3)

    def on_start(self):
        """
        Run once when the user starts. 
        We generate a random username so we don't crash the DB with duplicates.
        """
        self.username = f"test_user_{random.randint(1, 999999)}"
        self.password = "password123"

    @task(3) # Weight of 3: Happens 3x more often
    def health_check(self):
        """Just pings the server to see if it's up."""
        self.client.get("/health", name="Health Check")

    @task(1) # Weight of 1: Happens less often
    def login_and_register(self):
        """
        Tries to register. If user exists, tries to login.
        This tests if the Database is correctly connected.
        """
        # 1. Try to register
        payload = {"username": self.username, "password": self.password}
        with self.client.post("/auth/register", json=payload, catch_response=True) as response:
            
            # If successful (201) or if user already exists (422), we call it a "success" for this test
            if response.status_code == 201:
                response.success()
            elif response.status_code == 422:
                # User exists, so let's verify login works
                self.client.post("/auth/login", json=payload, name="Login Check")
                response.success()
            else:
                response.failure(f"Unexpected error: {response.status_code}")