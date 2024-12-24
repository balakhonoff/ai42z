# ai42z - The First LLM Processor For Proactive Autonomous AI Agents

**ai42z** is an experimental framework designed to enable Large Language Models (LLMs) to function as proactive, autonomous AI agents. Rather than simply answering questions, these agents continuously evaluate their environment, decide on the next best action, and perform it—all guided by predefined functions and goals.

## Key Features

### Proactive Decision Making
- Continuous environment evaluation
- Goal-driven autonomous actions
- Step-by-step execution with clear reasoning

### Long-Term Memory and Learning
- Accumulates knowledge and insights during execution
- Periodically summarizes and consolidates learnings
- Uses accumulated knowledge to inform future decisions
- Extracts best practices, useful findings, and helpful knowledge
- Maintains a growing knowledge base that evolves with experience

## Quick Start

1. **Installation**:
```bash
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

### Maze Solver
A pathfinding agent that navigates through a maze to find the exit. This example demonstrates:
- Spatial navigation and exploration
- Decision making based on current state and history
- Efficient pathfinding using look_around and move commands
- Simple maze representation using ASCII characters:
  - `#` - Wall
  - `.` - Empty path
  - `X` - Exit
  - Starting position is always at (1, 1)

Example maze:
```
#######
#.....#  # Agent starts at (1,1)
###.#.#
###.###
###.###
#....X#  # Exit is marked with X
####### 
```

The agent uses three commands:
1. `look_around` - Check adjacent cells in all directions
2. `move` - Move in a specified direction (north, south, east, west)
3. `check_status` - Get current position and exploration statistics

Success criteria:
- Find and reach the exit cell marked as 'X'
- Avoid walls and stay within maze boundaries
- Use efficient exploration to minimize steps

This example showcases how the framework can be used for spatial navigation tasks and demonstrates the agent's ability to:
- Explore unknown environments
- Make decisions based on partial information
- Adapt strategy based on discovered obstacles
- Track progress towards a goal

## Advanced Features

### Long-Term Memory System
The framework includes a sophisticated long-term memory system that helps agents learn from experience:

1. **Knowledge Accumulation**:
   - Periodically analyzes recent actions and their outcomes
   - Extracts useful patterns, strategies, and insights
   - Merges new findings with existing knowledge

2. **Memory Configuration**:
   ```python
   processor = LLMProcessor(
       functions_file="config/functions.json",
       goal_file="config/goal.yaml",
       summary_interval=7,    # Update knowledge every 7 steps
       summary_window=15      # Consider last 15 steps when learning
   )
   ```

3. **Knowledge Integration**:
   - Accumulated knowledge is included in each prompt
   - Helps inform future decisions
   - Enables learning from past experiences
   - Improves decision quality over time

4. **Visual Monitoring** (Optional):
   ```python
   processor = LLMProcessor(
       # ... other parameters ...
       ui_visibility=True    # Enable web UI to monitor prompts
   )
   ```

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
- **Continuous Learning**: Agents accumulate and apply knowledge from their experiences

## Development

```bash
# Run all tests
cd src
pytest -v -s

# Run basic examples (calculator and coffee maker)
pytest -v -s tests/test_examples.py

# Run individual examples
pytest -v -s examples/calculator/tests/test_calculator.py
pytest -v -s examples/coffee_maker/tests/test_coffee_maker.py
pytest -v -s examples/maze_solver/tests/test_maze_solver.py

# Run with detailed logs
pytest -v -s examples/calculator/tests/test_calculator.py --log-cli-level=DEBUG
```

## Contributing

1. Fork the repository
2. Create your feature branch
3. Add your example or improvement
4. Create a pull request

## License

MIT License

Copyright (c) 2024

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
