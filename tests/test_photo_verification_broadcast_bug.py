"""
Test to verify that photo verification requests are only sent to the relevant team,
not to all players.
"""
import unittest
import os
import yaml
from unittest.mock import AsyncMock, MagicMock
from bot import AmazingRaceBot


class TestPhotoVerificationBroadcastBug(unittest.IsolatedAsyncioTestCase):
    """Test that photo verification requests are not broadcast to wrong teams."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.test_config_file = "test_photo_verif_broadcast_config.yml"
        self.test_state_file = "test_photo_verif_broadcast_state.json"
        
        # Create test configuration
        self.config = {
            'telegram': {'bot_token': 'test_token'},
            'game': {
                'name': 'Test Game',
                'max_teams': 10,
                'max_team_size': 5,
                'challenges': [
                    {
                        'id': 1,
                        'name': 'Challenge 1',
                        'description': 'First challenge',
                        'location': 'Start',
                        'type': 'riddle',
                        'verification': {'method': 'answer', 'answer': 'test1'}
                    },
                    {
                        'id': 2,
                        'name': 'Challenge 2',
                        'description': 'Second challenge - requires photo verification',
                        'location': 'Location 2',
                        'type': 'riddle',
                        'verification': {'method': 'answer', 'answer': 'test2'},
                        'requires_photo_verification': True
                    }
                ]
            },
            'admin': 999999999
        }
        
    def tearDown(self):
        """Clean up test files."""
        for file in [self.test_config_file, self.test_state_file, "game_state.json"]:
            if os.path.exists(file):
                os.remove(file)
    
    async def test_photo_verification_request_only_to_relevant_team(self):
        """Test that photo verification request is only sent to the team that advanced, not other teams."""
        with open(self.test_config_file, 'w') as f:
            yaml.dump(self.config, f)
        
        bot = AmazingRaceBot(self.test_config_file)
        bot.game_state.start_game()
        
        # Create two teams
        # Team A: Alice (111) and Bob (222)
        bot.game_state.create_team("Team A", 111, "Alice")
        bot.game_state.join_team("Team A", 222, "Bob")
        
        # Team B: Charlie (333) and Diana (444)
        bot.game_state.create_team("Team B", 333, "Charlie")
        bot.game_state.join_team("Team B", 444, "Diana")
        
        # Only Team A completes challenge 1
        bot.game_state.complete_challenge("Team A", 1, 2, {'type': 'answer'})
        
        # Mock update and context for Alice (Team A member) submitting
        update = MagicMock()
        update.effective_user = MagicMock()
        update.effective_user.id = 111
        update.effective_user.first_name = "Alice"
        
        context = MagicMock()
        context.bot = MagicMock()
        context.bot.send_message = AsyncMock()
        
        # Broadcast the next challenge (which requires photo verification) to Team A
        await bot.broadcast_current_challenge(context, "Team A", exclude_user_id=111)
        
        # Collect all user IDs that received messages
        send_message_calls = context.bot.send_message.call_args_list
        user_ids_messaged = [call.kwargs['chat_id'] for call in send_message_calls]
        
        # VERIFY: Only Team A members should receive messages (Bob, excluding Alice)
        # Team B members (Charlie and Diana) should NOT receive messages
        self.assertIn(222, user_ids_messaged, "Bob (Team A member) should receive photo verification request")
        self.assertNotIn(111, user_ids_messaged, "Alice should be excluded as submitter")
        self.assertNotIn(333, user_ids_messaged, "Charlie (Team B member) should NOT receive photo verification request")
        self.assertNotIn(444, user_ids_messaged, "Diana (Team B member) should NOT receive photo verification request")
        
        # VERIFY: Message content includes photo verification request
        if send_message_calls:
            message_text = send_message_calls[0].kwargs['text']
            self.assertIn("Photo Verification Required", message_text)
            self.assertIn("Challenge #2", message_text)


    async def test_no_duplicate_photo_verification_messages(self):
        """Test that team members don't receive duplicate photo verification messages."""
        with open(self.test_config_file, 'w') as f:
            yaml.dump(self.config, f)
        
        bot = AmazingRaceBot(self.test_config_file)
        bot.game_state.start_game()
        
        # Create one team with two members
        bot.game_state.create_team("Team A", 111, "Alice")
        bot.game_state.join_team("Team A", 222, "Bob")
        
        # Mock update and context
        update = MagicMock()
        update.effective_user = MagicMock()
        update.effective_user.id = 111
        update.effective_user.first_name = "Alice"
        update.message = MagicMock()
        update.message.reply_text = AsyncMock()
        
        context = MagicMock()
        context.args = ['test1']  # Correct answer for challenge 1
        context.bot_data = {}
        context.bot = MagicMock()
        context.bot.send_message = AsyncMock()
        
        # Alice submits correct answer for challenge 1
        await bot.submit_command(update, context)
        
        # Collect all messages sent to Bob (the other team member)
        send_message_calls = context.bot.send_message.call_args_list
        bob_messages = [call for call in send_message_calls if call.kwargs.get('chat_id') == 222]
        
        # Count how many messages mention "Photo Verification"
        # Using specific phrase to identify photo verification request messages
        photo_verification_messages = [
            msg for msg in bob_messages 
            if 'Photo Verification Required' in msg.kwargs.get('text', '') and
               'Before you can view this challenge' in msg.kwargs.get('text', '')
        ]
        
        # VERIFY: There should be exactly ONE photo verification message
        self.assertEqual(len(photo_verification_messages), 1, 
                        "Bob should receive exactly ONE photo verification message, not multiple")
        
        # VERIFY: The completion message should NOT mention photo verification
        completion_messages = [
            msg for msg in bob_messages 
            if 'Challenge Completed' in msg.kwargs.get('text', '')
        ]
        self.assertEqual(len(completion_messages), 1, "Should have one completion message")
        completion_text = completion_messages[0].kwargs.get('text', '')
        self.assertNotIn('Photo Verification', completion_text, 
                        "Completion message should NOT mention photo verification to avoid duplication")
        
        # VERIFY: The detailed photo verification message exists
        # Check for multiple key phrases to ensure it's the correct message type
        detailed_verif_messages = [
            msg for msg in bob_messages 
            if 'Photo Verification Required' in msg.kwargs.get('text', '') and
               'Before you can view this challenge' in msg.kwargs.get('text', '') and
               'Send the photo to this bot' in msg.kwargs.get('text', '')
        ]
        self.assertEqual(len(detailed_verif_messages), 1, 
                        "Should have one detailed photo verification message with full instructions")


if __name__ == '__main__':
    unittest.main()
