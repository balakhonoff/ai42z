import asyncio
import os
import sys
from datetime import datetime, timedelta
from typing import Dict, Any
from dotenv import load_dotenv

# Add src to Python path (adjust for your local environment)
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

# Load environment variables
load_dotenv()

# External imports
import tweepy

# -------------------------------------------------------------------------
# LLM Processor (your existing module)
# -------------------------------------------------------------------------
from core.llm_processor import LLMProcessor

# -------------------------------------------------------------------------
# TwitterAPI Classes & Mock Structures
# -------------------------------------------------------------------------
class TwitterAPIException(Exception):
    """Custom exception to mimic Twikit's TwitterException."""
    pass

class MockMedia:
    """Mock class to indicate presence of media (for filtering)."""
    def __init__(self):
        pass

class MockUser:
    """Mimics a user object."""
    def __init__(self, user_data: dict):
        self.id = user_data["id"]
        self.name = user_data.get("name")
        self.screen_name = user_data.get("username")
        self.description = user_data.get("description")

        pm = user_data.get("public_metrics", {})
        self.followers_count = pm.get("followers_count", 0)
        self.following_count = pm.get("following_count", 0)
        self.verified = user_data.get("verified", False)
        self.is_blue_verified = False  # Not directly provided in v2

class MockTweet:
    """Mimics a tweet object."""
    def __init__(self, tweet_data: dict, user_data: dict = None, media_in_tweet: bool = False):
        self.id = str(tweet_data["id"])
        self.text = tweet_data.get("text")
        self.created_at = tweet_data.get("created_at", datetime.utcnow())

        pm = tweet_data.get("public_metrics", {})
        self.favorite_count = pm.get("like_count", 0)
        self.retweet_count = pm.get("retweet_count", 0)
        self.reply_count = pm.get("reply_count", 0)

        self.lang = tweet_data.get("lang", "en")
        self.is_quote_status = False  # Not directly in v2
        self.media = [MockMedia()] if media_in_tweet else []

        if user_data is not None:
            self.user = MockUser(user_data)
        else:
            self.user = None

