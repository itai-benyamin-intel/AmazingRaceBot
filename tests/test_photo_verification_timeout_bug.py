"""
Test to reproduce the bug where next challenge is broadcast immediately after
photo verification approval, ignoring timeout penalties.
"""
import unittest
import os
from datetime import datetime, timedelta
from game_state import GameState


class TestPhotoVerificationTimeoutBug(unittest.TestCase):
    """Test case to reproduce photo verification + timeout bug."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.test_state_file = "test_photo_timeout_bug.json"
        
    def tearDown(self):
        """Clean up test files."""
        if os.path.exists(self.test_state_file):
            os.remove(self.test_state_file)
    
    def test_timeout_should_prevent_next_challenge_broadcast_after_photo_verification(self):
        """
        Test that demonstrates the bug:
        1. Team completes Challenge 1 with a hint (2-minute penalty)
        2. Completion time deferred (photo verification enabled)
        3. Team submits photo for Challenge 2 location
        4. Admin approves photo for Challenge 2 location
        5. Challenge 2 is revealed (correct)
        6. Team completes Challenge 2
        7. BUG: Should NOT broadcast Challenge 3 until timeout expires
        
        This test verifies the game_state behavior is correct.
        The bug is likely in bot.py where broadcast_current_challenge is called.
        """
        game_state = GameState(self.test_state_file)
        game_state.set_photo_verification(True)
        
        # Create a team
        game_state.create_team("Test Team", 1, "Test User")
        
        # Simulate Challenge 1 completion with a hint
        game_state.use_hint("Test Team", 1, 0, 1, "Test User")
        game_state.complete_challenge("Test Team", 1, 3)  # 3 total challenges
        
        # At this point:
        # - Challenge 1 is complete but completion time is NOT set (deferred)
        # - Team is on Challenge 2
        # - No timeout should be active yet
        
        team = game_state.teams["Test Team"]
        self.assertEqual(team['current_challenge_index'], 1)  # On challenge 2 (index 1)
        self.assertIn(1, team['completed_challenges'])
        
        completion_times = team.get('challenge_completion_times', {})
        self.assertNotIn('1', completion_times, "Completion time should be deferred")
        
        # No timeout yet (completion time not set)
        unlock_time = game_state.get_challenge_unlock_time("Test Team", 2)
        self.assertIsNone(unlock_time, "No timeout should be active before photo verification")
        
        # Team submits photo for Challenge 2 location
        verification_id = game_state.add_pending_photo_verification(
            "Test Team", 2, "photo_id", 1, "Test User"
        )
        
        # Admin approves photo
        approval_time_before = datetime.now()
        result = game_state.approve_photo_verification(verification_id)
        approval_time_after = datetime.now()
        
        self.assertTrue(result, "Photo verification should be approved")
        
        # After photo approval:
        # - Completion time for Challenge 1 should be set NOW
        # - Timeout should be active for Challenge 2
        
        completion_times = team.get('challenge_completion_times', {})
        self.assertIn('1', completion_times, "Completion time should be set after photo approval")
        
        completion_time = datetime.fromisoformat(completion_times['1'])
        self.assertGreaterEqual(completion_time, approval_time_before)
        self.assertLessEqual(completion_time, approval_time_after)
        
        # Now check if timeout is active for Challenge 2
        unlock_time_str = game_state.get_challenge_unlock_time("Test Team", 2)
        self.assertIsNotNone(unlock_time_str, "Timeout should be active after photo approval")
        
        unlock_time = datetime.fromisoformat(unlock_time_str)
        expected_unlock = completion_time + timedelta(minutes=2)
        
        # Allow 5 second tolerance
        time_diff = abs((unlock_time - expected_unlock).total_seconds())
        self.assertLess(time_diff, 5, f"Unlock time should be 2 minutes from photo approval")
        
        # The bug would be if bot.py broadcasts Challenge 2 immediately after photo approval
        # without checking if unlock_time is in the future
        # 
        # In bot.py, after approve_photo_verification, it calls:
        #   await self.broadcast_current_challenge(context, team_name)
        # 
        # This is correct - it reveals Challenge 2.
        # But the team should NOT be able to proceed to Challenge 3 until the timeout expires.
        
        # Let's verify that Challenge 2 is indeed the current challenge
        self.assertEqual(team['current_challenge_index'], 1)  # Still on Challenge 2
        
        # Now simulate Challenge 2 completion
        game_state.complete_challenge("Test Team", 2, 3)
        
        # After Challenge 2 completion:
        # - Team should move to Challenge 3
        # - But Challenge 3 should be locked until the timeout from Challenge 1 expires
        
        self.assertEqual(team['current_challenge_index'], 2)  # Now on Challenge 3
        self.assertIn(2, team['completed_challenges'])
        
        # Check if Challenge 3 has a timeout
        # This should check the timeout from Challenge 1 (which applies to Challenge 2)
        unlock_time_str_ch3 = game_state.get_challenge_unlock_time("Test Team", 3)
        
        # Here's the question: should Challenge 3 have a timeout?
        # If Challenge 2 was completed during the timeout period from Challenge 1,
        # then the timeout still applies.
        
        # Actually, I think I misunderstood the timeout logic.
        # Let me re-examine...
        
        # The timeout is calculated based on the PREVIOUS challenge's completion time.
        # So:
        # - Challenge 2 unlock time = Challenge 1 completion time + penalty
        # - Challenge 3 unlock time = Challenge 2 completion time + penalty (if any)
        
        # If Challenge 2 has no hints, then Challenge 3 should have no timeout.
        # Let's verify this:
        
        # Challenge 2 completion time should be set immediately (no photo verification for next challenge)
        completion_times = team.get('challenge_completion_times', {})
        self.assertIn('2', completion_times, "Challenge 2 completion time should be set")
        
        # Challenge 3 timeout should be based on Challenge 2 completion time
        # Since we didn't use hints for Challenge 2, there should be no timeout
        unlock_time_ch3 = game_state.get_challenge_unlock_time("Test Team", 3)
        
        # But wait, game_state.get_challenge_unlock_time takes a previous_challenge parameter
        # Let me check what it does with it...
        
        print(f"\nDebug info:")
        print(f"Challenge 1 completion time: {completion_times.get('1')}")
        print(f"Challenge 2 completion time: {completion_times.get('2')}")
        print(f"Challenge 2 unlock time: {unlock_time_str}")
        print(f"Challenge 3 unlock time: {unlock_time_ch3}")


if __name__ == '__main__':
    unittest.main()
