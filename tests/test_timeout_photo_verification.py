"""
Unit tests for timeout behavior with photo verification.
"""
import unittest
import os
from datetime import datetime, timedelta
from game_state import GameState


class TestTimeoutWithPhotoVerification(unittest.TestCase):
    """Test cases for timeout behavior when photo verification is enabled."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.test_state_file = "test_timeout_photo_state.json"
        
    def tearDown(self):
        """Clean up test files."""
        if os.path.exists(self.test_state_file):
            os.remove(self.test_state_file)
    
    def test_completion_time_deferred_with_photo_verification_enabled(self):
        """Test that completion time is deferred when photo verification is enabled."""
        game_state = GameState(self.test_state_file)
        game_state.set_photo_verification(True)
        
        # Create a team
        game_state.create_team("Test Team", 1, "Test User")
        
        # Record hint usage for challenge 1
        game_state.use_hint("Test Team", 1, 0, 1, "Test User")
        
        # Complete challenge 1
        result = game_state.complete_challenge("Test Team", 1, 3)
        self.assertTrue(result)
        
        # Completion time should NOT be set yet (deferred until photo verification)
        completion_times = game_state.teams["Test Team"].get('challenge_completion_times', {})
        self.assertNotIn('1', completion_times, 
                        "Completion time should be deferred when photo verification is enabled")
        
        # Verify challenge is marked as completed
        self.assertIn(1, game_state.teams["Test Team"]['completed_challenges'])
        
        # Verify team moved to next challenge
        self.assertEqual(game_state.teams["Test Team"]['current_challenge_index'], 1)
    
    def test_completion_time_set_on_photo_verification_approval(self):
        """Test that completion time is set when photo verification is approved."""
        game_state = GameState(self.test_state_file)
        game_state.set_photo_verification(True)
        
        # Create a team
        game_state.create_team("Test Team", 1, "Test User")
        
        # Record hint usage for challenge 1
        game_state.use_hint("Test Team", 1, 0, 1, "Test User")
        
        # Complete challenge 1 (completion time should be deferred)
        game_state.complete_challenge("Test Team", 1, 3)
        
        # Add and approve photo verification for challenge 2
        verification_id = game_state.add_pending_photo_verification(
            "Test Team", 2, "photo_id", 1, "Test User"
        )
        
        # Record time before approval
        time_before = datetime.now()
        
        # Approve photo verification
        result = game_state.approve_photo_verification(verification_id)
        self.assertTrue(result)
        
        # Now completion time for challenge 1 should be set
        completion_times = game_state.teams["Test Team"].get('challenge_completion_times', {})
        self.assertIn('1', completion_times, 
                     "Completion time should be set after photo verification is approved")
        
        # Verify completion time is recent (set during photo approval)
        completion_time = datetime.fromisoformat(completion_times['1'])
        self.assertGreaterEqual(completion_time, time_before)
        self.assertLessEqual(completion_time, datetime.now())
    
    def test_penalty_timeout_calculated_from_photo_approval_time(self):
        """Test that penalty timeout is calculated from photo approval time."""
        game_state = GameState(self.test_state_file)
        game_state.set_photo_verification(True)
        
        # Create a team
        game_state.create_team("Test Team", 1, "Test User")
        
        # Record hint usage for challenge 1 (2 minute penalty)
        game_state.use_hint("Test Team", 1, 0, 1, "Test User")
        
        # Complete challenge 1
        game_state.complete_challenge("Test Team", 1, 3)
        
        # At this point, no unlock time should be calculated yet
        unlock_time = game_state.get_challenge_unlock_time("Test Team", 2)
        self.assertIsNone(unlock_time, 
                         "Unlock time should be None before photo verification")
        
        # Add and approve photo verification for challenge 2
        verification_id = game_state.add_pending_photo_verification(
            "Test Team", 2, "photo_id", 1, "Test User"
        )
        
        # Record time before approval
        approval_time = datetime.now()
        
        # Approve photo verification
        game_state.approve_photo_verification(verification_id)
        
        # Now unlock time should be calculated
        unlock_time_str = game_state.get_challenge_unlock_time("Test Team", 2)
        self.assertIsNotNone(unlock_time_str, 
                            "Unlock time should be calculated after photo verification")
        
        # Verify unlock time is approximately 2 minutes from approval time
        unlock_time = datetime.fromisoformat(unlock_time_str)
        expected_unlock = approval_time + timedelta(minutes=2)
        
        # Allow 5 second tolerance
        time_diff = abs((unlock_time - expected_unlock).total_seconds())
        self.assertLess(time_diff, 5, 
                       f"Unlock time should be ~2 minutes from photo approval. Difference: {time_diff}s")
    
    def test_completion_time_immediate_when_photo_verification_disabled(self):
        """Test that completion time is set immediately when photo verification is disabled."""
        game_state = GameState(self.test_state_file)
        game_state.set_photo_verification(False)
        
        # Create a team
        game_state.create_team("Test Team", 1, "Test User")
        
        # Record hint usage
        game_state.use_hint("Test Team", 1, 0, 1, "Test User")
        
        # Record time before completion
        time_before = datetime.now()
        
        # Complete challenge 1
        result = game_state.complete_challenge("Test Team", 1, 3)
        self.assertTrue(result)
        
        # Completion time should be set immediately
        completion_times = game_state.teams["Test Team"].get('challenge_completion_times', {})
        self.assertIn('1', completion_times, 
                     "Completion time should be set immediately when photo verification is disabled")
        
        # Verify completion time is recent
        completion_time = datetime.fromisoformat(completion_times['1'])
        self.assertGreaterEqual(completion_time, time_before)
        self.assertLessEqual(completion_time, datetime.now())
    
    def test_last_challenge_completion_time_set_immediately(self):
        """Test that last challenge completion time is set immediately even with photo verification."""
        game_state = GameState(self.test_state_file)
        game_state.set_photo_verification(True)
        
        # Create a team
        game_state.create_team("Test Team", 1, "Test User")
        
        # Complete challenges 1 and 2 to get to challenge 3 (last one)
        game_state.complete_challenge("Test Team", 1, 3)
        game_state.complete_challenge("Test Team", 2, 3)
        
        # Record time before completing last challenge
        time_before = datetime.now()
        
        # Complete challenge 3 (last challenge)
        result = game_state.complete_challenge("Test Team", 3, 3)
        self.assertTrue(result)
        
        # Completion time should be set immediately for last challenge
        completion_times = game_state.teams["Test Team"].get('challenge_completion_times', {})
        self.assertIn('3', completion_times, 
                     "Completion time should be set immediately for last challenge")
        
        # Verify completion time is recent
        completion_time = datetime.fromisoformat(completion_times['3'])
        self.assertGreaterEqual(completion_time, time_before)
        self.assertLessEqual(completion_time, datetime.now())
    
    def test_no_duplicate_completion_time_set(self):
        """Test that completion time is not overwritten if already set."""
        game_state = GameState(self.test_state_file)
        game_state.set_photo_verification(False)
        
        # Create a team
        game_state.create_team("Test Team", 1, "Test User")
        
        # Complete challenge 1 (completion time set immediately because photo verification is off)
        game_state.complete_challenge("Test Team", 1, 3)
        
        # Get original completion time
        original_time = game_state.teams["Test Team"]['challenge_completion_times']['1']
        
        # Now enable photo verification and try to approve a photo for challenge 2
        game_state.set_photo_verification(True)
        verification_id = game_state.add_pending_photo_verification(
            "Test Team", 2, "photo_id", 1, "Test User"
        )
        
        # Approve photo verification (should not overwrite challenge 1 completion time)
        game_state.approve_photo_verification(verification_id)
        
        # Completion time for challenge 1 should remain unchanged
        current_time = game_state.teams["Test Team"]['challenge_completion_times']['1']
        self.assertEqual(original_time, current_time, 
                        "Completion time should not be overwritten if already set")


if __name__ == '__main__':
    unittest.main()
