# test_processor_real.py
import pytest
from datetime import datetime, timedelta
import json
import sys
import os

# Add the src directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))

from examples.coffee_maker.main import (
    initialize_processor,
    is_goal_achieved
)

@pytest.mark.asyncio
async def test_coffee_scenario_gpt4():
    """Test coffee making scenario with real GPT-4"""
    # Инициализация процессора
    processor = await initialize_processor()
    
    max_steps = 6
    success = False
    
    print("\n=== Starting GPT-4 Coffee Making Test ===")
    
    for step in range(max_steps):
        print(f"\n=== Step {step + 1} of {max_steps} ===")
        
        response = await processor.get_next_action()
        assert response is not None, "Should get valid response from GPT-4"
        
        print("\n=== Processed LLM Response ===")
        print(json.dumps(response, indent=2))
        
        print(f"\nChosen action: {response['action']}")
        print(f"Reasoning: {response['analysis']['reasoning']}")
        
        action = response['action']
        result = await processor.execute_command(
            action['command_id'],
            action['parameters'],
            response['analysis']['reasoning']
        )
        
        print(f"Action result: {result}\n")
        
        if is_goal_achieved(processor.execution_history):
            success = True
            print("\n=== Goal Achieved! ===")
            break
    
    assert success, "Should complete coffee making process"

    print("\n=== Final Execution History ===")
    for entry in processor.execution_history:
        print(f"- Command: {entry.command_name}")
        print(f"  Parameters: {entry.parameters}")
        print(f"  Result: {entry.result}\n")
    
    # Проверка выполненных команд
    commands_executed = [entry.command_name for entry in processor.execution_history]
    assert 'power_coffee_machine' in commands_executed, "Should have powered on the machine"
    assert 'throttle' in commands_executed, "Should have waited for heating"
    assert 'add_coffee' in commands_executed, "Should have added coffee"
    assert 'start_brewing' in commands_executed, "Should have started brewing"

if __name__ == "__main__":
    pytest.main(["-v", __file__])