"""
Game state management for the Amazing Race Telegram bot.
"""
import json
import os
from typing import Dict, List, Optional
from datetime import datetime


class GameState:
    """Manages the state of the Amazing Race game."""
    
    def __init__(self, state_file: str = "game_state.json"):
        self.state_file = state_file
        self.teams: Dict[str, Dict] = {}
        self.challenges: Dict[int, Dict] = {}
        self.game_started: bool = False
        self.game_ended: bool = False
        self.load_state()
    
    def load_state(self):
        """Load game state from file."""
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file, 'r') as f:
                    data = json.load(f)
                    self.teams = data.get('teams', {})
                    self.challenges = data.get('challenges', {})
                    self.game_started = data.get('game_started', False)
                    self.game_ended = data.get('game_ended', False)
            except Exception as e:
                print(f"Error loading state: {e}")
    
    def save_state(self):
        """Save game state to file."""
        try:
            data = {
                'teams': self.teams,
                'challenges': self.challenges,
                'game_started': self.game_started,
                'game_ended': self.game_ended
            }
            with open(self.state_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Error saving state: {e}")
    
    def create_team(self, team_name: str, captain_id: int, captain_name: str) -> bool:
        """Create a new team."""
        if team_name in self.teams:
            return False
        
        self.teams[team_name] = {
            'captain_id': captain_id,
            'captain_name': captain_name,
            'members': [{'id': captain_id, 'name': captain_name}],
            'score': 0,
            'completed_challenges': [],
            'created_at': datetime.now().isoformat()
        }
        self.save_state()
        return True
    
    def join_team(self, team_name: str, user_id: int, user_name: str) -> bool:
        """Add a user to a team."""
        if team_name not in self.teams:
            return False
        
        # Check if user is already in a team
        for team in self.teams.values():
            if any(member['id'] == user_id for member in team['members']):
                return False
        
        self.teams[team_name]['members'].append({
            'id': user_id,
            'name': user_name
        })
        self.save_state()
        return True
    
    def complete_challenge(self, team_name: str, challenge_id: int, points: int) -> bool:
        """Mark a challenge as completed for a team."""
        if team_name not in self.teams:
            return False
        
        if challenge_id in self.teams[team_name]['completed_challenges']:
            return False
        
        self.teams[team_name]['completed_challenges'].append(challenge_id)
        self.teams[team_name]['score'] += points
        self.save_state()
        return True
    
    def get_team_by_user(self, user_id: int) -> Optional[str]:
        """Get the team name for a given user."""
        for team_name, team_data in self.teams.items():
            if any(member['id'] == user_id for member in team_data['members']):
                return team_name
        return None
    
    def get_leaderboard(self) -> List[tuple]:
        """Get sorted list of teams by score."""
        sorted_teams = sorted(
            self.teams.items(),
            key=lambda x: x[1]['score'],
            reverse=True
        )
        return [(name, data['score']) for name, data in sorted_teams]
    
    def start_game(self):
        """Start the game."""
        self.game_started = True
        self.save_state()
    
    def end_game(self):
        """End the game."""
        self.game_ended = True
        self.save_state()
    
    def reset_game(self):
        """Reset the game state."""
        self.teams = {}
        self.challenges = {}
        self.game_started = False
        self.game_ended = False
        self.save_state()
