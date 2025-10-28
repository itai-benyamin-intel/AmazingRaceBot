"""
Unit tests for multi_choice challenge bugs described in the issue.

Tests that:
1. /current command works for multi_choice challenges (returns a message)
2. After submitting a correct answer, the bot only reveals items that were answered correctly,
   not the entire checklist
"""
import unittest
import os
import yaml
from unittest.mock import AsyncMock, MagicMock
from bot import AmazingRaceBot


class TestMultiChoiceBugFix(unittest.IsolatedAsyncioTestCase):
    """Test cases for multi_choice challenge bug fixes."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.test_config_file = "test_multi_choice_bugs_config.yml"
        self.config = {
            'telegram': {'bot_token': 'test_token'},
            'game': {
                'name': 'Test Game',
                'max_teams': 10,
                'max_team_size': 5,
                'challenges': [
                    {
                        'id': 1,
                        'name': 'Capital Cities Quiz',
                        'description': 'Name capital cities',
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
                        'name': 'Second Challenge',
                        'description': 'Another challenge',
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
        
        with open(self.test_config_file, 'w') as f:
            yaml.dump(self.config, f)
    
    def tearDown(self):
        """Clean up test files."""
        if os.path.exists(self.test_config_file):
            os.remove(self.test_config_file)
        if os.path.exists("game_state.json"):
            os.remove("game_state.json")
    
    async def test_current_command_works_for_multi_choice(self):
        """
        Test that /current command works for multi_choice challenge.
        
        Issue: /current command does not work for multi_choice challenge 
        (does not return any message when /current is typed).
        
        Expected: /current should return challenge details for multi_choice challenges.
        """
        bot = AmazingRaceBot(self.test_config_file)
        bot.game_state.start_game()
        bot.game_state.create_team("Team A", 111111, "Alice")
        
        # Mock update and context
        update = MagicMock()
        update.effective_user = MagicMock()
        update.effective_user.id = 111111
        update.message = MagicMock()
        update.message.reply_text = AsyncMock()
        
        context = MagicMock()
        
        # Call /current
        await bot.current_challenge_command(update, context)
        
        # Verify a message was sent
        self.assertTrue(update.message.reply_text.called, 
                       "/current should return a message for multi_choice challenges")
        
        # Verify response contains challenge details
        call_args = update.message.reply_text.call_args[0][0]
        self.assertIn("Capital Cities Quiz", call_args, 
                     "Response should contain challenge name")
        self.assertIn("Name capital cities", call_args, 
                     "Response should contain challenge description")
        self.assertIn("multi_choice", call_args.lower(), 
                     "Response should indicate challenge type")
        
        # Verify response does NOT show uncompleted checklist items
        self.assertNotIn("Tokyo", call_args, 
                        "Uncompleted items should not be revealed")
        self.assertNotIn("Paris", call_args, 
                        "Uncompleted items should not be revealed")
        self.assertNotIn("⬜", call_args, 
                        "Uncompleted item markers should not be shown")
    
    async def test_submit_reveals_only_answered_items(self):
        """
        Test that after submitting a correct answer, bot only reveals items 
        that were answered correctly, not the entire checklist.
        
        Issue: After submitting a correct answer the bot replies with the entire 
        checklist (including the answers). It should only reveal the items that 
        were answered correctly.
        
        Expected: Only completed items should be shown, not all checklist items.
        """
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
        context.user_data = {}
        context.bot_data = {}
        
        # Submit first item: Tokyo
        context.args = ['Tokyo']
        await bot.submit_command(update, context)
        
        # Get the response message
        call_args = update.message.reply_text.call_args[0][0]
        
        # Verify Tokyo is shown (the item we submitted)
        self.assertIn('Tokyo', call_args, 
                     "Submitted item should be revealed")
        self.assertIn('✅', call_args, 
                     "Completed items should be marked")
        
        # Verify other items are NOT revealed
        self.assertNotIn('Paris', call_args, 
                        "Unanswered items should NOT be revealed")
        self.assertNotIn('Cairo', call_args, 
                        "Unanswered items should NOT be revealed")
        self.assertNotIn('Brasilia', call_args, 
                        "Unanswered items should NOT be revealed")
        self.assertNotIn('Canberra', call_args, 
                        "Unanswered items should NOT be revealed")
        self.assertNotIn('⬜', call_args, 
                        "Uncompleted item markers should NOT be shown")
        
        # Verify progress shows 1/5
        self.assertIn('1/5', call_args, 
                     "Progress should show 1 out of 5 completed")
        
        # Submit second item: Paris
        update.message.reply_text.reset_mock()
        context.args = ['Paris']
        await bot.submit_command(update, context)
        
        # Get the response message
        call_args = update.message.reply_text.call_args[0][0]
        
        # Verify both Tokyo and Paris are shown now
        self.assertIn('Tokyo', call_args, 
                     "Previously submitted items should still be shown")
        self.assertIn('Paris', call_args, 
                     "Newly submitted item should be shown")
        
        # Verify other items are still NOT revealed
        self.assertNotIn('Cairo', call_args, 
                        "Unanswered items should NOT be revealed")
        self.assertNotIn('Brasilia', call_args, 
                        "Unanswered items should NOT be revealed")
        self.assertNotIn('Canberra', call_args, 
                        "Unanswered items should NOT be revealed")
        self.assertNotIn('⬜', call_args, 
                        "Uncompleted item markers should NOT be shown")
        
        # Verify progress shows 2/5
        self.assertIn('2/5', call_args, 
                     "Progress should show 2 out of 5 completed")
    
    async def test_wrong_answer_does_not_reveal_items(self):
        """
        Test that submitting a wrong answer doesn't reveal any checklist items.
        """
        bot = AmazingRaceBot(self.test_config_file)
        bot.game_state.start_game()
        bot.game_state.create_team("Team A", 111111, "Alice")
        
        # Submit one correct item first
        bot.game_state.update_checklist_item("Team A", 1, "Tokyo")
        
        # Mock update and context
        update = MagicMock()
        update.effective_user = MagicMock()
        update.effective_user.id = 111111
        update.effective_user.first_name = "Alice"
        update.message = MagicMock()
        update.message.reply_text = AsyncMock()
        
        context = MagicMock()
        context.user_data = {}
        context.bot_data = {}
        
        # Submit wrong answer
        context.args = ['London']  # Not in the checklist
        await bot.submit_command(update, context)
        
        # Get the response message
        call_args = update.message.reply_text.call_args[0][0]
        
        # Verify only Tokyo is shown (previously completed)
        self.assertIn('Tokyo', call_args, 
                     "Previously completed items should be shown")
        
        # Verify other items are NOT revealed
        self.assertNotIn('Paris', call_args, 
                        "Unanswered items should NOT be revealed")
        self.assertNotIn('Cairo', call_args, 
                        "Unanswered items should NOT be revealed")
        self.assertNotIn('⬜', call_args, 
                        "Uncompleted item markers should NOT be shown")
        
        # Verify error message
        self.assertIn('No match', call_args, 
                     "Should show error message for wrong answer")
        
        # Verify progress still shows 1/5
        self.assertIn('1/5', call_args, 
                     "Progress should still be 1 out of 5")
    
    async def test_current_after_partial_completion(self):
        """
        Test that /current command only shows completed items after partial progress.
        """
        bot = AmazingRaceBot(self.test_config_file)
        bot.game_state.start_game()
        bot.game_state.create_team("Team A", 111111, "Alice")
        
        # Submit some items
        bot.game_state.update_checklist_item("Team A", 1, "Tokyo")
        bot.game_state.update_checklist_item("Team A", 1, "Cairo")
        
        # Mock update and context
        update = MagicMock()
        update.effective_user = MagicMock()
        update.effective_user.id = 111111
        update.message = MagicMock()
        update.message.reply_text = AsyncMock()
        
        context = MagicMock()
        
        # Call /current
        await bot.current_challenge_command(update, context)
        
        # Get the response message
        call_args = update.message.reply_text.call_args[0][0]
        
        # Verify only completed items are shown
        self.assertIn('Tokyo', call_args, 
                     "Completed items should be shown")
        self.assertIn('Cairo', call_args, 
                     "Completed items should be shown")
        
        # Verify uncompleted items are NOT shown
        self.assertNotIn('Paris', call_args, 
                        "Uncompleted items should NOT be shown")
        self.assertNotIn('Brasilia', call_args, 
                        "Uncompleted items should NOT be shown")
        self.assertNotIn('Canberra', call_args, 
                        "Uncompleted items should NOT be shown")
        self.assertNotIn('⬜', call_args, 
                        "Uncompleted item markers should NOT be shown")
        
        # Verify progress
        self.assertIn('2/5', call_args, 
                     "Progress should show 2 out of 5")


if __name__ == '__main__':
    unittest.main()

