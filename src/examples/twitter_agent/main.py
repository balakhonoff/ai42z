import asyncio
import os
from datetime import datetime, timedelta
from typing import Dict, Any
import sys

# Добавляем верхний уровень src в Python-path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from core.llm_processor import LLMProcessor
from twikit import Client, TwitterException


# Глобальные переменные для guardrails
MAX_REPLIES_PER_HOUR = 10
replies_last_hour = 0
last_hour_window_start = datetime.now()

async def tweet_search(params: Dict[str, Any], processor: LLMProcessor = None) -> Dict[str, Any]:
    """Ищет твиты по теме AI agents."""
    count = params.get("count", 5)
    try:
        # Для примера возьмём 'AI agents' — можно расширять
        tweets = await processor.twitter_client.search_tweet("AI agents", "Latest", count=count)
        tweet_ids = [t.id for t in tweets]
        return {
            "status": "success",
            "found_tweets": tweet_ids,
            "message": f"Найдено {len(tweet_ids)} твитов"
        }
    except TwitterException as e:
        return {
            "status": "error",
            "message": f"Ошибка при поиске твитов: {str(e)}"
        }

async def tweet_reply(params: Dict[str, Any], processor: LLMProcessor = None) -> Dict[str, Any]:
    """Отправляет ответ на твит. Проверяем guardrails (не более 10 в час)."""
    global replies_last_hour, last_hour_window_start

    tweet_id = params.get("tweet_id")
    text = params.get("text", "")

    # Проверка лимита
    now = datetime.now()
    if now - last_hour_window_start > timedelta(hours=1):
        # Сбрасываем счетчик, если прошёл час
        replies_last_hour = 0
        last_hour_window_start = now

    if replies_last_hour >= MAX_REPLIES_PER_HOUR:
        return {
            "status": "error",
            "message": "Лимит 10 ответов в час исчерпан"
        }

    try:
        posted = await processor.twitter_client.create_tweet(text=text, reply_to=tweet_id)
        replies_last_hour += 1

        return {
            "status": "success",
            "message": f"Ответ опубликован: {posted.id}",
            "tweet_id": posted.id
        }

    except TwitterException as e:
        return {
            "status": "error",
            "message": f"Ошибка при ответе на твит: {str(e)}"
        }

async def tweet_sleep(params: Dict[str, Any], processor: LLMProcessor = None) -> Dict[str, Any]:
    """Ждём заданное число секунд (реальный sleep)."""
    seconds = params.get("seconds", 10)
    await asyncio.sleep(seconds)
    return {
        "status": "success",
        "message": f"Поспали {seconds} секунд"
    }

async def tweet_check_stats(params: Dict[str, Any], processor: LLMProcessor = None) -> Dict[str, Any]:
    """Смотрим лайки/реплаи (favorite_count, reply_count, retweet_count)."""
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
            "message": f"Не удалось проверить статистику: {str(e)}"
        }


async def initialize_processor():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    config_dir = os.path.join(current_dir, 'config')

    # Создаём LLMProcessor
    proc = LLMProcessor(
        functions_file=os.path.join(config_dir, 'functions.json'),
        goal_file=os.path.join(config_dir, 'goal.yaml'),
        model_type="openai",
        model_name="gpt-4o-mini",
        ui_visibility=False,   # Или True, если хотим web UI
        history_size=10,
        summary_interval=7,
        summary_window=15
    )

    # Создаём обёртки для функций, которые будут включать processor
    async def wrapped_tweet_search(params):
        return await tweet_search(params, processor=proc)
        
    async def wrapped_tweet_reply(params):
        return await tweet_reply(params, processor=proc)
        
    async def wrapped_tweet_sleep(params):
        return await tweet_sleep(params, processor=proc)
        
    async def wrapped_tweet_check_stats(params):
        return await tweet_check_stats(params, processor=proc)

    # Регистрируем обёртки функций
    proc.register_function("tweet_search", wrapped_tweet_search)
    proc.register_function("tweet_reply", wrapped_tweet_reply)
    proc.register_function("tweet_sleep", wrapped_tweet_sleep)
    proc.register_function("tweet_check_stats", wrapped_tweet_check_stats)

    # Создаём twikit Client
    # Можно логиниться через cookies или через логин/пароль из .env
    tw_user = os.getenv("TWITTER_USER", "your_user")
    tw_pass = os.getenv("TWITTER_PASSWORD", "your_pass")
    proc.twitter_client = Client(language='en-US')

    # Логинимся, если нужно (или загружаем cookies)
    try:
        # Можно вместо логина загрузить cookies:
        # proc.twitter_client.load_cookies('cookies.json')
        await proc.twitter_client.login(
            auth_info_1=tw_user,
            password=tw_pass
        )
    except TwitterException as e:
        print(f"Ошибка логина: {e}")

    return proc


# Глобальный объект процессора (можно инициализировать один раз)
processor: LLMProcessor = None

async def main():
    global processor
    processor = await initialize_processor()

    # Бесконечный цикл, где агент будет запрашивать у LLM задачу и исполнять
    # Для примера - только несколько шагов
    for step in range(20):
        response = await processor.get_next_action()
        action = response["action"]
        cmd_id = action["command_id"]
        params = action["parameters"]
        reasoning = response["analysis"].get("reasoning", "no reasoning")

        # Исполняем команду
        res = await processor.execute_command(cmd_id, params, context=reasoning)
        print(f"--- Step {step+1} result ---")
        print(res)
        # При желании: проверяем какие-то критические условия

    # Выход из цикла, логаут
    await processor.twitter_client.logout()
    print("Агент завершил работу.")


if __name__ == "__main__":
    asyncio.run(main())