class TwitterAPIWrapper:
    """
    A thin wrapper around Tweepy v2's Client, providing async-like methods that
    return simplified tweet/user structures (MockTweet, MockUser).
    """

    def __init__(self):
        # Load credentials from environment
        api_key = os.getenv("TWITTER_API_KEY", "")
        api_secret = os.getenv("TWITTER_API_SECRET", "")
        access_token = os.getenv("TWITTER_ACCESS_TOKEN_ai42z", "")
        access_token_secret = os.getenv("TWITTER_ACCESS_SECRET_ai42z", "")
        bearer_token = os.getenv("TWITTER_BEARER_TOKEN", None)

        try:
            self.client = tweepy.Client(
                bearer_token=bearer_token,
                consumer_key=api_key,
                consumer_secret=api_secret,
                access_token=access_token,
                access_token_secret=access_token_secret
            )
        except Exception as e:
            raise TwitterAPIException(f"Error initializing Tweepy client: {e}")

    async def search_tweet(self, query: str, sort_order: str, count: int):
        """Use 'search_recent_tweets' to find tweets about AI agents."""
        try:
            max_results = min(count, 100)
            response = self.client.search_recent_tweets(
                query=query,
                max_results=max_results,
                tweet_fields=["id", "text", "created_at", "lang", "public_metrics"],
                expansions=["author_id", "attachments.media_keys", "referenced_tweets.id"],
                user_fields=["id", "name", "username", "description", "public_metrics", "verified"]
            )
            if not response or not response.data:
                return []

            tweets_data = response.data
            includes = response.includes if response.includes else {}
            users = {u["id"]: u for u in includes.get("users", [])}

            results = []
            for td in tweets_data:
                author_id = td.author_id
                user_data = users.get(author_id) if author_id else None

                # Check if media is present
                media_in_tweet = False
                if td.attachments and "media_keys" in td.attachments:
                    if len(td.attachments["media_keys"]) > 0:
                        media_in_tweet = True

                # Convert Tweepy Tweet to a dictionary
                tweet_data = {
                    "id": td.id,
                    "text": td.text,
                    "created_at": td.created_at,  # We'll handle conversion after
                    "lang": td.lang,
                    "public_metrics": td.public_metrics,
                }
                results.append(MockTweet(tweet_data, user_data, media_in_tweet))

            return results

        except Exception as e:
            raise TwitterAPIException(f"Error searching tweets: {e}")

    async def get_tweet_by_id(self, tweet_id: str):
        """Fetch a single tweet by ID."""
        print(f"[DEBUG] get_tweet_by_id: Attempting to retrieve tweet {tweet_id}")
        try:
            response = self.client.get_tweet(
                id=tweet_id,
                expansions=["author_id", "attachments.media_keys", "referenced_tweets.id"],
                tweet_fields=["id", "text", "created_at", "lang", "public_metrics", "referenced_tweets"],
                user_fields=["id", "name", "username", "description", "public_metrics", "verified"]
            )
            print(f"[DEBUG] Raw response for tweet {tweet_id}: {response}")

            if not response or not response.data:
                print(f"[DEBUG] No data found for tweet {tweet_id}")
                return None

            tweet_obj = response.data

            # 'includes' is separate from the main tweet object
            includes = response.includes if response.includes else {}
            users = {u["id"]: u for u in includes.get("users", [])}

            media_in_tweet = False
            if tweet_obj.attachments and "media_keys" in tweet_obj.attachments:
                if len(tweet_obj.attachments["media_keys"]) > 0:
                    media_in_tweet = True

            tweet_data = {
                "id": tweet_obj.id,
                "text": tweet_obj.text,
                "created_at": tweet_obj.created_at,
                "lang": tweet_obj.lang,
                "public_metrics": tweet_obj.public_metrics,
            }

            if tweet_obj.referenced_tweets:
                print(f"[DEBUG] Tweet references another tweet: {tweet_obj.referenced_tweets}")

            author_id = tweet_obj.author_id
            user_data = users.get(author_id) if author_id else None

            return MockTweet(tweet_data, user_data, media_in_tweet)

        except Exception as e:
            print(f"[DEBUG] Exception in get_tweet_by_id for tweet {tweet_id}: {e}")
            raise TwitterAPIException(f"Error getting tweet by ID: {e}")

    async def reply_to_tweet(self, tweet_id: str, text: str) -> str:
        """Posts a reply. Returns the new tweet's ID as a string."""
        try:
            print(f"[DEBUG] reply_to_tweet: Attempting to reply to {tweet_id} with text: {text}")
            resp = self.client.create_tweet(text=text, in_reply_to_tweet_id=tweet_id)
            print(f"[DEBUG] Raw response from create_tweet: {resp}")
            if not resp or not resp.data:
                raise TwitterAPIException("No response from Twitter when creating tweet.")
            new_tweet_id = resp.data.get("id")
            return str(new_tweet_id)
        except Exception as e:
            raise TwitterAPIException(f"Error posting reply: {e}")

# -------------------------------------------------------------------------
# Tweet Tracking & Rate-Limit Logic
# -------------------------------------------------------------------------
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
    """Get current reply count and reset if needed."""
    try:
        try:
            with open(LAST_RESET_FILE, 'r') as f:
                last_reset = datetime.fromisoformat(f.read().strip())
        except (FileNotFoundError, ValueError):
            last_reset = datetime.now()
            with open(LAST_RESET_FILE, 'w') as f:
                f.write(last_reset.isoformat())

        if (datetime.now() - last_reset).total_seconds() >= RESET_HOURS * 3600:
            with open(REPLY_COUNT_FILE, 'w') as f:
                f.write('0')
            with open(LAST_RESET_FILE, 'w') as f:
                f.write(datetime.now().isoformat())
            return 0

        with open(REPLY_COUNT_FILE, 'r') as f:
            return int(f.read().strip())
    except (FileNotFoundError, ValueError):
        with open(REPLY_COUNT_FILE, 'w') as f:
            f.write('0')
        return 0

async def increment_reply_count():
    """Increment the reply count by 1."""
    count = await get_reply_count()
    with open(REPLY_COUNT_FILE, 'w') as f:
        f.write(str(count + 1))

async def should_sleep() -> tuple[bool, float]:
    """Check if we need to sleep (rate-limiting)."""
    count = await get_reply_count()
    if count >= MAX_REPLIES:
        with open(LAST_RESET_FILE, 'r') as f:
            last_reset = datetime.fromisoformat(f.read().strip())
        next_reset = last_reset + timedelta(hours=RESET_HOURS)
        sleep_seconds = (next_reset - datetime.now()).total_seconds()
        return True, max(0, sleep_seconds)
    return False, 0

# -------------------------------------------------------------------------
# Functions that interact with Twitter (using TwitterAPIWrapper)
# -------------------------------------------------------------------------
def _datetime_to_str(dt):
    """Convert a datetime to ISO-format string or leave it alone if not datetime."""
    if isinstance(dt, datetime):
        return dt.isoformat()
    return dt

