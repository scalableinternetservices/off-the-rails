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
        self.conversation_lock = threading.Lock()
        self.experts = {}
        self.expert_lock = threading.Lock()
        self.waiting_conversations = []

    def get_random_user(self):
        with self.username_lock:
            if not self.used_usernames:
                return None
            random_username = random.choice(list(self.used_usernames.keys()))
            return self.used_usernames[random_username]

    def store_user(self, username, auth_token, user_id, is_expert=False):
        with self.username_lock:
            self.used_usernames[username] = {
                "username": username,
                "auth_token": auth_token,
                "user_id": user_id,
                "is_expert": is_expert
            }
            if is_expert:
                with self.expert_lock:
                    self.experts[username] = self.used_usernames[username]
            return self.used_usernames[username]
    
    def add_conversation(self, conversation_id, status='waiting'):
        with self.conversation_lock:
            if conversation_id not in self.conversations:
                self.conversations.append(conversation_id)
            if status == 'waiting' and conversation_id not in self.waiting_conversations:
                self.waiting_conversations.append(conversation_id)
    
    def get_random_conversation(self):
        with self.conversation_lock:
            if not self.conversations:
                return None
            return random.choice(self.conversations)
    
    def get_waiting_conversation(self):
        with self.conversation_lock:
            if not self.waiting_conversations:
                return None
            return random.choice(self.waiting_conversations)
    
    def mark_conversation_claimed(self, conversation_id):
        with self.conversation_lock:
            if conversation_id in self.waiting_conversations:
                self.waiting_conversations.remove(conversation_id)


user_store = UserStore()
user_name_generator = UserNameGenerator(max_users=MAX_USERS)


def auth_headers(token):
    """Generate authentication headers."""
    return {"Authorization": f"Bearer {token}"}


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
            is_expert = username.endswith('_expert')
            return user_store.store_user(username, data.get("token"), data.get("user", {}).get("id"), is_expert=is_expert)
        return None
        
    def register(self, username, password, is_expert=False):
        """Register a new user."""
        response = self.client.post(
            "/auth/register",
            json={"username": username, "password": password},
            name="/auth/register"
        )
        if response.status_code in [200, 201]:
            data = response.json()
            return user_store.store_user(username, data.get("token"), data.get("user", {}).get("id"), is_expert=is_expert)
        return None

    def check_conversation_updates(self, user):
        """Check for conversation updates."""
        params = {}
        if hasattr(self, 'last_check_time') and self.last_check_time:
            params["since"] = self.last_check_time.isoformat()
        
        response = self.client.get(
            "/api/conversations/updates",
            params=params,
            headers=auth_headers(user.get("auth_token")),
            name="/api/conversations/updates"
        )
        
        return response.status_code == 200
    
    def check_message_updates(self, user):
        """Check for message updates."""
        params = {}
        if hasattr(self, 'last_check_time') and self.last_check_time:
            params["since"] = self.last_check_time.isoformat()
        
        response = self.client.get(
            "/api/messages/updates",
            params=params,
            headers=auth_headers(user.get("auth_token")),
            name="/api/messages/updates"
        )
        
        return response.status_code == 200
    
    def check_expert_queue_updates(self, user):
        """Check for expert queue updates."""
        params = {}
        if hasattr(self, 'last_check_time') and self.last_check_time:
            params["since"] = self.last_check_time.isoformat()
        
        response = self.client.get(
            "/api/expert-queue/updates",
            params=params,
            headers=auth_headers(user.get("auth_token")),
            name="/api/expert-queue/updates"
        )
        
        return response.status_code == 200
    
    def create_conversation(self, user, title):
        """Create a new conversation."""
        response = self.client.post(
            "/conversations",
            json={"title": title},
            headers=auth_headers(user.get("auth_token")),
            name="/conversations [CREATE]"
        )
        
        if response.status_code in [200, 201]:
            data = response.json()
            conversation_id = data.get("id")
            if conversation_id:
                user_store.add_conversation(conversation_id, status='waiting')
            return conversation_id
        return None
    
    def get_conversations(self, user):
        """Get all conversations for the user."""
        response = self.client.get(
            "/conversations",
            headers=auth_headers(user.get("auth_token")),
            name="/conversations [LIST]"
        )
        
        if response.status_code == 200:
            conversations = response.json()
            for conv in conversations:
                conv_id = conv.get("id")
                if conv_id:
                    user_store.add_conversation(conv_id, status=conv.get("status"))
            return conversations
        return []
    
    def send_message(self, user, conversation_id, content):
        """Send a message to a conversation."""
        response = self.client.post(
            f"/conversations/{conversation_id}/messages",
            json={"content": content},
            headers=auth_headers(user.get("auth_token")),
            name="/conversations/[id]/messages [POST]"
        )
        
        return response.status_code in [200, 201]
    
    def get_messages(self, user, conversation_id):
        """Get messages from a conversation."""
        response = self.client.get(
            f"/conversations/{conversation_id}/messages",
            headers=auth_headers(user.get("auth_token")),
            name="/conversations/[id]/messages [GET]"
        )
        
        return response.status_code == 200
    
    def monitor_expert_queue(self, user):
        """Check the expert queue."""
        response = self.client.get(
            "/expert/queue",
            headers=auth_headers(user.get("auth_token")),
            name="/expert/queue"
        )
        
        if response.status_code == 200:
            return response.json()
        return None
    
    def claim_conversation(self, user, conversation_id):
        """Claim a waiting conversation."""
        response = self.client.post(
            f"/expert/conversations/{conversation_id}/claim",
            headers=auth_headers(user.get("auth_token")),
            name="/expert/conversations/[id]/claim"
        )
        
        if response.status_code == 200:
            user_store.mark_conversation_claimed(conversation_id)
            return True
        return False
    
    def unclaim_conversation(self, user, conversation_id):
        """Unclaim a conversation."""
        response = self.client.post(
            f"/expert/conversations/{conversation_id}/unclaim",
            headers=auth_headers(user.get("auth_token")),
            name="/expert/conversations/[id]/unclaim"
        )
        
        if response.status_code == 200:
            user_store.add_conversation(conversation_id, status='waiting')
            return True
        return False


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
        
        # Some idle users are experts
        is_expert = random.random() < 0.2
        if is_expert:
            username += "_expert"
        
        self.user = self.login(username, password) or self.register(username, password, is_expert=is_expert)
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


