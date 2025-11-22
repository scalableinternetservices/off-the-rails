"""
Locust load test for chat-backend-rails application (Project 3).

This test suite is designed to evaluate four scaling configurations:
1. Single Instance: 1x m7g.medium app server + 1x db.m5.large DB
2. Vertical Scaling: 1x m7g.large app server + 1x db.m5.large DB
3. Horizontal Scaling 1: 4x m7g.medium app servers + 1x db.m5.large DB
4. Horizontal Scaling 2: 4x m7g.medium app servers + 1x db.m5.xlarge DB

The test simulates an expert chat system with realistic traffic patterns:
- Initiators: Create conversations and message with experts
- Experts: Claim waiting conversations and respond to initiators
- Both user types poll for updates continuously

This allows you to measure:
- Throughput (requests/second) across configurations
- Response times at different load levels
- Database bottlenecks (single vs larger DB instance)
- Application server bottlenecks (single vs multiple instances)
- System breaking points (max concurrent users before degradation)
"""

import random
import threading
from datetime import datetime
from locust import HttpUser, task, between


# Configuration
MAX_USERS = 10000
EXPERT_RATIO = 0.2  # 20% of users are experts


class UserNameGenerator:
    """Generates unique usernames using prime number distribution."""
    PRIME_NUMBERS = [2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47, 53, 59, 61, 67, 71, 73, 79, 83, 89, 97]

    def __init__(self, max_users=MAX_USERS, seed=None, prime_number=None):
        self.seed = seed or random.randint(0, max_users)
        self.prime_number = prime_number or random.choice(self.PRIME_NUMBERS)
        self.current_index = -1
        self.max_users = max_users
    
    def generate_username(self):
        self.current_index += 1
        return f"user_{(self.seed + self.current_index * self.prime_number) % self.max_users}"


class SharedState:
    """Thread-safe storage for shared data across all simulated users."""
    
    def __init__(self):
        self.users = {}
        self.experts = {}
        self.conversations = []
        self.waiting_conversations = []
        self.lock = threading.Lock()

    def store_user(self, username, auth_token, user_id, is_expert=False):
        """Store user credentials and role."""
        with self.lock:
            user_data = {
                "username": username,
                "auth_token": auth_token,
                "user_id": user_id,
                "is_expert": is_expert
            }
            self.users[username] = user_data
            if is_expert:
                self.experts[username] = user_data
            return user_data

    def get_random_expert(self):
        """Get a random expert user."""
        with self.lock:
            if not self.experts:
                return None
            return random.choice(list(self.experts.values()))

    def get_random_user(self):
        """Get any random user."""
        with self.lock:
            if not self.users:
                return None
            return random.choice(list(self.users.values()))
    
    def add_conversation(self, conversation_id, status='waiting'):
        """Store a conversation ID."""
        with self.lock:
            if conversation_id not in self.conversations:
                self.conversations.append(conversation_id)
            if status == 'waiting' and conversation_id not in self.waiting_conversations:
                self.waiting_conversations.append(conversation_id)
    
    def mark_conversation_claimed(self, conversation_id):
        """Remove conversation from waiting list."""
        with self.lock:
            if conversation_id in self.waiting_conversations:
                self.waiting_conversations.remove(conversation_id)
    
    def get_random_conversation(self):
        """Get a random conversation ID."""
        with self.lock:
            if not self.conversations:
                return None
            return random.choice(self.conversations)
    
    def get_waiting_conversation(self):
        """Get a random waiting conversation."""
        with self.lock:
            if not self.waiting_conversations:
                return None
            return random.choice(self.waiting_conversations)


shared_state = SharedState()
user_name_generator = UserNameGenerator(max_users=MAX_USERS)


def auth_headers(token):
    """Generate authentication headers with JWT token."""
    return {"Authorization": f"Bearer {token}"}


class ChatBackendBase():
    """
    Base class providing common authentication and API methods.
    """        
    
    def login(self, username, password):
        """Login an existing user and store credentials."""
        response = self.client.post(
            "/auth/login",
            json={"username": username, "password": password},
            name="/auth/login"
        )
        if response.status_code == 200:
            data = response.json()
            is_expert = username.endswith('_expert')
            return shared_state.store_user(
                username, 
                data.get("token"), 
                data.get("user", {}).get("id"),
                is_expert=is_expert
            )
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
            return shared_state.store_user(
                username, 
                data.get("token"), 
                data.get("user", {}).get("id"),
                is_expert=is_expert
            )
        return None

    def check_conversation_updates(self, user):
        """Check for conversation updates - tests DB query performance with timestamp filtering."""
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
        """Check for message updates - tests DB query performance with timestamp filtering."""
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
        """Check for expert queue updates - tests DB query performance."""
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
        """Create a new conversation - tests DB writes and transaction handling."""
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
                shared_state.add_conversation(conversation_id, status='waiting')
            return conversation_id
        return None
    
    def get_conversations(self, user):
        """Get all conversations for user - tests DB read performance."""
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
                    shared_state.add_conversation(conv_id, status=conv.get("status"))
            return conversations
        return []
    
    def send_message(self, user, conversation_id, content):
        """Send a message - tests DB writes and conversation updates."""
        response = self.client.post(
            f"/conversations/{conversation_id}/messages",
            json={"content": content},
            headers=auth_headers(user.get("auth_token")),
            name="/conversations/[id]/messages [POST]"
        )
        
        return response.status_code in [200, 201]
    
    def get_messages(self, user, conversation_id):
        """Get messages - tests DB read performance with ordering."""
        response = self.client.get(
            f"/conversations/{conversation_id}/messages",
            headers=auth_headers(user.get("auth_token")),
            name="/conversations/[id]/messages [GET]"
        )
        
        return response.status_code == 200


