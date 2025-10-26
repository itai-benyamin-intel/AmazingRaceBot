"""
Unit tests for penalty notification broadcast functionality.
"""
import unittest
import os
import yaml
from unittest.mock import AsyncMock, MagicMock, patch, call
from bot import AmazingRaceBot


class TestPenaltyBroadcast(unittest.IsolatedAsyncioTestCase):
    """Test cases for penalty notification broadcast."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.test_config_file = "test_penalty_broadcast_config.yml"
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
                        'verification': {
                            'method': 'answer',
                            'answer': 'test1'
                        },
                        'hints': [
                            'Hint 1',
                            'Hint 2',
                            'Hint 3'
                        ]
                    },
                    {
                        'id': 2,
                        'name': 'Challenge 2',
                        'description': 'Second challenge',
                        'location': 'Library',
                        'type': 'riddle',
                        'verification': {
                            'method': 'answer',
                            'answer': 'test2'
                        }
                    }
                ]
            },
            'admin': 999999999
        }
        
    def tearDown(self):
        """Clean up test files."""
        if os.path.exists(self.test_config_file):
            os.remove(self.test_config_file)
        if os.path.exists("game_state.json"):
            os.remove("game_state.json")
    
    async def test_penalty_notification_broadcast_to_all_team_members(self):
        """Test that penalty notification is broadcast to all team members when challenge is completed."""
        with open(self.test_config_file, 'w') as f:
            yaml.dump(self.config, f)
        
        bot = AmazingRaceBot(self.test_config_file)
        bot.game_state.start_game()
        
        # Create team with multiple members
        bot.game_state.create_team("Team A", 111111, "Alice")
        bot.game_state.join_team("Team A", 222222, "Bob")
        bot.game_state.join_team("Team A", 333333, "Charlie")
        
        # Use 2 hints on challenge 1
        bot.game_state.use_hint("Team A", 1, 0, 111111, "Alice")
        bot.game_state.use_hint("Team A", 1, 1, 111111, "Alice")
        
        # Mock the update and context
        update = MagicMock()
        update.effective_user = MagicMock()
        update.effective_user.id = 111111
        update.effective_user.first_name = "Alice"
        update.message = MagicMock()
        update.message.reply_text = AsyncMock()
        
        context = MagicMock()
        context.args = ['test1']
        context.bot_data = {}
        context.bot.send_message = AsyncMock()
        
        # Submit challenge
        await bot.submit_command(update, context)
        
        # Verify challenge was completed
        team = bot.game_state.teams["Team A"]
        self.assertEqual(len(team['completed_challenges']), 1)
        
        # Get all broadcast messages
        calls = context.bot.send_message.call_args_list
        sent_messages = [(call[1]['chat_id'], call[1]['text']) for call in calls]
        
        # Find completion broadcast messages (should go to Bob, Charlie, and Admin)
        completion_messages = [(chat_id, text) for chat_id, text in sent_messages if "Challenge Completed!" in text]
        
        # Should have 3 completion messages (Bob, Charlie, Admin)
        self.assertEqual(len(completion_messages), 3)
        
        # Verify penalty information is included in all completion broadcasts
        for chat_id, message_text in completion_messages:
            self.assertIn("Hint Penalty Applied", message_text)
            self.assertIn("You used 2 hint(s) on this challenge", message_text)
            self.assertIn("Next challenge unlocks in 4 minutes at:", message_text)
        
        # Verify messages were sent to Bob, Charlie, and Admin
        completion_recipients = [chat_id for chat_id, _ in completion_messages]
        self.assertIn(222222, completion_recipients)  # Bob
        self.assertIn(333333, completion_recipients)  # Charlie
        self.assertIn(999999999, completion_recipients)  # Admin
    
    async def test_no_penalty_broadcast_when_no_hints_used(self):
        """Test that no penalty notification is sent when no hints were used."""
        with open(self.test_config_file, 'w') as f:
            yaml.dump(self.config, f)
        
        bot = AmazingRaceBot(self.test_config_file)
        bot.game_state.start_game()
        
        # Create team with multiple members
        bot.game_state.create_team("Team A", 111111, "Alice")
        bot.game_state.join_team("Team A", 222222, "Bob")
        
        # Mock the update and context
        update = MagicMock()
        update.effective_user = MagicMock()
        update.effective_user.id = 111111
        update.effective_user.first_name = "Alice"
        update.message = MagicMock()
        update.message.reply_text = AsyncMock()
        
        context = MagicMock()
        context.args = ['test1']
        context.bot_data = {}
        context.bot.send_message = AsyncMock()
        
        # Submit challenge without using hints
        await bot.submit_command(update, context)
        
        # Get all broadcast messages
        calls = context.bot.send_message.call_args_list
        sent_messages = [(call[1]['chat_id'], call[1]['text']) for call in calls]
        
        # Find completion broadcast messages
        completion_messages = [(chat_id, text) for chat_id, text in sent_messages if "Challenge Completed!" in text]
        
        # Verify no penalty information is included
        for chat_id, message_text in completion_messages:
            self.assertNotIn("Hint Penalty Applied", message_text)
            self.assertNotIn("Next challenge unlocks", message_text)
    
    async def test_photo_verification_notification_broadcast(self):
        """Test that photo verification notification is broadcast when photo verification is enabled."""
        # Update config to enable photo verification
        self.config['game']['photo_verification_enabled'] = True
        
        with open(self.test_config_file, 'w') as f:
            yaml.dump(self.config, f)
        
        bot = AmazingRaceBot(self.test_config_file)
        bot.game_state.start_game()
        bot.game_state.photo_verification_enabled = True
        
        # Create team with multiple members
        bot.game_state.create_team("Team A", 111111, "Alice")
        bot.game_state.join_team("Team A", 222222, "Bob")
        bot.game_state.join_team("Team A", 333333, "Charlie")
        
        # Mock the update and context
        update = MagicMock()
        update.effective_user = MagicMock()
        update.effective_user.id = 111111
        update.effective_user.first_name = "Alice"
        update.message = MagicMock()
        update.message.reply_text = AsyncMock()
        
        context = MagicMock()
        context.args = ['test1']
        context.bot_data = {}
        context.bot.send_message = AsyncMock()
        
        # Submit challenge
        await bot.submit_command(update, context)
        
        # Get all broadcast messages
        calls = context.bot.send_message.call_args_list
        sent_messages = [(call[1]['chat_id'], call[1]['text']) for call in calls]
        
        # Find completion broadcast messages
        completion_messages = [(chat_id, text) for chat_id, text in sent_messages if "Challenge Completed!" in text]
        
        # Should have 3 completion messages (Bob, Charlie, Admin)
        self.assertEqual(len(completion_messages), 3)
        
        # Verify photo verification notification is included
        for chat_id, message_text in completion_messages:
            self.assertIn("Photo Verification Required", message_text)
            self.assertIn("send a photo of your team at the challenge location", message_text)
    
    async def test_photo_verification_without_penalty_on_completion(self):
        """Test that when photo verification is enabled, penalty timer doesn't start until photo approval."""
        # Update config to enable photo verification
        self.config['game']['photo_verification_enabled'] = True
        
        with open(self.test_config_file, 'w') as f:
            yaml.dump(self.config, f)
        
        bot = AmazingRaceBot(self.test_config_file)
        bot.game_state.start_game()
        bot.game_state.photo_verification_enabled = True
        
        # Create team with multiple members
        bot.game_state.create_team("Team A", 111111, "Alice")
        bot.game_state.join_team("Team A", 222222, "Bob")
        
        # Use 1 hint on challenge 1
        bot.game_state.use_hint("Team A", 1, 0, 111111, "Alice")
        
        # Mock the update and context
        update = MagicMock()
        update.effective_user = MagicMock()
        update.effective_user.id = 111111
        update.effective_user.first_name = "Alice"
        update.message = MagicMock()
        update.message.reply_text = AsyncMock()
        
        context = MagicMock()
        context.args = ['test1']
        context.bot_data = {}
        context.bot.send_message = AsyncMock()
        
        # Submit challenge
        await bot.submit_command(update, context)
        
        # Get all broadcast messages
        calls = context.bot.send_message.call_args_list
        sent_messages = [(call[1]['chat_id'], call[1]['text']) for call in calls]
        
        # Find completion broadcast messages
        completion_messages = [(chat_id, text) for chat_id, text in sent_messages if "Challenge Completed!" in text]
        
        # When photo verification is enabled, penalty timer doesn't start until photo is approved
        # So completion broadcast should only mention photo verification, NOT penalty
        for chat_id, message_text in completion_messages:
            self.assertNotIn("Hint Penalty Applied", message_text)
            self.assertIn("Photo Verification Required", message_text)
            self.assertIn("send a photo of your team at the challenge location", message_text)
    
    async def test_penalty_broadcast_on_photo_approval(self):
        """Test that penalty notification is broadcast when photo is approved (with hints used)."""
        # Update config to add photo challenge
        self.config['game']['challenges'] = [
            {
                'id': 1,
                'name': 'Challenge 1',
                'description': 'Photo challenge',
                'location': 'Start',
                'type': 'photo',
                'verification': {
                    'method': 'photo'
                },
                'hints': ['Hint 1', 'Hint 2']
            },
            {
                'id': 2,
                'name': 'Challenge 2',
                'description': 'Second challenge',
                'location': 'Library',
                'type': 'riddle',
                'verification': {
                    'method': 'answer',
                    'answer': 'test2'
                }
            }
        ]
        
        with open(self.test_config_file, 'w') as f:
            yaml.dump(self.config, f)
        
        bot = AmazingRaceBot(self.test_config_file)
        bot.game_state.start_game()
        
        # Create team with multiple members
        bot.game_state.create_team("Team A", 111111, "Alice")
        bot.game_state.join_team("Team A", 222222, "Bob")
        bot.game_state.join_team("Team A", 333333, "Charlie")
        
        # Use 2 hints on challenge 1
        bot.game_state.use_hint("Team A", 1, 0, 111111, "Alice")
        bot.game_state.use_hint("Team A", 1, 1, 111111, "Alice")
        
        # Submit photo challenge
        submission_data = {
            'type': 'photo',
            'photo_file_id': 'test_photo_123'
        }
        submission_id = bot.game_state.add_pending_photo_submission(
            "Team A", 1, 111111, "Alice", submission_data
        )
        
        # Mock context for photo approval
        context = MagicMock()
        context.bot.send_message = AsyncMock()
        
        # Approve the photo
        bot.game_state.approve_photo_submission(submission_id, len(bot.challenges))
        
        # Get the unlock time for the next challenge
        from datetime import datetime
        unlock_time_str = bot.game_state.get_challenge_unlock_time("Team A", 2)
        self.assertIsNotNone(unlock_time_str, "Unlock time should be set after photo approval")
        unlock_time = datetime.fromisoformat(unlock_time_str)
        
        # Now broadcast the completion (simulating what happens in the callback handler)
        await bot.broadcast_challenge_completion(
            context, "Team A", 1, "Challenge 1",
            111111, "Alice", 1, 2,
            penalty_info={
                'hint_count': 2,
                'penalty_minutes': 4,
                'unlock_time': unlock_time
            },
            photo_verification_needed=False
        )
        
        # Get all broadcast messages
        calls = context.bot.send_message.call_args_list
        sent_messages = [(call[1]['chat_id'], call[1]['text']) for call in calls]
        
        # Find completion broadcast messages (should go to Bob, Charlie, and Admin)
        completion_messages = [(chat_id, text) for chat_id, text in sent_messages if "Challenge Completed!" in text]
        
        # Should have 3 completion messages (Bob, Charlie, Admin - Alice is the submitter)
        self.assertEqual(len(completion_messages), 3)
        
        # Verify penalty information is included in all completion broadcasts
        for chat_id, message_text in completion_messages:
            self.assertIn("Hint Penalty Applied", message_text)
            self.assertIn("You used 2 hint(s) on this challenge", message_text)
            self.assertIn("Next challenge unlocks in 4 minutes at:", message_text)


if __name__ == '__main__':
    unittest.main()
