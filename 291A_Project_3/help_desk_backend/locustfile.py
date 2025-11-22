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
        if response.status_code == 200 or response.status_code == 201:
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
            name="/conversations"
        )
        if response.status_code == 200 or response.status_code == 201:
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
            name="/messages/create"
        )
        return response.status_code == 200 or response.status_code == 201

    # def expert_queue(self, user):
    #     response = self.client.get(
    #         "/expert/queue",
    #         headers=self.auth_headers(user.get("auth_token")),
    #         name="/expert/queue"
    #     )



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

# class ExpertUser(HttpUser, ChatBackend):
#     weight = 7
#     wait_time = between(5, 10)

# NOTE: Jonathan Cheng code testing
class InitiatorUser(HttpUser, ChatBackend):
    """
    Persona: Regular user (initiator) who creates conversations and waits for expert help.
    
    Behavior:
    - Creates new conversations seeking expert assistance
    - Sends messages describing their problem
    - Checks for expert responses
    - Polls for updates while waiting
    - Reads and responds to expert messages
    """
    weight = 3
    wait_time = between(3, 10)

    def on_start(self):
        """Initialize user - register or login."""
        self.last_check_time = None
        username = user_name_generator.generate_username()
        password = username
        self.user = self.login(username, password) or self.register(username, password, is_expert=False)
        if not self.user:
            raise Exception(f"Failed to login or register user {username}")
        
        self.my_conversations = []

    @task(3)
    def create_conversation_and_send_message(self):
        """Create a new conversation and send initial message."""
        conversation_id = self.create_convo(self.user)
        if conversation_id:
            self.my_conversations.append(conversation_id)
            # Send initial message
            self.send_message(self.user, conversation_id)
    
    @task(5)
    def check_for_responses(self):
        """Check conversations for new messages from experts."""
        if self.my_conversations:
            conversation_id = random.choice(self.my_conversations)
            response = self.client.get(
                f"/conversations/{conversation_id}/messages",
                headers=self.auth_headers(self.user.get("auth_token")),
                name="/conversations/[id]/messages"
            )
        elif user_store.conversations:
            conversation_id = user_store.get_random_convo()
            if conversation_id:
                response = self.client.get(
                    f"/conversations/{conversation_id}/messages",
                    headers=self.auth_headers(self.user.get("auth_token")),
                    name="/conversations/[id]/messages"
                )
    
    @task(4)
    def respond_to_expert(self):
        """Send a follow-up message in an existing conversation."""
        conversation_id = (random.choice(self.my_conversations) if self.my_conversations 
                          else user_store.get_random_convo())
        if conversation_id:
            self.send_message(self.user, conversation_id)
    
    @task(2)
    def browse_my_conversations(self):
        """Browse the user's conversation list."""
        response = self.client.get(
            "/conversations",
            headers=self.auth_headers(self.user.get("auth_token")),
            name="/conversations"
        )
        
        if response.status_code == 200:
            conversations = response.json()
            self.my_conversations = [c.get("id") for c in conversations if c.get("id")]
    
    @task(6)
    def poll_for_updates(self):
        """Poll for updates (conversations and messages)."""
        self.check_conversation_updates(self.user)
        self.check_message_updates(self.user)
        self.last_check_time = datetime.utcnow()


class ExpertUser2(HttpUser, ChatBackend):
    """
    Persona: Expert user who monitors the queue, claims conversations, and helps initiators.
    
    Behavior:
    - Monitors expert queue for waiting conversations
    - Claims conversations from the queue
    - Responds to initiator messages
    - Manages multiple active conversations
    - Polls for updates in assigned conversations
    - Occasionally unclaims conversations when done
    """
    weight = 2
    wait_time = between(2, 8)

    def on_start(self):
        """Initialize expert user."""
        self.last_check_time = None
        username = user_name_generator.generate_username() + "_expert"
        password = username
        self.user = self.login(username, password) or self.register(username, password, is_expert=True)
        if not self.user:
            raise Exception(f"Failed to login or register expert {username}")
        
        self.my_claimed_conversations = []
    
    @task(6)
    def monitor_expert_queue(self):
        """Check the expert queue for waiting conversations."""
        response = self.client.get(
            "/expert/queue",
            headers=self.auth_headers(self.user.get("auth_token")),
            name="/expert/queue"
        )
        
        if response.status_code == 200:
            data = response.json()
            assigned = data.get("assignedConversations", [])
            
            # Update local tracking
            self.my_claimed_conversations = [c.get("id") for c in assigned if c.get("id")]
    
    @task(5)
    def claim_waiting_conversation(self):
        """Claim a conversation from the waiting queue."""
        conversation_id = user_store.get_waiting_convo()
        if conversation_id:
            response = self.client.post(
                f"/expert/conversations/{conversation_id}/claim",
                headers=self.auth_headers(self.user.get("auth_token")),
                name="/expert/conversations/[id]/claim"
            )
            
            if response.status_code == 200:
                user_store.mark_convo_claimed(conversation_id)
                self.my_claimed_conversations.append(conversation_id)
                
                # Send initial expert response
                self.send_message(self.user, conversation_id)
    
    @task(7)
    def respond_to_initiator(self):
        """Send a response message in a claimed conversation."""
        if not self.my_claimed_conversations:
            return
        
        conversation_id = random.choice(self.my_claimed_conversations)
        self.send_message(self.user, conversation_id)
    
    @task(4)
    def read_conversation_messages(self):
        """Read messages from an assigned conversation."""
        if not self.my_claimed_conversations:
            return
        
        conversation_id = random.choice(self.my_claimed_conversations)
        response = self.client.get(
            f"/conversations/{conversation_id}/messages",
            headers=self.auth_headers(self.user.get("auth_token")),
            name="/conversations/[id]/messages"
        )
    
    @task(1)
    def unclaim_conversation(self):
        """Unclaim a conversation (mark as resolved)."""
        if not self.my_claimed_conversations:
            return
        
        # Only unclaim with 30% probability to keep some active
        if random.random() > 0.3:
            return
        
        conversation_id = random.choice(self.my_claimed_conversations)
        response = self.client.post(
            f"/expert/conversations/{conversation_id}/unclaim",
            headers=self.auth_headers(self.user.get("auth_token")),
            name="/expert/conversations/[id]/unclaim"
        )
        
        if response.status_code == 200:
            self.my_claimed_conversations.remove(conversation_id)
            # Put back in waiting queue
            user_store.add_convo(conversation_id, status='waiting')
    
    @task(3)
    def poll_expert_updates(self):
        """Poll for expert queue updates."""
        self.check_expert_queue_updates(self.user)
        self.check_conversation_updates(self.user)
        self.check_message_updates(self.user)
        self.last_check_time = datetime.utcnow()