class InitiatorUser(HttpUser, ChatBackendBase):
    """
    Regular users who create conversations and wait for expert help.
    
    Key scaling tests:
    - Conversation creation throughput (DB writes)
    - Message sending throughput (DB writes + updates)
    - Polling load (DB reads with timestamp filtering)
    - Authentication overhead (JWT validation)
    """
    weight = 5
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
        """Tests: DB write performance, transaction handling."""
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
        """Tests: DB read performance, message ordering queries."""
        if self.my_conversations or shared_state.conversations:
            conversation_id = (random.choice(self.my_conversations) if self.my_conversations 
                             else shared_state.get_random_conversation())
            if conversation_id:
                self.get_messages(self.user, conversation_id)
    
    @task(4)
    def respond_to_expert(self):
        """Tests: DB write throughput, concurrent message inserts."""
        conversation_id = (random.choice(self.my_conversations) if self.my_conversations 
                          else shared_state.get_random_conversation())
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
        """Tests: DB read performance, query filtering by user_id."""
        conversations = self.get_conversations(self.user)
        if conversations:
            self.my_conversations = [c.get("id") for c in conversations if c.get("id")]
    
    @task(6)
    def poll_for_updates(self):
        """Tests: Sustained DB read load, timestamp-based filtering, index usage."""
        self.check_conversation_updates(self.user)
        self.check_message_updates(self.user)
        self.last_check_time = datetime.utcnow()


class ExpertUser(HttpUser, ChatBackendBase):
    """
    Expert users who claim conversations and respond to initiators.
    
    Key scaling tests:
    - Expert queue query performance (complex WHERE clauses)
    - Conversation claiming race conditions (DB locking under load)
    - Transaction throughput (claim/unclaim operations)
    - Concurrent write conflicts
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
        """Tests: Complex DB queries (status filtering, user_id filtering), query optimization."""
        response = self.client.get(
            "/expert/queue",
            headers=auth_headers(self.user.get("auth_token")),
            name="/expert/queue"
        )
        
        if response.status_code == 200:
            data = response.json()
            assigned = data.get("assignedConversations", [])
            self.my_claimed_conversations = [c.get("id") for c in assigned if c.get("id")]
    
    @task(5)
    def claim_waiting_conversation(self):
        """Tests: Race condition handling, DB locking (conversation.lock!), transaction throughput."""
        conversation_id = shared_state.get_waiting_conversation()
        if conversation_id:
            response = self.client.post(
                f"/expert/conversations/{conversation_id}/claim",
                headers=auth_headers(self.user.get("auth_token")),
                name="/expert/conversations/[id]/claim"
            )
            
            if response.status_code == 200:
                shared_state.mark_conversation_claimed(conversation_id)
                self.my_claimed_conversations.append(conversation_id)
                
                greetings = [
                    "Hello! I'm here to help you.",
                    "Hi, I've reviewed your question. Let me assist you.",
                    "Welcome! I can help with that.",
                    "I'm an expert and I'm here to support you."
                ]
                self.send_message(self.user, conversation_id, random.choice(greetings))
    
    @task(7)
    def respond_to_initiator(self):
        """Tests: DB write performance, message insertion throughput."""
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
        """Tests: DB read performance with ordering, index usage on conversation_id."""
        if not self.my_claimed_conversations:
            return
        
        conversation_id = random.choice(self.my_claimed_conversations)
        self.get_messages(self.user, conversation_id)
    
    @task(1)
    def unclaim_conversation(self):
        """Tests: Transaction handling, DB update performance, status changes."""
        if not self.my_claimed_conversations:
            return
        
        # Only unclaim with 30% probability
        if random.random() > 0.3:
            return
        
        conversation_id = random.choice(self.my_claimed_conversations)
        response = self.client.post(
            f"/expert/conversations/{conversation_id}/unclaim",
            headers=auth_headers(self.user.get("auth_token")),
            name="/expert/conversations/[id]/unclaim"
        )
        
        if response.status_code == 200:
            self.my_claimed_conversations.remove(conversation_id)
            shared_state.add_conversation(conversation_id, status='waiting')
    
    @task(3)
    def poll_expert_updates(self):
        """Tests: Sustained DB read load for expert-specific queries, timestamp filtering."""
        self.check_expert_queue_updates(self.user)
        self.check_conversation_updates(self.user)
        self.check_message_updates(self.user)
        self.last_check_time = datetime.utcnow()


class IdlePollingUser(HttpUser, ChatBackendBase):
    """
    Users with the app open but not actively using it - constant polling.
    
    Key scaling tests:
    - Sustained high-frequency read load (every 5 seconds)
    - DB connection pool utilization
    - Index performance on updated_at/created_at columns
    - Load balancer distribution (horizontal scaling)
    - Database read replica potential (if configured)
    
    This is the PRIMARY bottleneck test - most users are idle and polling.
    """
    weight = 10
    wait_time = between(5, 5)  # Poll exactly every 5 seconds

    def on_start(self):
        """Initialize idle user."""
        self.last_check_time = None
        username = user_name_generator.generate_username()
        password = username
        is_expert = random.random() < EXPERT_RATIO
        if is_expert:
            username += "_expert"
        
        self.user = self.login(username, password) or self.register(username, password, is_expert=is_expert)
        if not self.user:
            raise Exception(f"Failed to login or register user {username}")

    @task
    def poll_all_updates(self):
        """Tests: Maximum DB read load, connection pool limits, query performance at scale."""
        self.check_conversation_updates(self.user)
        self.check_message_updates(self.user)
        self.check_expert_queue_updates(self.user)
        self.last_check_time = datetime.utcnow()