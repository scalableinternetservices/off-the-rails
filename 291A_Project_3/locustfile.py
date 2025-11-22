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
        """Register a new user."""
        response = self.client.post(
            "/auth/register",
            json={"username": username, "password": password},
            name="/auth/register"
        )

        if response.status_code == 201:
            data = response.json()
            return user_store.store_user(
                username,
                data.get("token"),
                data.get("user", {}).get("id")
            )

        return None


    def check_conversation_updates(self, user):
        """Check for conversation updates."""
        params = {"userId": user.get("user_id")}
        if self.last_check_time:
            params["since"] = self.last_check_time.isoformat()
        
        response = self.client.get(
            "/api/conversations/updates",
            params=params,
            headers=auth_headers(user.get("auth_token")),
            name="/api/conversations/updates"
        )
        
        return response.status_code == 200
    
    def check_message_updates(self, user):
        """Poll for message updates."""
        params = {"userId": user.get("user_id")}
        if self.last_check_time:
            params["since"] = self.last_check_time.isoformat()

        response = self.client.get(
            "/api/messages/updates",
            params=params,
            headers=auth_headers(user.get("auth_token")),
            name="/api/messages/updates"
        )

        return response.status_code == 200

    
    def check_expert_queue_updates(self, user):
        """Poll for expert queue updates (only works if the user is an expert)."""
        params = {"expertId": user.get("user_id")}
        if self.last_check_time:
            params["since"] = self.last_check_time.isoformat()

        response = self.client.get(
            "/api/expert-queue/updates",
            params=params,
            headers=auth_headers(user.get("auth_token")),
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

class ExpertUser(HttpUser, ChatBackend):
    """
    Persona: An expert user who checks the queue, claims conversations,
    reads messages, replies, and polls for updates.
    """

    weight = 3       # Less common than regular users
    wait_time = between(2, 6)

    def on_start(self):
        """Login or register expert, ensure profile exists."""
        username = user_name_generator.generate_username()
        password = username

        self.user = self.login(username, password) or self.register(username, password)
        if not self.user:
            raise Exception(f"Failed to login/register expert {username}")

        self.ensure_expert_profile()

        self.last_check_time = None

        self.active_conversations = {}

    # Helper: Ensure expert profile exists
    def ensure_expert_profile(self):
        response = self.client.get(
            "/expert/profile",
            headers=auth_headers(self.user["auth_token"]),
            name="/expert/profile"
        )
        if response.status_code == 404:
            self.client.put(
                "/expert/profile",
                json={
                    "bio": "Load test expert",
                    "knowledgeBaseLinks": ["https://example.com/help"]
                },
                headers=auth_headers(self.user["auth_token"]),
                name="/expert/profile (create)"
            )

    # Polling expert queue
    @task(5)
    def poll_expert_queue(self):
        """Poll for updates, claim new conversations, and manage ongoing ones."""

        updated = self.check_expert_queue_updates(self.user)
        if not updated:
            return

        # Fetch full expert queue
        response = self.client.get(
            "/expert/queue",
            headers=auth_headers(self.user["auth_token"]),
            name="/expert/queue"
        )
        if response.status_code != 200:
            return

        data = response.json()
        waiting = data.get("waitingConversations", [])
        assigned = data.get("assignedConversations", [])

        for convo in assigned:
            cid = convo["id"]
            if cid not in self.active_conversations:
                self.active_conversations[cid] = {
                    "last_reply": datetime.utcnow()
                }

        # Claim new conversations if available
        if waiting:
            num_to_claim = min(len(waiting), random.randint(1, 2))
            for convo in waiting[:num_to_claim]:
                self.claim_conversation(convo["id"])

        self.check_message_updates(self.user)
        self.check_conversation_updates(self.user)
        # Manage existing conversations (reply occasionally)
        for convo_id in list(self.active_conversations):
            self.maybe_reply_to_conversation(convo_id)

        self.last_check_time = datetime.utcnow()

    # Claim conversation
    def claim_conversation(self, conversation_id):
        response = self.client.post(
            f"/expert/queue/{conversation_id}/claim",
            headers=auth_headers(self.user["auth_token"]),
            name="/expert/claim"
        )

        if response.status_code == 200:
            # Track new claimed conversation
            self.active_conversations[conversation_id] = {
                "last_reply": datetime.utcnow()
            }

    def maybe_reply_to_conversation(self, convo_id):
        convo_state = self.active_conversations.get(convo_id)
        if not convo_state:
            return

        # Only reply every ~3–10 seconds
        if (datetime.utcnow() - convo_state["last_reply"]).total_seconds() < random.randint(3, 10):
            return

        # Send message
        response = self.client.post(
            "/messages/send",
            json={
                "conversationId": convo_id,
                "senderId": self.user["user_id"],
                "text": random.choice([
                    "Here is a detailed explanation.",
                    "Let's walk through this step by step.",
                    "I can help with that.",
                    "Great question. The issue is likely this..."
                ])
            },
            headers=auth_headers(self.user["auth_token"]),
            name="/messages/send"
        )

        if response.status_code == 200:
            convo_state["last_reply"] = datetime.utcnow()
        else:
            # If conversation is closed, remove it
            self.active_conversations.pop(convo_id, None)

