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
        self.photo_verification_enabled: bool = False
        self.hint_usage: Dict[str, Dict] = {}  # Track hint usage per team
        self.pending_photo_submissions: Dict[str, Dict] = {}  # Track pending photo submissions
        self.pending_photo_verifications: Dict[str, Dict] = {}  # Track pending photo verifications for location
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
                    self.photo_verification_enabled = data.get('photo_verification_enabled', False)
                    self.hint_usage = data.get('hint_usage', {})
                    self.pending_photo_submissions = data.get('pending_photo_submissions', {})
                    self.pending_photo_verifications = data.get('pending_photo_verifications', {})
            except Exception as e:
                print(f"Error loading state: {e}")
    
    def save_state(self):
        """Save game state to file."""
        try:
            data = {
                'teams': self.teams,
                'challenges': self.challenges,
                'game_started': self.game_started,
                'game_ended': self.game_ended,
                'photo_verification_enabled': self.photo_verification_enabled,
                'hint_usage': self.hint_usage,
                'pending_photo_submissions': self.pending_photo_submissions,
                'pending_photo_verifications': self.pending_photo_verifications
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
        
        # Record completion time for penalty tracking
        # When photo verification is enabled and this is not the last challenge,
        # defer setting completion time until photo verification for next challenge is approved
        next_challenge_id = challenge_id + 1
        should_defer = (self.photo_verification_enabled and 
                       next_challenge_id <= total_challenges)
        
        if not should_defer:
            # No photo verification OR last challenge - set completion time immediately
            self.set_challenge_completion_time(team_name, challenge_id)
        
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
        self.photo_verification_enabled = False
        self.hint_usage = {}
        self.pending_photo_submissions = {}
        self.pending_photo_verifications = {}
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
    
    def toggle_photo_verification(self) -> bool:
        """Toggle photo verification on/off.
        
        Returns:
            New state of photo verification (True if enabled, False if disabled)
        """
        self.photo_verification_enabled = not self.photo_verification_enabled
        self.save_state()
        return self.photo_verification_enabled
    
    def set_photo_verification(self, enabled: bool) -> None:
        """Set photo verification state.
        
        Args:
            enabled: True to enable, False to disable
        """
        self.photo_verification_enabled = enabled
        self.save_state()
    
    def add_pending_photo_verification(self, team_name: str, challenge_id: int, 
                                       photo_id: str, user_id: int, user_name: str) -> str:
        """Add a pending photo verification for location arrival.
        
        Args:
            team_name: Name of the team
            challenge_id: ID of the challenge they're arriving at
            photo_id: Telegram photo file ID
            user_id: ID of user who submitted
            user_name: Name of user who submitted
            
        Returns:
            Verification ID (unique identifier for this verification)
        """
        verification_id = f"{team_name}_{challenge_id}_{datetime.now().timestamp()}"
        
        self.pending_photo_verifications[verification_id] = {
            'team_name': team_name,
            'challenge_id': challenge_id,
            'photo_id': photo_id,
            'user_id': user_id,
            'user_name': user_name,
            'timestamp': datetime.now().isoformat(),
            'status': 'pending'
        }
        
        self.save_state()
        return verification_id
    
    def get_pending_photo_verifications(self) -> Dict[str, Dict]:
        """Get all pending photo verifications for location arrival.
        
        Returns:
            Dictionary of pending verifications
        """
        return {k: v for k, v in self.pending_photo_verifications.items() 
                if v.get('status') == 'pending'}
    
    def approve_photo_verification(self, verification_id: str) -> bool:
        """Approve a photo verification for location arrival.
        
        Args:
            verification_id: ID of the verification to approve
            
        Returns:
            True if successful, False otherwise
        """
        if verification_id not in self.pending_photo_verifications:
            return False
        
        verification = self.pending_photo_verifications[verification_id]
        team_name = verification['team_name']
        challenge_id = verification['challenge_id']
        
        # Store photo verification in team data
        if team_name not in self.teams:
            return False
        
        if 'photo_verifications' not in self.teams[team_name]:
            self.teams[team_name]['photo_verifications'] = {}
        
        self.teams[team_name]['photo_verifications'][str(challenge_id)] = {
            'verified_by': verification['user_id'],
            'user_name': verification['user_name'],
            'photo_id': verification['photo_id'],
            'timestamp': verification['timestamp'],
            'approved_at': datetime.now().isoformat()
        }
        
        # When photo verification is approved, set the completion time for the previous challenge
        # This ensures penalty timeout starts only after photo verification is complete
        previous_challenge_id = challenge_id - 1
        if previous_challenge_id >= 1:
            # Check if previous challenge was completed but completion time was not set
            if previous_challenge_id in self.teams[team_name]['completed_challenges']:
                completion_times = self.teams[team_name].get('challenge_completion_times', {})
                if str(previous_challenge_id) not in completion_times:
                    # Set completion time now (penalty timer starts from here)
                    self.set_challenge_completion_time(team_name, previous_challenge_id)
        
        # Mark verification as approved
        self.pending_photo_verifications[verification_id]['status'] = 'approved'
        self.save_state()
        return True
    
    def reject_photo_verification(self, verification_id: str) -> bool:
        """Reject a photo verification for location arrival.
        
        Args:
            verification_id: ID of the verification to reject
            
        Returns:
            True if successful, False otherwise
        """
        if verification_id not in self.pending_photo_verifications:
            return False
        
        # Mark verification as rejected
        self.pending_photo_verifications[verification_id]['status'] = 'rejected'
        self.save_state()
        return True
    
    def get_photo_verification_by_id(self, verification_id: str) -> Optional[Dict]:
        """Get a photo verification by its ID.
        
        Args:
            verification_id: ID of the verification
            
        Returns:
            Verification data or None if not found
        """
        return self.pending_photo_verifications.get(verification_id)

    
    def use_hint(self, team_name: str, challenge_id: int, hint_index: int, user_id: int, user_name: str) -> bool:
        """Record hint usage for a team's challenge.
        
        Args:
            team_name: Name of the team
            challenge_id: ID of the challenge
            hint_index: Index of the hint (0, 1, or 2)
            user_id: ID of the user requesting the hint
            user_name: Name of the user requesting the hint
            
        Returns:
            True if hint was recorded, False otherwise
        """
        if team_name not in self.teams:
            return False
        
        # Initialize hint_usage for team if not exists
        if team_name not in self.hint_usage:
            self.hint_usage[team_name] = {}
        
        # Initialize challenge hints if not exists
        challenge_key = str(challenge_id)
        if challenge_key not in self.hint_usage[team_name]:
            self.hint_usage[team_name][challenge_key] = []
        
        # Record the hint usage
        self.hint_usage[team_name][challenge_key].append({
            'hint_index': hint_index,
            'user_id': user_id,
            'user_name': user_name,
            'timestamp': datetime.now().isoformat()
        })
        
        self.save_state()
        return True
    
    def get_used_hints(self, team_name: str, challenge_id: int) -> List[Dict]:
        """Get list of hints used for a challenge.
        
        Args:
            team_name: Name of the team
            challenge_id: ID of the challenge
            
        Returns:
            List of hint usage records
        """
        if team_name not in self.hint_usage:
            return []
        
        challenge_key = str(challenge_id)
        return self.hint_usage.get(team_name, {}).get(challenge_key, [])
    
    def get_hint_count(self, team_name: str, challenge_id: int) -> int:
        """Get number of hints used for a challenge.
        
        Args:
            team_name: Name of the team
            challenge_id: ID of the challenge
            
        Returns:
            Number of hints used
        """
        return len(self.get_used_hints(team_name, challenge_id))
    
    def get_total_penalty_time(self, team_name: str, challenge_id: int) -> int:
        """Get total penalty time in seconds for hints used on a challenge.
        
        Args:
            team_name: Name of the team
            challenge_id: ID of the challenge
            
        Returns:
            Total penalty time in seconds (2 minutes per hint)
        """
        hint_count = self.get_hint_count(team_name, challenge_id)
        return hint_count * 120  # 2 minutes = 120 seconds per hint
    
    def set_challenge_completion_time(self, team_name: str, challenge_id: int) -> None:
        """Set the completion time for a challenge (used for penalty timing).
        
        Args:
            team_name: Name of the team
            challenge_id: ID of the challenge
        """
        if team_name not in self.teams:
            return
        
        if 'challenge_completion_times' not in self.teams[team_name]:
            self.teams[team_name]['challenge_completion_times'] = {}
        
        self.teams[team_name]['challenge_completion_times'][str(challenge_id)] = datetime.now().isoformat()
        self.save_state()
    
    def get_challenge_unlock_time(self, team_name: str, challenge_id: int) -> Optional[str]:
        """Get the time when a challenge will be unlocked (after penalty).
        
        Args:
            team_name: Name of the team
            challenge_id: ID of the challenge (the one being unlocked)
            
        Returns:
            ISO format timestamp when challenge unlocks, or None if no penalty
        """
        if team_name not in self.teams:
            return None
        
        # Get the previous challenge ID
        previous_challenge_id = challenge_id - 1
        if previous_challenge_id < 1:
            return None
        
        # Get completion time of previous challenge
        completion_times = self.teams[team_name].get('challenge_completion_times', {})
        completion_time_str = completion_times.get(str(previous_challenge_id))
        
        if not completion_time_str:
            return None
        
        # Get penalty time for previous challenge
        penalty_seconds = self.get_total_penalty_time(team_name, previous_challenge_id)
        
        if penalty_seconds == 0:
            return None
        
        # Calculate unlock time
        from datetime import datetime, timedelta
        completion_time = datetime.fromisoformat(completion_time_str)
        unlock_time = completion_time + timedelta(seconds=penalty_seconds)
        
        return unlock_time.isoformat()
    
    def add_pending_photo_submission(self, team_name: str, challenge_id: int, 
                                     photo_id: str, user_id: int, user_name: str) -> str:
        """Add a pending photo submission.
        
        Args:
            team_name: Name of the team
            challenge_id: ID of the challenge
            photo_id: Telegram photo file ID
            user_id: ID of user who submitted
            user_name: Name of user who submitted
            
        Returns:
            Submission ID (unique identifier for this submission)
        """
        submission_id = f"{team_name}_{challenge_id}_{datetime.now().timestamp()}"
        
        self.pending_photo_submissions[submission_id] = {
            'team_name': team_name,
            'challenge_id': challenge_id,
            'photo_id': photo_id,
            'user_id': user_id,
            'user_name': user_name,
            'timestamp': datetime.now().isoformat(),
            'status': 'pending'
        }
        
        self.save_state()
        return submission_id
    
    def get_pending_photo_submissions(self) -> Dict[str, Dict]:
        """Get all pending photo submissions.
        
        Returns:
            Dictionary of pending submissions
        """
        return {k: v for k, v in self.pending_photo_submissions.items() 
                if v.get('status') == 'pending'}
    
    def approve_photo_submission(self, submission_id: str, total_challenges: int) -> bool:
        """Approve a photo submission and complete the challenge.
        
        Args:
            submission_id: ID of the submission to approve
            total_challenges: Total number of challenges in the game
            
        Returns:
            True if successful, False otherwise
        """
        if submission_id not in self.pending_photo_submissions:
            return False
        
        submission = self.pending_photo_submissions[submission_id]
        team_name = submission['team_name']
        challenge_id = submission['challenge_id']
        
        # Complete the challenge
        submission_data = {
            'type': 'photo',
            'photo_id': submission['photo_id'],
            'timestamp': submission['timestamp'],
            'submitted_by': submission['user_id'],
            'user_name': submission['user_name'],
            'team_name': team_name,
            'status': 'approved'
        }
        
        if self.complete_challenge(team_name, challenge_id, total_challenges, submission_data):
            # Mark submission as approved
            self.pending_photo_submissions[submission_id]['status'] = 'approved'
            self.save_state()
            return True
        
        return False
    
    def reject_photo_submission(self, submission_id: str) -> bool:
        """Reject a photo submission.
        
        Args:
            submission_id: ID of the submission to reject
            
        Returns:
            True if successful, False otherwise
        """
        if submission_id not in self.pending_photo_submissions:
            return False
        
        # Mark submission as rejected
        self.pending_photo_submissions[submission_id]['status'] = 'rejected'
        self.save_state()
        return True
    
    def get_submission_by_id(self, submission_id: str) -> Optional[Dict]:
        """Get a submission by its ID.
        
        Args:
            submission_id: ID of the submission
            
        Returns:
            Submission data or None if not found
        """
        return self.pending_photo_submissions.get(submission_id)
    
    def get_checklist_progress(self, team_name: str, challenge_id: int) -> Dict[str, bool]:
        """Get checklist progress for a team's challenge.
        
        Args:
            team_name: Name of the team
            challenge_id: ID of the challenge
            
        Returns:
            Dictionary mapping checklist items to completion status
        """
        if team_name not in self.teams:
            return {}
        
        team_data = self.teams[team_name]
        checklist_progress = team_data.get('checklist_progress', {})
        return checklist_progress.get(str(challenge_id), {})
    
    def update_checklist_item(self, team_name: str, challenge_id: int, item: str, completed: bool = True) -> bool:
        """Update completion status of a checklist item.
        
        Args:
            team_name: Name of the team
            challenge_id: ID of the challenge
            item: The checklist item text
            completed: Whether the item is completed
            
        Returns:
            True if successful, False otherwise
        """
        if team_name not in self.teams:
            return False
        
        team_data = self.teams[team_name]
        
        # Initialize checklist_progress if it doesn't exist
        if 'checklist_progress' not in team_data:
            team_data['checklist_progress'] = {}
        
        challenge_key = str(challenge_id)
        if challenge_key not in team_data['checklist_progress']:
            team_data['checklist_progress'][challenge_key] = {}
        
        # Update the item status
        team_data['checklist_progress'][challenge_key][item] = completed
        self.save_state()
        return True
    
    def is_checklist_complete(self, team_name: str, challenge_id: int, checklist_items: List[str]) -> bool:
        """Check if all checklist items are completed.
        
        Args:
            team_name: Name of the team
            challenge_id: ID of the challenge
            checklist_items: List of all checklist items
            
        Returns:
            True if all items are completed, False otherwise
        """
        if team_name not in self.teams:
            return False
        
        progress = self.get_checklist_progress(team_name, challenge_id)
        
        # Check if all items are marked as completed
        for item in checklist_items:
            if not progress.get(item, False):
                return False
        
        return True

