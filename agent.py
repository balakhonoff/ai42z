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

async def telegram_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat and update.effective_chat.id == TELEGRAM_CHAT_ID:
        text = update.message.text
        user_messages_queue.append(text)
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

class ChatMessage:
    def __init__(self, role: str, content: str):
        self.role = role  # 'system', 'assistant', 'user'
        self.content = content

    def to_dict(self):
        return {
            "role": self.role,
            "content": self.content
        }

chat_history: List[ChatMessage] = []

def add_chat_message(role: str, content: str):
    chat_history.append(ChatMessage(role, content))

def get_available_commands():
    return f"""[AVAILABLE COMMANDS]
1 - get_tweets: Fetch new tweets with the topic you choose via seach query (input: search query)
2 - send_message_to_customer: Send a message to the customer with a tweet, it's link (URL) and your proposal on how to reply (input: message text)
3 - {"read_customer_messages (new messages from the customer are available now)" if len(user_messages_queue) > 0 else "read_customer_messages (no new messages at the moment)"}: Read new messages from customer if they are availabe - you'll see the mark about it near this command (no input needed) 
0 - do_nothing: Skip this turn (no input needed)

Please respond with exactly one command in JSON format:
{{"command": (int), "input": "(string)"}} for example {{"command": 1, "input": "ai agents github"}}
NEVER RESPOND WITH THE PLAIN TEXT! ONLY JSON!"""

system_prompt = """You are an AI agent assistant that helps to the customer reply to interesting tweets related to AI agents development.

Each request you receive will have this structure:

[PREVIOUS COMMAND RESULT]
(If there was a previous command, its result will appear here. Like if you ask for )

""" + get_available_commands()

async def call_llm():
    # Просто берем всю историю и отправляем в LLM
    messages = [msg.to_dict() for msg in chat_history]
    try:
        response = await asyncio.get_event_loop().run_in_executor(None, lambda: openai.ChatCompletion.create(
            model=MODEL_NAME,
            messages=messages,
            **generation_kwargs
        ))
        generated = response.choices[0].message.content.strip()

        add_chat_message("assistant", generated)  # Сохраняем ответ ассистента
        return generated
    except Exception as e:
        error_msg = f"[ERROR] LLM call failed: {e}"
        print(error_msg)
        return '{"command":0,"input":""}'

async def execute_action(action_id: int, action_input: str, monitor: TwitterMonitor):
    try:
        if action_id == 0:
            result = "No action taken."#. because your response was not the actual JSON with a choice of command. Try again with correct JSON structure."
        elif action_id == 1:
            search_query = action_input if action_input else "AI agents OR artificial intelligence agents OR autonomous agents"
            tweets = await monitor.fetch_ai_tweets(30, search_query)
            tweet_data = []
            for t in tweets:
                tweet_data.append({"id": t.id, "text": t.text, "author": t.user.screen_name, "link": f"https://x.com/{t.user.screen_name}/status/{t.id}"})
            result = f"Fetched tweets: {json.dumps(tweet_data, ensure_ascii=False)}"
        elif action_id == 2:
            send_message_to_user(action_input)
            result = f"Sent to user: {action_input}"
        elif action_id == 3:
            msgs = read_user_messages()
            if msgs:
                result = f"Read user messages: {msgs}"
            else:
                result = "No new user messages available."
        else:
            result = "Unknown action"
            
        return result
    except Exception as e:
        error_msg = f"Error executing action {action_id}: {e}"
        return error_msg

async def run_agent_loop(monitor: TwitterMonitor):
    print("[AGENT] Starting main loop...")

    chat_history.clear()
    clear_messages()
    add_chat_message("system", system_prompt)
    add_message("system", system_prompt)

    global last_action_result

    while True:
        user_content = ""
        if last_action_result:
            user_content += f"[PREVIOUS COMMAND RESULT]\n{last_action_result}\n\n"
        user_content += get_available_commands()

        add_chat_message("user", user_content)
        add_message("user", user_content)

        print("[AGENT] Calling LLM...")
        response_text = await call_llm()  # Тут ассистент выбирает команду

        # Парсим JSON
        action_id, action_input = parse_llm_command(response_text)

        # Выполняем команду
        last_action_result = await execute_action(action_id, action_input, monitor)

        # Обновляем монитор сообщений
        clear_messages()
        for msg in chat_history:
            add_message(msg.role, msg.content)

        print("[AGENT] Done tick, waiting 5 seconds...")
        await asyncio.sleep(5)

async def main():
    start_monitor()
    clear_messages()

    monitor = TwitterMonitor(auth_info=TWITTER_USERNAME, password=TWITTER_PASSWORD)
    await monitor.initialize()
    
    global application
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, telegram_message_handler))

    await application.initialize()
    await application.start()
    await application.updater.start_polling()

    try:
        await run_agent_loop(monitor)
    finally:
        await application.updater.stop()
        await application.stop()
        await application.shutdown()

def parse_llm_command(response_text: str) -> tuple[int, str]:
    """Extract command and input from LLM response text, ignoring any additional text."""
    try:
        # Ищем любой валидный JSON в тексте
        matches = re.finditer(r'\{[^{]*"command"\s*:\s*(\d+)[^{]*"input"\s*:\s*"([^"]*)"[^}]*\}', response_text)
        # Берем последний найденный JSON (обычно это самый актуальный ответ)
        for match in matches:
            action_id = int(match.group(1))
            action_input = match.group(2)
            return action_id, action_input
            
        print(f"Could not find valid JSON command in response: {response_text}")
    except Exception as e:
        print(f"Error parsing assistant command: {e}")
    return 0, ""

if __name__ == "__main__":
    asyncio.run(main())
