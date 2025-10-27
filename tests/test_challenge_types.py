"""
Unit tests for challenge types functionality.
"""
import unittest
import os
import json
import yaml
from datetime import datetime
from game_state import GameState


class MockBot:
    """Mock bot for testing challenge type methods.
    
    Note: This mock intentionally duplicates the verification logic from bot.py
    to ensure tests remain isolated and don't depend on the full bot implementation.
    The logic should be kept in sync with bot.py's verify_answer method.
    """
    
    def __init__(self, challenges):
        self.challenges = challenges
    
    def get_challenge_type_emoji(self, challenge_type: str) -> str:
        """Get emoji representation for challenge type."""
        type_emojis = {
            'photo': '📷',
            'riddle': '🧩',
            'code': '💻',
            'multi_choice': '❓',
            'location': '📍',
            'text': '📝',
            'scavenger': '🔍',
            'team_activity': '🤝',
            'decryption': '🔐',
            'tournament': '🏆'
        }
        return type_emojis.get(challenge_type, '🎯')
    
    def verify_answer(self, challenge: dict, user_answer: str) -> bool:
        """Verify a text answer for a challenge."""
        verification = challenge.get('verification', {})
        if verification.get('method') != 'answer':
            return False
        
        user_answer = user_answer.lower().strip()
        
        # Check if there's a list of acceptable answers (for code challenges and alternatives)
        acceptable_answers = verification.get('acceptable_answers')
        if acceptable_answers:
            # For code challenges: accept any one of the acceptable answers
            for acceptable in acceptable_answers:
                acceptable_lower = acceptable.lower().strip()
                if acceptable_lower == user_answer or acceptable_lower in user_answer:
                    return True
            # None matched
            return False
        
        expected_answer = verification.get('answer', '').lower().strip()
        
        # Check if the expected answer is a comma-separated list (for multi_choice)
        if ',' in expected_answer:
            # For multi_choice with multiple answers, check if user answer contains all required keywords
            required_keywords = [kw.strip() for kw in expected_answer.split(',')]
            return all(keyword in user_answer for keyword in required_keywords)
        else:
            # For single answer, check exact match or if expected answer is in user answer
            return expected_answer == user_answer or expected_answer in user_answer
    
    def get_challenge_instructions(self, challenge: dict, team_name: str = None) -> str:
        """Get submission instructions based on challenge type."""
        verification = challenge.get('verification', {})
        method = verification.get('method', 'photo')
        
        if method == 'photo':
            photos_required = verification.get('photos_required', 1)
            if photos_required > 1:
                return f"📷 Submit {photos_required} photos to complete this challenge."
            else:
                return "📷 Submit a photo to complete this challenge."
        elif method == 'answer':
            challenge_type = challenge.get('type', 'text')
            if challenge_type == 'riddle':
                return "💡 Reply with your answer to this riddle."
            elif challenge_type == 'code':
                return "💻 Reply with your code solution or the result."
            elif challenge_type == 'multi_choice':
                return "📝 Reply with your answer."
            elif challenge_type == 'decryption':
                return "🔓 Reply with the decrypted message."
            else:
                return "📝 Reply with your answer."
        elif method == 'location':
            return "📍 You need to be at the correct location."
        elif method == 'auto':
            return "✅ This challenge is auto-verified."
        elif method == 'tournament':
            return "🏆 Admin will report tournament results."
        else:
            return "📝 Submit your response to complete this challenge."


