"""Shared test fixtures for the WHOP backend tests."""

import sys
from pathlib import Path

import pytest

# Add backend to path so imports work
sys.path.insert(0, str(Path(__file__).parent.parent))

from data.starting_state import create_starting_state
from models.game_state import GameState


@pytest.fixture
def fresh_game() -> GameState:
    """A fresh game state with FNER starting positions."""
    return create_starting_state(game_id="test-game")
