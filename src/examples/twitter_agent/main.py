import asyncio
import os
from datetime import datetime, timedelta
from typing import Dict, Any
import sys

# Add src to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from core.llm_processor import LLMProcessor
from twikit import Client, TwitterException


# Global variables for guardrails
MAX_REPLIES_PER_HOUR = 10
replies_last_hour = 0
last_hour_window_start = datetime.now()

async def tweet_search(params: Dict[str, Any], processor: LLMProcessor = None) -> Dict[str, Any]:
    """Search for tweets about AI agents."""
    count = params.get("count", 5)
    try:
        # Example search for 'AI agents' - can be expanded
        tweets = await processor.twitter_client.search_tweet("AI agents", "Latest", count=count)
        tweet_ids = [t.id for t in tweets]
        return {
            "status": "success",
            "found_tweets": tweet_ids,
            "message": f"Found {len(tweet_ids)} tweets"
        }
    except TwitterException as e:
        return {
            "status": "error",
            "message": f"Error searching tweets: {str(e)}"
        }

async def tweet_reply(params: Dict[str, Any], processor: LLMProcessor = None) -> Dict[str, Any]:
    """Reply to a tweet. Check guardrails (max 10 per hour)."""
    global replies_last_hour, last_hour_window_start

    tweet_id = params.get("tweet_id")
    text = params.get("text", "")

    # Check rate limit
    now = datetime.now()
    if now - last_hour_window_start > timedelta(hours=1):
        # Reset counter after an hour
        replies_last_hour = 0
        last_hour_window_start = now

    if replies_last_hour >= MAX_REPLIES_PER_HOUR:
        return {
            "status": "error",
            "message": "Rate limit of 10 replies per hour exceeded"
        }

    try:
        posted = await processor.twitter_client.create_tweet(text=text, reply_to=tweet_id)
        replies_last_hour += 1

        return {
            "status": "success",
            "message": f"Reply posted: {posted.id}",
            "tweet_id": posted.id
        }

    except TwitterException as e:
        return {
            "status": "error",
            "message": f"Error replying to tweet: {str(e)}"
        }

async def tweet_sleep(params: Dict[str, Any], processor: LLMProcessor = None) -> Dict[str, Any]:
    """Wait for specified number of seconds (real sleep)."""
    seconds = params.get("seconds", 10)
    await asyncio.sleep(seconds)
    return {
        "status": "success",
        "message": f"Slept for {seconds} seconds"
    }

async def tweet_check_stats(params: Dict[str, Any], processor: LLMProcessor = None) -> Dict[str, Any]:
    """Check likes/replies (favorite_count, reply_count, retweet_count)."""
    tweet_id = params.get("tweet_id")
    try:
        tw = await processor.twitter_client.get_tweet_by_id(tweet_id)
        return {
            "status": "success",
            "favorite_count": tw.favorite_count,
            "reply_count": tw.reply_count,
            "retweet_count": tw.retweet_count
        }
    except TwitterException as e:
        return {
            "status": "error",
            "message": f"Failed to check statistics: {str(e)}"
        }


async def initialize_processor():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    config_dir = os.path.join(current_dir, 'config')

    # Create LLMProcessor
    proc = LLMProcessor(
        functions_file=os.path.join(config_dir, 'functions.json'),
        goal_file=os.path.join(config_dir, 'goal.yaml'),
        model_type="openai",
        model_name="gpt-4o-mini",
        ui_visibility=False,   # Or True if we want web UI
        history_size=10,
        summary_interval=7,
        summary_window=15
    )

    # Create wrappers for functions that will include processor
    async def wrapped_tweet_search(params):
        return await tweet_search(params, processor=proc)
        
    async def wrapped_tweet_reply(params):
        return await tweet_reply(params, processor=proc)
        
    async def wrapped_tweet_sleep(params):
        return await tweet_sleep(params, processor=proc)
        
    async def wrapped_tweet_check_stats(params):
        return await tweet_check_stats(params, processor=proc)

    # Register function wrappers
    proc.register_function("tweet_search", wrapped_tweet_search)
    proc.register_function("tweet_reply", wrapped_tweet_reply)
    proc.register_function("tweet_sleep", wrapped_tweet_sleep)
    proc.register_function("tweet_check_stats", wrapped_tweet_check_stats)

    # Create twikit Client
    # Can login via cookies or username/password from .env
    tw_user = os.getenv("TWITTER_USER", "your_user")
    tw_pass = os.getenv("TWITTER_PASSWORD", "your_pass")
    proc.twitter_client = Client(language='en-US')

    # Login if needed (or load cookies)
    try:
        # Can load cookies instead of login:
        # proc.twitter_client.load_cookies('cookies.json')
        await proc.twitter_client.login(
            auth_info_1=tw_user,
            password=tw_pass
        )
    except TwitterException as e:
        print(f"Login error: {e}")

    return proc


# Global processor object (can be initialized once)
processor: LLMProcessor = None

async def main():
    global processor
    processor = await initialize_processor()

    # Infinite loop where the agent will ask LLM for a task and execute
    # For example - only a few steps
    for step in range(20):
        response = await processor.get_next_action()
        action = response["action"]
        cmd_id = action["command_id"]
        params = action["parameters"]
        reasoning = response["analysis"].get("reasoning", "no reasoning")

        # Execute command
        res = await processor.execute_command(cmd_id, params, context=reasoning)
        print(f"--- Step {step+1} result ---")
        print(res)
        # If desired: check some critical conditions

    # Exit loop, logout
    await processor.twitter_client.logout()
    print("Agent finished working.")


if __name__ == "__main__":
    asyncio.run(main())
