import tweepy
import os
import sys

from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

load_dotenv()


# The app's API (Consumer) credentials from your paid account
api_key = os.getenv("TWITTER_API_KEY") or ""
api_secret = os.getenv("TWITTER_API_SECRET") or ""

def get_oauth_tokens_for_other_account():
    """
    Minimal script to generate OAuth 1.0a tokens for the other account,
    using out-of-band (PIN) flow.
    """
    # 1. Initialize OAuth1UserHandler
    auth = tweepy.OAuth1UserHandler(
        api_key,
        api_secret,
        callback="oob"   # 'oob' means Twitter gives you a PIN code
    )

    # 2. Get authorization URL
    try:
        redirect_url = auth.get_authorization_url(signin_with_twitter=True)
    except tweepy.TweepyException as e:
        print("Error! Failed to get request token:", e)
        return

    # 3. Prompt user to visit the URL and authorize your app
    print(f"Please go here and authorize with the OTHER account:\n{redirect_url}")
    verifier = input("Enter the PIN provided by Twitter: ")

    # 4. Exchange the PIN for access tokens
    try:
        auth.get_access_token(verifier)
        # 5. Print or store the tokens
        print("Access Token:", auth.access_token)
        print("Access Token Secret:", auth.access_token_secret)
    except tweepy.TweepyException as e:
        print("Error! Failed to get access token:", e)

get_oauth_tokens_for_other_account()