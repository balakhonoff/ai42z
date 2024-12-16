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

##################################################
# LM Studio Settings
##################################################
openai.api_base = "http://127.0.0.1:1234/v1"
openai.api_key = "lm-studio"
MODEL_NAME = "hermes-3-llama-3.2-3b"  # Replace with the exact model name in LM Studio

##################################################
# Constants and Settings
##################################################

CONTEXT_WINDOW = 8192
MAX_TOKENS_CONTEXT = int(CONTEXT_WINDOW * 0.7)
HISTORY_LIMIT = 10

logging.basicConfig(level=logging.INFO)

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = int(os.getenv("TELEGRAM_CHAT_ID"))

TWITTER_USERNAME = os.getenv("TWITTER_USERNAME")
TWITTER_PASSWORD = os.getenv("TWITTER_PASSWORD")

generation_kwargs = {
    "max_tokens": 512,
    "temperature": 0.7,
    "top_p": 0.9
}

##################################################
# Working with Twitter via TwitterMonitor
##################################################

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

    async def fetch_ai_tweets(self, count: int = 30) -> List[Tweet]:
        if not self.client:
            raise RuntimeError("Client not initialized")

        now = time.time()
        if now - self.last_fetch_time < self.min_interval:
            wait_time = self.min_interval - (now - self.last_fetch_time)
            print(f"[TWITTER] Waiting {wait_time:.1f} seconds before next fetch...")
            await asyncio.sleep(wait_time)

        self.last_fetch_time = time.time()

        try:
            search_results = await self.client.search_tweet(
                query="AI agents OR artificial intelligence agents OR autonomous agents",
                product="Latest",
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

##################################################
# Peripheral Input/Output (Telegram)
##################################################

user_messages_queue = []

async def telegram_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat and update.effective_chat.id == TELEGRAM_CHAT_ID:
        text = update.message.text
        user_messages_queue.append(text)
        print(f"[TELEGRAM IN]: {text}")

def send_message_to_user(text: str):
    global application
    asyncio.create_task(application.bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=text))
    print(f"[TELEGRAM OUT]: {text}")

def read_user_messages():
    global user_messages_queue
    msgs = user_messages_queue[:]
    user_messages_queue.clear()
    return msgs

##################################################
# Agent State
##################################################

system_prompt = """You are a specialized agent that fetches AI-related news tweets, filters for interesting (especially research-related) AI content, crafts a short insightful response, and sends the news & your commentary to the user via Telegram. The user may send feedback (like/dislike), and based on that feedback you may update your strategy using the update_strategy command.

Commands:
[0] - do_nothing
[1] - get_tweets
[2] - send_message_to_user (input: text)
[3] - read_user_messages
[4] - update_strategy (input: new strategy)
"""

history_operations: List[str] = []
summary = "Initial strategy: pick AI+research tweets and give a neutral, informative answer."
current_strategy = "Selecting AI research tweets, responding with neutral scientific insight."
last_query_was = ""
last_response_was = ""
available_actions = """[0] - do_nothing
[1] - get_tweets
[2] - send_message_to_user (input: text)
[3] - read_user_messages
[4] - update_strategy (input: new strategy)"""

def shorten_history():
    global history_operations
    if len(history_operations) > HISTORY_LIMIT:
        history_operations = history_operations[-HISTORY_LIMIT:]

async def summarize_context(context_text: str) -> str:
    print("[SUMMARIZATION] Summarizing context due to length limit...")
    summarize_system_prompt = "You are an efficient summarizer. Briefly summarize the following text."
    messages = [
        {"role": "system", "content": summarize_system_prompt},
        {"role": "user", "content": "Summarize this:\n" + context_text}
    ]
    try:
        response = await asyncio.get_event_loop().run_in_executor(None, lambda: openai.ChatCompletion.create(
            model=MODEL_NAME,
            messages=messages,
            **generation_kwargs
        ))
        generated = response.choices[0].message.content.strip()
        return generated
    except Exception as e:
        print(f"[ERROR] Summarization failed: {e}")
        return "Summary unavailable due to error."

def build_body():
    current_datetime = datetime.utcnow().isoformat()
    body = f"""
<current_datetime>{current_datetime}</current_datetime>
<current_state_summary>{summary}</current_state_summary>
<current_strategy>{current_strategy}</current_strategy>
<latest_interations>{json.dumps(history_operations[-HISTORY_LIMIT:], ensure_ascii=False)}</latest_interations>
<latest_query_was>{last_query_was}</latest_query_was>
<latest_response_was>{last_response_was}</latest_response_was>
<available_actions>{available_actions}</available_actions>
"""
    return body.strip()

