import time
import json
import os
import re
import asyncio
import logging
from datetime import datetime
from typing import List, Dict
from twikit import Client, Tweet
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes
import openai
from monitor import start_monitor, add_message, clear_messages

openai.api_base = "http://127.0.0.1:1234/v1"
openai.api_key = "lm-studio"
MODEL_NAME = "hermes-3-llama-3.2-3b"

CONTEXT_WINDOW = 8192
HISTORY_LIMIT = 20

logging.basicConfig(level=logging.INFO)

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = int(os.getenv("TELEGRAM_CHAT_ID"))

TWITTER_USERNAME = os.getenv("TWITTER_USERNAME")
TWITTER_PASSWORD = os.getenv("TWITTER_PASSWORD")

# Global variables for state management
chat_history = []
last_action_result = None
user_messages_queue = []

generation_kwargs = {
    "max_tokens": 512,
    "temperature": 0.7,
    "top_p": 0.9
}

class TwitterMonitor:
    def __init__(self, auth_info: str, password: str, language: str = 'en'):
        self.auth_info = auth_info
        self.password = password
        self.language = language
        self.client: Client = None
        self.seen_tweets = set()
        self.last_fetch_time = 0
        self.min_interval = 30

    async def initialize(self):
        try:
            self.client = Client(language=self.language)
            cookie_file = 'cookies.json'
            if os.path.exists(cookie_file):
                self.client.load_cookies(cookie_file)
                print("[TWITTER] Loaded cookies for login reuse.")
            else:
                await self.client.login(
                    auth_info_1=self.auth_info,
                    password=self.password
                )
                self.client.save_cookies(cookie_file)
                print("[TWITTER] Successfully logged in and saved cookies.")
        except Exception as e:
            print(f"[TWITTER] Failed to initialize: {e}")
            raise

    async def fetch_ai_tweets(self, count: int = 30, query: str = None) -> List[Tweet]:
        if not self.client:
            raise RuntimeError("Client not initialized")

        now = time.time()
        if now - self.last_fetch_time < self.min_interval:
            wait_time = self.min_interval - (now - self.last_fetch_time)
            print(f"[TWITTER] Waiting {wait_time:.1f} seconds before next fetch...")
            await asyncio.sleep(wait_time)

        self.last_fetch_time = time.time()

        try:
            default_query = "AI agents OR artificial intelligence agents OR autonomous agents"
            search_results = await self.client.search_tweet(
                query=query if query else default_query,
                product="Top",
                count=count
            )
            new_tweets = []
            for tweet in search_results:
                if tweet.id not in self.seen_tweets:
                    new_tweets.append(tweet)
                    self.seen_tweets.add(tweet.id)
            if new_tweets:
                print(f"[TWITTER] Found {len(new_tweets)} new tweets.")
            return new_tweets
        except Exception as e:
            print(f"[TWITTER] Error fetching tweets: {e}")
            return []

user_messages_queue = []

async def telegram_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat and update.effective_chat.id == TELEGRAM_CHAT_ID:
        text = update.message.text
        user_messages_queue.append(text)
        add_message(
            role="user",
            content=text
        )
        print(f"[TELEGRAM IN]: {text}")
        print(f"[DEBUG] Message added to queue. Queue size: {len(user_messages_queue)}")

def send_message_to_user(text: str):
    global application
    asyncio.create_task(application.bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=text))
    print(f"[TELEGRAM OUT]: {text}")

def read_user_messages():
    global user_messages_queue
    msgs = user_messages_queue[:]
    user_messages_queue.clear()
    return msgs

current_strategy = "Selecting AI research tweets, responding with neutral scientific insight."

history_operations: List[Dict] = []

class ChatMessage:
    def __init__(self, role: str, content: str, timestamp: datetime = None):
        self.role = role  # 'system', 'assistant', 'user'
        self.content = content
        self.timestamp = timestamp or datetime.now()

    def to_dict(self):
        return {
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp.isoformat()
        }

chat_history: List[ChatMessage] = []

def add_chat_message(role: str, content: str):
    chat_history.append(ChatMessage(role, content))

