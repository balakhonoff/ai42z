from dataclasses import dataclass
from typing import List, Dict, Any, Optional, Callable, Tuple, Union
import json
import yaml
from datetime import datetime
import asyncio
import openai
import os
from dotenv import load_dotenv
import re

load_dotenv()  # download data from .env

@dataclass
class ExecutionHistoryEntry:
    timestamp: datetime
    command_id: int
    command_name: str
    parameters: Dict[str, Any]
    result: Dict[str, Any]
    status: str
    context: str

class LLMProcessor:
    def __init__(self, 
                 functions_file: str, 
                 goal_file: str, 
                 model_type: str = "openai",
                 history_size: int = 10,
                 model_name: str = "gpt-4o-mini"):
        """Initialize the LLM Processor
        
        Args:
            functions_file: Path to functions configuration JSON
            goal_file: Path to goal configuration YAML
            model_type: Type of LLM to use
            history_size: Number of recent actions to include in history (default: 10)
            model_name: Name of the model to use (default: gpt-4o-mini)
        """
        self.functions_file = functions_file
        self.goal_file = goal_file
        self.model_type = model_type
        self.history_size = history_size
        self.execution_history = []
        self.implementations = {}
        self.functions: Dict = self._load_json(self.functions_file)
        self.goal: Dict = self._load_yaml(self.goal_file)
        self._load_available_functions()
        
        # LLM configuration
        if model_type == "local":
            openai.api_base = "http://127.0.0.1:1234/v1"
            openai.api_key = "lm-studio"
            self.model_name = model_name
        else:  # OpenAI
            openai.api_base = "https://api.openai.com/v1"
            openai.api_key = os.getenv("OPENAI_API_KEY")
            self.model_name = model_name

        self.generation_kwargs = {
            # "max_tokens": 512,
            # "temperature": 0.7,
            # "top_p": 0.9
        }

    def _load_json(self, file_path: str) -> Dict:
        """Load JSON configuration file"""
        with open(file_path, 'r') as f:
            return json.load(f)

    def _load_yaml(self, file_path: str) -> Dict:
        """Load YAML configuration file"""
        with open(file_path, 'r') as f:
            return yaml.safe_load(f)

    def register_function(self, name: str, implementation: Callable):
        """Register a function implementation"""
        self.implementations[name] = implementation

    def _entry_to_dict(self, entry: ExecutionHistoryEntry) -> Dict:
        """Convert history entry to dictionary for prompt generation"""
        return {
            "timestamp": entry.timestamp.isoformat(),
            "command_id": entry.command_id,
            "command_name": entry.command_name,
            "parameters": entry.parameters,
            "result": entry.result,
            "status": entry.status,
            "context": entry.context
        }

    def generate_prompt(self) -> str:
        """Generate prompt for LLM"""
        # Get the last N entries from history
        history = self.execution_history[-self.history_size:] if self.execution_history else []
        
        # Convert history entries to dict format
        history_dicts = [self._entry_to_dict(entry) for entry in history]
        
        prompt = f"""# LLM Processor Environment
You are participating in an iterative decision-making task. Your role is to analyze the current state and determine the SINGLE NEXT optimal action. You are NOT expected to solve the entire task in one step. Instead, focus on choosing the most logical next action given the current state and history.

## Decision Making Guidelines
- Analyze the execution history to understand what has been tried
- Consider the current state in relation to the goal
- Choose ONE next action that brings you closer to the goal
- Provide clear reasoning for why this specific action is the best next step
- Do not try to plan multiple steps ahead - focus only on the immediate next action

## Available Commands
{json.dumps(self.functions, indent=2)}

## Goal Configuration
{json.dumps(self.goal, indent=2)}

## Execution History (Last N={self.history_size} Actions)
{json.dumps(history_dicts, indent=2)}

## Your Response Format
Analyze the current state and provide a single next action. Your response must be a JSON object:

{{
  "analysis": {{
    "current_situation": "Brief assessment of the current state",
    "history_consideration": "How past actions influence this decision",
    "reasoning": "Detailed explanation of why this specific action is the best next step"
  }},
  "action": {{
    "command_id": 0,
    "parameters": {{
      // Parameters for the chosen command
    }},
    "expected_outcome": "What you expect this action to achieve towards the goal"
  }}
}}"""
        return prompt

    async def execute_command(self, command_id: int, parameters: Dict[str, Any], context: str) -> Dict[str, Any]:
        """Execute a command and record it in history"""
        # Find command definition
        command = next((cmd for cmd in self.functions['functions'] if cmd['id'] == command_id), None)
        if not command:
            raise ValueError(f"Unknown command ID: {command_id}")

        # Execute implementation
        if command['name'] not in self.implementations:
            raise ValueError(f"No implementation registered for command: {command['name']}")

        implementation = self.implementations[command['name']]
        
        # Handle both async and sync implementations
        if asyncio.iscoroutinefunction(implementation):
            result = await implementation(parameters)
        else:
            result = implementation(parameters)

        # Record in history
        entry = ExecutionHistoryEntry(
            timestamp=datetime.now(),
            command_id=command_id,
            command_name=command['name'],
            parameters=parameters,
            result=result,
            status="success" if result.get('status') in ['success', 'accepted'] else "failed",
            context=context
        )
        self.execution_history.append(entry)

        return result

    async def get_next_action(self) -> Dict[str, Any]:
        """Get the next action from the LLM"""
        prompt = self.generate_prompt()
        
        # Use only the last N actions in the prompt
        history = self.execution_history[-self.history_size:] if self.execution_history else []
        
        try:
            if self.model_type == "local":
                import openai
                client = openai.OpenAI(
                    base_url="http://127.0.0.1:1234/v1",
                    api_key="lm-studio"
                )
            else:
                from openai import OpenAI
                client = OpenAI()

            print("\n### Prompt to LLM ###")
            print(prompt)
            print("### End of Prompt ###\n")

            response = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: client.chat.completions.create(
                    model=self.model_name,
                    messages=[{"role": "user", "content": prompt}],
                    **self.generation_kwargs
                )
            )

            print("\n### LLM Raw Response ###")
            print(response)
            print("### End of LLM Raw Response ###\n")

            content = response.choices[0].message.content.strip()

            json_block_match = re.search(r"```json\s*(.*?)\s*```", content, flags=re.DOTALL | re.IGNORECASE)
            
            if json_block_match:
                json_str = json_block_match.group(1).strip()
            else:
                json_str = content.strip('`').strip()

            try:
                result = json.loads(json_str)
            except json.JSONDecodeError:
                print("Warning: Could not parse LLM response as JSON. Returning fallback action.")
                return {
                    "action": {"command_id": 0, "parameters": {}},
                    "analysis": {
                        "reasoning": "Error parsing response",
                        "current_situation": "Error occurred",
                        "history_consideration": "Error occurred"
                    }
                }

            # Add empty analysis if it doesn't exist
            if 'analysis' not in result:
                result['analysis'] = {
                    'reasoning': 'No reasoning provided',
                    'current_situation': 'No situation analysis provided', 
                    'history_consideration': 'No history consideration provided'
                }

            return result

        except Exception as e:
            print(f"Error calling LLM: {e}")
            return {
                "action": {"command_id": 0, "parameters": {}},
                "analysis": {
                    "reasoning": f"Error: {str(e)}",
                    "current_situation": "Error occurred",
                    "history_consideration": "Error occurred"
                }
            }

    def _load_available_functions(self):
        with open(self.functions_file, 'r') as f:
            self.available_functions = json.load(f)
    
    def _validate_command_params(self, command_id: int, params: Dict[str, Any]) -> Tuple[bool, str]:
        """Validates that all required parameters are present for the command"""
        if command_id not in self.available_functions:
            return False, f"Unknown command_id: {command_id}"
            
        function_spec = self.available_functions[command_id]
        required_params = {
            param_name for param_name, param_spec in function_spec.get('parameters', {}).items()
            if param_spec.get('required', False)
        }
        
        missing_params = required_params - set(params.keys())
        if missing_params:
            return False, f"Missing required parameters: {', '.join(missing_params)}"
            
        return True, ""

    async def process_response(self, response: str) -> Tuple[bool, Union[Dict, str]]:
        try:
            parsed = json.loads(response)
            command_id = parsed.get('command_id')
            params = parsed.get('params', {})
            
            # Validate command parameters
            is_valid, error_message = self._validate_command_params(command_id, params)
            if not is_valid:
                return False, error_message
                
            return True, parsed
        except json.JSONDecodeError:
            return False, "Failed to parse LLM response as JSON"
        except Exception as e:
            return False, f"Error processing LLM response: {str(e)}"