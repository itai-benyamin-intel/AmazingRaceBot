"""
Integration test to verify bot initialization with hints feature.
This test checks that the bot can be initialized with hints in the config.
"""
import os
import yaml
import sys


def test_bot_initialization_with_hints():
    """Test that bot initializes correctly with hints in config."""
    
    # Create a temporary test config with hints
    test_config = {
        'telegram': {'bot_token': 'test_token_12345'},
        'game': {
            'name': 'Test Game',
            'max_teams': 10,
            'max_team_size': 5,
            'location_verification_enabled': False,
            'challenges': [
                {
                    'id': 1,
                    'name': 'Test Challenge 1',
                    'description': 'Test description',
                    'location': 'Test location',
                    'type': 'riddle',
                    'verification': {'method': 'answer', 'answer': 'test'},
                    'hints': [
                        'Hint 1 for challenge 1',
                        'Hint 2 for challenge 1'
                    ]
                },
                {
                    'id': 2,
                    'name': 'Test Challenge 2',
                    'description': 'Test description 2',
                    'location': 'Test location 2',
                    'type': 'photo',
                    'verification': {'method': 'photo'},
                    'hints': [
                        'Hint 1 for challenge 2',
                        'Hint 2 for challenge 2',
                        'Hint 3 for challenge 2'
                    ]
                },
                {
                    'id': 3,
                    'name': 'Test Challenge 3 (no hints)',
                    'description': 'Test description 3',
                    'location': 'Test location 3',
                    'type': 'trivia',
                    'verification': {'method': 'answer', 'answer': 'test'}
                    # No hints field - should work fine
                }
            ]
        },
        'admin': 123456789
    }
    
    test_config_file = 'test_integration_config.yml'
    test_state_file = 'test_integration_game_state.json'
    
    try:
        # Write test config
        with open(test_config_file, 'w') as f:
            yaml.dump(test_config, f)
        
        # Import bot module
        from bot import AmazingRaceBot
        
        # Initialize bot
        bot = AmazingRaceBot(test_config_file)
        
        # Verify bot initialized correctly
        assert bot.config['game']['name'] == 'Test Game'
        assert len(bot.challenges) == 3
        
        # Verify hints are loaded correctly
        assert 'hints' in bot.challenges[0]
        assert len(bot.challenges[0]['hints']) == 2
        assert bot.challenges[0]['hints'][0] == 'Hint 1 for challenge 1'
        
        assert 'hints' in bot.challenges[1]
        assert len(bot.challenges[1]['hints']) == 3
        
        # Challenge 3 has no hints
        assert bot.challenges[2].get('hints', []) == []
        
        # Verify game state has hint tracking
        assert hasattr(bot.game_state, 'hint_usage')
        assert isinstance(bot.game_state.hint_usage, dict)
        
        print("✅ All integration tests passed!")
        print(f"   - Bot initialized successfully")
        print(f"   - Loaded {len(bot.challenges)} challenges")
        print(f"   - Challenge 1: {len(bot.challenges[0]['hints'])} hints")
        print(f"   - Challenge 2: {len(bot.challenges[1]['hints'])} hints")
        print(f"   - Challenge 3: {len(bot.challenges[2].get('hints', []))} hints")
        print(f"   - Hint tracking initialized: {len(bot.game_state.hint_usage)} teams")
        
        return True
        
    except Exception as e:
        print(f"❌ Integration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        # Cleanup
        if os.path.exists(test_config_file):
            os.remove(test_config_file)
        if os.path.exists(test_state_file):
            os.remove(test_state_file)


if __name__ == '__main__':
    success = test_bot_initialization_with_hints()
    sys.exit(0 if success else 1)