async def tweet_search(params: Dict[str, Any], processor: LLMProcessor = None) -> Dict[str, Any]:
    """Search for tweets about AI agents."""
    count = params.get("count", 5)
    try:
        replied_tweets = await load_tweet_ids(REPLIED_TWEETS_FILE)
        seen_tweets = await load_tweet_ids(SEEN_TWEETS_FILE)

        # Get more tweets than requested to allow for filtering
        tweets = await processor.twitter_client.search_tweet("AI agents", "Latest", count=count * 2)

        tweet_data = []
        for t in tweets:
            # Skip if already replied, seen, or has media
            if t.id in replied_tweets or t.id in seen_tweets or len(t.media) > 0:
                continue

            # Convert datetime to string so we can JSON-serialize
            created_str = _datetime_to_str(t.created_at)

            tweet_info = {
                "id": t.id,
                "author": {
                    "id": t.user.id if t.user else None,
                    "name": t.user.name if t.user else None,
                    "screen_name": t.user.screen_name if t.user else None,
                    "description": t.user.description if t.user else None,
                    "followers_count": t.user.followers_count if t.user else 0,
                    "following_count": t.user.following_count if t.user else 0,
                    "verified": t.user.verified if t.user else False,
                    "is_blue_verified": t.user.is_blue_verified if t.user else False
                },
                "text": t.text,
                "created_at": created_str,
                "favorite_count": t.favorite_count,
                "retweet_count": t.retweet_count,
                "reply_count": t.reply_count,
                "lang": t.lang,
                "is_quote_status": t.is_quote_status,
                "has_media": (len(t.media) > 0)
            }
            tweet_data.append(tweet_info)

            # Mark tweet as seen
            await save_tweet_id(SEEN_TWEETS_FILE, t.id)

            # Stop once we've collected enough
            if len(tweet_data) >= count:
                break

        return {
            "status": "success",
            "tweets": tweet_data,
            "message": f"Found {len(tweet_data)} new tweets (excluding previously seen, replied, and media tweets)"
        }
    except TwitterAPIException as e:
        return {
            "status": "error",
            "message": f"Error searching tweets: {str(e)}"
        }

async def tweet_reply(params: Dict[str, Any], processor: LLMProcessor = None) -> Dict[str, Any]:
    """Reply to a tweet using the Twitter API."""
    should_sleep_now, sleep_seconds = await should_sleep()
    if should_sleep_now:
        hours = sleep_seconds / 3600
        return {
            "status": "rate_limit",
            "message": f"Reached maximum replies ({MAX_REPLIES}). Sleeping for {hours:.1f} hours."
        }

    tweet_id = params.get("tweet_id")
    text = params.get("text", "")

    print(f"[DEBUG] tweet_reply called with tweet_id={tweet_id} and text={text}")

    try:
        # Confirm the tweet exists
        tweet = await processor.twitter_client.get_tweet_by_id(tweet_id)
        if not tweet:
            return {
                "status": "error",
                "message": f"Tweet not found with ID {tweet_id}"
            }

        # Post the reply
        reply_id = await processor.twitter_client.reply_to_tweet(tweet.id, text)

        # Record that we replied
        await save_tweet_id(REPLIED_TWEETS_FILE, tweet_id)
        await increment_reply_count()

        # Sleep for 30 seconds after replying
        await asyncio.sleep(30)

        return {
            "status": "success",
            "message": f"Reply posted: {reply_id}",
            "tweet_id": reply_id
        }
    except TwitterAPIException as e:
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

# -------------------------------------------------------------------------
# Processor Initialization
# -------------------------------------------------------------------------
async def initialize_processor():
    """
    Create the LLMProcessor, attach the TwitterAPIWrapper, and register functions.
    """
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

    # Attach our Twitter API wrapper
    proc.twitter_client = TwitterAPIWrapper()

    # Wrap each function to pass processor
    async def wrapped_search(params):
        return await tweet_search(params, processor=proc)

    async def wrapped_reply(params):
        return await tweet_reply(params, processor=proc)

    async def wrapped_sleep(params):
        return await tweet_sleep(params, processor=proc)

    # Register them so the LLM can call them
    proc.register_function("tweet_search", wrapped_search)
    proc.register_function("tweet_reply", wrapped_reply)
    proc.register_function("tweet_sleep", wrapped_sleep)

    return proc

# -------------------------------------------------------------------------
# Main (Entry Point)
# -------------------------------------------------------------------------
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

    print("Agent finished working.")

if __name__ == "__main__":
    asyncio.run(main())
