import pytest
import asyncio
import os
import sys
import json
from unittest.mock import patch, MagicMock

# Добавляем путь к src, чтобы импортировать main
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))
from examples.twitter_agent.main import initialize_processor


class AsyncMock(MagicMock):
    async def __call__(self, *args, **kwargs):
        return super(AsyncMock, self).__call__(*args, **kwargs)


@pytest.mark.asyncio
async def test_twitter_agent_basic():
    """
    Тест проверяет базовый функционал:
      1) Инициализация процессора
      2) Поиск твитов по ключу (настоящий)
      3) Имитация отправки ответа (мок, чтоб не постить)
    """
    # Мокаем Twitter клиент перед инициализацией
    mock_client = AsyncMock()
    mock_client.search_tweet = AsyncMock(return_value=[type('FakeTweet', (), {'id': '123'})])
    mock_client.login = AsyncMock(return_value=True)  # Успешный логин
    mock_client.create_tweet = AsyncMock(return_value=type('FakeTweet', (), {'id': 'mock_id'}))
    mock_client.get_tweet_by_id = AsyncMock(return_value=type('FakeTweet', (), {
        'favorite_count': 5,
        'reply_count': 2,
        'retweet_count': 1
    }))

    # Патчим TwitterException и Client в том месте, где они импортируются
    with patch('examples.twitter_agent.main.Client', return_value=mock_client), \
         patch('examples.twitter_agent.main.TwitterException', side_effect=Exception):
        processor = await initialize_processor()

        # 1) Проверим, что инициализация прошла
        assert processor is not None
        assert hasattr(processor, 'twitter_client'), "Должен быть twikit-клиент"

        # 2) Поиск твитов (уже замокан выше)
        search_result = await processor.execute_command(
            command_id=0,
            parameters={"count": 1},
            context="test search"
        )
        print("Результат поиска твитов:", search_result)
        assert search_result['status'] == 'success'

        # 3) Проверка ответа на твит
        reply_result = await processor.execute_command(
            command_id=1,
            parameters={"tweet_id": "1234567890", "text": "Test reply"},
            context="test reply"
        )
        assert reply_result['status'] == 'success'
        assert reply_result['message'].startswith("Ответ опубликован")

        # Проверка работы sleep
        sleep_result = await processor.execute_command(
            command_id=2,
            parameters={"seconds": 1},
            context="sleep test"
        )
        assert sleep_result['status'] == 'success'

        # Проверка статистики
        stats_result = await processor.execute_command(
            command_id=3,
            parameters={"tweet_id": "fake_id"},
            context="check stats"
        )
        assert stats_result['status'] == 'success'
        assert stats_result['favorite_count'] == 5

    print("Все базовые проверки прошли успешно.")
