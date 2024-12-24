# ai42z - The First LLM Processor For Proactive Autonomous AI Agents

**ai42z** is an experimental framework designed to enable Large Language Models (LLMs) to function as proactive, autonomous AI agents. Rather than simply answering questions, these agents continuously evaluate their environment, decide on the next best action, and perform it—all guided by predefined functions and goals.

## Quick Start

1. **Installation**:
```bash
# Clone the repository
git clone <repository-url>
cd ai42z

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up your OpenAI API key
export OPENAI_API_KEY='your-api-key-here'
```

2. **Try the Examples**:
```bash
cd src

# Run the calculator example
pytest -v -s examples/calculator/tests/test_calculator.py

# Run the coffee maker example
pytest -v -s examples/coffee_maker/tests/test_coffee_maker.py
```

## Available Examples

### Calculator Agent
A simple example demonstrating basic arithmetic operations and result submission. The agent:
- Calculates (4 + 3) * 2 using available operations
- Uses proper order of operations
- Submits the final result for verification

Located in `src/examples/calculator/`

### Coffee Maker Agent
A more complex example simulating coffee machine control with state management. The agent:
- Powers on the machine
- Waits for heating
- Adds the correct amount of coffee
- Starts brewing
- Monitors operation sequence and conditions

Located in `src/examples/coffee_maker/`

## Project Structure
```
src/
├── core/                     # Core framework components
│   └── llm_processor.py     # Main LLM interaction logic
├── examples/                 # Example implementations
│   ├── calculator/          # Simple arithmetic calculator agent
│   │   ├── config/         # Agent-specific configurations
│   │   ├── tests/         # Agent-specific tests
│   │   └── main.py        # Agent implementation
│   └── coffee_maker/       # Coffee machine control agent
```

## Creating Your Own Agent

1. Create a new directory under `examples/`:
```bash
mkdir -p src/examples/your_agent/{config,tests}
touch src/examples/your_agent/{__init__.py,main.py}
touch src/examples/your_agent/tests/{__init__.py,test_your_agent.py}
```

2. Define your functions in `config/functions.json`:
```json
{
  "functions": [
    {
      "id": 1,
      "name": "your_function",
      "description": "Description of what it does",
      "parameters": {
        "param1": {
          "type": "number",
          "description": "Parameter description"
        }
      }
    }
  ]
}
```

3. Define your goal in `config/goal.yaml`:
```yaml
goal:
  description: "What your agent needs to achieve"
  success_criteria:
    - "List of criteria"
```

4. Implement your agent in `main.py` and create tests in `tests/test_your_agent.py`

## Key Concepts

- **LLMs as Action-Oriented Agents**: Transform LLMs from static responders into iterative decision-makers
- **Goal-Driven Autonomy**: Agents work toward clear objectives through step-by-step actions
- **Execution History**: Actions and outcomes are recorded and used for context in subsequent decisions
- **Explainable Reasoning**: Agents articulate their decision-making process

## Development

```bash
# Run all tests
cd src
pytest -v -s

# Run with detailed logs
pytest -v -s examples/calculator/tests/test_calculator.py --log-cli-level=DEBUG
```

## Contributing

1. Fork the repository
2. Create your feature branch
3. Add your example or improvement
4. Create a pull request

## License

[Your chosen license]

---

For more detailed information about the framework's architecture, advanced use cases, and roadmap, please visit our [documentation](link-to-docs).