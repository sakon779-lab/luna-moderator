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

class TestNightActions(unittest.TestCase):
    
    def setUp(self):
        """เตรียมสถานะให้พร้อมก่อนทดสอบ (จำลองเริ่มเกม 7 คน เพื่อให้มี Bodyguard)"""
        self.engine = GameEngine(game_id="TEST_ACTION_001")
        for i in range(1, 8):
            self.engine.register_player(f"P0{i}", f"Player{i}", i)
            
        self.engine.start_game() # ตอนนี้เป็น NIGHT_1
        
        # คืนแรก: ระบุตัวตน
        self.engine.identify_players_for_role(["P01", "P02"], Role.WEREWOLF)
        self.engine.identify_players_for_role(["P03"], Role.SEER)
        self.engine.identify_players_for_role(["P04"], Role.BODYGUARD)
        self.engine.conclude_first_night_identification()
        # ตอนนี้ทุกคนมี Role แล้ว แต่ยังเป็น NIGHT_1 อยู่
        
        # เปลี่ยนให้เป็นกลางคืนที่ 2 เพื่อเริ่มใช้สกิล
        self.engine.next_phase()  # เปลี่ยนเป็น DAY 1
        self.engine.next_phase()  # เปลี่ยนเป็น NIGHT 2 (พร้อมเทสต์)

    def test_standard_kill_success(self):
        """Test Case 1: หมาป่ากัดชาวบ้าน (ไม่มีใครป้องกัน) -> ชาวบ้านต้องตาย"""
        # หมาป่ากัด P05
        self.engine.execute_night_action(Role.WEREWOLF, "P05")
        
        self.engine.resolve_night()
        
        self.assertFalse(self.engine.state.players["P05"].is_alive)
        self.assertEqual(self.engine.state.phase, GamePhase.DAY)

    def test_bodyguard_protect_success(self):
        """Test Case 2: บอดี้การ์ดคุ้มครองสำเร็จ -> เป้าหมายต้องรอดชีวิต"""
        # หมาป่ากัด P05
        self.engine.execute_night_action(Role.WEREWOLF, "P05")
        # บอดี้การ์ดคุ้มครอง P05
        self.engine.execute_night_action(Role.BODYGUARD, "P05")
        
        self.engine.resolve_night()
        
        # P05 ต้องรอดชีวิต
        self.assertTrue(self.engine.state.players["P05"].is_alive)
        # ตรวจสอบว่า Action State ถูกเคลียร์หลังจากจบเงื่อนไข
        self.assertIsNone(self.engine.state.night_actions.kill_target)

    def test_action_on_dead_player(self):
        """Test Case 3: ใช้สกิลใส่คนที่ตายไปแล้ว -> ต้อง Error"""
        # เสกให้ P05 ตายไปก่อน
        self.engine.state.players["P05"].is_alive = False
        
        # หมาป่าพยายามกัดศพ
        with self.assertRaises(ValueError) as context:
            self.engine.execute_night_action(Role.WEREWOLF, "P05")
            
        self.assertIn("ไม่สามารถเลือกคนที่ตายไปแล้วเป็นเป้าหมายได้", str(context.exception))

    def test_dead_role_cannot_act(self):
        """Test Case 4: บทบาทที่ตายไปแล้ว พยายามใช้สกิล -> ระบบต้องไม่บันทึกค่า"""
        # เสกให้ Bodyguard (P04) ตายไปก่อน
        self.engine.state.players["P04"].is_alive = False
        
        # สั่งให้ Bodyguard คุ้มครอง P05
        self.engine.execute_night_action(Role.BODYGUARD, "P05")
        
        # ตรวจสอบว่าระบบไม่บันทึกเป้าหมายการคุ้มครอง (เพราะตัวบอดี้การ์ดตายไปแล้ว)
        self.assertIsNone(self.engine.state.night_actions.protect_target)

    def test_seer_investigation(self):
        """Test Case 5: Seer ส่องหมาป่าและชาวบ้าน -> ต้องคืนค่าถูกฝ่าย"""
        # ส่อง P01 (หมาป่า)
        result_wolf = self.engine.execute_night_action(Role.SEER, "P01")
        self.assertEqual(result_wolf, "ฝ่ายร้าย")
        
        # ส่อง P05 (ชาวบ้าน)
        result_villager = self.engine.execute_night_action(Role.SEER, "P05")
        self.assertEqual(result_villager, "ฝ่ายดี")

if __name__ == '__main__':
    unittest.main()