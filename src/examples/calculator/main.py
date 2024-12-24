from typing import Dict, Any
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from core.llm_processor import LLMProcessor

def is_goal_achieved(history) -> bool:
    """Check if calculation goal is achieved"""
    try:
        # Find addition operation
        add_op = next(entry for entry in history 
                     if entry.command_name == 'add' 
                     and entry.result['status'] == 'success')
        
        # Find multiplication operation that came after addition
        mult_op = next(entry for entry in history 
                      if entry.command_name == 'multiply' 
                      and entry.timestamp > add_op.timestamp
                      and entry.result['status'] == 'success'
                      and entry.result['value'] == 14)
        
        return True
    except StopIteration:
        return False

async def initialize_processor():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    config_dir = os.path.join(current_dir, 'config')
    
    processor = LLMProcessor(
        os.path.join(config_dir, 'functions.json'),
        os.path.join(config_dir, 'goal.yaml'),
        model_type="openai"
    )
    
    async def add(params: Dict[str, Any]) -> Dict[str, Any]:
        result = params['a'] + params['b']
        return {
            "status": "success",
            "message": f"Added {params['a']} + {params['b']}",
            "value": result
        }

    async def multiply(params: Dict[str, Any]) -> Dict[str, Any]:
        result = params['a'] * params['b']
        return {
            "status": "success",
            "message": f"Multiplied {params['a']} * {params['b']}",
            "value": result
        }

    processor.register_function('add', add)
    processor.register_function('multiply', multiply)

    return processor 