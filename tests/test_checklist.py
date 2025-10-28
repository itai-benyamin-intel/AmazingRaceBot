"""
Unit tests for checklist functionality.

Tests that the bot correctly handles checklist challenges:
- Submit individual checklist items
- Track progress for each item
- Complete challenge when all items are submitted
- Display progress to users
"""
import unittest
import os
import yaml
from unittest.mock import AsyncMock, MagicMock, patch
from bot import AmazingRaceBot


class TestChecklistFeature(unittest.IsolatedAsyncioTestCase):
    """Test cases for checklist functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.test_config_file = "test_checklist_config.yml"
        self.config = {
            'telegram': {'bot_token': 'test_token'},
            'game': {
                'name': 'Test Game',
                'max_teams': 10,
                'max_team_size': 5,
                'challenges': [
                    {
                        'id': 1,
                        'name': 'Capital Cities',
                        'description': 'Name 5 capital cities',
                        'location': 'Anywhere',
                        'type': 'multi_choice',
                        'verification': {
                            'method': 'answer',
                            'checklist_items': [
                                'Tokyo',
                                'Paris',
                                'Cairo',
                                'Brasilia',
                                'Canberra'
                            ]
                        }
                    },
                    {
                        'id': 2,
                        'name': 'Regular Challenge',
                        'description': 'A normal answer challenge',
                        'location': 'Library',
                        'type': 'riddle',
                        'verification': {
                            'method': 'answer',
                            'answer': 'library'
                        }
                    }
                ]
            },
            'admin': 123456789
        }
        
        # Write config file
        with open(self.test_config_file, 'w') as f:
            yaml.dump(self.config, f)
    
    def tearDown(self):
        """Clean up test files."""
        if os.path.exists(self.test_config_file):
            os.remove(self.test_config_file)
        if os.path.exists("game_state.json"):
            os.remove("game_state.json")
    
    async def test_submit_single_checklist_item(self):
        """Test submitting a single checklist item."""
        bot = AmazingRaceBot(self.test_config_file)
        bot.game_state.start_game()
        bot.game_state.create_team("Team A", 111111, "Alice")
        
        # Mock update and context
        update = MagicMock()
        update.effective_user = MagicMock()
        update.effective_user.id = 111111
        update.effective_user.first_name = "Alice"
        update.message = MagicMock()
        update.message.reply_text = AsyncMock()
        
        context = MagicMock()
        context.args = ['Tokyo']
        context.user_data = {}
        context.bot_data = {}
        
        # Submit first item
        await bot.submit_command(update, context)
        
        # Check that partial completion message was sent
        call_args = update.message.reply_text.call_args[0][0]
        self.assertIn('Checklist Progress', call_args)
        self.assertIn('Tokyo', call_args)
        self.assertIn('1/5', call_args)
        
        # Verify progress is saved
        progress = bot.game_state.get_checklist_progress("Team A", 1)
        self.assertTrue(progress.get('Tokyo', False))
        self.assertFalse(progress.get('Paris', False))
    
    async def test_submit_multiple_checklist_items(self):
        """Test submitting multiple checklist items one by one."""
        bot = AmazingRaceBot(self.test_config_file)
        bot.game_state.start_game()
        bot.game_state.create_team("Team A", 111111, "Alice")
        
        update = MagicMock()
        update.effective_user = MagicMock()
        update.effective_user.id = 111111
        update.effective_user.first_name = "Alice"
        update.message = MagicMock()
        update.message.reply_text = AsyncMock()
        
        context = MagicMock()
        context.user_data = {}
        context.bot_data = {}
        
        # Submit items one by one
        items = ['Tokyo', 'Paris', 'Cairo']
        for item in items:
            context.args = [item]
            update.message.reply_text.reset_mock()
            await bot.submit_command(update, context)
        
        # Verify progress
        progress = bot.game_state.get_checklist_progress("Team A", 1)
        for item in items:
            self.assertTrue(progress.get(item, False))
        
        # Check last message shows 3/5 progress
        call_args = update.message.reply_text.call_args[0][0]
        self.assertIn('3/5', call_args)
    
    async def test_complete_checklist_challenge(self):
        """Test completing a checklist challenge by submitting all items."""
        bot = AmazingRaceBot(self.test_config_file)
        bot.game_state.start_game()
        bot.game_state.create_team("Team A", 111111, "Alice")
        
        update = MagicMock()
        update.effective_user = MagicMock()
        update.effective_user.id = 111111
        update.effective_user.first_name = "Alice"
        update.message = MagicMock()
        update.message.reply_text = AsyncMock()
        
        context = MagicMock()
        context.user_data = {}
        context.bot_data = {}
        context.bot = MagicMock()
        context.bot.send_message = AsyncMock()
        
        # Submit all items
        items = ['Tokyo', 'Paris', 'Cairo', 'Brasilia', 'Canberra']
        for item in items:
            context.args = [item]
            update.message.reply_text.reset_mock()
            await bot.submit_command(update, context)
        
        # Check that challenge was completed on last item
        call_args = update.message.reply_text.call_args[0][0]
        self.assertIn('Correct', call_args)
        self.assertIn('completed', call_args)
        
        # Verify challenge is marked as completed
        team = bot.game_state.teams["Team A"]
        self.assertIn(1, team['completed_challenges'])
        self.assertEqual(team['current_challenge_index'], 1)
    
    async def test_checklist_progress_display(self):
        """Test that checklist progress is displayed correctly."""
        bot = AmazingRaceBot(self.test_config_file)
        bot.game_state.start_game()
        bot.game_state.create_team("Team A", 111111, "Alice")
        
        # Submit some items
        bot.game_state.update_checklist_item("Team A", 1, "Tokyo")
        bot.game_state.update_checklist_item("Team A", 1, "Paris")
        
        update = MagicMock()
        update.effective_user = MagicMock()
        update.effective_user.id = 111111
        update.message = MagicMock()
        update.message.reply_text = AsyncMock()
        
        context = MagicMock()
        
        # Call current command
        await bot.current_challenge_command(update, context)
        
        # Check that only completed items are displayed (not incomplete ones)
        call_args = update.message.reply_text.call_args[0][0]
        self.assertIn('Completed Items', call_args)
        self.assertIn('Tokyo', call_args)
        self.assertIn('Paris', call_args)
        self.assertIn('2/5', call_args)
        self.assertIn('✅', call_args)  # Completed items
        # Incomplete items should NOT be shown
        self.assertNotIn('Cairo', call_args)
        self.assertNotIn('Brasilia', call_args)
        self.assertNotIn('Canberra', call_args)
        self.assertNotIn('⬜', call_args)  # No incomplete item markers
    
    async def test_non_matching_answer_shows_progress(self):
        """Test that submitting a non-matching answer shows current progress."""
        bot = AmazingRaceBot(self.test_config_file)
        bot.game_state.start_game()
        bot.game_state.create_team("Team A", 111111, "Alice")
        
        # Submit one valid item
        bot.game_state.update_checklist_item("Team A", 1, "Tokyo")
        
        update = MagicMock()
        update.effective_user = MagicMock()
        update.effective_user.id = 111111
        update.effective_user.first_name = "Alice"
        update.message = MagicMock()
        update.message.reply_text = AsyncMock()
        
        context = MagicMock()
        context.args = ['London']  # Not in checklist
        context.user_data = {}
        context.bot_data = {}
        
        await bot.submit_command(update, context)
        
        # Check that progress is shown with error
        call_args = update.message.reply_text.call_args[0][0]
        self.assertIn('No match', call_args)
        self.assertIn('1/5', call_args)
    
    async def test_case_insensitive_checklist_matching(self):
        """Test that checklist items are matched case-insensitively."""
        bot = AmazingRaceBot(self.test_config_file)
        bot.game_state.start_game()
        bot.game_state.create_team("Team A", 111111, "Alice")
        
        update = MagicMock()
        update.effective_user = MagicMock()
        update.effective_user.id = 111111
        update.effective_user.first_name = "Alice"
        update.message = MagicMock()
        update.message.reply_text = AsyncMock()
        
        context = MagicMock()
        context.user_data = {}
        context.bot_data = {}
        
        # Submit items with different casing
        context.args = ['tokyo']
        await bot.submit_command(update, context)
        
        # Verify item was matched
        progress = bot.game_state.get_checklist_progress("Team A", 1)
        self.assertTrue(progress.get('Tokyo', False))
        
        # Try uppercase
        update.message.reply_text.reset_mock()
        context.args = ['PARIS']
        await bot.submit_command(update, context)
        
        progress = bot.game_state.get_checklist_progress("Team A", 1)
        self.assertTrue(progress.get('Paris', False))
    
    async def test_duplicate_checklist_item_submission(self):
        """Test that submitting an already completed item shows progress."""
        bot = AmazingRaceBot(self.test_config_file)
        bot.game_state.start_game()
        bot.game_state.create_team("Team A", 111111, "Alice")
        
        update = MagicMock()
        update.effective_user = MagicMock()
        update.effective_user.id = 111111
        update.effective_user.first_name = "Alice"
        update.message = MagicMock()
        update.message.reply_text = AsyncMock()
        
        context = MagicMock()
        context.user_data = {}
        context.bot_data = {}
        
        # Submit Tokyo twice
        context.args = ['Tokyo']
        await bot.submit_command(update, context)
        
        update.message.reply_text.reset_mock()
        context.args = ['Tokyo']
        await bot.submit_command(update, context)
        
        # Should still show partial progress
        call_args = update.message.reply_text.call_args[0][0]
        self.assertIn('1/5', call_args)
    
    async def test_regular_challenge_still_works(self):
        """Test that regular (non-checklist) challenges still work correctly."""
        bot = AmazingRaceBot(self.test_config_file)
        bot.game_state.start_game()
        bot.game_state.set_photo_verification(False)  # Disable photo verification for this test
        bot.game_state.create_team("Team A", 111111, "Alice")
        
        # Complete first challenge (checklist)
        for item in ['Tokyo', 'Paris', 'Cairo', 'Brasilia', 'Canberra']:
            bot.game_state.update_checklist_item("Team A", 1, item)
        bot.game_state.complete_challenge("Team A", 1, 2)
        
        update = MagicMock()
        update.effective_user = MagicMock()
        update.effective_user.id = 111111
        update.effective_user.first_name = "Alice"
        update.message = MagicMock()
        update.message.reply_text = AsyncMock()
        
        context = MagicMock()
        context.args = ['library']
        context.user_data = {}
        context.bot_data = {}
        context.bot = MagicMock()
        context.bot.send_message = AsyncMock()
        
        # Submit answer to regular challenge
        await bot.submit_command(update, context)
        
        # Check completion
        call_args = update.message.reply_text.call_args[0][0]
        self.assertIn('Correct', call_args)
        
        team = bot.game_state.teams["Team A"]
        self.assertIn(2, team['completed_challenges'])
    
    async def test_checklist_with_partial_text_match(self):
        """Test that checklist items can be matched when included in longer text."""
        bot = AmazingRaceBot(self.test_config_file)
        bot.game_state.start_game()
        bot.game_state.create_team("Team A", 111111, "Alice")
        
        update = MagicMock()
        update.effective_user = MagicMock()
        update.effective_user.id = 111111
        update.effective_user.first_name = "Alice"
        update.message = MagicMock()
        update.message.reply_text = AsyncMock()
        
        context = MagicMock()
        context.user_data = {}
        context.bot_data = {}
        
        # Submit with extra text
        context.args = ['The', 'capital', 'is', 'Tokyo']
        await bot.submit_command(update, context)
        
        # Verify item was matched
        progress = bot.game_state.get_checklist_progress("Team A", 1)
        self.assertTrue(progress.get('Tokyo', False))


if __name__ == '__main__':
    unittest.main()
