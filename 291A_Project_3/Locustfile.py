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
        self.conversations = []
        self.convo_lock = threading.Lock()

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

    def add_convo(self, convo_id):
        with self.convo_lock:
            self.conversations.append(convo_id)
    
    def get_random_convo(self):
        with self.convo_lock:
            if not self.conversations:
                return None
            return random.choice(self.conversations)



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
        if response.status.code == 200 or response.status.code == 201:
            data = response.json()
            return user_store.store_user(username, data.get("token"), data.get("user", {}).get("id"))
        return None

    def auth_headers(self, token):
        return {"Authorization": f"Bearer {token}"}

    def create_convo(self, user):
        title = f"Conversation {random.randint(1, 10000) * random.randint(1, 10000)}"
        response = self.client.post(
            "/conversations",
            json={"title": title},
            headers=self.auth_headers(user.get("auth_token")),
            name="/conversations#create"
        )
        if response.status.code == 200 or response.status.code == 201:
            data = response.json()
            user_store.add_convo(data["id"])
            return True
        return False
    
    def send_message(self, user, convo_id):
        content = f"Message {random.randint(1, 10000) * random.randint(1, 10000)}"
        response = self.client.post(
            "/messages",
            json={"conversationId": convo_id, "content": content},
            headers=self.auth_headers(user.get("auth_token")),
            name="/messages#create"
        )
        return response.status.code == 200 or response.status.code == 201


    def check_conversation_updates(self, user):
        """Check for conversation updates."""
        params = {"userId": user.get("user_id")}
        if self.last_check_time:
            params["since"] = self.last_check_time.isoformat()

        response = self.client.get(
            "/api/conversations/updates",
            params=params,
            headers=self.auth_headers(user.get("auth_token")),
            name="/api/conversations/updates"
        )

        return response.status_code == 200

    def check_message_updates(self, user):
        """Check for message updates."""
        params = {"userId": user.get("user_id")}
        if self.last_check_time:
            params["since"] = self.last_check_time.isoformat()

        response = self.client.get(
            "/api/messages/updates",
            params=params,
            headers=self.auth_headers(user.get("auth_token")),
            name="/api/messages/updates"
        )

        return response.status_code == 200


    def check_expert_queue_updates(self, user):
        """Check for expert queue updates"""
        params = {"expertId": user.get("user_id")}
        if self.last_check_time:
            params["since"] = self.last_check_time.isoformat()

        response = self.client.get(
            "/api/expert-queue/updates",
            params=params,
            headers=self.auth_headers(user.get("auth_token")),
            name="/api/expert-queue/updates"
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

class NewUser(HttpUser, ChatBackend):
    # 1 out of 10 users, registers and does very little
    weight = 1
    wait_time = between(10, 20)

    def on_start(self):
        # Register a user (or login) on start, create a conversation and send a message
        self.last_check_time = None
        username = user_name_generator.generate_username()
        password = username
        self.user = self.register(username, password)
        if not self.user:
            self.user = self.login(username, password)
        if not self.user:
            raise Exception(f"Failed to register new user {username}")
        if self.create_convo(self.user):
            cid = user_store.get_random_convo()
            if cid:
                self.send_message(self.user, cid)

    @task
    def browse_updates(self):
        # New user occasionally polls for updates
        self.check_conversation_updates(self.user)
        self.check_message_updates(self.user)
        self.last_check_time = datetime.utcnow()


class ActiveUser(HttpUser, ChatBackend):
    """
    Persona: Existing active user.
    Logs as a pre-registered user, creates conversations,
    sends messages, browses existing convos.
    """
    weight = 5
    wait_time = between(1, 3)

    def on_start(self):
        self.last_check_time = None

        # Choose an existing user from store.
        # If no users exist yet, create one.
        try:
            self.user = user_store.get_random_user()
        except Exception:
            # fallback if no users exist yet
            username = user_name_generator.generate_username()
            password = username
            self.user = self.register(username, password)

        if not self.user:
            raise Exception("ActiveUser could not acquire or create a valid user")

        # create an initial convo
        self.create_convo(self.user)

    @task(5)
    def create_conversation(self):
        # Frequent behavior: create new conversations
        self.create_convo(self.user)

    @task(10)
    def post_message(self):
        # Post messages in random existing conversations
        cid = user_store.get_random_convo()
        if cid:
            self.send_message(self.user, cid)
        return

    @task(3)
    def poll_updates(self):
        # Actively browse updates
        self.check_message_updates(self.user)
        self.check_conversation_updates(self.user)
        self.last_check_time = datetime.utcnow()

    # @task(2)
    # def read_random_conversation(self):
    #     # Simulate navigating to a conversation page
    #     cid = user_store.get_random_convo()
    #     if not cid:
    #         return
    #     response = self.client.get(
    #         f"/conversations/{cid}",
    #         headers=self.auth_headers(self.user.get("auth_token")),
    #         name="/conversations#show"
    #     )
    #     return response.status_code == 200
