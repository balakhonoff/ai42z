from typing import Dict, Any
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from core.llm_processor import LLMProcessor

def is_goal_achieved(history) -> bool:
    """Check if calculation goal is achieved"""
    try:
        # Find submission with correct result
        submit = next(entry for entry in history 
                     if entry.command_name == 'submit_result' 
                     and entry.result['status'] == 'success'
                     and entry.parameters['value'] == 14)
        return True
    except StopIteration:
        return False

async def initialize_processor():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    config_dir = os.path.join(current_dir, 'config')
    
    processor = LLMProcessor(
        os.path.join(config_dir, 'functions.json'),
        os.path.join(config_dir, 'goal.yaml'),
        model_type="openai",
        ui_visibility=False
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

    async def submit_result(params: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "status": "success",
            "message": f"Submitted result: {params['value']}",
            "value": params['value']
        }

    processor.register_function('add', add)
    processor.register_function('multiply', multiply)
    processor.register_function('submit_result', submit_result)

    return processor 