class InitiatorUser(HttpUser, ChatBackend):
    """
    Persona: An active initiator user who creates conversations and messages with experts.
    
    Behavior:
    - Creates new conversations seeking expert help
    - Sends messages to conversations
    - Checks for expert responses
    - Polls for updates
    """
    weight = 5
    wait_time = between(3, 10)

    def on_start(self):
        """Initialize user."""
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
        titles = [
            "Need help with account issue",
            "Question about product features",
            "Technical support needed",
            "Billing question",
            "General inquiry"
        ]
        
        conversation_id = self.create_conversation(self.user, random.choice(titles))
        if conversation_id:
            self.my_conversations.append(conversation_id)
            initial_messages = [
                "Hi, I need help with my account.",
                "Can someone assist me with a technical issue?",
                "I have a question about your service.",
                "Looking for support with a problem I'm experiencing.",
                "Need expert advice on how to proceed."
            ]
            self.send_message(self.user, conversation_id, random.choice(initial_messages))
    
    @task(5)
    def check_for_responses(self):
        """Check conversations for new messages."""
        if self.my_conversations or user_store.conversations:
            conversation_id = (random.choice(self.my_conversations) if self.my_conversations 
                             else user_store.get_random_conversation())
            if conversation_id:
                self.get_messages(self.user, conversation_id)
    
    @task(4)
    def respond_to_expert(self):
        """Send a follow-up message."""
        conversation_id = (random.choice(self.my_conversations) if self.my_conversations 
                          else user_store.get_random_conversation())
        if conversation_id:
            follow_up_messages = [
                "Thank you for the response!",
                "That helps, but I have another question.",
                "Can you clarify that?",
                "I tried that but it didn't work.",
                "Yes, that makes sense.",
                "Could you provide more details?"
            ]
            self.send_message(self.user, conversation_id, random.choice(follow_up_messages))
    
    @task(2)
    def browse_my_conversations(self):
        """Browse the user's conversation list."""
        conversations = self.get_conversations(self.user)
        if conversations:
            self.my_conversations = [c.get("id") for c in conversations if c.get("id")]
    
    @task(6)
    def poll_for_updates(self):
        """Poll for updates."""
        self.check_conversation_updates(self.user)
        self.check_message_updates(self.user)
        self.last_check_time = datetime.utcnow()


class ExpertUser(HttpUser, ChatBackend):
    """
    Persona: An expert user who monitors the queue, claims conversations, and helps initiators.
    
    Behavior:
    - Monitors expert queue for waiting conversations
    - Claims conversations from the queue
    - Responds to initiator messages
    - Manages multiple active conversations
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
    def monitor_queue(self):
        """Check the expert queue for waiting conversations."""
        queue_data = self.monitor_expert_queue(self.user)
        
        if queue_data:
            assigned = queue_data.get("assignedConversations", [])
            self.my_claimed_conversations = [c.get("id") for c in assigned if c.get("id")]
    
    @task(5)
    def claim_waiting_conversation(self):
        """Claim a conversation from the waiting queue."""
        conversation_id = user_store.get_waiting_conversation()
        if conversation_id:
            if self.claim_conversation(self.user, conversation_id):
                self.my_claimed_conversations.append(conversation_id)
                
                # Send initial expert response
                greetings = [
                    "Hello! I'm here to help you.",
                    "Hi, I've reviewed your question. Let me assist you.",
                    "Welcome! I can help with that.",
                    "I'm an expert and I'm here to support you."
                ]
                self.send_message(self.user, conversation_id, random.choice(greetings))
    
    @task(7)
    def respond_to_initiator(self):
        """Send a response message in a claimed conversation."""
        if not self.my_claimed_conversations:
            return
        
        conversation_id = random.choice(self.my_claimed_conversations)
        
        expert_responses = [
            "Based on what you've described, here's what I recommend...",
            "I understand your concern. Let me explain...",
            "That's a great question. The solution is...",
            "I've seen this before. Try the following steps...",
            "Let me help you troubleshoot this issue.",
            "Here's some additional information that might help."
        ]
        
        self.send_message(self.user, conversation_id, random.choice(expert_responses))
    
    @task(4)
    def read_conversation_messages(self):
        """Read messages from an assigned conversation."""
        if not self.my_claimed_conversations:
            return
        
        conversation_id = random.choice(self.my_claimed_conversations)
        self.get_messages(self.user, conversation_id)
    
    @task(1)
    def unclaim_conversation(self):
        """Unclaim a conversation (mark as resolved)."""
        if not self.my_claimed_conversations:
            return
        
        # Only unclaim with 30% probability
        if random.random() > 0.3:
            return
        
        conversation_id = random.choice(self.my_claimed_conversations)
        if self.unclaim_conversation(self.user, conversation_id):
            self.my_claimed_conversations.remove(conversation_id)
    
    @task(3)
    def poll_expert_updates(self):
        """Poll for expert queue updates."""
        self.check_expert_queue_updates(self.user)
        self.check_conversation_updates(self.user)
        self.check_message_updates(self.user)
        self.last_check_time = datetime.utcnow()