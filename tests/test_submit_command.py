"""
Unit tests for the submit command with optional challenge_id parameter.
"""
import unittest
import os
import yaml
from unittest.mock import AsyncMock, MagicMock, patch
from bot import AmazingRaceBot


class TestSubmitCommand(unittest.IsolatedAsyncioTestCase):
    """Test cases for the submit command."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.test_config_file = "test_submit_config.yml"
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
                            'answer': 'test2'
                        }
                    },
                    {
                        'id': 3,
                        'name': 'Challenge 3',
                        'description': 'Third challenge',
                        'location': 'Park',
                        'type': 'photo',
                        'verification': {
                            'method': 'photo'
                        }
                    }
                ]
            },
            'admin': 123456789
        }
        
    def tearDown(self):
        """Clean up test files."""
        if os.path.exists(self.test_config_file):
            os.remove(self.test_config_file)
        if os.path.exists("game_state.json"):
            os.remove("game_state.json")
    
    async def test_submit_without_challenge_id_answer_challenge(self):
        """Test submit command without challenge_id for answer challenge."""
        with open(self.test_config_file, 'w') as f:
            yaml.dump(self.config, f)
        
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
        update.message.reply_text = AsyncMock()
        
        context = MagicMock()
        context.args = ['test1']  # Just the answer, no challenge_id
        context.bot_data = {}
        
        # Call submit_command
        await bot.submit_command(update, context)
        
        # Verify challenge was completed
        team = bot.game_state.teams["Team A"]
        self.assertEqual(len(team['completed_challenges']), 1)
        self.assertIn(1, team['completed_challenges'])
        
        # Verify correct response
        update.message.reply_text.assert_called()
        call_args = update.message.reply_text.call_args[0][0]
        self.assertIn("Correct!", call_args)
        self.assertIn("Challenge 1", call_args)
    
    async def test_submit_with_number_as_answer(self):
        """Test submit command with a number as answer (no backward compatibility)."""
        with open(self.test_config_file, 'w') as f:
            yaml.dump(self.config, f)
        
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
        update.message.reply_text = AsyncMock()
        
        context = MagicMock()
        context.args = ['1']  # Number treated as answer, not challenge_id
        context.bot_data = {}
        
        # Call submit_command
        await bot.submit_command(update, context)
        
        # Verify challenge was NOT completed (wrong answer)
        team = bot.game_state.teams["Team A"]
        self.assertEqual(len(team['completed_challenges']), 0)
        
        # Verify incorrect answer message
        update.message.reply_text.assert_called()
        call_args = update.message.reply_text.call_args[0][0]
        self.assertIn("Incorrect", call_args)
    
    async def test_submit_without_answer_requests_answer(self):
        """Test submit command without answer requests it in a message."""
        with open(self.test_config_file, 'w') as f:
            yaml.dump(self.config, f)
        
        bot = AmazingRaceBot(self.test_config_file)
        bot.game_state.start_game()
        
        # Create team and user
        bot.game_state.create_team("Team A", 111111, "Alice")
        
        # Mock the update and context
        update = MagicMock()
        update.effective_user = MagicMock()
        update.effective_user.id = 111111
        update.message = MagicMock()
        update.message.reply_text = AsyncMock()
        
        context = MagicMock()
        context.args = []  # No answer provided
        context.bot_data = {}
        
        # Call submit_command
        await bot.submit_command(update, context)
        
        # Verify challenge was NOT completed
        team = bot.game_state.teams["Team A"]
        self.assertEqual(len(team['completed_challenges']), 0)
        
        # Verify message requests answer
        update.message.reply_text.assert_called()
        call_args = update.message.reply_text.call_args[0][0]
        self.assertIn("Please provide your answer", call_args)
    
    async def test_submit_without_args_photo_challenge(self):
        """Test submit command without args for photo challenge."""
        with open(self.test_config_file, 'w') as f:
            yaml.dump(self.config, f)
        
        bot = AmazingRaceBot(self.test_config_file)
        bot.game_state.start_game()
        
        # Disable photo verification for this test
        bot.game_state.set_photo_verification(False)
        
        # Create team and complete first two challenges
        bot.game_state.create_team("Team A", 111111, "Alice")
        bot.game_state.complete_challenge("Team A", 1, 3, {'type': 'answer'})
        bot.game_state.complete_challenge("Team A", 2, 3, {'type': 'answer'})
        
        # Mock the update and context
        update = MagicMock()
        update.effective_user = MagicMock()
        update.effective_user.id = 111111
        update.message = MagicMock()
        update.message.reply_text = AsyncMock()
        
        context = MagicMock()
        context.args = []  # No args for photo challenge
        context.bot_data = {}
        
        # Call submit_command
        await bot.submit_command(update, context)
        
        # Verify pending submission was created
        self.assertIn(111111, context.bot_data['pending_submissions'])
        pending = context.bot_data['pending_submissions'][111111]
        self.assertEqual(pending['challenge_id'], 3)
        self.assertEqual(pending['team_name'], "Team A")
        
        # Verify message asks for photo
        update.message.reply_text.assert_called()
        call_args = update.message.reply_text.call_args[0][0]
        self.assertIn("Please send a photo", call_args)
    
    async def test_submit_sequential_challenges(self):
        """Test submitting challenges in sequence without challenge_id."""
        with open(self.test_config_file, 'w') as f:
            yaml.dump(self.config, f)
        
        bot = AmazingRaceBot(self.test_config_file)
        bot.game_state.start_game()
        
        # Disable photo verification for this test
        bot.game_state.set_photo_verification(False)
        
        # Create team and user
        bot.game_state.create_team("Team A", 111111, "Alice")
        
        # Mock the update and context
        update = MagicMock()
        update.effective_user = MagicMock()
        update.effective_user.id = 111111
        update.effective_user.first_name = "Alice"
        update.message = MagicMock()
        update.message.reply_text = AsyncMock()
        
        context = MagicMock()
        context.bot_data = {}
        
        # Submit challenge 1
        context.args = ['test1']
        await bot.submit_command(update, context)
        team = bot.game_state.teams["Team A"]
        self.assertEqual(len(team['completed_challenges']), 1)
        
        # Submit challenge 2
        context.args = ['test2']
        await bot.submit_command(update, context)
        team = bot.game_state.teams["Team A"]
        self.assertEqual(len(team['completed_challenges']), 2)
        
        # Verify both challenges completed
        self.assertIn(1, team['completed_challenges'])
        self.assertIn(2, team['completed_challenges'])


class TestCurrentChallengeCommand(unittest.IsolatedAsyncioTestCase):
    """Test cases for the current_challenge command."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.test_config_file = "test_current_challenge_config.yml"
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
                            'answer': 'test2'
                        }
                    }
                ]
            },
            'admin': 123456789
        }
        
    def tearDown(self):
        """Clean up test files."""
        if os.path.exists(self.test_config_file):
            os.remove(self.test_config_file)
        if os.path.exists("game_state.json"):
            os.remove("game_state.json")
    
    async def test_current_challenge_first_challenge(self):
        """Test current_challenge command for first challenge."""
        with open(self.test_config_file, 'w') as f:
            yaml.dump(self.config, f)
        
        bot = AmazingRaceBot(self.test_config_file)
        bot.game_state.create_team("Team A", 111111, "Alice")
        
        # Mock the update and context
        update = MagicMock()
        update.effective_user = MagicMock()
        update.effective_user.id = 111111
        update.message = MagicMock()
        update.message.reply_text = AsyncMock()
        
        context = MagicMock()
        
        # Call current_challenge_command
        await bot.current_challenge_command(update, context)
        
        # Verify message shows current challenge
        update.message.reply_text.assert_called()
        call_args = update.message.reply_text.call_args[0][0]
        self.assertIn("Your Current Challenge", call_args)
        self.assertIn("Challenge #1", call_args)
        self.assertIn("Challenge 1", call_args)
        self.assertIn("/submit [answer]", call_args)
    
    async def test_current_challenge_no_team(self):
        """Test current_challenge command when user is not in a team."""
        with open(self.test_config_file, 'w') as f:
            yaml.dump(self.config, f)
        
        bot = AmazingRaceBot(self.test_config_file)
        
        # Mock the update and context
        update = MagicMock()
        update.effective_user = MagicMock()
        update.effective_user.id = 111111
        update.message = MagicMock()
        update.message.reply_text = AsyncMock()
        
        context = MagicMock()
        
        # Call current_challenge_command
        await bot.current_challenge_command(update, context)
        
        # Verify error message
        update.message.reply_text.assert_called()
        call_args = update.message.reply_text.call_args[0][0]
        self.assertIn("not in any team", call_args)
    
    async def test_current_challenge_all_completed(self):
        """Test current_challenge command when all challenges are completed."""
        with open(self.test_config_file, 'w') as f:
            yaml.dump(self.config, f)
        
        bot = AmazingRaceBot(self.test_config_file)
        bot.game_state.create_team("Team A", 111111, "Alice")
        
        # Complete all challenges
        bot.game_state.complete_challenge("Team A", 1, 2, {'type': 'answer'})
        bot.game_state.complete_challenge("Team A", 2, 2, {'type': 'answer'})
        
        # Mock the update and context
        update = MagicMock()
        update.effective_user = MagicMock()
        update.effective_user.id = 111111
        update.message = MagicMock()
        update.message.reply_text = AsyncMock()
        
        context = MagicMock()
        
        # Call current_challenge_command
        await bot.current_challenge_command(update, context)
        
        # Verify congratulations message
        update.message.reply_text.assert_called()
        call_args = update.message.reply_text.call_args[0][0]
        self.assertIn("Congratulations", call_args)
        self.assertIn("completed all challenges", call_args)


if __name__ == '__main__':
    unittest.main()
