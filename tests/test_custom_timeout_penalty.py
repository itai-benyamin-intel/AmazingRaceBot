"""
Unit tests for custom timeout penalty feature.
"""
import unittest
import os
from datetime import datetime, timedelta
from game_state import GameState

# Timing tolerance for unlock time tests (in seconds)
TIMING_TOLERANCE_SECONDS = 1


class TestCustomTimeoutPenalty(unittest.TestCase):
    """Test cases for custom timeout penalty feature."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.test_state_file = "test_custom_penalty_state.json"
        self.game_state = GameState(self.test_state_file)
        
        # Disable photo verification for these tests
        self.game_state.set_photo_verification(False)
        
        # Create a test team
        self.game_state.create_team("Test Team", 12345, "Alice")
        self.game_state.join_team("Test Team", 67890, "Bob")
    
    def tearDown(self):
        """Clean up test files."""
        if os.path.exists(self.test_state_file):
            os.remove(self.test_state_file)
    
    def test_default_penalty_without_config(self):
        """Test that default 2-minute penalty is used when no custom config provided."""
        # Use 1 hint on challenge 1
        self.game_state.use_hint("Test Team", 1, 0, 12345, "Alice")
        
        # Get penalty time without providing challenge config
        penalty_seconds = self.game_state.get_total_penalty_time("Test Team", 1)
        
        # Default should be 2 minutes = 120 seconds
        self.assertEqual(penalty_seconds, 120)
    
    def test_default_penalty_with_empty_config(self):
        """Test that default 2-minute penalty is used when challenge config has no timeout_penalty_minutes."""
        # Use 1 hint on challenge 1
        self.game_state.use_hint("Test Team", 1, 0, 12345, "Alice")
        
        # Get penalty time with empty challenge config
        challenge = {'id': 1, 'name': 'Test Challenge'}
        penalty_seconds = self.game_state.get_total_penalty_time("Test Team", 1, challenge)
        
        # Default should be 2 minutes = 120 seconds
        self.assertEqual(penalty_seconds, 120)
    
    def test_custom_penalty_3_minutes(self):
        """Test custom 3-minute penalty per hint."""
        # Use 1 hint on challenge 1
        self.game_state.use_hint("Test Team", 1, 0, 12345, "Alice")
        
        # Get penalty time with custom 3-minute penalty
        challenge = {'id': 1, 'name': 'Test Challenge', 'timeout_penalty_minutes': 3}
        penalty_seconds = self.game_state.get_total_penalty_time("Test Team", 1, challenge)
        
        # Should be 3 minutes = 180 seconds
        self.assertEqual(penalty_seconds, 180)
    
    def test_custom_penalty_5_minutes_multiple_hints(self):
        """Test custom 5-minute penalty with multiple hints."""
        # Use 3 hints on challenge 1
        self.game_state.use_hint("Test Team", 1, 0, 12345, "Alice")
        self.game_state.use_hint("Test Team", 1, 1, 67890, "Bob")
        self.game_state.use_hint("Test Team", 1, 2, 12345, "Alice")
        
        # Get penalty time with custom 5-minute penalty
        challenge = {'id': 1, 'name': 'Test Challenge', 'timeout_penalty_minutes': 5}
        penalty_seconds = self.game_state.get_total_penalty_time("Test Team", 1, challenge)
        
        # Should be 3 hints * 5 minutes = 15 minutes = 900 seconds
        self.assertEqual(penalty_seconds, 900)
    
    def test_custom_penalty_1_minute(self):
        """Test custom 1-minute penalty (more lenient than default)."""
        # Use 2 hints on challenge 1
        self.game_state.use_hint("Test Team", 1, 0, 12345, "Alice")
        self.game_state.use_hint("Test Team", 1, 1, 67890, "Bob")
        
        # Get penalty time with custom 1-minute penalty
        challenge = {'id': 1, 'name': 'Test Challenge', 'timeout_penalty_minutes': 1}
        penalty_seconds = self.game_state.get_total_penalty_time("Test Team", 1, challenge)
        
        # Should be 2 hints * 1 minute = 2 minutes = 120 seconds
        self.assertEqual(penalty_seconds, 120)
    
    def test_unlock_time_with_custom_penalty(self):
        """Test that unlock time is calculated correctly with custom penalty."""
        # Use 2 hints on challenge 1
        self.game_state.use_hint("Test Team", 1, 0, 12345, "Alice")
        self.game_state.use_hint("Test Team", 1, 1, 67890, "Bob")
        
        # Complete challenge 1
        self.game_state.complete_challenge("Test Team", 1, 5, {})
        
        # Custom 3-minute penalty per hint
        challenge = {'id': 1, 'name': 'Test Challenge', 'timeout_penalty_minutes': 3}
        
        # Challenge 2 should have an unlock time (6 minutes from completion)
        unlock_time_str = self.game_state.get_challenge_unlock_time("Test Team", 2, challenge)
        self.assertIsNotNone(unlock_time_str)
        
        # Verify the unlock time is 6 minutes (360 seconds) after completion
        completion_time_str = self.game_state.teams["Test Team"]['challenge_completion_times']['1']
        completion_time = datetime.fromisoformat(completion_time_str)
        unlock_time = datetime.fromisoformat(unlock_time_str)
        
        expected_unlock_time = completion_time + timedelta(seconds=360)
        # Use module constant for timing tolerance
        self.assertLess(abs((unlock_time - expected_unlock_time).total_seconds()), TIMING_TOLERANCE_SECONDS)
    
    def test_get_penalty_minutes_per_hint_default(self):
        """Test getting penalty minutes per hint with default value."""
        penalty_minutes = self.game_state.get_penalty_minutes_per_hint()
        self.assertEqual(penalty_minutes, 2)
    
    def test_get_penalty_minutes_per_hint_custom(self):
        """Test getting penalty minutes per hint with custom value."""
        challenge = {'id': 1, 'timeout_penalty_minutes': 4}
        penalty_minutes = self.game_state.get_penalty_minutes_per_hint(challenge)
        self.assertEqual(penalty_minutes, 4)
    
    def test_get_penalty_minutes_per_hint_empty_config(self):
        """Test getting penalty minutes per hint with empty config."""
        challenge = {'id': 1, 'name': 'Test'}
        penalty_minutes = self.game_state.get_penalty_minutes_per_hint(challenge)
        self.assertEqual(penalty_minutes, 2)


if __name__ == '__main__':
    unittest.main()
