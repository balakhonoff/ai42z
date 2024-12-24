import pytest
import sys
import os

# Add the src directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

# Import the test functions from a different module name to avoid pytest discovering them
from examples.calculator.tests.test_calculator import test_calculator_scenario as _calculator_test
from examples.coffee_maker.tests.test_coffee_maker import test_coffee_scenario_gpt4 as _coffee_test

@pytest.mark.asyncio
async def test_basic_examples():
    """Run basic examples (calculator and coffee maker) to verify core functionality"""
    print("\n=== Testing Calculator Example ===")
    await _calculator_test()
    
    print("\n=== Testing Coffee Maker Example ===")
    await _coffee_test()
    
    print("\n=== All Basic Examples Passed ===")

if __name__ == "__main__":
    pytest.main(["-v", __file__]) 