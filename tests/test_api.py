import unittest
import json
import requests
from src.core.models import Role

class TestAPIEndpoints(unittest.TestCase):
    """Test API endpoints according to DoD:  Identify -> Action -> Resolve"""
    
    def setUp(self):
        """Setup test game"""
        self.game_id = 'TEST_API_GAME'
        self.base_url = 'http://localhost:9000'
        
        # Clear existing game if any
        try:
            requests.delete(f'{self.base_url}/api/v1/{self.game_id}')
        except:
            pass
    
    def test_complete_game_flow(self):
        """Test Case: Complete game flow according to DoD"""
        
        print("\n=== 1. Register Players ===")
        players = [
            {'player_id': 'P01', 'name': 'Golf', 'seat_index': 1},
            {'player_id': 'P02', 'name': 'Bank', 'seat_index': 2},
            {'player_id': 'P03', 'name': 'Champ', 'seat_index': 3},
            {'player_id': 'P04', 'name': 'Dream', 'seat_index': 4},
            {'player_id': 'P05', 'name': 'Earn', 'seat_index': 5}
        ]
        
        for p in players:
            r = requests.post(f'{self.base_url}/api/v1/{self.game_id}/lobby/register', json=p)
            self.assertEqual(r.status_code, 200, f"Failed to register {p['player_id']}")
            response = r.json()
            self.assertEqual(response['status'], 'success')
            self.assertEqual(response['data']['game_id'], self.game_id)
            print(f"  Registered {p['player_id']}: OK")
        
        print("\n=== 2. Start Game ===")
        r = requests.post(f'{self.base_url}/api/v1/{self.game_id}/game/start')
        self.assertEqual(r.status_code, 200)
        response = r.json()
        self.assertEqual(response['status'], 'success')
        self.assertEqual(response['data']['game_id'], self.game_id)
        self.assertEqual(response['data']['phase'], 'Night')
        self.assertEqual(response['data']['current_turn'], 1)
        print("  Game started: OK")
        
        print("\n=== 3. Identify Werewolf (Night 1) ===")
        r = requests.post(f'{self.base_url}/api/v1/{self.game_id}/hardware/identify', 
                          json={'identified_role': 'Werewolf', 'player_ids': ['P01']})
        self.assertEqual(r.status_code, 200)
        response = r.json()
        self.assertEqual(response['status'], 'success')
        self.assertEqual(response['data']['identified_role'], 'Werewolf')
        self.assertEqual(response['data']['assigned_players'], ['P01'])
        self.assertIn('Seer', response['data']['pending_roles'])
        self.assertEqual(response['data']['game_id'], self.game_id)
        print("  Werewolf identified: OK")
        
        print("\n=== 4. Identify Seer (Night 1) ===")
        r = requests.post(f'{self.base_url}/api/v1/{self.game_id}/hardware/identify',
                          json={'identified_role': 'Seer', 'player_ids': ['P03']})
        self.assertEqual(r.status_code, 200)
        response = r.json()
        self.assertEqual(response['status'], 'success')
        self.assertEqual(response['data']['identified_role'], 'Seer')
        self.assertEqual(response['data']['assigned_players'], ['P03'])
        # After identifying all special roles, pending_roles should be empty or just Villager
        self.assertEqual(response['data']['game_id'], self.game_id)
        print("  Seer identified: OK")
        
        print("\n=== 5. Execute Werewolf Action ===")
        r = requests.post(f'{self.base_url}/api/v1/{self.game_id}/hardware/action',
                          json={'actor_role': 'Werewolf', 'target_id': 'P02'})
        self.assertEqual(r.status_code, 200)
        response = r.json()
        self.assertEqual(response['status'], 'success')
        self.assertEqual(response['data']['message'], 'Action recorded successfully.')
        self.assertEqual(response['data']['game_id'], self.game_id)
        print("  Werewolf action: OK")
        
        print("\n=== 6. Execute Seer Action (with investigation result) ===")
        r = requests.post(f'{self.base_url}/api/v1/{self.game_id}/hardware/action',
                          json={'actor_role': 'Seer', 'target_id': 'P01'})
        self.assertEqual(r.status_code, 200)
        response = r.json()
        self.assertEqual(response['status'], 'success')
        self.assertEqual(response['data']['message'], 'Action recorded successfully.')
        self.assertIn('investigation_result', response['data'])
        self.assertEqual(response['data']['investigation_result'], ' ')  # P01 is Werewolf
        self.assertEqual(response['data']['game_id'], self.game_id)
        print("  Seer action with investigation: OK")
        
        print("\n=== 7. Resolve Night (Transition to Day) ===")
        r = requests.post(f'{self.base_url}/api/v1/{self.game_id}/game/resolve-night')
        self.assertEqual(r.status_code, 200)
        response = r.json()
        self.assertEqual(response['status'], 'success')
        self.assertEqual(response['data']['new_phase'], 'Day')
        self.assertEqual(response['data']['current_turn'], 1)  # Still turn 1, just changed phase
        self.assertEqual(response['data']['game_id'], self.game_id)
        print("  Night resolved: OK")
        
        print("\n=== 8. Verify Final Game State ===")
        r = requests.get(f'{self.base_url}/api/v1/{self.game_id}/game/status')
        self.assertEqual(r.status_code, 200)
        response = r.json()
        self.assertEqual(response['status'], 'success')
        self.assertEqual(response['data']['game_id'], self.game_id)
        self.assertEqual(response['data']['phase'], 'Day')
        self.assertEqual(response['data']['current_turn'], 1)
        
        # Check that P02 is dead (killed by werewolf)
        players = {p['player_id']: p for p in response['data']['players']}
        self.assertFalse(players['P02']['is_alive'], 'P02 should be dead')
        self.assertTrue(players['P01']['is_alive'], 'P01 should be alive')
        self.assertTrue(players['P03']['is_alive'], 'P03 should be alive')
        
        print("  Final state verified: OK")
        print("\n=== DoD PASSED: API flow works correctly! ===")

    def test_error_handling(self):
        """Test API error handling"""
        
        print("\n=== Test Error: Identify outside Night 1 ===")
        # Start game first
        requests.post(f'{self.base_url}/api/v1/{self.game_id}/lobby/register', 
                     json={'player_id': 'P01', 'name': 'Test', 'seat_index': 1})
        requests.post(f'{self.base_url}/api/v1/{self.game_id}/game/start')
        
        # Try to identify without starting game properly
        r = requests.post(f'{self.base_url}/api/v1/INVALID_GAME/hardware/identify',
                          json={'identified_role': 'Werewolf', 'player_ids': ['P01']})
        # Should work (creates new game)
        self.assertEqual(r.status_code, 400)  # Should error because not in Night 1
        
        print("  Error handling: OK")

if __name__ == '__main__':
    unittest.main()
