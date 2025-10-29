"""
Test to verify /current command shows correct submit instructions for team_activity challenges.
"""
import unittest
import os
import yaml
import asyncio
from unittest.mock import MagicMock, AsyncMock
from telegram import Update, User, Message

from bot import AmazingRaceBot


class TestTeamActivityCurrentCommand(unittest.TestCase):
    """Test that /current command works correctly for team_activity challenges."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.test_config_file = "test_team_activity_current_config.yml"
        self.test_state_file = "test_team_activity_current_state.json"
        
    def tearDown(self):
        """Clean up test files."""
        if os.path.exists(self.test_config_file):
            os.remove(self.test_config_file)
        if os.path.exists(self.test_state_file):
            os.remove(self.test_state_file)
    
    def test_current_command_photo_team_activity(self):
        """Test /current command for team_activity with photo verification."""
        config = {
            'telegram': {'bot_token': 'test_token'},
            'game': {
                'name': 'Test Game',
                'max_teams': 10,
                'max_team_size': 5,
                'challenges': [
                    {
                        'id': 1,
                        'name': 'First Challenge',
                        'description': 'Complete first task',
                        'location': 'Start',
                        'type': 'text',
                        'verification': {'method': 'answer', 'answer': 'test'}
                    },
                    {
                        'id': 2,
                        'name': 'Team Pyramid',
                        'description': 'Create a human pyramid with your team',
                        'location': 'Outdoor Area',
                        'type': 'team_activity',
                        'verification': {'method': 'photo'}
                    }
                ]
            },
            'admin': 123456789
        }
        
        with open(self.test_config_file, 'w') as f:
            yaml.dump(config, f)
        
        bot = AmazingRaceBot(self.test_config_file)
        bot.game_state.state_file = self.test_state_file
        
        # Create team and start game
        bot.game_state.create_team("TestTeam", 111, "User1")
        bot.game_state.start_game()
        
        # Complete first challenge to reach team_activity
        bot.game_state.complete_challenge("TestTeam", 1, 2, None, False)
        
        # Mock update and context
        update = MagicMock(spec=Update)
        update.effective_user = User(id=111, first_name="User1", is_bot=False)
        update.effective_chat = MagicMock()
        update.effective_chat.id = 111
        update.message = MagicMock(spec=Message)
        update.message.reply_text = AsyncMock()
        
        context = MagicMock()
        context.bot = MagicMock()
        context.bot.send_message = AsyncMock()
        
        # Call current_challenge_command
        async def run_test():
            await bot.current_challenge_command(update, context)
            
            # Verify message was sent
            self.assertTrue(update.message.reply_text.called, "Message should be sent")
            
            # Get the message text
            call_args = update.message.reply_text.call_args
            message_text = call_args[0][0] if call_args[0] else call_args[1].get('text', '')
            
            # Verify message contains challenge info
            self.assertIn('Team Pyramid', message_text)
            self.assertIn('team_activity', message_text)
            
            # Verify submit instructions are appropriate for photo challenges
            self.assertIn('Use /submit to upload your photo', message_text)
            # Should NOT say "[answer]" for photo challenges
            self.assertNotIn('[answer]', message_text)
        
        asyncio.run(run_test())
    
    def test_current_command_video_team_activity(self):
        """Test /current command for team_activity with video verification."""
        config = {
            'telegram': {'bot_token': 'test_token'},
            'game': {
                'name': 'Test Game',
                'max_teams': 10,
                'max_team_size': 5,
                'challenges': [
                    {
                        'id': 1,
                        'name': 'First Challenge',
                        'description': 'Complete first task',
                        'location': 'Start',
                        'type': 'text',
                        'verification': {'method': 'answer', 'answer': 'test'}
                    },
                    {
                        'id': 2,
                        'name': 'Team Video',
                        'description': 'Make a team video',
                        'location': 'Anywhere',
                        'type': 'team_activity',
                        'verification': {'method': 'video'}
                    }
                ]
            },
            'admin': 123456789
        }
        
        with open(self.test_config_file, 'w') as f:
            yaml.dump(config, f)
        
        bot = AmazingRaceBot(self.test_config_file)
        bot.game_state.state_file = self.test_state_file
        
        # Create team and start game
        bot.game_state.create_team("TestTeam", 111, "User1")
        bot.game_state.start_game()
        
        # Complete first challenge to reach team_activity
        bot.game_state.complete_challenge("TestTeam", 1, 2, None, False)
        
        # Mock update and context
        update = MagicMock(spec=Update)
        update.effective_user = User(id=111, first_name="User1", is_bot=False)
        update.effective_chat = MagicMock()
        update.effective_chat.id = 111
        update.message = MagicMock(spec=Message)
        update.message.reply_text = AsyncMock()
        
        context = MagicMock()
        context.bot = MagicMock()
        context.bot.send_message = AsyncMock()
        
        # Call current_challenge_command
        async def run_test():
            await bot.current_challenge_command(update, context)
            
            # Verify message was sent
            self.assertTrue(update.message.reply_text.called, "Message should be sent")
            
            # Get the message text
            call_args = update.message.reply_text.call_args
            message_text = call_args[0][0] if call_args[0] else call_args[1].get('text', '')
            
            # Verify message contains challenge info
            self.assertIn('Team Video', message_text)
            
            # Verify submit instructions are appropriate for video challenges
            self.assertIn('Use /submit to upload your video', message_text)
            # Should NOT say "[answer]" for video challenges
            self.assertNotIn('[answer]', message_text)
        
        asyncio.run(run_test())


if __name__ == '__main__':
    unittest.main()
