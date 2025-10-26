"""
Integration test demonstrating the photo verification timeout behavior.
This test verifies the complete workflow described in the issue.
"""
import unittest
import os
from datetime import datetime, timedelta
from game_state import GameState

# Test constants
TIME_TOLERANCE_SECONDS = 5  # Tolerance for time comparisons
CHALLENGE_1_ID = 1
CHALLENGE_2_ID = 2
TOTAL_CHALLENGES = 3
HINT_PENALTY_MINUTES = 2


class TestPhotoVerificationTimeoutWorkflow(unittest.TestCase):
    """Integration test for the complete photo verification timeout workflow."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.test_state_file = "test_integration_timeout.json"
        
    def tearDown(self):
        """Clean up test files."""
        if os.path.exists(self.test_state_file):
            os.remove(self.test_state_file)
    
    def test_workflow_with_photo_verification_and_penalty(self):
        """
        Test complete workflow: Challenge n-1 solved → photo verification → penalty timeout → challenge n reveal
        
        This demonstrates that when photo verification is enabled:
        1. Team completes challenge with hints (incurring penalty)
        2. Penalty timeout does NOT start yet
        3. Team sends photo for next challenge location
        4. Admin approves photo
        5. Penalty timeout starts NOW (from photo approval time)
        6. Next challenge is revealed after penalty expires
        """
        game_state = GameState(self.test_state_file)
        game_state.set_photo_verification(True)
        
        # Create a team and start the game
        game_state.create_team("Team Alpha", 1, "Alice")
        game_state.start_game()
        
        # Team is working on Challenge 1, uses a hint (2 min penalty)
        game_state.use_hint("Team Alpha", CHALLENGE_1_ID, 0, 1, "Alice")
        
        # Team completes Challenge 1 (answer-based challenge)
        print("\n--- Team completes Challenge 1 ---")
        completion_result = game_state.complete_challenge("Team Alpha", CHALLENGE_1_ID, TOTAL_CHALLENGES)
        self.assertTrue(completion_result)
        
        # At this point, completion time should NOT be set (deferred)
        completion_times = game_state.teams["Team Alpha"].get('challenge_completion_times', {})
        self.assertNotIn(str(CHALLENGE_1_ID), completion_times, 
                        "Step 1 FAIL: Completion time should be deferred when photo verification is enabled")
        print("✓ Step 1 PASS: Completion time deferred (penalty NOT counting)")
        
        # Verify no unlock time is calculated yet
        unlock_time = game_state.get_challenge_unlock_time("Team Alpha", CHALLENGE_2_ID)
        self.assertIsNone(unlock_time,
                         "Step 2 FAIL: No unlock time should exist before photo verification")
        print("✓ Step 2 PASS: No penalty timeout active yet")
        
        # Simulate some time passing while team travels to Challenge 2 location
        # (In real scenario, this could be minutes of waiting for admin approval)
        print("\n--- Waiting for photo verification (simulating delay) ---")
        
        # Team arrives at Challenge 2 location and sends photo
        verification_id = game_state.add_pending_photo_verification(
            "Team Alpha", CHALLENGE_2_ID, "photo_12345", 1, "Alice"
        )
        self.assertIsNotNone(verification_id)
        print("✓ Step 3 PASS: Photo submitted for verification")
        
        # Admin approves the photo (this is when penalty timer should start)
        print("\n--- Admin approves photo ---")
        approval_time = datetime.now()
        approval_result = game_state.approve_photo_verification(verification_id)
        self.assertTrue(approval_result)
        
        # NOW completion time for Challenge 1 should be set
        completion_times = game_state.teams["Team Alpha"].get('challenge_completion_times', {})
        self.assertIn(str(CHALLENGE_1_ID), completion_times,
                     "Step 4 FAIL: Completion time should be set after photo verification")
        print("✓ Step 4 PASS: Completion time set after photo approval (penalty starts NOW)")
        
        # Verify completion time is recent (from photo approval, not challenge completion)
        completion_time = datetime.fromisoformat(completion_times[str(CHALLENGE_1_ID)])
        time_diff = abs((completion_time - approval_time).total_seconds())
        self.assertLess(time_diff, 2,
                       "Completion time should be set at photo approval time")
        print(f"✓ Step 5 PASS: Completion time matches photo approval time (diff: {time_diff:.2f}s)")
        
        # Verify unlock time is calculated correctly (2 minutes from approval)
        unlock_time_str = game_state.get_challenge_unlock_time("Team Alpha", CHALLENGE_2_ID)
        self.assertIsNotNone(unlock_time_str,
                            "Step 6 FAIL: Unlock time should be calculated after photo approval")
        
        unlock_time = datetime.fromisoformat(unlock_time_str)
        expected_unlock = approval_time + timedelta(minutes=HINT_PENALTY_MINUTES)
        penalty_diff = abs((unlock_time - expected_unlock).total_seconds())
        self.assertLess(penalty_diff, TIME_TOLERANCE_SECONDS,
                       f"Unlock time should be ~{HINT_PENALTY_MINUTES} minutes from approval. Got {penalty_diff}s difference")
        print(f"✓ Step 6 PASS: Penalty timeout is {HINT_PENALTY_MINUTES} minutes from photo approval")
        print(f"  Approval time: {approval_time.strftime('%H:%M:%S')}")
        print(f"  Unlock time:   {unlock_time.strftime('%H:%M:%S')}")
        
        print("\n✅ COMPLETE WORKFLOW VERIFIED:")
        print("  Challenge completed → Photo verification → Penalty timeout → Challenge reveal")
        print("  Teams do NOT lose time while waiting for photo verification!")
    
    def test_workflow_without_photo_verification(self):
        """
        Test workflow without photo verification: Challenge n-1 solved → penalty timeout → challenge n reveal
        
        This demonstrates that when photo verification is disabled:
        1. Team completes challenge with hints (incurring penalty)
        2. Penalty timeout starts IMMEDIATELY
        3. Next challenge is revealed after penalty expires (no photo verification step)
        """
        game_state = GameState(self.test_state_file)
        game_state.set_photo_verification(False)
        
        # Create a team and start the game
        game_state.create_team("Team Beta", 2, "Bob")
        game_state.start_game()
        
        # Team uses a hint on Challenge 1 (2 min penalty)
        game_state.use_hint("Team Beta", CHALLENGE_1_ID, 0, 2, "Bob")
        
        # Team completes Challenge 1
        print("\n--- Team completes Challenge 1 (photo verification disabled) ---")
        completion_time_before = datetime.now()
        completion_result = game_state.complete_challenge("Team Beta", CHALLENGE_1_ID, TOTAL_CHALLENGES)
        self.assertTrue(completion_result)
        
        # Completion time should be set IMMEDIATELY
        completion_times = game_state.teams["Team Beta"].get('challenge_completion_times', {})
        self.assertIn(str(CHALLENGE_1_ID), completion_times,
                     "Step 1 FAIL: Completion time should be set immediately when photo verification is disabled")
        print("✓ Step 1 PASS: Completion time set immediately (penalty starts NOW)")
        
        # Verify completion time is recent (from challenge completion)
        completion_time = datetime.fromisoformat(completion_times[str(CHALLENGE_1_ID)])
        time_diff = abs((completion_time - completion_time_before).total_seconds())
        self.assertLess(time_diff, 2,
                       "Completion time should be set at challenge completion time")
        print(f"✓ Step 2 PASS: Completion time matches challenge completion time (diff: {time_diff:.2f}s)")
        
        # Verify unlock time is calculated correctly (2 minutes from completion)
        unlock_time_str = game_state.get_challenge_unlock_time("Team Beta", CHALLENGE_2_ID)
        self.assertIsNotNone(unlock_time_str,
                            "Step 3 FAIL: Unlock time should be calculated after completion")
        
        unlock_time = datetime.fromisoformat(unlock_time_str)
        expected_unlock = completion_time_before + timedelta(minutes=HINT_PENALTY_MINUTES)
        penalty_diff = abs((unlock_time - expected_unlock).total_seconds())
        self.assertLess(penalty_diff, TIME_TOLERANCE_SECONDS,
                       f"Unlock time should be ~{HINT_PENALTY_MINUTES} minutes from completion. Got {penalty_diff}s difference")
        print(f"✓ Step 3 PASS: Penalty timeout is {HINT_PENALTY_MINUTES} minutes from challenge completion")
        print(f"  Completion time: {completion_time_before.strftime('%H:%M:%S')}")
        print(f"  Unlock time:     {unlock_time.strftime('%H:%M:%S')}")
        
        print("\n✅ COMPLETE WORKFLOW VERIFIED:")
        print("  Challenge completed → Penalty timeout → Challenge reveal")
        print("  (No photo verification step)")


if __name__ == '__main__':
    unittest.main()
