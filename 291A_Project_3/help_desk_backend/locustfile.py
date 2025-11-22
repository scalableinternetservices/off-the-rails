"""
Locust load test for chat-backend-rails application.

User personas:
1. New user registering for the first time (1 in every 10 users)
2. Polling user that checks for updates every 5 seconds
3. Active user that uses existing usernames to create conversations, post messages, and browse
"""

import random
import threading
from datetime import datetime
from locust import HttpUser, task, between

def auth_headers(token):
    return {"Authorization": f"Bearer {token}"}

# Configuration
MAX_USERS = 10000

class UserNameGenerator:
    PRIME_NUMBERS = [2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47, 53, 59, 61, 67, 71, 73, 79, 83, 89, 97]

    def __init__(self, max_users=MAX_USERS, seed=None, prime_number=None):
        self.seed = seed or random.randint(0, max_users)
        self.prime_number = prime_number or random.choice(self.PRIME_NUMBERS)
        self.current_index = -1
        self.max_users = max_users
    
    def generate_username(self):
        self.current_index += 1
        return f"user_{(self.seed + self.current_index * self.prime_number) % self.max_users}"


class UserStore:
    def __init__(self):
        self.used_usernames = {}
        self.username_lock = threading.Lock()

    def get_random_user(self):
        with self.username_lock:
            random_username = random.choice(list(self.used_usernames.keys()))
            return self.used_usernames[random_username]

    def store_user(self, username, auth_token, user_id):
        with self.username_lock:
            self.used_usernames[username] = {
                "username": username,
                "auth_token": auth_token,
                "user_id": user_id
            }
            return self.used_usernames[username]


user_store = UserStore()
user_name_generator = UserNameGenerator(max_users=MAX_USERS)

class ChatBackend():
    """
    Base class for all user personas.
    Provides common authentication and API interaction methods.
    """        
    
    def login(self, username, password):
        """Login an existing user."""
        response = self.client.post(
            "/auth/login",
            json={"username": username, "password": password},
            name="/auth/login"
        )
        if response.status_code == 200:
            data = response.json()
            return user_store.store_user(username, data.get("token"), data.get("user", {}).get("id"))
        return None
        
    def register(self, username, password):
        response = self.client.post(
            "/auth/register",
            json={"username": username, "password": password},
            name="/auth/register"
        )
        if response.status_code == 201:
            data = response.json()
            return user_store.store_user(
                username,
                data["token"],
                data["user"]["id"]
            )
        return None

    def check_conversation_updates(self, user):
        """Check for conversation updates."""
        # params = {"userId": user.get("user_id")}
        # if self.last_check_time:
        #     params["since"] = self.last_check_time.isoformat()
        
        response = self.client.get(
            "/api/conversations",
            headers=auth_headers(user["auth_token"]),
            name="/api/conversations"
        )
        return response.status_code == 200
    
    def check_message_updates(self, user):
        convos_response = self.client.get(
            "/api/conversations",
            headers=auth_headers(user["auth_token"]),
            name="/api/conversations"
        )

        if convos_response.status_code != 200:
            return False
        
        convos = convos_response.json()
        if not convos:
            return False


        convo = random.choice(convos)
        convo_id = convo["id"]

        messages_response = self.client.get(
            f"/api/messages?conversation_id={convo_id}",
            headers=auth_headers(user["auth_token"]),
            name="/api/messages"
        )

        return messages_response.status_code == 200
    
    def check_expert_queue_updates(self, user):
        response = self.client.get(
            "/expert/queue",
            headers=auth_headers(user["auth_token"]),
            name="/expert/queue"
        )
        return response.status_code == 200
    

class IdleUser(HttpUser, ChatBackend):
    """
    Persona: A user that logs in and is idle but their browser polls for updates.
    Checks for message updates, conversation updates, and expert queue updates every 5 seconds.
    """
    weight = 10
    wait_time = between(5, 5)  # Check every 5 seconds

    def on_start(self):
        """Called when a simulated user starts."""
        self.last_check_time = None
        username = user_name_generator.generate_username()
        password = username
        self.user = self.login(username, password) or self.register(username, password)
        if not self.user:
            raise Exception(f"Failed to login or register user {username}")

    @task
    def poll_for_updates(self):
        """Poll for all types of updates."""
        # Check conversation updates
        self.check_conversation_updates(self.user)
        
        # Check message updates
        self.check_message_updates(self.user)
        
        # Check expert queue updates
        self.check_expert_queue_updates(self.user)
        
        # Update last check time
        self.last_check_time = datetime.utcnow()
        
class LightActiveUser(HttpUser, ChatBackend):
    weight = 3
    wait_time = between(10, 15)

    def on_start(self):
        self.last_check_time = None
        username = user_name_generator.generate_username()
        password = username

        self.user = self.login(username, password) or self.register(username, password)
        if not self.user:
            raise Exception(f"Failed to init LightActiveUser {username}")

    @task(4)
    def view_conversations(self):
        self.client.get(
            "/api/conversations",
            headers=auth_headers(self.user["auth_token"]),
            name="/api/conversations"
        )

    @task(4)
    def view_messages(self):
        convos_response = self.client.get(
            "/api/conversations",
            headers=auth_headers(self.user["auth_token"]),
            name="/api/conversations"
        )
        if convos_response.status_code != 200:
            return
        
        convos = convos_response.json()
        if not convos:
            return

        convo = random.choice(convos)
        convo_id = convo["id"]

        self.client.get(
            f"/api/messages?conversation_id={convo_id}",
            headers=auth_headers(self.user["auth_token"]),
            name="/api/messages"
        )

    @task(1)
    def maybe_create_conversation(self):
        if random.random() < 0.10:
            self.client.post(
                "/api/conversations",
                json={"title": f"test_conv_{random.randint(1, 100000)}"},
                headers=auth_headers(self.user["auth_token"]),
                name="/api/conversations/create"
            )
