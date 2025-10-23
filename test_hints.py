"""
Unit tests for the hints feature.
"""
import unittest
import os
from datetime import datetime, timedelta
from game_state import GameState


class TestHintsFeature(unittest.TestCase):
    """Test cases for the hints feature."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.test_state_file = "test_hints_game_state.json"
        self.game_state = GameState(self.test_state_file)
        
        # Create a test team
        self.game_state.create_team("Test Team", 12345, "Alice")
        self.game_state.join_team("Test Team", 67890, "Bob")
    
    def tearDown(self):
        """Clean up test files."""
        if os.path.exists(self.test_state_file):
            os.remove(self.test_state_file)
    
    def test_use_hint(self):
        """Test recording hint usage."""
        result = self.game_state.use_hint("Test Team", 1, 0, 12345, "Alice")
        self.assertTrue(result)
        
        # Verify hint was recorded
        used_hints = self.game_state.get_used_hints("Test Team", 1)
        self.assertEqual(len(used_hints), 1)
        self.assertEqual(used_hints[0]['hint_index'], 0)
        self.assertEqual(used_hints[0]['user_id'], 12345)
        self.assertEqual(used_hints[0]['user_name'], "Alice")
    
    def test_use_multiple_hints(self):
        """Test using multiple hints for the same challenge."""
        self.game_state.use_hint("Test Team", 1, 0, 12345, "Alice")
        self.game_state.use_hint("Test Team", 1, 1, 67890, "Bob")
        self.game_state.use_hint("Test Team", 1, 2, 12345, "Alice")
        
        used_hints = self.game_state.get_used_hints("Test Team", 1)
        self.assertEqual(len(used_hints), 3)
        
        # Verify hint indices
        hint_indices = [h['hint_index'] for h in used_hints]
        self.assertEqual(hint_indices, [0, 1, 2])
    
    def test_get_hint_count(self):
        """Test getting hint count for a challenge."""
        # No hints used initially
        self.assertEqual(self.game_state.get_hint_count("Test Team", 1), 0)
        
        # Use some hints
        self.game_state.use_hint("Test Team", 1, 0, 12345, "Alice")
        self.assertEqual(self.game_state.get_hint_count("Test Team", 1), 1)
        
        self.game_state.use_hint("Test Team", 1, 1, 67890, "Bob")
        self.assertEqual(self.game_state.get_hint_count("Test Team", 1), 2)
    
    def test_get_total_penalty_time(self):
        """Test calculating total penalty time."""
        # No penalty initially
        self.assertEqual(self.game_state.get_total_penalty_time("Test Team", 1), 0)
        
        # 1 hint = 2 minutes = 120 seconds
        self.game_state.use_hint("Test Team", 1, 0, 12345, "Alice")
        self.assertEqual(self.game_state.get_total_penalty_time("Test Team", 1), 120)
        
        # 2 hints = 4 minutes = 240 seconds
        self.game_state.use_hint("Test Team", 1, 1, 67890, "Bob")
        self.assertEqual(self.game_state.get_total_penalty_time("Test Team", 1), 240)
        
        # 3 hints = 6 minutes = 360 seconds
        self.game_state.use_hint("Test Team", 1, 2, 12345, "Alice")
        self.assertEqual(self.game_state.get_total_penalty_time("Test Team", 1), 360)
    
    def test_set_challenge_completion_time(self):
        """Test setting challenge completion time."""
        self.game_state.set_challenge_completion_time("Test Team", 1)
        
        # Verify completion time was recorded
        completion_times = self.game_state.teams["Test Team"].get('challenge_completion_times', {})
        self.assertIn('1', completion_times)
        
        # Verify it's a valid ISO timestamp
        timestamp = completion_times['1']
        parsed_time = datetime.fromisoformat(timestamp)
        self.assertIsInstance(parsed_time, datetime)
    
    def test_get_challenge_unlock_time_no_penalty(self):
        """Test getting unlock time when no hints were used."""
        # Complete challenge 1 without using hints
        self.game_state.complete_challenge("Test Team", 1, 5, {})
        
        # Challenge 2 should unlock immediately (no penalty)
        unlock_time = self.game_state.get_challenge_unlock_time("Test Team", 2)
        self.assertIsNone(unlock_time)
    
    def test_get_challenge_unlock_time_with_penalty(self):
        """Test getting unlock time when hints were used."""
        # Use 2 hints on challenge 1
        self.game_state.use_hint("Test Team", 1, 0, 12345, "Alice")
        self.game_state.use_hint("Test Team", 1, 1, 67890, "Bob")
        
        # Complete challenge 1
        self.game_state.complete_challenge("Test Team", 1, 5, {})
        
        # Challenge 2 should have an unlock time (4 minutes from completion)
        unlock_time_str = self.game_state.get_challenge_unlock_time("Test Team", 2)
        self.assertIsNotNone(unlock_time_str)
        
        # Verify the unlock time is 4 minutes (240 seconds) after completion
        completion_time_str = self.game_state.teams["Test Team"]['challenge_completion_times']['1']
        completion_time = datetime.fromisoformat(completion_time_str)
        unlock_time = datetime.fromisoformat(unlock_time_str)
        
        expected_unlock_time = completion_time + timedelta(seconds=240)
        # Allow 1 second difference due to timing
        self.assertLess(abs((unlock_time - expected_unlock_time).total_seconds()), 1)
    
    def test_hints_for_different_challenges(self):
        """Test that hints are tracked separately for each challenge."""
        # Use hints on challenge 1
        self.game_state.use_hint("Test Team", 1, 0, 12345, "Alice")
        self.game_state.use_hint("Test Team", 1, 1, 67890, "Bob")
        
        # Complete challenge 1 and move to challenge 2
        self.game_state.complete_challenge("Test Team", 1, 5, {})
        
        # Use hints on challenge 2
        self.game_state.use_hint("Test Team", 2, 0, 12345, "Alice")
        
        # Verify separate tracking
        self.assertEqual(self.game_state.get_hint_count("Test Team", 1), 2)
        self.assertEqual(self.game_state.get_hint_count("Test Team", 2), 1)
    
    def test_hint_usage_persistence(self):
        """Test that hint usage is persisted across save/load."""
        # Use some hints
        self.game_state.use_hint("Test Team", 1, 0, 12345, "Alice")
        self.game_state.use_hint("Test Team", 1, 1, 67890, "Bob")
        
        # Save state
        self.game_state.save_state()
        
        # Create a new game state instance
        new_game_state = GameState(self.test_state_file)
        
        # Verify hints were persisted
        used_hints = new_game_state.get_used_hints("Test Team", 1)
        self.assertEqual(len(used_hints), 2)
        self.assertEqual(new_game_state.get_hint_count("Test Team", 1), 2)
    
    def test_reset_game_clears_hints(self):
        """Test that resetting the game clears hint usage."""
        # Use some hints
        self.game_state.use_hint("Test Team", 1, 0, 12345, "Alice")
        
        # Reset game
        self.game_state.reset_game()
        
        # Verify hints were cleared
        self.assertEqual(len(self.game_state.hint_usage), 0)
    
    def test_use_hint_nonexistent_team(self):
        """Test that using hint for nonexistent team fails."""
        result = self.game_state.use_hint("Nonexistent Team", 1, 0, 12345, "Alice")
        self.assertFalse(result)
    
    def test_get_used_hints_nonexistent_team(self):
        """Test getting hints for nonexistent team returns empty list."""
        hints = self.game_state.get_used_hints("Nonexistent Team", 1)
        self.assertEqual(hints, [])
    
    def test_get_hint_count_nonexistent_team(self):
        """Test getting hint count for nonexistent team returns 0."""
        count = self.game_state.get_hint_count("Nonexistent Team", 1)
        self.assertEqual(count, 0)


if __name__ == '__main__':
    unittest.main()
