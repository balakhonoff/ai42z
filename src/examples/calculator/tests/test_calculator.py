import pytest
import json
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))
from examples.calculator.main import initialize_processor

EXPECTED_RESULT = 14  # The expected result of (4 + 3) * 2

def is_goal_achieved(history) -> bool:
    """Check if calculation goal is achieved with correct result"""
    try:
        # Find submission and verify the result
        submit = next(entry for entry in history 
                     if entry.command_name == 'submit_result' 
                     and entry.result['status'] == 'success'
                     and entry.parameters['value'] == EXPECTED_RESULT)
        return True
    except StopIteration:
        return False

@pytest.mark.asyncio
async def test_calculator_scenario():
    """Test basic arithmetic operations using LLM"""
    processor = await initialize_processor()
    
    max_steps = 4  # Increased to allow for submission step
    success = False
    
    print("\n=== Starting Calculator Test ===")
    
    for step in range(max_steps):
        print(f"\n=== Step {step + 1} of {max_steps} ===")
        
        response = await processor.get_next_action()
        assert response is not None, "Should get valid response from LLM"
        
        print("\n=== Processed LLM Response ===")
        print(json.dumps(response, indent=2))
        
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
    
    assert success, "Should complete calculation process"
    
    # Verify the sequence of operations
    commands = [(e.command_name, e.result.get('value')) for e in processor.execution_history]
    assert len(commands) >= 2, "Should take at least 2 steps before submission"
    
    # Find the successful submission
    final_submission = next(e for e in processor.execution_history 
                          if e.command_name == 'submit_result' 
                          and e.result['status'] == 'success')
    assert final_submission.parameters['value'] == 14, "Should submit the correct result" 