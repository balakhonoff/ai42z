import asyncio
import os
import sys
from datetime import datetime, timedelta
from typing import Dict, Any
from dotenv import load_dotenv

# Add src to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

# Load environment variables
load_dotenv()

from core.llm_processor import LLMProcessor
from twikit import Client, TwitterException

# --------------------------------------------------------------------------------
# Tweet Tracking
# --------------------------------------------------------------------------------

REPLIED_TWEETS_FILE = 'replied_tweets.txt'
SEEN_TWEETS_FILE = 'seen_tweets.txt'
REPLY_COUNT_FILE = 'reply_count.txt'
LAST_RESET_FILE = 'last_reset.txt'
MAX_REPLIES = 49
RESET_HOURS = 24

async def load_tweet_ids(filename: str) -> set:
    """Load tweet IDs from a file into a set."""
    try:
        with open(filename, 'r') as f:
            return set(line.strip() for line in f if line.strip())
    except FileNotFoundError:
        return set()

async def save_tweet_id(filename: str, tweet_id: str):
    """Append a tweet ID to a file."""
    with open(filename, 'a') as f:
        f.write(f"{tweet_id}\n")

async def get_reply_count() -> int:
    """Get current reply count and check if we need to reset."""
    try:
        # Check last reset time
        try:
            with open(LAST_RESET_FILE, 'r') as f:
                last_reset = datetime.fromisoformat(f.read().strip())
        except (FileNotFoundError, ValueError):
            last_reset = datetime.now()
            with open(LAST_RESET_FILE, 'w') as f:
                f.write(last_reset.isoformat())

        # If it's been more than RESET_HOURS since last reset, reset the count
        if (datetime.now() - last_reset).total_seconds() >= RESET_HOURS * 3600:
            with open(REPLY_COUNT_FILE, 'w') as f:
                f.write('0')
            with open(LAST_RESET_FILE, 'w') as f:
                f.write(datetime.now().isoformat())
            return 0

        # Get current count
        with open(REPLY_COUNT_FILE, 'r') as f:
            return int(f.read().strip())
    except (FileNotFoundError, ValueError):
        # If file doesn't exist or is invalid, start from 0
        with open(REPLY_COUNT_FILE, 'w') as f:
            f.write('0')
        return 0

async def increment_reply_count():
    """Increment the reply count."""
    count = await get_reply_count()
    with open(REPLY_COUNT_FILE, 'w') as f:
        f.write(str(count + 1))

async def should_sleep() -> tuple[bool, float]:
    """Check if we need to sleep and for how long."""
    count = await get_reply_count()
    if count >= MAX_REPLIES:
        # Get time until next reset
        with open(LAST_RESET_FILE, 'r') as f:
            last_reset = datetime.fromisoformat(f.read().strip())
        next_reset = last_reset + timedelta(hours=RESET_HOURS)
        sleep_seconds = (next_reset - datetime.now()).total_seconds()
        return True, max(0, sleep_seconds)
    return False, 0

# --------------------------------------------------------------------------------
# Mock & Real Functions
# --------------------------------------------------------------------------------

async def tweet_search(params: Dict[str, Any], processor: LLMProcessor = None) -> Dict[str, Any]:
    """Search for tweets about AI agents."""
    count = params.get("count", 5)
    try:
        # Load previously interacted tweets
        replied_tweets = await load_tweet_ids(REPLIED_TWEETS_FILE)
        seen_tweets = await load_tweet_ids(SEEN_TWEETS_FILE)
        
        # Get more tweets than requested to account for filtering
        tweets = await processor.twitter_client.search_tweet("AI agents", "Latest", count=count * 2)
        
        # Filter and process tweets
        tweet_data = []
        for t in tweets:
            # Skip if already replied, seen, or has media
            if t.id in replied_tweets or t.id in seen_tweets or t.media:
                continue
                
            tweet_info = {
                "id": t.id,
                "author": {
                    "id": t.user.id,
                    "name": t.user.name,
                    "screen_name": t.user.screen_name,
                    "description": t.user.description,
                    "followers_count": t.user.followers_count,
                    "following_count": t.user.following_count,
                    "verified": t.user.verified,
                    "is_blue_verified": t.user.is_blue_verified
                },
                "text": t.text,
                "created_at": t.created_at,
                "favorite_count": t.favorite_count,
                "retweet_count": t.retweet_count,
                "reply_count": t.reply_count,
                "lang": t.lang,
                "is_quote_status": t.is_quote_status,
                "has_media": bool(t.media)
            }
            tweet_data.append(tweet_info)
            
            # Mark tweet as seen
            await save_tweet_id(SEEN_TWEETS_FILE, t.id)
            
            # Break if we have enough tweets
            if len(tweet_data) >= count:
                break
                
        return {
            "status": "success",
            "tweets": tweet_data,
            "message": f"Found {len(tweet_data)} new tweets (excluding previously seen, replied, and media tweets)"
        }
    except TwitterException as e:
        return {
            "status": "error",
            "message": f"Error searching tweets: {str(e)}"
        }

