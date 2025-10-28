"""
Test to verify that timeout penalties are enforced after photo verification approval.
"""
import unittest
import os
from datetime import datetime, timedelta
from game_state import GameState


class TestPhotoVerificationTimeoutEnforcement(unittest.TestCase):
    """Test case to verify timeout enforcement after photo verification approval."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.test_state_file = "test_photo_timeout_bug.json"
        
    def tearDown(self):
        """Clean up test files."""
        if os.path.exists(self.test_state_file):
            os.remove(self.test_state_file)
    
    def test_timeout_active_after_photo_verification_approval(self):
        """
        Test that timeout is calculated correctly after photo verification approval.
        
        Scenario:
        1. Team completes Challenge 1 with a hint (2-minute penalty)
        2. Completion time deferred (photo verification enabled)
        3. Team submits photo for Challenge 2 location
        4. Admin approves photo for Challenge 2 location
        5. Challenge 1 completion time is set at photo approval time
        6. Challenge 2 should have a 2-minute timeout from the approval time
        """
        game_state = GameState(self.test_state_file)
        game_state.set_photo_verification(True)
        
        # Create a team
        game_state.create_team("Test Team", 1, "Test User")
        
        # Simulate Challenge 1 completion with a hint
        game_state.use_hint("Test Team", 1, 0, 1, "Test User")
        game_state.complete_challenge("Test Team", 1, 3)  # 3 total challenges
        
        # Verify completion time is deferred
        team = game_state.teams["Test Team"]
        completion_times = team.get('challenge_completion_times', {})
        self.assertNotIn('1', completion_times, "Completion time should be deferred")
        
        # No timeout should be active yet
        unlock_time = game_state.get_challenge_unlock_time("Test Team", 2)
        self.assertIsNone(unlock_time, "No timeout should be active before photo verification")
        
        # Team submits photo for Challenge 2 location
        verification_id = game_state.add_pending_photo_verification(
            "Test Team", 2, "photo_id", 1, "Test User"
        )
        
        # Admin approves photo
        approval_time = datetime.now()
        result = game_state.approve_photo_verification(verification_id)
        self.assertTrue(result, "Photo verification should be approved")
        
        # After photo approval, Challenge 1 completion time should be set
        completion_times = team.get('challenge_completion_times', {})
        self.assertIn('1', completion_times, "Completion time should be set after photo approval")
        
        completion_time = datetime.fromisoformat(completion_times['1'])
        
        # Get previous challenge config for custom penalty support
        previous_challenge = {'id': 1}  # Simulating previous challenge config
        
        # Now check if timeout is active for Challenge 2
        unlock_time_str = game_state.get_challenge_unlock_time("Test Team", 2, previous_challenge)
        self.assertIsNotNone(unlock_time_str, "Timeout should be active after photo approval")
        
        unlock_time = datetime.fromisoformat(unlock_time_str)
        expected_unlock = completion_time + timedelta(minutes=2)
        
        # Verify unlock time is 2 minutes from completion time
        time_diff = abs((unlock_time - expected_unlock).total_seconds())
        self.assertLess(time_diff, 5, f"Unlock time should be 2 minutes from photo approval")
        
        # Verify timeout is in the future
        now = datetime.now()
        self.assertGreater(unlock_time, now, "Unlock time should be in the future")
    
    def test_no_timeout_when_no_hints_used(self):
        """
        Test that no timeout is applied when no hints were used.
        """
        game_state = GameState(self.test_state_file)
        game_state.set_photo_verification(True)
        
        # Create a team
        game_state.create_team("Test Team", 1, "Test User")
        
        # Complete Challenge 1 without hints
        game_state.complete_challenge("Test Team", 1, 3)
        
        # Team submits photo for Challenge 2 location
        verification_id = game_state.add_pending_photo_verification(
            "Test Team", 2, "photo_id", 1, "Test User"
        )
        
        # Admin approves photo
        game_state.approve_photo_verification(verification_id)
        
        # No timeout should be active for Challenge 2
        previous_challenge = {'id': 1}
        unlock_time = game_state.get_challenge_unlock_time("Test Team", 2, previous_challenge)
        self.assertIsNone(unlock_time, "No timeout should be active when no hints were used")
    
    def test_timeout_expires_before_photo_approval(self):
        """
        Test edge case where timeout would have expired before photo approval.
        
        This tests that if a team waits a long time before submitting the location photo,
        and the timeout would have already expired, there should be no timeout.
        """
        game_state = GameState(self.test_state_file)
        game_state.set_photo_verification(True)
        
        # Create a team
        game_state.create_team("Test Team", 1, "Test User")
        
        # Complete Challenge 1 with a hint
        game_state.use_hint("Test Team", 1, 0, 1, "Test User")
        game_state.complete_challenge("Test Team", 1, 3)
        
        # Manually set Challenge 1 completion time to 5 minutes ago
        # (simulating a team that waited a long time)
        team = game_state.teams["Test Team"]
        old_completion_time = datetime.now() - timedelta(minutes=5)
        if 'challenge_completion_times' not in team:
            team['challenge_completion_times'] = {}
        team['challenge_completion_times']['1'] = old_completion_time.isoformat()
        game_state.save_state()
        
        # Now check if timeout would be active
        previous_challenge = {'id': 1}
        unlock_time_str = game_state.get_challenge_unlock_time("Test Team", 2, previous_challenge)
        
        # Timeout should exist but should have already expired
        self.assertIsNotNone(unlock_time_str, "Timeout should exist")
        
        unlock_time = datetime.fromisoformat(unlock_time_str)
        now = datetime.now()
        
        # Timeout should be in the past (already expired)
        self.assertLess(unlock_time, now, "Timeout should have already expired")


if __name__ == '__main__':
    unittest.main()
