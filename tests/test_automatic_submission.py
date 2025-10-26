"""
Unit tests for automatic submission feature (without /submit command).
Tests that messages and photos sent during an active game are treated as submissions.
"""
import unittest
import os
import yaml
from unittest.mock import AsyncMock, MagicMock, patch
from bot import AmazingRaceBot


class TestAutomaticTextSubmission(unittest.IsolatedAsyncioTestCase):
    """Test cases for automatic text submission without /submit command."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.test_config_file = "test_auto_submit_config.yml"
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
                            'answer': 'paris'
                        }
                    },
                    {
                        'id': 2,
                        'name': 'Challenge 2',
                        'description': 'Second challenge',
                        'location': 'Library',
                        'type': 'trivia',
                        'verification': {
                            'method': 'answer',
                            'answer': 'eiffel tower'
                        }
                    }
                ]
            },
            'admin': 123456789
        }
        
        with open(self.test_config_file, 'w') as f:
            yaml.dump(self.config, f)
    
    def tearDown(self):
        """Clean up test files."""
        if os.path.exists(self.test_config_file):
            os.remove(self.test_config_file)
        if os.path.exists("game_state.json"):
            os.remove("game_state.json")
    
    async def test_text_message_as_submission_during_active_game(self):
        """Test that a text message is treated as a submission during active game."""
        bot = AmazingRaceBot(self.test_config_file)
        bot.game_state.start_game()
        
        # Create team and user
        bot.game_state.create_team("Team A", 111111, "Alice")
        
        # Mock the update and context
        update = MagicMock()
        update.effective_user = MagicMock()
        update.effective_user.id = 111111
        update.effective_user.first_name = "Alice"
        update.message = MagicMock()
        update.message.text = "paris"  # Answer without /submit command
        update.message.reply_text = AsyncMock()
        
        context = MagicMock()
        context.bot = MagicMock()
        context.bot.send_message = AsyncMock()
        context.bot_data = {}
        context.user_data = {}
        
        # Call unrecognized_message_handler (should route to submit_command)
        await bot.unrecognized_message_handler(update, context)
        
        # Verify challenge was completed
        team = bot.game_state.teams["Team A"]
        self.assertEqual(len(team['completed_challenges']), 1)
        self.assertIn(1, team['completed_challenges'])
        
        # Verify correct response was sent
        update.message.reply_text.assert_called()
        call_args = update.message.reply_text.call_args[0][0]
        self.assertIn("Correct", call_args)
        self.assertIn("Team A", call_args)
    
    async def test_text_message_not_submitted_when_game_not_started(self):
        """Test that text messages are not treated as submissions when game hasn't started."""
        bot = AmazingRaceBot(self.test_config_file)
        # Don't start the game
        
        # Create team and user
        bot.game_state.create_team("Team A", 111111, "Alice")
        
        # Mock the update and context
        update = MagicMock()
        update.effective_user = MagicMock()
        update.effective_user.id = 111111
        update.effective_user.first_name = "Alice"
        update.message = MagicMock()
        update.message.text = "paris"
        update.message.reply_text = AsyncMock()
        
        context = MagicMock()
        context.user_data = {}
        
        # Call unrecognized_message_handler
        await bot.unrecognized_message_handler(update, context)
        
        # Verify challenge was NOT completed
        team = bot.game_state.teams["Team A"]
        self.assertEqual(len(team['completed_challenges']), 0)
        
        # Verify helpful message was sent
        update.message.reply_text.assert_called()
        call_args = update.message.reply_text.call_args[0][0]
        self.assertIn("didn't understand", call_args)
    
    async def test_text_message_not_submitted_when_game_ended(self):
        """Test that text messages are not treated as submissions when game has ended."""
        bot = AmazingRaceBot(self.test_config_file)
        bot.game_state.start_game()
        bot.game_state.end_game()
        
        # Create team and user
        bot.game_state.create_team("Team A", 111111, "Alice")
        
        # Mock the update and context
        update = MagicMock()
        update.effective_user = MagicMock()
        update.effective_user.id = 111111
        update.effective_user.first_name = "Alice"
        update.message = MagicMock()
        update.message.text = "paris"
        update.message.reply_text = AsyncMock()
        
        context = MagicMock()
        context.user_data = {}
        
        # Call unrecognized_message_handler
        await bot.unrecognized_message_handler(update, context)
        
        # Verify challenge was NOT completed
        team = bot.game_state.teams["Team A"]
        self.assertEqual(len(team['completed_challenges']), 0)
        
        # Verify helpful message was sent
        update.message.reply_text.assert_called()
        call_args = update.message.reply_text.call_args[0][0]
        self.assertIn("didn't understand", call_args)
    
    async def test_text_message_not_submitted_when_user_not_in_team(self):
        """Test that text messages are not treated as submissions when user has no team."""
        bot = AmazingRaceBot(self.test_config_file)
        bot.game_state.start_game()
        
        # Don't create a team for the user
        
        # Mock the update and context
        update = MagicMock()
        update.effective_user = MagicMock()
        update.effective_user.id = 111111
        update.effective_user.first_name = "Alice"
        update.message = MagicMock()
        update.message.text = "paris"
        update.message.reply_text = AsyncMock()
        
        context = MagicMock()
        context.user_data = {}
        
        # Call unrecognized_message_handler
        await bot.unrecognized_message_handler(update, context)
        
        # Verify helpful message was sent
        update.message.reply_text.assert_called()
        call_args = update.message.reply_text.call_args[0][0]
        self.assertIn("didn't understand", call_args)
    
    async def test_incorrect_text_answer_automatic_submission(self):
        """Test that incorrect automatic text submission is handled properly."""
        bot = AmazingRaceBot(self.test_config_file)
        bot.game_state.start_game()
        
        # Create team and user
        bot.game_state.create_team("Team A", 111111, "Alice")
        
        # Mock the update and context
        update = MagicMock()
        update.effective_user = MagicMock()
        update.effective_user.id = 111111
        update.effective_user.first_name = "Alice"
        update.message = MagicMock()
        update.message.text = "wrong answer"  # Incorrect answer
        update.message.reply_text = AsyncMock()
        
        context = MagicMock()
        context.bot_data = {}
        context.user_data = {}
        
        # Call unrecognized_message_handler
        await bot.unrecognized_message_handler(update, context)
        
        # Verify challenge was NOT completed
        team = bot.game_state.teams["Team A"]
        self.assertEqual(len(team['completed_challenges']), 0)
        
        # Verify incorrect answer message was sent
        update.message.reply_text.assert_called()
        call_args = update.message.reply_text.call_args[0][0]
        self.assertIn("Incorrect", call_args)
    
    async def test_command_still_ignored(self):
        """Test that messages starting with / are still ignored."""
        bot = AmazingRaceBot(self.test_config_file)
        bot.game_state.start_game()
        
        # Create team and user
        bot.game_state.create_team("Team A", 111111, "Alice")
        
        # Mock the update and context
        update = MagicMock()
        update.effective_user = MagicMock()
        update.effective_user.id = 111111
        update.message = MagicMock()
        update.message.text = "/unknowncommand"  # Command
        update.message.reply_text = AsyncMock()
        
        context = MagicMock()
        context.user_data = {}
        
        # Call unrecognized_message_handler
        await bot.unrecognized_message_handler(update, context)
        
        # Should return early, no message sent
        update.message.reply_text.assert_not_called()


