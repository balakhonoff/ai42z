import pytest
import json
import sys
import os

# Add the src directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))

from examples.maze_solver.main import initialize_processor

def is_goal_achieved(history) -> bool:
    """Check if maze has been solved"""
    try:
        # Look for a successful move that reached the exit
        for entry in history:
            if (entry.command_name == 'move' and 
                entry.result.get('message') == 'Reached the exit!' and
                entry.result.get('status') == 'success'):
                return True
        return False
    except Exception:
        return False

@pytest.mark.asyncio
async def test_maze_solving():
    """Test maze solving capabilities"""
    processor = await initialize_processor()
    
    max_steps = 100
    success = False
    
    print("\n=== Starting Maze Solver Test ===")
    
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
            print(f"\n=== Maze Solved in {step} steps! ===")
            break
    
    assert success, f"Should solve the maze in less than {max_steps}"
    
    # Verify efficient exploration
    # moves = [e for e in processor.execution_history if e.command_name == 'move']
    # assert len(moves) < 40, "Should solve maze in reasonable number of moves" 