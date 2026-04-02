import unittest
from src.core.engine import GameEngine
from src.core.models import GamePhase, Role

class TestGameInitialization(unittest.TestCase):
    
    def setUp(self):
        """ฟังก์ชันนี้จะทำงานก่อนเริ่ม Test ทุกข้อ (ใช้ Reset State)"""
        self.engine = GameEngine(game_id="TEST_001")

    def test_start_game_not_enough_players(self):
        """Test Case 1: เริ่มเกมด้วยผู้เล่น 4 คน (ต้อง Fail)"""
        for i in range(1, 5):
            self.engine.register_player(f"P0{i}", f"Player{i}", i)
            
        with self.assertRaises(ValueError) as context:
            self.engine.start_game()
            
        self.assertIn("ไม่ตรงกับกติกา", str(context.exception))

    def test_start_game_success_5_players(self):
        """Test Case 2: เริ่มเกมด้วยผู้เล่น 5 คน (Role ทุกคนต้องเป็น Unassigned)"""
        for i in range(1, 6):
            self.engine.register_player(f"P0{i}", f"Player{i}", i)
            
        self.engine.start_game()
        
        # ตรวจสอบว่าเปลี่ยน Phase และ Turn ถูกต้อง
        self.assertEqual(self.engine.state.phase, GamePhase.NIGHT)
        self.assertEqual(self.engine.state.current_turn, 1)
        
        # ตรวจสอบว่าดึง Expected Roles มาครบ 5 บทบาท
        self.assertEqual(len(self.engine.expected_roles), 5)
        self.assertIn(Role.WEREWOLF, self.engine.expected_roles)
        self.assertIn(Role.SEER, self.engine.expected_roles)
        
        # ตรวจสอบว่าผู้เล่นทุกคนเป็น UNASSIGNED
        for player in self.engine.state.players.values():
            self.assertEqual(player.role, Role.UNASSIGNED)

    def test_start_game_twice_blocked(self):
        """Test Case 3: กด start_game() ซ้ำ 2 รอบ (รอบสองต้องโดน Block)"""
        for i in range(1, 6):
            self.engine.register_player(f"P0{i}", f"Player{i}", i)
            
        # กดครั้งที่ 1 (ต้องผ่าน)
        self.engine.start_game()
        
        # กดครั้งที่ 2 (ต้องพังและขึ้น Error)
        with self.assertRaises(ValueError) as context:
            self.engine.start_game()
            
        self.assertIn("เกมกำลังดำเนินอยู่", str(context.exception))

if __name__ == '__main__':
    unittest.main()