class TestAutomaticPhotoSubmission(unittest.IsolatedAsyncioTestCase):
    """Test cases for automatic photo submission without /submit command."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.test_config_file = "test_auto_photo_submit_config.yml"
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
                        'description': 'Take a photo',
                        'location': 'Park',
                        'type': 'photo',
                        'verification': {
                            'method': 'photo'
                        }
                    },
                    {
                        'id': 2,
                        'name': 'Challenge 2',
                        'description': 'Another photo',
                        'location': 'Museum',
                        'type': 'photo',
                        'verification': {
                            'method': 'photo'
                        }
                    }
                ]
            },
            'admin': 123456789
        }
        
        with open(self.test_config_file, 'w') as f:
            yaml.dump(self.config, f)
    
    def tearDown(self):
        """Clean up test files."""
        if os.path.exists(self.test_config_file):
            os.remove(self.test_config_file)
        if os.path.exists("game_state.json"):
            os.remove("game_state.json")
    
    async def test_photo_as_submission_during_active_game(self):
        """Test that a photo is treated as a submission during active game."""
        bot = AmazingRaceBot(self.test_config_file)
        bot.game_state.start_game()
        
        # Create team and user
        bot.game_state.create_team("Team A", 111111, "Alice")
        
        # Mock the update and context
        update = MagicMock()
        update.effective_user = MagicMock()
        update.effective_user.id = 111111
        update.effective_user.first_name = "Alice"
        update.message = MagicMock()
        update.message.photo = [MagicMock()]  # List of photos
        update.message.photo[-1].file_id = "test_photo_id"
        update.message.reply_text = AsyncMock()
        
        context = MagicMock()
        context.bot = MagicMock()
        context.bot.send_photo = AsyncMock()
        context.bot_data = {}
        
        # Call photo_handler
        await bot.photo_handler(update, context)
        
        # Verify photo submission was created
        pending = bot.game_state.get_pending_photo_submissions()
        self.assertEqual(len(pending), 1)
        
        # Verify user was notified
        update.message.reply_text.assert_called()
        call_args = update.message.reply_text.call_args[0][0]
        self.assertIn("Photo submitted", call_args)
        
        # Verify admin was notified
        context.bot.send_photo.assert_called()
    
    async def test_photo_not_submitted_when_game_not_started(self):
        """Test that photos are not treated as submissions when game hasn't started."""
        bot = AmazingRaceBot(self.test_config_file)
        # Don't start the game
        
        # Create team and user
        bot.game_state.create_team("Team A", 111111, "Alice")
        
        # Mock the update and context
        update = MagicMock()
        update.effective_user = MagicMock()
        update.effective_user.id = 111111
        update.message = MagicMock()
        update.message.photo = [MagicMock()]
        update.message.photo[-1].file_id = "test_photo_id"
        update.message.reply_text = AsyncMock()
        
        context = MagicMock()
        context.bot_data = {}
        
        # Call photo_handler
        await bot.photo_handler(update, context)
        
        # Verify no photo submission was created
        pending = bot.game_state.get_pending_photo_submissions()
        self.assertEqual(len(pending), 0)
        
        # Verify no message was sent (should ignore)
        update.message.reply_text.assert_not_called()
    
    async def test_photo_not_submitted_when_user_not_in_team(self):
        """Test that photos are not treated as submissions when user has no team."""
        bot = AmazingRaceBot(self.test_config_file)
        bot.game_state.start_game()
        
        # Don't create a team for the user
        
        # Mock the update and context
        update = MagicMock()
        update.effective_user = MagicMock()
        update.effective_user.id = 111111
        update.message = MagicMock()
        update.message.photo = [MagicMock()]
        update.message.photo[-1].file_id = "test_photo_id"
        update.message.reply_text = AsyncMock()
        
        context = MagicMock()
        context.bot_data = {}
        
        # Call photo_handler
        await bot.photo_handler(update, context)
        
        # Verify no photo submission was created
        pending = bot.game_state.get_pending_photo_submissions()
        self.assertEqual(len(pending), 0)
        
        # Verify no message was sent (should ignore)
        update.message.reply_text.assert_not_called()


