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

## Planned Features

### Enhanced Memory Architecture
- Persistent long-term memory storage across sessions
- Hierarchical memory organization with categorization
- Ability to prune and consolidate outdated information
- Cross-session learning and knowledge transfer

### Graceful Interruption Handling
- Support for pausing and resuming agent operations
- Safe state preservation during unexpected shutdowns
- Ability to handle external interruptions without losing progress
- Graceful cleanup of resources during interruption

### Modern Tools Integration
- Migration from function-based to tool-based architecture
- Enhanced error handling and validation
- Improved type safety and documentation
- Better support for async operations and streaming

### Streamlined Configuration
- Single YAML configuration file for all settings
- Dynamic configuration reloading
- Environment-specific configurations
- Simplified setup process for new agents

### Visual Input Processing
- Support for image analysis and understanding
- Multi-modal reasoning combining text and images
- Visual state tracking and change detection
- Image-based decision making capabilities

### System Integration
- Safe and controlled access to computer resources
- File system operations with proper permissions
- Network access with security controls
- Integration with system services and APIs

### Goal Progress Tracking
- Real-time monitoring of goal completion status
- Progress visualization and metrics
- Dynamic goal adjustment based on conditions
- Clear success/failure criteria evaluation

### Action Feedback System
- Detailed outcome analysis for each action
- Learning from successful and failed attempts
- Performance metrics and improvement suggestions
- Historical action effectiveness tracking

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

   # Run the new Twitter agent example (instructions below)
   ```

## Available Examples

### Calculator Agent
A simple example demonstrating basic arithmetic operations and result submission. The agent:
- Calculates `(4 + 3) * 2` using available operations
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
- Efficient pathfinding using `look_around` and `move` commands
- Simple ASCII-based maze representation  

Located in `src/examples/maze_solver/`

### Twitter Agent
A **new** example that integrates with the **Twitter API** to:
- **Search** for tweets about AI agents  
- **Filter** out tweets already seen or replied to  
- **Reply** to selected tweets with insights on multi-agent systems, web3, etc.  

**Key Points**:
- Requires valid **Twitter API credentials** (bearer token, consumer key/secret, access token/secret).  
- Demonstrates error handling for tweet retrieval and rate limiting.  
- Leverages the **LLMProcessor** to decide which tweets to respond to and craft replies.

**Usage**:
1. Set up environment variables in your `.env` (or export them):
   ```bash
   TWITTER_API_KEY="your_consumer_key"
   TWITTER_API_SECRET="your_consumer_secret"
   TWITTER_ACCESS_TOKEN_ai42z="your_access_token"
   TWITTER_ACCESS_SECRET_ai42z="your_access_secret"
   TWITTER_BEARER_TOKEN="your_bearer_token"
   ```
2. Run the example:
   ```bash
   pytest -v -s examples/twitter_agent/tests/test_twitter_agent.py
   ```
   Or directly:
   ```bash
   python src/examples/twitter_agent/main.py
   ```
3. Observe the agent’s search results, replies, and any debug logs.

Located in `src/examples/twitter_agent/`

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
│   └── llm_processor.py      # Main LLM interaction logic
├── examples/                 # Example implementations
│   ├── calculator/           # Simple arithmetic calculator agent
│   │   ├── config/           # Agent-specific configurations
│   │   ├── tests/            # Agent-specific tests
│   │   └── main.py           # Agent implementation
│   ├── coffee_maker/         # Coffee machine control agent
│   ├── maze_solver/          # Maze navigation agent
│   └── twitter_agent/        # Twitter integration example
│       ├── config/           # Contains the agent's goal and function definitions
│       ├── tests/            # Tests for the Twitter agent
│       └── main.py           # Main code for searching and replying on Twitter
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

- **LLMs as Action-Oriented Agents**: Transform LLMs from static responders into iterative decision-makers.  
- **Goal-Driven Autonomy**: Agents work toward clear objectives through step-by-step actions.  
- **Execution History**: Actions and outcomes are recorded and used for context in subsequent decisions.  
- **Explainable Reasoning**: Agents articulate their decision-making process.  
- **Continuous Learning**: Agents accumulate and apply knowledge from their experiences.

## Development

```bash
# Run all tests
cd src
pytest -v -s

# Run basic examples (calculator, coffee maker, maze solver)
pytest -v -s tests/test_examples.py

# Run individual examples
pytest -v -s examples/calculator/tests/test_calculator.py
pytest -v -s examples/coffee_maker/tests/test_coffee_maker.py
pytest -v -s examples/maze_solver/tests/test_maze_solver.py

# Run the Twitter agent
pytest -v -s examples/twitter_agent/tests/test_twitter_agent.py

# Run with detailed logs
pytest -v -s examples/calculator/tests/test_calculator.py --log-cli-level=DEBUG
```

## Contributing

1. Fork the repository  
2. Create your feature branch  
3. Add your example or improvement  
4. Create a pull request  
