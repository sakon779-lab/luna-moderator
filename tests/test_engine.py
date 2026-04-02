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

class TestNightIdentification(unittest.TestCase):
    
    def setUp(self):
        """เตรียมสถานะให้พร้อมก่อนทดสอบ (จำลองว่าเริ่มเกม 5 คนแล้ว)"""
        self.engine = GameEngine(game_id="TEST_NIGHT_001")
        for i in range(1, 6):
            self.engine.register_player(f"P0{i}", f"Player{i}", i)
            
        # กดเริ่มเกม เพื่อให้ Role ทุกคนเป็น UNASSIGNED และเข้าสู่ NIGHT_1
        self.engine.start_game()

    def test_identify_empty_array(self):
        """Edge Case 1: กล้องจับใครไม่ได้เลยส่งเป็น Array ว่าง []"""
        # ถ้าเรียกหมาป่า แล้วไม่มีคนลืมตา (คนลืมตา 0 คน)
        # ระบบต้องไม่พัง และโควต้าหมาป่า (Expected Roles) ต้องยังอยู่เท่าเดิม
        initial_expected_count = len(self.engine.expected_roles)
        
        self.engine.identify_players_for_role([], Role.WEREWOLF)
        
        # ตรวจสอบว่าโควต้าไม่ลดลง และทุกคนยังคงเป็น UNASSIGNED
        self.assertEqual(len(self.engine.expected_roles), initial_expected_count)
        self.assertIn(Role.WEREWOLF, self.engine.expected_roles)

    def test_identify_ghost_id(self):
        """Edge Case 2: กล้องส่ง ID ผี (ไม่มีใน LOBBY) มาให้"""
        with self.assertRaises(ValueError) as context:
            # P99 ไม่มีอยู่ในเกม
            self.engine.identify_players_for_role(["P99"], Role.WEREWOLF)
            
        self.assertIn("ไม่พบรหัสผู้เล่น", str(context.exception))

    def test_identify_over_quota(self):
        """Edge Case 3: กล้องส่งคนเกินโควต้า (เช่น Seer มี 1 แต่กล้องจับได้ 2)"""
        with self.assertRaises(ValueError) as context:
            # เกม 5 คน มี Seer แค่ 1 ตำแหน่ง แต่ส่งไป 2 ID
            self.engine.identify_players_for_role(["P01", "P02"], Role.SEER)
            
        self.assertIn("ครบตามจำนวนหรือไม่มีในเกม", str(context.exception))

    def test_identify_duplicate_role(self):
        """Edge Case 4: คนที่มีบทบาทแล้วแอบลืมตาซ้ำ (แถมให้)"""
        # ครั้งแรก P01 เป็นหมาป่า (ผ่านปกติ)
        self.engine.identify_players_for_role(["P01"], Role.WEREWOLF)
        self.assertEqual(self.engine.state.players["P01"].role, Role.WEREWOLF)
        
        # ครั้งที่สอง P01 แอบลืมตาตอนเรียก Seer (ต้องพัง)
        with self.assertRaises(ValueError) as context:
            self.engine.identify_players_for_role(["P01"], Role.SEER)
            
        self.assertIn("ถูกระบุบทบาทไปแล้ว", str(context.exception))

    def test_conclude_night_villagers(self):
        """Test Case: สรุปผลคืนแรก กวาดคนที่เหลือเป็นชาวบ้าน"""
        # ระบุหมาป่า 1, Seer 1
        self.engine.identify_players_for_role(["P02"], Role.WEREWOLF)
        self.engine.identify_players_for_role(["P04"], Role.SEER)
        
        # เรียกฟังก์ชันสรุปผล
        self.engine.conclude_first_night_identification()
        
        # ตรวจสอบคนที่เหลือ (P01, P03, P05) ต้องกลายเป็น Villager
        self.assertEqual(self.engine.state.players["P01"].role, Role.VILLAGER)
        self.assertEqual(self.engine.state.players["P03"].role, Role.VILLAGER)
        self.assertEqual(self.engine.state.players["P05"].role, Role.VILLAGER)

if __name__ == '__main__':
    unittest.main()