class TestChallengeTypes(unittest.TestCase):
    """Test cases for challenge types system."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create test challenges
        self.test_challenges = [
            {
                'id': 1,
                'name': 'Photo Challenge',
                'description': 'Take a team photo',
                'location': 'Park',
                'type': 'photo',
                'verification': {
                    'method': 'photo'
                }
            },
            {
                'id': 2,
                'name': 'Riddle Challenge',
                'description': 'What has keys but no locks?',
                'location': 'Library',
                'type': 'riddle',
                'verification': {
                    'method': 'answer',
                    'answer': 'keyboard'
                }
            },
            {
                'id': 3,
                'name': 'Multi Choice Challenge',
                'description': 'Name three programming languages',
                'location': 'Anywhere',
                'type': 'multi_choice',
                'verification': {
                    'method': 'answer',
                    'answer': 'python, java, javascript'
                }
            }
        ]
        
        self.bot = MockBot(self.test_challenges)
        self.game_state = GameState("test_challenge_types.json")
        self.game_state.reset_game()
    
    def tearDown(self):
        """Clean up test files."""
        if os.path.exists(self.game_state.state_file):
            os.remove(self.game_state.state_file)
    
    def test_get_challenge_type_emoji(self):
        """Test that challenge types have correct emojis."""
        self.assertEqual(self.bot.get_challenge_type_emoji('photo'), '📷')
        self.assertEqual(self.bot.get_challenge_type_emoji('riddle'), '🧩')
        self.assertEqual(self.bot.get_challenge_type_emoji('code'), '💻')
        self.assertEqual(self.bot.get_challenge_type_emoji('multi_choice'), '❓')
        self.assertEqual(self.bot.get_challenge_type_emoji('tournament'), '🏆')
        self.assertEqual(self.bot.get_challenge_type_emoji('unknown'), '🎯')
    
    def test_verify_answer_exact_match(self):
        """Test exact answer verification."""
        challenge = {
            'verification': {
                'method': 'answer',
                'answer': 'keyboard'
            }
        }
        self.assertTrue(self.bot.verify_answer(challenge, 'keyboard'))
        self.assertTrue(self.bot.verify_answer(challenge, 'KEYBOARD'))
        self.assertTrue(self.bot.verify_answer(challenge, '  keyboard  '))
        self.assertFalse(self.bot.verify_answer(challenge, 'mouse'))
    
    def test_verify_answer_partial_match(self):
        """Test partial answer verification."""
        challenge = {
            'verification': {
                'method': 'answer',
                'answer': 'keyboard'
            }
        }
        # Should accept if answer contains the keyword
        self.assertTrue(self.bot.verify_answer(challenge, 'the answer is keyboard'))
    
    def test_verify_answer_multi_choice_multiple(self):
        """Test multi_choice with multiple required keywords."""
        challenge = {
            'verification': {
                'method': 'answer',
                'answer': 'python, java, javascript'
            }
        }
        # All keywords present
        self.assertTrue(self.bot.verify_answer(challenge, 'python, java, javascript'))
        self.assertTrue(self.bot.verify_answer(challenge, 'I know python and java and javascript'))
        
        # Missing keywords
        self.assertFalse(self.bot.verify_answer(challenge, 'python and java'))
        self.assertFalse(self.bot.verify_answer(challenge, 'ruby and python'))
    
    def test_verify_answer_wrong_method(self):
        """Test that verification fails for wrong method."""
        challenge = {
            'verification': {
                'method': 'photo'
            }
        }
        self.assertFalse(self.bot.verify_answer(challenge, 'any answer'))
    
    def test_get_challenge_instructions_photo(self):
        """Test instructions for photo challenges."""
        challenge = {
            'type': 'photo',
            'verification': {'method': 'photo'}
        }
        instructions = self.bot.get_challenge_instructions(challenge)
        self.assertIn('photo', instructions.lower())
    
    def test_get_challenge_instructions_photo_multiple(self):
        """Test instructions for photo challenges with multiple photos required."""
        challenge = {
            'type': 'scavenger',
            'verification': {
                'method': 'photo',
                'photos_required': 5
            }
        }
        instructions = self.bot.get_challenge_instructions(challenge)
        self.assertIn('5 photos', instructions.lower())
    
    def test_get_challenge_instructions_riddle(self):
        """Test instructions for riddle challenges."""
        challenge = {
            'type': 'riddle',
            'verification': {'method': 'answer'}
        }
        instructions = self.bot.get_challenge_instructions(challenge)
        self.assertIn('answer', instructions.lower())
    
    def test_get_challenge_instructions_code(self):
        """Test instructions for code challenges."""
        challenge = {
            'type': 'code',
            'verification': {'method': 'answer'}
        }
        instructions = self.bot.get_challenge_instructions(challenge)
        self.assertIn('code', instructions.lower())
    
    def test_get_challenge_instructions_multi_choice(self):
        """Test instructions for multi_choice challenges."""
        challenge = {
            'type': 'multi_choice',
            'verification': {'method': 'answer'}
        }
        instructions = self.bot.get_challenge_instructions(challenge)
        self.assertIn('answer', instructions.lower())
    
    def test_complete_challenge_with_submission_data(self):
        """Test completing challenge with submission data."""
        self.game_state.create_team("Team A", 123, "Alice")
        
        submission_data = {
            'type': 'answer',
            'answer': 'keyboard',
            'timestamp': '2024-01-01T12:00:00'
        }
        
        result = self.game_state.complete_challenge("Team A", 1, 4, submission_data)
        self.assertTrue(result)
        
        # Check submission data was stored
        team = self.game_state.teams["Team A"]
        self.assertIn('challenge_submissions', team)
        self.assertIn('1', team['challenge_submissions'])
        self.assertEqual(team['challenge_submissions']['1']['answer'], 'keyboard')
    
    def test_complete_challenge_without_submission_data(self):
        """Test completing challenge without submission data (backward compatibility)."""
        self.game_state.create_team("Team A", 123, "Alice")
        
        result = self.game_state.complete_challenge("Team A", 1, 4)
        self.assertTrue(result)
        
        # Should still work without submission data
        team = self.game_state.teams["Team A"]
        self.assertEqual(len(team['completed_challenges']), 1)
    
    def test_challenge_types_in_config(self):
        """Test that challenges have types."""
        challenges = self.test_challenges
        
        self.assertEqual(len(challenges), 3)
        self.assertEqual(challenges[0]['type'], 'photo')
        self.assertEqual(challenges[1]['type'], 'riddle')
        self.assertEqual(challenges[2]['type'], 'multi_choice')
    
    def test_challenge_verification_config(self):
        """Test that verification config is structured correctly."""
        challenges = self.test_challenges
        
        # Photo challenge
        self.assertEqual(challenges[0]['verification']['method'], 'photo')
        
        # Riddle challenge
        self.assertEqual(challenges[1]['verification']['method'], 'answer')
        self.assertEqual(challenges[1]['verification']['answer'], 'keyboard')
        
        # Multi Choice challenge
        self.assertEqual(challenges[2]['verification']['method'], 'answer')
        self.assertEqual(challenges[2]['verification']['answer'], 'python, java, javascript')
    
    def test_submission_data_persistence(self):
        """Test that submission data is persisted correctly."""
        self.game_state.create_team("Team A", 123, "Alice")
        
        submission_data = {
            'type': 'photo',
            'photo_id': 'test_photo_123',
            'timestamp': datetime.now().isoformat()
        }
        
        self.game_state.complete_challenge("Team A", 1, 4, submission_data)
        self.game_state.save_state()
        
        # Load state in new instance
        new_game_state = GameState(self.game_state.state_file)
        team = new_game_state.teams["Team A"]
        
        self.assertIn('challenge_submissions', team)
        self.assertEqual(team['challenge_submissions']['1']['photo_id'], 'test_photo_123')
    
    def test_code_challenge_acceptable_answers(self):
        """Test code challenge with multiple acceptable answers."""
        challenge = {
            'type': 'code',
            'verification': {
                'method': 'answer',
                'acceptable_answers': ['5', 'five', 'answer is 5']
            }
        }
        
        # All acceptable answers should pass
        self.assertTrue(self.bot.verify_answer(challenge, '5'))
        self.assertTrue(self.bot.verify_answer(challenge, 'five'))
        self.assertTrue(self.bot.verify_answer(challenge, 'answer is 5'))
        self.assertTrue(self.bot.verify_answer(challenge, 'The answer is 5'))
        
        # Wrong answers should fail
        self.assertFalse(self.bot.verify_answer(challenge, '3'))
        self.assertFalse(self.bot.verify_answer(challenge, 'seven'))
    
    def test_code_challenge_acceptable_answers_case_insensitive(self):
        """Test that acceptable answers are case-insensitive."""
        challenge = {
            'type': 'code',
            'verification': {
                'method': 'answer',
                'acceptable_answers': ['fibonacci', 'Fibonacci sequence']
            }
        }
        
        # Case variations should work
        self.assertTrue(self.bot.verify_answer(challenge, 'fibonacci'))
        self.assertTrue(self.bot.verify_answer(challenge, 'FIBONACCI'))
        self.assertTrue(self.bot.verify_answer(challenge, 'Fibonacci'))
        self.assertTrue(self.bot.verify_answer(challenge, 'The fibonacci sequence'))
        self.assertTrue(self.bot.verify_answer(challenge, 'fibonacci SEQUENCE'))
    
    def test_code_challenge_exact_match_vs_partial(self):
        """Test exact match and partial match for code challenges."""
        challenge = {
            'type': 'code',
            'verification': {
                'method': 'answer',
                'acceptable_answers': ['42', 'def fibonacci']
            }
        }
        
        # Exact matches
        self.assertTrue(self.bot.verify_answer(challenge, '42'))
        self.assertTrue(self.bot.verify_answer(challenge, 'def fibonacci'))
        
        # Partial matches (answer contains acceptable answer)
        self.assertTrue(self.bot.verify_answer(challenge, 'The answer is 42'))
        self.assertTrue(self.bot.verify_answer(challenge, 'def fibonacci(n):'))
        
        # No match
        self.assertFalse(self.bot.verify_answer(challenge, '43'))
    
    def test_code_challenge_backward_compatibility(self):
        """Test that old code challenges with 'answer' still work."""
        challenge = {
            'type': 'code',
            'verification': {
                'method': 'answer',
                'answer': 'fibonacci'
            }
        }
        
        # Should still work with keyword matching
        self.assertTrue(self.bot.verify_answer(challenge, 'fibonacci'))
        self.assertTrue(self.bot.verify_answer(challenge, 'The fibonacci function'))
        self.assertFalse(self.bot.verify_answer(challenge, 'factorial'))


if __name__ == '__main__':
    unittest.main()
