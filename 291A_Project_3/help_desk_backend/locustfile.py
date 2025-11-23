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
        self.conversations = []  # Keep for backward compatibility if needed
        self.convo_lock = threading.Lock()
        self.user_conversations = {}  # NEW: Track conversations per username
        self.user_convo_lock = threading.Lock()

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

    def add_convo(self, convo_id, username=None):  # Add username parameter
        with self.convo_lock:
            self.conversations.append(convo_id)
        
        # Also track per username
        if username:
            with self.user_convo_lock:
                if username not in self.user_conversations:
                    self.user_conversations[username] = []
                self.user_conversations[username].append(convo_id)
    
    def get_random_convo(self):
        with self.convo_lock:
            if not self.conversations:
                return None
            return random.choice(self.conversations)
    
    def get_user_convo(self, username):  # NEW: Get conversation for specific username
        with self.user_convo_lock:
            if username not in self.user_conversations or not self.user_conversations[username]:
                return None
            return random.choice(self.user_conversations[username])


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
        if response.status_code in (200, 201): #changed to make it look a bit cleaner
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
        if response.status_code in (200, 201):
            data = response.json()
            convo_id = data["id"]
            user_store.add_convo(convo_id, user.get("username"))  # Pass username
            return convo_id  # Return the ID instead of True
        return None  # Return None instead of False
    
    def send_message(self, user, convo_id):
        content = f"Message {random.randint(1, 10000) * random.randint(1, 10000)}"
        response = self.client.post(
            "/messages",
            json={"conversationId": convo_id, "content": content},
            headers=self.auth_headers(user.get("auth_token")),
            name="/messages"
        )
        return response.status_code in (200, 201)


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
            raise Exception(f"IdleUser: Failed to login or register user {username}")

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
    weight = 2
    wait_time = between(10, 20)

    def on_start(self):
        # Register a user (or login) on start, create a conversation and send a message
        self.last_check_time = None
        username = user_name_generator.generate_username()
        password = username
        self.user = self.register(username, password) or self.login(username, password)
        #if not self.user:
        #    self.user = self.login(username, password)
        if not self.user:
            raise Exception(f"NewUser: Failed to register new user {username}")
        if self.create_convo(self.user):
            # cid = user_store.get_random_convo() #NOTE: changed
            cid = user_store.get_user_convo(username)
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
        # cid = user_store.get_random_convo() NOTE: changed
        cid = user_store.get_user_convo(self.user.get("username"))
        if cid:
            self.send_message(self.user, cid)
        return

    @task(3)
    def poll_updates(self):
        # Actively browse updates
        self.check_message_updates(self.user)
        self.check_conversation_updates(self.user)
        self.last_check_time = datetime.utcnow()


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
        self.user = self.login(username, password) or self.register(username, password)
        if not self.user:
            raise Exception(f"InitiatorUser: Failed to login or register user {username}")
        
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
                name="/conversations/{conversation_id}/messages"
            )
        elif user_store.conversations:
            conversation_id = user_store.get_user_convo(self.user.get("username"))
            if conversation_id:
                response = self.client.get(
                    f"/conversations/{conversation_id}/messages",
                    headers=self.auth_headers(self.user.get("auth_token")),
                    name="/conversations/{conversation_id}/messages"
                )
    
    @task(4)
    def respond_to_expert(self):
        """Send a follow-up message in an existing conversation."""
        conversation_id = (random.choice(self.my_conversations) if self.my_conversations 
                          else user_store.get_user_convo(self.user.get("username")))
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

