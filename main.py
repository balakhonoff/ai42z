# main.py
from datetime import datetime, timedelta
from llm_processor import LLMProcessor
from typing import Dict, Any

def check_command_possibility(history, command_name: str) -> tuple[bool, str]:
    """Check if command can be executed based on history"""
    # Skip checks for power and throttle commands
    if command_name in ['power_coffee_machine', 'throttle']:
        return True, ""
        
    # Check if machine is powered on
    last_power = next((entry for entry in reversed(history) 
                      if entry.command_name == 'power_coffee_machine' 
                      and entry.result['status'] == 'success'), None)
    if not last_power or last_power.parameters.get('power') != 'on':
        return False, "Machine is not powered on"

    if command_name == 'add_coffee':
        # Check for successful throttle after power on
        last_throttle = next((entry for entry in reversed(history) 
                            if entry.command_name == 'throttle'
                            and entry.result['status'] == 'accepted'
                            and entry.timestamp > last_power.timestamp), None)
        if not last_throttle:
            return False, "Machine is not heated yet"
            
    if command_name == 'start_brewing':
        # Check for successful coffee addition
        last_coffee = next((entry for entry in reversed(history) 
                          if entry.command_name == 'add_coffee'
                          and entry.result['status'] == 'success'), None)
        if not last_coffee:
            return False, "No coffee grounds added"
            
    return True, ""

async def initialize_processor():
    processor = LLMProcessor('config/functions.json', 'config/goal.yaml', model_type="openai")
    
    # Define function implementations
    async def power_coffee_machine(params: Dict[str, Any]) -> Dict[str, Any]:
        if "power" not in params:
            return {"status": "error", "message": "Missing required parameter 'power'"}
        
        possible, error = check_command_possibility(processor.execution_history, 'power_coffee_machine')
        if not possible:
            return {"status": "error", "message": error}
        
        return {
            "status": "success",
            "message": f"Machine powered {params['power']}"
        }

    async def add_coffee(params: Dict[str, Any]) -> Dict[str, Any]:
        possible, error = check_command_possibility(processor.execution_history, 'add_coffee')
        if not possible:
            return {"status": "error", "message": error}
            
        return {
            "status": "success", 
            "message": f"Added {params['amount_grams']}g coffee"
        }

    async def start_brewing(params: Dict[str, Any]) -> Dict[str, Any]:
        possible, error = check_command_possibility(processor.execution_history, 'start_brewing')
        if not possible:
            return {"status": "error", "message": error}
            
        # Check for correct amount of coffee
        last_coffee = next((entry for entry in reversed(processor.execution_history) 
                         if entry.command_name == 'add_coffee'
                         and entry.result['status'] == 'success'), None)
        if last_coffee.parameters['amount_grams'] != params['cups'] * 15:
            return {
                "status": "error", 
                "message": f"Wrong amount of coffee. Need {params['cups'] * 15}g for {params['cups']} cups"
            }
            
        return {
            "status": "success", 
            "message": f"Successfully brewing {params['cups']} cups of coffee"
        }

    async def throttle(params: Dict[str, Any]) -> Dict[str, Any]:
        return {"status": "accepted"}

    # Register implementations
    processor.register_function('throttle', throttle)
    processor.register_function('power_coffee_machine', power_coffee_machine)
    processor.register_function('add_coffee', add_coffee)
    processor.register_function('start_brewing', start_brewing)

    return processor

def is_goal_achieved(history) -> bool:
    """Check if coffee making goal is achieved based on command history"""
    try:
        # Check command sequence
        power_on = next(entry for entry in history 
                       if entry.command_name == 'power_coffee_machine' 
                       and entry.parameters['power'] == 'on' 
                       and entry.result['status'] == 'success')
                       
        throttle = next(entry for entry in history 
                       if entry.command_name == 'throttle' 
                       and entry.timestamp > power_on.timestamp)
                       
        add_coffee = next(entry for entry in history 
                         if entry.command_name == 'add_coffee' 
                         and entry.parameters['amount_grams'] == 30 
                         and entry.result['status'] == 'success')
                         
        brew = next(entry for entry in history 
                   if entry.command_name == 'start_brewing' 
                   and entry.parameters['cups'] == 2 
                   and entry.result['status'] == 'success')
                   
        return True
    except StopIteration:
        return False