system_prompt = """You are an AI agent assistant that helps with monitoring and interacting with AI-related content.

Available commands:
1 - get_tweets: Fetch new AI-related tweets (input: search query, e.g. "AI agents" or "machine learning")
2 - send_message_to_customer: Send a message to the customer (input: message text)
0 - do_nothing: Skip this turn (input: not needed)

When customer messages are available, this additional command becomes available:
3 - read_customer_messages: Read new messages from customer (input: not needed)

Please respond with exactly one command in JSON format:
{"command": <int>, "input": "<string>"}

Guidelines:
1. For get_tweets: provide only the search terms
2. For send_message_to_customer, format tweet messages as:
   ```
   Tweet by @username:
   <tweet_text>

   Link: https://twitter.com/username/status/<tweet_id>

   Suggested reply:
   <your proposed reply>
   ```
3. No explanations needed, just the JSON command
"""

def build_user_message():
    # Convert chat history to prompt
    messages = []
    
    # Always start with system prompt
    messages.append({"role": "system", "content": system_prompt})
    
    # Add chat history in the correct sequence
    for msg in chat_history[-HISTORY_LIMIT:]:
        messages.append({
            "role": msg.role,
            "content": msg.content
        })
    
    # Add current command list
    user_prompt = """Available commands:
1 - get_tweets: Fetch new AI-related tweets
2 - send_message_to_customer: Send a message
3 - read_customer_messages: Read new messages (if available)
0 - do_nothing: Skip this turn

Please respond with exactly one command in JSON format with numeric command:
{"command": 1, "input": "search terms"}"""

    if last_action_result:
        user_prompt = f"{last_action_result}\n\n{user_prompt}"
        
    messages.append({
        "role": "user",
        "content": user_prompt
    })
    
    return messages

async def call_llm(monitor: TwitterMonitor):
    messages = build_user_message()
    
    try:
        response = await asyncio.get_event_loop().run_in_executor(None, lambda: openai.ChatCompletion.create(
            model=MODEL_NAME,
            messages=messages,
            **generation_kwargs
        ))
        generated = response.choices[0].message.content.strip()
        
        # Add assistant's response to history
        add_chat_message("assistant", generated)
        
        # Execute action and get result
        try:
            parsed = json.loads(generated)
            action_id = parsed.get("command", 0)
            if not isinstance(action_id, int):
                action_id = 0
            action_input = parsed.get("input", "")
            
            # Get action result and store it
            global last_action_result
            last_action_result = await execute_action(action_id, action_input, monitor)
            
        except Exception as e:
            error_msg = f"Error parsing/executing command: {str(e)}"
            last_action_result = error_msg
        
        # Display the current state
        clear_messages()
        for msg in messages:  # Show all history including system prompt
            add_message(msg["role"], msg["content"])
        add_message("assistant", generated)  # Show current response
        
        return generated
        
    except Exception as e:
        error_msg = f"[ERROR] LLM call failed: {e}"
        print(error_msg)
        last_action_result = error_msg
        return '{"command":0,"input":""}'

async def execute_action(action_id: int, action_input: str, monitor: TwitterMonitor):
    try:
        if action_id == 0:
            result = "No action taken."
        elif action_id == 1:
            search_query = action_input if action_input else "AI agents OR artificial intelligence agents OR autonomous agents"
            tweets = await monitor.fetch_ai_tweets(30, search_query)
            tweet_data = []
            for t in tweets:
                tweet_data.append({"id": t.id, "text": t.text, "author": t.user.screen_name})
            result = f"Fetched tweets: {json.dumps(tweet_data, ensure_ascii=False)}"
        elif action_id == 2:
            send_message_to_user(action_input)
            result = f"Sent to user: {action_input}"
        elif action_id == 3:
            msgs = read_user_messages()
            if msgs:
                result = f"User messages: {msgs}"
            else:
                result = "No new user messages available."
        else:
            result = "Unknown action"
            
        add_chat_message("user", result)  # Add result to chat history
        return result
    except Exception as e:
        error_msg = f"Error executing action {action_id}: {e}"
        add_chat_message("user", error_msg)
        return error_msg

async def run_agent_loop(monitor: TwitterMonitor):
    print("[AGENT] Starting main loop...")
    while True:
        print("[AGENT] Calling LLM...")
        response_text = await call_llm(monitor)
        
        print("[AGENT] Done tick, waiting...")
        await asyncio.sleep(5)

async def main():
    start_monitor()
    clear_messages()  # Clear at startup
    
    # Add system prompt at startup
    add_message("system", system_prompt)
    
    monitor = TwitterMonitor(auth_info=TWITTER_USERNAME, password=TWITTER_PASSWORD)
    await monitor.initialize()
    
    global application
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, telegram_message_handler))

    await application.initialize()
    await application.start()

    try:
        await run_agent_loop(monitor)
    finally:
        await application.stop()
        await application.shutdown()

if __name__ == "__main__":
    asyncio.run(main())