async def ensure_context_limit(messages: List[Dict[str,str]]):
    global summary, history_operations
    
    full_text = "\n".join(m["content"] for m in messages)
    tokens_est = len(full_text.split())
    if tokens_est > MAX_TOKENS_CONTEXT:
        combined_context = summary + "\n" + current_strategy + "\n" + json.dumps(history_operations, ensure_ascii=False)
        new_summary = await summarize_context(combined_context)
        summary = new_summary
        history_operations = history_operations[-2:]
        messages = build_messages()

        full_text = "\n".join(m["content"] for m in messages)
        tokens_est = len(full_text.split())
        if tokens_est > MAX_TOKENS_CONTEXT:
            print("[WARN] Even after summarization context too long, clearing more history.")
            history_operations.clear()
            messages = build_messages()
    return messages

def build_messages():
    messages = [{"role": "system", "content": system_prompt}]
    for line in history_operations:
        if line.startswith("AGENT:"):
            assistant_msg = line[len("AGENT:"):].strip()
            messages.append({"role": "assistant", "content": assistant_msg})
        elif line.startswith("PERIPHERY:"):
            periphery_msg = line[len("PERIPHERY:"):].strip()
            messages.append({"role": "user", "content": periphery_msg})
    body = build_body()
    messages.append({"role": "user", "content": body})
    return messages

async def call_llm():
    messages = build_messages()
    messages = await ensure_context_limit(messages)
    
    # Get just the current context (last message)
    current_context = messages[-1]  # This is the latest build_body() result
    
    # Clear previous messages and show current context
    clear_messages()
    add_message("system", "Current Interaction:")
    add_message(current_context["role"], current_context["content"])
    
    try:
        response = await asyncio.get_event_loop().run_in_executor(None, lambda: openai.ChatCompletion.create(
            model=MODEL_NAME,
            messages=messages,
            **generation_kwargs
        ))
        generated = response.choices[0].message.content.strip()
        add_message("assistant", generated)
        return generated
    except Exception as e:
        error_msg = f"[ERROR] LLM call failed: {e}"
        print(error_msg)
        add_message("system", f"Error: {str(e)}")
        return "Action:0 input:''"

async def execute_action(action_id: int, action_input: str, monitor: TwitterMonitor):
    global last_query_was, last_response_was, summary, current_strategy
    peripheral_response = ""
    try:
        if action_id == 0:
            peripheral_response = "Waited."
        elif action_id == 1:
            tweets = await monitor.fetch_ai_tweets(30)
            tweet_data = []
            for t in tweets:
                tweet_data.append({"id": t.id, "text": t.text, "author": t.user.screen_name})
            peripheral_response = f"Fetched tweets: {json.dumps(tweet_data, ensure_ascii=False)}"
        elif action_id == 2:
            send_message_to_user(action_input)
            peripheral_response = f"Sent to user: {action_input}"
        elif action_id == 3:
            msgs = read_user_messages()
            if msgs:
                peripheral_response = f"User feedback: {msgs}"
            else:
                peripheral_response = "No new user messages"
        elif action_id == 4:
            current_strategy = action_input
            peripheral_response = f"Strategy updated to: {action_input}"
            summary += " (Strategy updated by LLM)"
        else:
            peripheral_response = "Unknown action"
    except Exception as e:
        peripheral_response = f"Error executing action {action_id}: {e}"

    return peripheral_response

async def run_agent_loop(monitor: TwitterMonitor):
    global history_operations
    
    if not isinstance(history_operations, list):
        print(f"[WARNING] history_operations was {type(history_operations)}, resetting to list")
        history_operations = []
    
    print("[AGENT] Starting main loop...")
    while True:
        print("[AGENT] Calling LLM...")
        response_text = await call_llm()

        history_operations.append(f"AGENT: {response_text}")
        shorten_history()

        action_id = 0
        action_input = ""

        match = re.search(r"(?:Action|action)\s*\:\s*(\d)", response_text)
        if not match:
            match = re.search(r"\[(\d)\]", response_text)
        if match:
            action_id = int(match.group(1))

        input_match = re.search(r"input\s*\:\s*(.*)", response_text, re.IGNORECASE)
        if input_match:
            action_input = input_match.group(1).strip().strip("'\"")

        print(f"[AGENT] Executing action {action_id} with input: {action_input}")
        peripheral_response = await execute_action(action_id, action_input, monitor)

        global last_query_was, last_response_was
        last_query_was = f"Action {action_id}, input: {action_input}"
        last_response_was = peripheral_response
        history_operations.append(f"PERIPHERY: {peripheral_response}")
        shorten_history()

        print("[AGENT] Done tick, waiting...")
        await asyncio.sleep(5)

async def main():
    start_monitor()
    clear_messages()  # Optional: clear any messages from previous runs
    
    monitor = TwitterMonitor(auth_info=TWITTER_USERNAME, password=TWITTER_PASSWORD)
    await monitor.initialize()

    global application
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, telegram_message_handler))
    
    # Start the application without blocking
    await application.initialize()
    await application.start()
    
    try:
        # Run the agent loop
        await run_agent_loop(monitor)
    finally:
        # Proper cleanup
        await application.stop()
        await application.shutdown()

if __name__ == "__main__":
    asyncio.run(main())