async def tweet_reply(params: Dict[str, Any], processor: LLMProcessor = None) -> Dict[str, Any]:
    """Reply to a tweet using the Twitter API."""
    # Check if we need to sleep
    should_sleep_now, sleep_seconds = await should_sleep()
    if should_sleep_now:
        hours = sleep_seconds / 3600
        return {
            "status": "rate_limit",
            "message": f"Reached maximum replies ({MAX_REPLIES}). Sleeping for {hours:.1f} hours."
        }

    tweet_id = params.get("tweet_id")
    text = params.get("text")
    
    try:
        # Get the tweet we're replying to
        tweet = await processor.twitter_client.get_tweet_by_id(tweet_id)
        # Post the reply
        reply = await tweet.reply(text)
        
        # Record that we replied to this tweet
        await save_tweet_id(REPLIED_TWEETS_FILE, tweet_id)
        await increment_reply_count()
        
        # Sleep for 30 seconds after replying
        await asyncio.sleep(30)
        
        return {
            "status": "success",
            "message": f"Reply posted: {reply.id}",
            "tweet_id": reply.id
        }
    except TwitterException as e:
        return {
            "status": "error",
            "message": f"Error posting reply: {str(e)}"
        }

async def tweet_sleep(params: Dict[str, Any], processor: LLMProcessor = None) -> Dict[str, Any]:
    """Wait for specified number of seconds (real sleep)."""
    seconds = params.get("seconds", 10)
    await asyncio.sleep(seconds)
    return {
        "status": "success",
        "message": f"Slept for {seconds} seconds"
    }

# --------------------------------------------------------------------------------
# Processor Initialization
# --------------------------------------------------------------------------------

COOKIE_FILE = 'cookies.json'

async def initialize_processor():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    config_dir = os.path.join(current_dir, 'config')

    proc = LLMProcessor(
        functions_file=os.path.join(config_dir, 'functions.json'),
        goal_file=os.path.join(config_dir, 'goal.yaml'),
        model_type="openai",
        model_name="gpt-4o-mini",
        ui_visibility=True,
        history_size=10,
        summary_interval=7,
        summary_window=15
    )

    # Wrap each function so the processor is passed
    async def wrapped_search(params):
        return await tweet_search(params, processor=proc)
    async def wrapped_reply(params):
        return await tweet_reply(params, processor=proc)
    async def wrapped_sleep(params):
        return await tweet_sleep(params, processor=proc)

    # Register functions
    proc.register_function("tweet_search", wrapped_search)
    proc.register_function("tweet_reply", wrapped_reply)
    proc.register_function("tweet_sleep", wrapped_sleep)

    # Create twikit client
    try:
        proc.twitter_client = Client(language='en-US')

        # Try loading cookies first
        if os.path.exists(COOKIE_FILE):
            try:
                proc.twitter_client.load_cookies(COOKIE_FILE)
                print("Successfully loaded existing cookies")
                return proc
            except Exception as e:
                print(f"Error loading cookies: {e}")

        # If no cookies or invalid, perform login
        tw_user = os.environ.get("TWITTER_USERNAME")
        tw_email = os.environ.get("TWITTER_EMAIL")
        tw_pass = os.environ.get("TWITTER_PASSWORD")
        print(tw_user, tw_email, tw_pass)
        await proc.twitter_client.login(auth_info_1=tw_user, auth_info_2=tw_email, password=tw_pass)

        # Save cookies for future use
        proc.twitter_client.save_cookies(COOKIE_FILE)
        print("Saved new cookies for future use")

    except TwitterException as e:
        print(f"Login error: {e}")
        raise

    return proc

# --------------------------------------------------------------------------------
# Main (no rate-limit checks)
# --------------------------------------------------------------------------------

async def main():
    processor = await initialize_processor()

    # Just 20 steps of "action → execution"
    for step in range(20):
        response = await processor.get_next_action()
        action = response["action"]
        cmd_id = action["command_id"]
        params = action["parameters"]
        reasoning = response["analysis"].get("reasoning", "no reasoning")

        # Execute the chosen command
        res = await processor.execute_command(cmd_id, params, context=reasoning)

        print(f"--- Step {step + 1} result ---")
        print(res)

    try:
        await processor.twitter_client.logout()
    except Exception as e:
        print(f"Error during logout: {e}")

    print("Agent finished working.")

if __name__ == "__main__":
    asyncio.run(main())
