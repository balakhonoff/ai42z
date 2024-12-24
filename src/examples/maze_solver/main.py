from typing import Dict, Any
import os
import sys
from dataclasses import dataclass
from enum import Enum

# Add the src directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from core.llm_processor import LLMProcessor

class CellType(Enum):
    EMPTY = "."
    WALL = "#"
    EXIT = "X"

@dataclass
class MazeState:
    position: tuple[int, int]
    visited: set[tuple[int, int]]

class MazeEnvironment:
    def __init__(self, maze_file: str, start_pos: tuple[int, int] = (1, 1)):
        self.maze = self._load_maze(maze_file)
        self.state = MazeState(start_pos, {start_pos})
        self.height = len(self.maze)
        self.width = len(self.maze[0])
        self.exit_pos = self._find_exit()

    def _load_maze(self, maze_file: str) -> list[list[str]]:
        """Load maze from file"""
        with open(maze_file, 'r') as f:
            return [list(line.strip()) for line in f.readlines()]

    def _find_exit(self) -> tuple[int, int]:
        """Find exit position in maze"""
        for y in range(self.height):
            for x in range(self.width):
                if self.maze[y][x] == 'X':
                    return (x, y)
        raise ValueError("No exit found in maze")

    def get_adjacent_cells(self) -> Dict[str, str]:
        """Return the content of adjacent cells"""
        x, y = self.state.position
        adjacent = {}
        for direction, (dx, dy) in {
            "north": (0, -1), "south": (0, 1),
            "east": (1, 0), "west": (-1, 0)
        }.items():
            new_x, new_y = x + dx, y + dy
            if 0 <= new_x < self.width and 0 <= new_y < self.height:
                adjacent[direction] = self.maze[new_y][new_x]
        return adjacent

async def initialize_processor():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    config_dir = os.path.join(current_dir, 'config')
    maze_file = os.path.join(config_dir, 'maze.txt')
    
    env = MazeEnvironment(maze_file)
    
    processor = LLMProcessor(
        os.path.join(config_dir, 'functions.json'),
        os.path.join(config_dir, 'goal.yaml'),
        model_type="openai",
        model_name="gpt-4o-mini",
        ui_visibility=True,
        history_size=10,
        summary_interval=5,
        summary_window=30
    )
    
    async def look_around(params: Dict[str, Any]) -> Dict[str, Any]:
        cells = env.get_adjacent_cells()
        return {
            "status": "success",
            "message": "Observed adjacent cells",
            "cells": cells
        }

    async def move(params: Dict[str, Any]) -> Dict[str, Any]:
        direction = params['direction']
        directions = {"north": (0, -1), "south": (0, 1), 
                     "east": (1, 0), "west": (-1, 0)}
        dx, dy = directions[direction]
        x, y = env.state.position
        new_x, new_y = x + dx, y + dy
        
        # Check if move is valid
        if not (0 <= new_x < env.width and 0 <= new_y < env.height):
            return {"status": "error", "message": "Cannot move outside maze"}
            
        if env.maze[new_y][new_x] == "#":
            return {"status": "error", "message": "Cannot move into wall"}
            
        # Make the move
        env.state.position = (new_x, new_y)
        env.state.visited.add((new_x, new_y))
        
        # Check if reached exit
        if env.maze[new_y][new_x] == 'X':
            return {
                "status": "success",
                "message": "Reached the exit!",
                "position": env.state.position
            }
        
        return {
            "status": "success",
            "message": f"Moved {direction}",
            "position": env.state.position
        }

    async def check_status(params: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "status": "success",
            "position": env.state.position,
            "visited_count": len(env.state.visited),
            "exit_position": env.exit_pos
        }

    processor.register_function('look_around', look_around)
    processor.register_function('move', move)
    processor.register_function('check_status', check_status)
    
    return processor

def is_goal_achieved(history) -> bool:
    """Check if maze solving goal is achieved based on command history"""
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