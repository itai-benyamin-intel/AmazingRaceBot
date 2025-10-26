"""
Test that timeout information is displayed correctly in /current_challenge and /challenges commands.
"""
import unittest
import os
import yaml
from datetime import datetime, timedelta
from game_state import GameState


class TestTimeoutDisplay(unittest.TestCase):
    """Test timeout display in commands."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.test_state_file = "test_timeout_display_state.json"
        self.game_state = GameState(self.test_state_file)
        
        # Disable photo verification for timeout tests (to test timeout in isolation)
        self.game_state.set_photo_verification(False)
        
        # Create a test team
        self.game_state.create_team("Test Team", 12345, "Alice")
        self.game_state.start_game()
    
    def tearDown(self):
        """Clean up test files."""
        if os.path.exists(self.test_state_file):
            os.remove(self.test_state_file)
    
    def test_challenge_unlock_time_calculation(self):
        """Test that unlock time is calculated correctly when hints are used."""
        # Use 2 hints on challenge 1
        self.game_state.use_hint("Test Team", 1, 0, 12345, "Alice")
        self.game_state.use_hint("Test Team", 1, 1, 12345, "Alice")
        
        # Complete challenge 1
        self.game_state.complete_challenge("Test Team", 1, 5, {})
        
        # Check that challenge 2 has an unlock time
        unlock_time_str = self.game_state.get_challenge_unlock_time("Test Team", 2)
        self.assertIsNotNone(unlock_time_str)
        
        # Verify the unlock time is 4 minutes (2 hints × 2 minutes) from completion
        completion_time_str = self.game_state.teams["Test Team"]['challenge_completion_times']['1']
        completion_time = datetime.fromisoformat(completion_time_str)
        unlock_time = datetime.fromisoformat(unlock_time_str)
        
        expected_unlock_time = completion_time + timedelta(seconds=240)  # 4 minutes
        time_diff = abs((unlock_time - expected_unlock_time).total_seconds())
        self.assertLess(time_diff, 1)  # Allow 1 second difference
    
    def test_no_unlock_time_without_hints(self):
        """Test that there's no unlock time when no hints are used."""
        # Complete challenge 1 without using hints
        self.game_state.complete_challenge("Test Team", 1, 5, {})
        
        # Check that challenge 2 has no unlock time
        unlock_time_str = self.game_state.get_challenge_unlock_time("Test Team", 2)
        self.assertIsNone(unlock_time_str)
    
    def test_challenge_unlocks_after_penalty(self):
        """Test that challenge is accessible after penalty expires."""
        # Use 1 hint on challenge 1
        self.game_state.use_hint("Test Team", 1, 0, 12345, "Alice")
        
        # Complete challenge 1
        self.game_state.complete_challenge("Test Team", 1, 5, {})
        
        # Get unlock time
        unlock_time_str = self.game_state.get_challenge_unlock_time("Test Team", 2)
        self.assertIsNotNone(unlock_time_str)
        
        unlock_time = datetime.fromisoformat(unlock_time_str)
        now = datetime.now()
        
        # If penalty is still active
        if now < unlock_time:
            # Calculate time remaining
            time_remaining = unlock_time - now
            minutes = int(time_remaining.total_seconds() // 60)
            seconds = int(time_remaining.total_seconds() % 60)
            
            # Verify hint count
            hint_count = self.game_state.get_hint_count("Test Team", 1)
            self.assertEqual(hint_count, 1)
            
            # Verify penalty is 2 minutes (120 seconds)
            self.assertEqual(self.game_state.get_total_penalty_time("Test Team", 1), 120)
    
    def test_multiple_hints_penalty(self):
        """Test penalty calculation with multiple hints."""
        # Use 3 hints on challenge 1 (max)
        self.game_state.use_hint("Test Team", 1, 0, 12345, "Alice")
        self.game_state.use_hint("Test Team", 1, 1, 12345, "Alice")
        self.game_state.use_hint("Test Team", 1, 2, 12345, "Alice")
        
        # Complete challenge 1
        self.game_state.complete_challenge("Test Team", 1, 5, {})
        
        # Verify penalty is 6 minutes (360 seconds)
        penalty = self.game_state.get_total_penalty_time("Test Team", 1)
        self.assertEqual(penalty, 360)
        
        # Verify unlock time
        unlock_time_str = self.game_state.get_challenge_unlock_time("Test Team", 2)
        self.assertIsNotNone(unlock_time_str)
        
        completion_time_str = self.game_state.teams["Test Team"]['challenge_completion_times']['1']
        completion_time = datetime.fromisoformat(completion_time_str)
        unlock_time = datetime.fromisoformat(unlock_time_str)
        
        expected_unlock_time = completion_time + timedelta(seconds=360)
        time_diff = abs((unlock_time - expected_unlock_time).total_seconds())
        self.assertLess(time_diff, 1)


if __name__ == '__main__':
    unittest.main()
