import pytest
import asyncio
import os
import sys
import json

# Add src to PYTHONPATH
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))

from examples.twitter_agent.main import initialize_processor


@pytest.mark.asyncio
async def test_twitter_agent_basic():
    """
    A full production-like test with no mocking:
      1) Processor initialization (logging into Twitter via .env)
      2) Searching tweets (real API call)
      3) Posting a reply to one of the found tweets (real tweet creation)
      4) Performing a sleep operation
      5) Checking stats (for the newly posted tweet)

    WARNING: This test will actually post a tweet. Ensure you have valid credentials 
    and that you're comfortable making a real post on Twitter.
    """

    # 1) Initialization (login with credentials)
    processor = await initialize_processor()
    assert processor is not None, "Processor should not be None"
    assert hasattr(processor, 'twitter_client'), "Processor should have a Twitter client"

    # 2) Searching tweets: let's fetch 1 tweet for "AI agents"
    search_result = await processor.execute_command(
        command_id=0,  # tweet_search
        parameters={"count": 1},
        context="test search"
    )
    print("Search result:", search_result)
    assert search_result['status'] == 'success', "Tweet search must succeed"

    found_tweets = search_result.get('found_tweets', [])
    assert len(found_tweets) > 0, "At least one tweet should be found"

    # We'll reply to the first tweet
    target_tweet_id = found_tweets[0]
    print("Tweet chosen for reply:", target_tweet_id)

    # 3) Post a reply to the found tweet
    reply_text = "Hello from AI_Agent test!"
    reply_result = await processor.execute_command(
        command_id=1,  # tweet_reply
        parameters={"tweet_id": target_tweet_id, "text": reply_text},
        context="test reply"
    )
    print("Reply result:", reply_result)
    if reply_result['status'] == 'error':
        pytest.fail(f"Could not post a reply. Reason: {reply_result['message']}")

    posted_tweet_id = reply_result.get('tweet_id')
    assert posted_tweet_id, "A successful reply must contain the 'tweet_id' field"
    print("Newly posted tweet:", posted_tweet_id)

    # 4) Perform a sleep
    sleep_result = await processor.execute_command(
        command_id=2,  # tweet_sleep
        parameters={"seconds": 5},
        context="sleep test"
    )
    print("Sleep result:", sleep_result)
    assert sleep_result['status'] == 'success', "Sleep command should succeed"

    # 5) Check stats for the new tweet
    stats_result = await processor.execute_command(
        command_id=3,  # tweet_check_stats
        parameters={"tweet_id": posted_tweet_id},
        context="check stats"
    )
    print("Check stats result:", stats_result)
    assert stats_result['status'] == 'success', "Stats command should succeed"
    assert 'favorite_count' in stats_result, "Expected favorite_count in the result"
    assert 'reply_count' in stats_result, "Expected reply_count in the result"

    print("All basic checks passed with real API calls!")
