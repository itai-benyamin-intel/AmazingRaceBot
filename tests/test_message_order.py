"""
Unit tests for challenge completion message ordering.

This test validates the fix for ensuring completion messages are sent
before next challenge messages, as per the requirements.
"""
import unittest
import os
import yaml
from unittest.mock import AsyncMock, MagicMock, call
from bot import AmazingRaceBot


class TestMessageOrdering(unittest.IsolatedAsyncioTestCase):
    """Test cases for message ordering in challenge completion flow."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.test_config_file = "test_message_order_config.yml"
        self.config = {
            'telegram': {'bot_token': 'test_token'},
            'game': {
                'max_teams': 10,
                'max_team_size': 5,
                'challenges': [
                    {
                        'id': 1,
                        'description': 'First challenge',
                        'location': 'Start',
                        'type': 'riddle',
                        'verification': {
                            'method': 'answer',
                            'answer': 'test1'
                        }
                    },
                    {
                        'id': 2,
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
    
    async def test_completion_message_sent_before_next_challenge(self):
        """Test that completion message is sent before next challenge message."""
        with open(self.test_config_file, 'w') as f:
            yaml.dump(self.config, f)
        
        bot = AmazingRaceBot(self.test_config_file)
        bot.game_state.start_game()
        
        # Disable photo verification for this test
        bot.game_state.set_photo_verification(False)
        
        # Create team with three members
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
        
        # Verify challenge was completed
        team = bot.game_state.teams["Team A"]
        self.assertEqual(len(team['completed_challenges']), 1)
        
        # Get all send_message calls
        calls = context.bot.send_message.call_args_list
        
        # Extract messages by type
        completion_messages = []
        next_challenge_messages = []
        
        for i, call_item in enumerate(calls):
            text = call_item[1]['text']
            chat_id = call_item[1]['chat_id']
            
            if "Challenge Completed!" in text:
                completion_messages.append((i, chat_id, text))
            elif "New Challenge Available!" in text:
                next_challenge_messages.append((i, chat_id, text))
        
        # Verify we have the expected number of messages
        # Completion: Bob, Charlie, Admin = 3
        # Next challenge: Bob, Charlie (not Alice, not Admin) = 2
        self.assertEqual(len(completion_messages), 3, 
                         "Should have 3 completion messages (Bob, Charlie, Admin)")
        self.assertEqual(len(next_challenge_messages), 2,
                         "Should have 2 next challenge messages (Bob, Charlie)")
        
        # Verify message ordering: ALL completion messages come before ALL next challenge messages
        max_completion_index = max(msg[0] for msg in completion_messages)
        min_next_challenge_index = min(msg[0] for msg in next_challenge_messages)
        
        self.assertLess(max_completion_index, min_next_challenge_index,
                        "All completion messages should be sent before any next challenge messages")
        
        # Verify recipients for completion messages
        completion_recipients = {msg[1] for msg in completion_messages}
        self.assertIn(222222, completion_recipients, "Bob should receive completion message")
        self.assertIn(333333, completion_recipients, "Charlie should receive completion message")
        self.assertIn(999999999, completion_recipients, "Admin should receive completion message")
        self.assertNotIn(111111, completion_recipients, "Alice (submitter) should NOT receive completion message")
        
        # Verify recipients for next challenge messages
        next_challenge_recipients = {msg[1] for msg in next_challenge_messages}
        self.assertIn(222222, next_challenge_recipients, "Bob should receive next challenge message")
        self.assertIn(333333, next_challenge_recipients, "Charlie should receive next challenge message")
        self.assertNotIn(111111, next_challenge_recipients, "Alice (submitter) should NOT receive next challenge message")
        self.assertNotIn(999999999, next_challenge_recipients, "Admin should NOT receive next challenge message")
    
    async def test_submitter_gets_correct_answer_confirmation_only(self):
        """Test that submitter only gets answer confirmation, not broadcasts."""
        with open(self.test_config_file, 'w') as f:
            yaml.dump(self.config, f)
        
        bot = AmazingRaceBot(self.test_config_file)
        bot.game_state.start_game()
        
        # Create team with two members
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
        
        # Submit challenge
        await bot.submit_command(update, context)
        
        # Verify submitter got direct reply
        update.message.reply_text.assert_called_once()
        reply_text = update.message.reply_text.call_args[0][0]
        self.assertIn("Correct!", reply_text, "Submitter should get 'Correct!' message")
        
        # Verify submitter did NOT get any send_message broadcasts
        calls = context.bot.send_message.call_args_list
        submitter_broadcasts = [call for call in calls if call[1]['chat_id'] == 111111]
        self.assertEqual(len(submitter_broadcasts), 0,
                         "Submitter should not receive any broadcast messages")
    
    async def test_admin_gets_completion_not_next_challenge(self):
        """Test that admin gets completion message but not next challenge message."""
        with open(self.test_config_file, 'w') as f:
            yaml.dump(self.config, f)
        
        bot = AmazingRaceBot(self.test_config_file)
        bot.game_state.start_game()
        
        # Create team
        bot.game_state.create_team("Team A", 111111, "Alice")
        
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
        
        # Get admin messages
        calls = context.bot.send_message.call_args_list
        admin_messages = [call for call in calls if call[1]['chat_id'] == 999999999]
        
        # Admin should get exactly 1 message (completion)
        self.assertEqual(len(admin_messages), 1, "Admin should get exactly 1 message")
        
        admin_message_text = admin_messages[0][1]['text']
        self.assertIn("Challenge Completed!", admin_message_text,
                      "Admin should receive completion message")
        self.assertNotIn("New Challenge Available!", admin_message_text,
                         "Admin should NOT receive next challenge message")


if __name__ == '__main__':
    unittest.main()
