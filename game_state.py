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
            'current_challenge_index': 0,
            'completed_challenges': [],
            'finish_time': None,
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
    
    def complete_challenge(self, team_name: str, challenge_id: int, total_challenges: int, 
                          submission_data: Optional[Dict] = None) -> bool:
        """Mark a challenge as completed for a team. Challenges must be completed sequentially.
        
        Args:
            team_name: Name of the team
            challenge_id: ID of the challenge to complete
            total_challenges: Total number of challenges in the game
            submission_data: Optional data about the submission (e.g., answer, photo_id, timestamp)
        
        Returns:
            True if challenge was successfully completed, False otherwise
        """
        if team_name not in self.teams:
            return False
        
        if challenge_id in self.teams[team_name]['completed_challenges']:
            return False
        
        # Get the current challenge index (0-based)
        current_index = self.teams[team_name]['current_challenge_index']
        
        # Challenge IDs are 1-based, so expected challenge ID is current_index + 1
        expected_challenge_id = current_index + 1
        
        # Only allow completing the next sequential challenge
        if challenge_id != expected_challenge_id:
            return False
        
        self.teams[team_name]['completed_challenges'].append(challenge_id)
        self.teams[team_name]['current_challenge_index'] += 1
        
        # Store submission data if provided
        if submission_data:
            if 'challenge_submissions' not in self.teams[team_name]:
                self.teams[team_name]['challenge_submissions'] = {}
            self.teams[team_name]['challenge_submissions'][str(challenge_id)] = submission_data
        
        # Check if team finished all challenges
        if len(self.teams[team_name]['completed_challenges']) >= total_challenges:
            self.teams[team_name]['finish_time'] = datetime.now().isoformat()
        
        self.save_state()
        return True
    
    def get_team_by_user(self, user_id: int) -> Optional[str]:
        """Get the team name for a given user."""
        for team_name, team_data in self.teams.items():
            if any(member['id'] == user_id for member in team_data['members']):
                return team_name
        return None
    
    def get_leaderboard(self) -> List[tuple]:
        """Get sorted list of teams by progress and finish time."""
        # Sort by: finished teams first (by finish time), then by progress
        def sort_key(item):
            name, data = item
            finish_time = data.get('finish_time')
            num_completed = len(data['completed_challenges'])
            
            # Teams that finished: sort by finish time (earlier is better)
            if finish_time:
                return (0, finish_time)
            # Teams still racing: sort by number of completed challenges (more is better)
            else:
                return (1, -num_completed)
        
        sorted_teams = sorted(self.teams.items(), key=sort_key)
        
        return [(name, len(data['completed_challenges']), data.get('finish_time')) 
                for name, data in sorted_teams]
    
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
    
    def update_team(self, team_name: str, new_team_name: str = None, 
                    new_captain_id: int = None, new_captain_name: str = None) -> bool:
        """Update team information."""
        if team_name not in self.teams:
            return False
        
        team_data = self.teams[team_name]
        
        # Update captain if provided
        if new_captain_id is not None and new_captain_name is not None:
            # Update captain in members list
            for member in team_data['members']:
                if member['id'] == team_data['captain_id']:
                    break
            team_data['captain_id'] = new_captain_id
            team_data['captain_name'] = new_captain_name
        
        # Rename team if new name provided
        if new_team_name and new_team_name != team_name:
            if new_team_name in self.teams:
                return False  # New name already exists
            self.teams[new_team_name] = team_data
            del self.teams[team_name]
        
        self.save_state()
        return True
    
    def remove_team(self, team_name: str) -> bool:
        """Remove a team from the game."""
        if team_name not in self.teams:
            return False
        
        del self.teams[team_name]
        self.save_state()
        return True
    
    def add_member_to_team(self, team_name: str, user_id: int, user_name: str, max_team_size: int) -> bool:
        """Add a member to a team (admin function)."""
        if team_name not in self.teams:
            return False
        
        # Check if user is already in any team
        for team in self.teams.values():
            if any(member['id'] == user_id for member in team['members']):
                return False
        
        # Check team size limit
        if len(self.teams[team_name]['members']) >= max_team_size:
            return False
        
        self.teams[team_name]['members'].append({
            'id': user_id,
            'name': user_name
        })
        self.save_state()
        return True
    
    def remove_member_from_team(self, team_name: str, user_id: int) -> bool:
        """Remove a member from a team."""
        if team_name not in self.teams:
            return False
        
        team = self.teams[team_name]
        
        # Don't allow removing the captain if they're the only member
        if team['captain_id'] == user_id and len(team['members']) == 1:
            return False
        
        # Remove the member
        team['members'] = [m for m in team['members'] if m['id'] != user_id]
        
        # If captain was removed, assign new captain
        if team['captain_id'] == user_id and team['members']:
            team['captain_id'] = team['members'][0]['id']
            team['captain_name'] = team['members'][0]['name']
        
        self.save_state()
        return True