class TestInteractionWithWaitingForInput(unittest.IsolatedAsyncioTestCase):
    """Test that automatic submission doesn't interfere with existing 'waiting_for' flow."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.test_config_file = "test_waiting_config.yml"
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
                            'answer': 'test'
                        }
                    }
                ]
            },
            'admin': 123456789
        }
        
        with open(self.test_config_file, 'w') as f:
            yaml.dump(self.config, f)
    
    def tearDown(self):
        """Clean up test files."""
        if os.path.exists(self.test_config_file):
            os.remove(self.test_config_file)
        if os.path.exists("game_state.json"):
            os.remove("game_state.json")
    
    async def test_waiting_for_submit_takes_precedence(self):
        """Test that waiting_for state takes precedence over automatic submission."""
        bot = AmazingRaceBot(self.test_config_file)
        bot.game_state.start_game()
        
        # Create team and user
        bot.game_state.create_team("Team A", 111111, "Alice")
        
        # Mock the update and context
        update = MagicMock()
        update.effective_user = MagicMock()
        update.effective_user.id = 111111
        update.effective_user.first_name = "Alice"
        update.message = MagicMock()
        update.message.text = "test"  # Answer
        update.message.reply_text = AsyncMock()
        
        context = MagicMock()
        context.bot = MagicMock()
        context.bot.send_message = AsyncMock()
        context.bot_data = {}
        context.user_data = {
            'waiting_for': {
                'command': 'submit',
                'challenge_id': 1
            }
        }
        
        # Call unrecognized_message_handler
        await bot.unrecognized_message_handler(update, context)
        
        # Verify challenge was completed
        team = bot.game_state.teams["Team A"]
        self.assertEqual(len(team['completed_challenges']), 1)
        
        # Verify waiting_for was cleared
        self.assertNotIn('waiting_for', context.user_data)


if __name__ == '__main__':
    unittest.main()
