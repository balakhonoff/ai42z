pytest_plugins = ["pytest_asyncio"]

# @pytest.fixture
# async def initialize_processor():
#     processor = LLMProcessor('config/functions.json', 'config/goal.yaml', model_type="openai")
#     # Регистрация функций...
#     return processor