class ExpertUser(HttpUser, ChatBackend):
    """
    Persona: An expert user who checks the queue, claims conversations, replies, and polls for updates.
    """

    weight = 3       # Less common than regular users
    wait_time = between(2, 6)

    def on_start(self):
        """Login or register expert, ensure profile exists."""
        username = user_name_generator.generate_username()
        password = username

        self.user = self.login(username, password) or self.register(username, password)
        if not self.user:
            raise Exception(f"ExpertUser: Failed to login/register expert {username}")

        self.ensure_expert_profile()

        self.last_check_time = None

        self.active_conversations = {}

    # Helper: Ensure expert profile exists
    def ensure_expert_profile(self):
        response = self.client.get(
            "/expert/profile",
            headers=self.auth_headers(self.user["auth_token"]),
            name="/expert/profile"
        )
        if response.status_code == 404:
            self.client.put(
                "/expert/profile",
                json={
                    "bio": "Load test expert",
                    "knowledgeBaseLinks": ["https://example.com/help"]
                },
                headers=self.auth_headers(self.user["auth_token"]),
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
            headers=self.auth_headers(self.user["auth_token"]),
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
                # self.claim_conversation(convo["id"])

                # NEW: idk if this prevents race conditions but lets see
                claimed = self.claim_conversation(convo["id"])
                if not claimed:
                    continue

        self.check_message_updates(self.user)
        self.check_conversation_updates(self.user)
        # Manage existing conversations (reply occasionally)
        for convo_id in list(self.active_conversations):
            self.reply_to_conversation(convo_id)

        self.last_check_time = datetime.utcnow()

    # Claim conversation
    def claim_conversation(self, conversation_id):
        response = self.client.post(
            f"/expert/conversations/{conversation_id}/claim",
            headers=self.auth_headers(self.user["auth_token"]),
            name="/expert/conversations/claim"
        )

        if response.status_code == 200:
            # Track new claimed conversation
            self.active_conversations[conversation_id] = {
                "last_reply": datetime.utcnow()
            }
            #print(f"[{self.user['username']}] Claimed conversation {conversation_id}")
            return True
        #print(f"[{self.user['username']}] Failed to claim conversation {conversation_id} (status {response.status_code})")
        return False # NEW: return false if convo is not claimed bc of race conditions

    def reply_to_conversation(self, convo_id):
        convo_state = self.active_conversations.get(convo_id)
        if not convo_state:
            return

        # Only reply every ~3–10 seconds
        if (datetime.utcnow() - convo_state["last_reply"]).total_seconds() < random.randint(3, 10):
            return

        # Send message
        success = self.send_message(self.user, convo_id)

        if success:
            convo_state["last_reply"] = datetime.utcnow()
            return True
        else:
            # If conversation is closed or message fails, remove it from active
            self.active_conversations.pop(convo_id, None)
            return False


class LightUser(HttpUser, ChatBackend):
    """
    Persona: Light browsing user.
    Logs in or registers, views conversations, views messages,and occasionally creates a conversation.
    """
    weight = 3
    wait_time = between(10, 15)

    def on_start(self):
        self.last_check_time = None
        username = user_name_generator.generate_username()
        password = username

        # Try login → fallback to register
        self.user = self.login(username, password) or self.register(username, password)

        if not self.user:
            raise Exception(f"LightUser: Failed to initialize user {username}")

    @task(4)
    def view_conversations(self):
        """Light user loads their conversation list."""
        self.client.get(
            "/api/conversations",
            headers=self.auth_headers(self.user["auth_token"]),
            name="/api/conversations"
        )

    @task(4)
    def view_messages(self):
        """View messages from a random existing conversation."""
        convos_response = self.client.get(
            "/api/conversations",
            headers=self.auth_headers(self.user["auth_token"]),
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
            headers=self.auth_headers(self.user["auth_token"]),
            name="/api/messages"
        )

    @task(1)
    def maybe_create_conversation(self):
        """10% chance this user creates a new conversation."""
        if random.random() < 0.10:
            response = self.client.post(
                "/api/conversations",
                json={"title": f"test_conv_{random.randint(1, 100000)}"},
                headers=self.auth_headers(self.user["auth_token"]),
                name="/api/conversations/create"
            )

            # Track in user_store if successful
            if response.status_code in (200, 201):
                data = response.json()
                convo_id = data.get("id")
                if convo_id:
                    user_store.add_convo(convo_id, self.user["username"])
