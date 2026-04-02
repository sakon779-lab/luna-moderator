import random
from src.core.models import GameState, Player, Role, GamePhase, NightActionState

# ==========================================
# Sub-task 2: Role Configuration & Balancing Matrix
# กำหนดสัดส่วนของบทบาทตามจำนวนผู้เล่น
# ==========================================
ROLE_MATRIX = {
    5: [Role.WEREWOLF, Role.SEER, Role.VILLAGER, Role.VILLAGER, Role.VILLAGER],
    6: [Role.WEREWOLF, Role.WEREWOLF, Role.SEER, Role.VILLAGER, Role.VILLAGER, Role.VILLAGER],
    7: [Role.WEREWOLF, Role.WEREWOLF, Role.SEER, Role.BODYGUARD, Role.VILLAGER, Role.VILLAGER, Role.VILLAGER],
}

class GameEngine:
    def __init__(self, game_id: str):
        self.state = GameState(game_id=game_id)

    def register_player(self, player_id: str, name: str, seat_index: int):
        """ฟังก์ชันสำหรับรับผู้เล่นเข้า Lobby"""
        if self.state.phase != GamePhase.LOBBY:
            raise ValueError("❌ ไม่สามารถเพิ่มผู้เล่นได้ เนื่องจากเกมเริ่มไปแล้ว")
        if player_id in self.state.players:
            raise ValueError(f"❌ ผู้เล่นรหัส {player_id} อยู่ในห้องแล้ว")
        
        # ตรวจสอบว่าที่นั่งนี้ถูกใช้ไปแล้วหรือไม่
        existing_seats = [p.seat_index for p in self.state.players.values()]
        if seat_index in existing_seats:
            raise ValueError(f"❌ ที่นั่ง {seat_index} ถูกใช้ไปแล้ว")
        
        new_player = Player(player_id=player_id, name=name, seat_index=seat_index)
        self.state.players[player_id] = new_player
        print(f"👋 Registered: {name} (Seat {seat_index})")

    # ==========================================
    # Sub-task 3 & 4: Start Game & Assign Roles
    # ==========================================
    def start_game(self):
        """เริ่มเกม: ทุกคนเป็น Unassigned รอให้ Hardware ระบุตัวตนในคืนแรก"""
        if self.state.phase != GamePhase.LOBBY:
            raise ValueError("❌ เกมกำลังดำเนินอยู่")
        
        player_count = len(self.state.players)
        if player_count not in ROLE_MATRIX:
            raise ValueError(f"❌ ผู้เล่น {player_count} คน ไม่ตรงกับกติกา")

        # 1. บันทึกว่าเกมนี้มี Role อะไรที่ต้องหาบ้าง (แต่ยังไม่รู้ว่าใครเป็นใคร)
        self.expected_roles = ROLE_MATRIX[player_count].copy()
        
        # 2. ทุกคนเริ่มต้นด้วย UNASSIGNED 
        for player in self.state.players.values():
            player.role = Role.UNASSIGNED

        # 3. เข้าสู่ Night 1 (ช่วงเวลา Identify ตัวตน)
        self.state.phase = GamePhase.NIGHT
        self.state.current_turn = 1
        
        message = "เริ่มเกม: เข้าสู่คืนแรก AI Moderator ขอให้ทุกคนหลับตา..."
        self.state.history_log.append(message)
        print(f"\n✅ {message}")

    def identify_players_for_role(self, player_ids: list[str], identified_role: Role):
        """รับค่าจาก Hardware: ระบุกลุ่มผู้เล่นที่ลืมตาขึ้นมาในเทิร์นของบทบาทนั้นๆ"""
        if self.state.phase != GamePhase.NIGHT or self.state.current_turn != 1:
            raise ValueError("❌ การระบุตัวตนทำได้เฉพาะในคืนแรก")

        # Edge Case 1: ถ้า Array ว่างมา ให้ Return ออกไปเลย ไม่ต้องทำอะไร
        if not player_ids:
            return

        # Edge Case 3: เช็คโควต้าก่อนทำงาน
        quota_left = self.expected_roles.count(identified_role)
        if len(player_ids) > quota_left:
            raise ValueError(f"❌ บทบาท {identified_role.value} ครบตามจำนวนหรือไม่มีในเกมรอบนี้แล้ว (โควต้า: {quota_left}, แต่กล้องส่งมา: {len(player_ids)})")

        for p_id in player_ids:
            if p_id not in self.state.players:
                raise ValueError(f"❌ ไม่พบรหัสผู้เล่น {p_id}")
            
            player = self.state.players[p_id]
            
            # Edge Case 4: ป้องกันการระบุ Role ซ้ำซ้อน
            if player.role != Role.UNASSIGNED:
                raise ValueError(f"❌ ผู้เล่น {player.name} ถูกระบุบทบาทไปแล้วว่าเป็น {player.role.value}")
            
            player.role = identified_role
            self.expected_roles.remove(identified_role) # หักออกจากโควต้า
            print(f"👁️ Hardware Detect: {player.name} -> บันทึกเป็น {identified_role.value}")

    def get_pending_roles(self):
        """เช็คว่าเหลือบทบาทไหนบ้างที่ AI ยังหาตัวไม่เจอ (ยกเว้น Villager)"""
        # กรองเอาแค่บทบาทพิเศษที่ยังเหลือใน expected_roles
        special_roles = [r.value for r in self.expected_roles if r != Role.VILLAGER]
        return list(set(special_roles)) # คืนค่าแบบไม่ซ้ำชื่อ

    def conclude_first_night_identification(self):
        """
        เรียกใช้เมื่อจบกระบวนการปลุกทุก Role (หมาป่า, Seer) ในคืนแรกแล้ว
        คนที่เหลือที่ไม่ได้ลืมตาเลย จะถูกตั้งค่าเป็น Villager ทันที
        """
        villagers_count = 0
        for player in self.state.players.values():
            if player.role == Role.UNASSIGNED:
                player.role = Role.VILLAGER
                villagers_count += 1
                
        print(f"\n🌅 เช้าวันใหม่: ผู้เล่นที่เหลือ {villagers_count} คน ถูกระบุว่าเป็น Villager")

    def check_win_condition(self) -> tuple[bool, str]:
        """ตรวจสอบเงื่อนไขการชนะ"""
        alive_players = [p for p in self.state.players.values() if p.is_alive]
        werewolves = [p for p in alive_players if p.role == Role.WEREWOLF]
        villagers = [p for p in alive_players if p.role != Role.WEREWOLF]
        
        if len(werewolves) == 0:
            return True, "🎉 หมู่บ้านชนะ! กำจัดหมาป่าได้ทั้งหมดแล้ว"
        
        if len(werewolves) >= len(villagers):
            return True, "🐺 หมาป่าชนะ! จำนวนหมาป่ามากกว่าหรือเท่ากับชาวบ้านแล้ว"
        
        return False, ""
    
    def next_phase(self):
        """เปลี่ยนไปยังเฟสถัดไป"""
        if self.state.phase == GamePhase.NIGHT:
            self.state.phase = GamePhase.DAY
            self.state.history_log.append(f"Day {self.state.current_turn} begins")
        elif self.state.phase == GamePhase.DAY:
            self.state.phase = GamePhase.NIGHT
            self.state.current_turn += 1
            self.state.history_log.append(f"Night {self.state.current_turn} begins")
        
        print(f"🔄 Phase changed to: {self.state.phase.value}")
        
        # ตรวจสอบเงื่อนไขการชนะหลังจากเปลี่ยนเฟส
        game_over, message = self.check_win_condition()
        if game_over:
            self.state.phase = GamePhase.GAME_OVER
            self.state.history_log.append(message)
            print(f"\n{message}")
    
    def eliminate_player(self, player_id: str, reason: str = ""):
        """คัดผู้เล่นออกจากเกม"""
        if player_id not in self.state.players:
            raise ValueError(f"❌ ไม่พบผู้เล่นรหัส {player_id}")
        
        player = self.state.players[player_id]
        if not player.is_alive:
            raise ValueError(f"❌ ผู้เล่น {player.name} ถูกคัดออกไปแล้ว")
        
        player.is_alive = False
        message = f"💀 {player.name} ({player.role.value}) ถูกคัดออก {reason}"
        self.state.history_log.append(message)
        print(message)

    # ==========================================
    # [WM-14] Execute Night Action (รับค่าจาก Hardware)
    # ==========================================
    def execute_night_action(self, actor_role: Role, target_id: str):
        """บันทึกการใช้สกิลของแต่ละบทบาท"""
        if self.state.phase != GamePhase.NIGHT:
            raise ValueError("❌ จะใช้สกิลได้เฉพาะตอนกลางคืนเท่านั้น")
            
        if target_id not in self.state.players:
            raise ValueError(f"❌ ไม่พบเป้าหมายรหัส {target_id}")
            
        target_player = self.state.players[target_id]
        if not target_player.is_alive:
            raise ValueError(f"❌ ไม่สามารถเลือกคนที่ตายไปแล้วเป็นเป้าหมายได้")

        # ตรวจสอบว่าบทบาทที่สั่งมา ยังมีชีวิตอยู่ในเกมหรือไม่
        alive_actors = [p for p in self.state.players.values() if p.role == actor_role and p.is_alive]
        if not alive_actors:
            print(f"⚠️ {actor_role.value} ตายหมดแล้ว สกิลจะไม่มีผล")
            return

        # บันทึก Action ลงใน State ตามบทบาท
        if actor_role == Role.WEREWOLF:
            self.state.night_actions.kill_target = target_id
            print(f"🐺 หมาป่าเลือกฆ่า: {target_player.name}")
            
        elif actor_role == Role.BODYGUARD:
            self.state.night_actions.protect_target = target_id
            print(f"🛡️ บอดี้การ์ดเลือกคุ้มครอง: {target_player.name}")
            
        elif actor_role == Role.SEER:
            self.state.night_actions.checked_target = target_id
            result = "ฝ่ายร้าย" if target_player.role == Role.WEREWOLF else "ฝ่ายดี"
            print(f"👁️ Seer ส่อง {target_player.name} -> ผลลัพธ์: {result}")
            return result # คืนค่าให้ Hardware/AI เพื่อบอก Seer

    # ==========================================
    # [WM-15] Night Resolution (สรุปผลตอนเช้า)
    # ==========================================
    def resolve_night(self):
        """ประมวลผลลัพธ์ทั้งหมด และเตรียมเข้าสู่ช่วงกลางวัน"""
        if self.state.phase != GamePhase.NIGHT:
            return

        actions = self.state.night_actions
        victim_id = actions.kill_target
        protector_id = actions.protect_target
        
        death_message = "เมื่อคืนที่ผ่านมา... ช่างสงบสุข ไม่มีใครเสียชีวิต"
        
        # Logic การฆ่า: ถ้ามีเป้าหมาย และเป้าหมายนั้นไม่มีคนคุ้มครอง
        if victim_id:
            if victim_id == protector_id:
                death_message = f"🛡️ หมาป่าพยายามโจมตี {self.state.players[victim_id].name} แต่บอดี้การ์ดคุ้มครองไว้ได้!"
            else:
                victim = self.state.players[victim_id]
                victim.is_alive = False
                death_message = f"💀 เมื่อคืนนี้ {victim.name} ถูกหมาป่าขย้ำเสียชีวิต"
        
        self.state.history_log.append(death_message)
        print(f"\n📢 ประกาศจาก Moderator: {death_message}")

        # รีเซ็ต Action สำหรับคืนถัดไป และเปลี่ยนเฟส
        self.state.night_actions = NightActionState()
        self.next_phase() # ใช้ฟังก์ชันเปลี่ยนเฟสเดิมที่คุณกอล์ฟเขียนไว้

# ==========================================
# Mockup Testing: จำลองการทำงานเพื่อดูผลลัพธ์
# ==========================================
if __name__ == "__main__":
    # สร้างห้องเกม
    engine = GameEngine(game_id="LUNA_MATCH_001")
    
    print("--- 1. Player Registration ---")
    engine.register_player("P01", "Golf", 1)
    engine.register_player("P02", "Alice", 2)
    engine.register_player("P03", "Bob", 3)
    engine.register_player("P04", "Charlie", 4)
    engine.register_player("P05", "David", 5)
    
    print("\n--- 2. Starting the Game ---")
    try:
        engine.start_game()
        
        print("\n--- 3. Night 1: Role Identification (Hardware Mock) ---")
        # สมมติว่า AI พูด "หมาป่าลืมตา" และกล้องตรวจจับ P01 ได้
        engine.identify_players_for_role(["P01"], Role.WEREWOLF)
        
        # สมมติว่า AI พูด "Seer ลืมตา" และกล้องตรวจจับ P03 ได้
        engine.identify_players_for_role(["P03"], Role.SEER)
         
        # เมื่อเรียกครบทุก Role แล้ว ให้ระบบจัดการคนที่เหลือให้เป็นชาวบ้าน
        engine.conclude_first_night_identification()
        
        print("\n🤫 Secret Role Reveal (After Identification):")
        for p_id, p in engine.state.players.items():
            print(f"Seat {p.seat_index} ({p.name}): {p.role.value}")
                
        print("\n--- 4. Simulating Night 1 Actions ---")
        # หมาป่า (P01) เล็งกัด P02
        engine.execute_night_action(Role.WEREWOLF, "P02")
        # Seer (P03) ส่อง P04
        engine.execute_night_action(Role.SEER, "P04")
        
        # สรุปผลคืนที่ 1 (ระบบจะประกาศคนตาย และเปลี่ยน Phase เป็น DAY ให้เลย)
        engine.resolve_night()
        
        print("\n--- 5. Simulating Day 1 ---")
        # จำลองการโหวตตอนกลางวัน: ชาวบ้านพลาดไปโหวต P04 (Charlie) ออก
        print("\n[Action] โหวตตอนกลางวัน...")
        engine.eliminate_player("P04", "ถูกโหวตออกจากหมู่บ้าน")
        
        # จบช่วงโหวต เปลี่ยนเป็นกลางคืนที่ 2
        engine.next_phase()
        
        print("\n--- 6. Simulating Night 2 Actions ---")
        # หมาป่า (P01) เล็งกัด P05
        engine.execute_night_action(Role.WEREWOLF, "P05")
        # Seer (P03) ส่อง P01 (เจอว่าเป็นหมาป่า!)
        engine.execute_night_action(Role.SEER, "P01")
        
        # สรุปผลคืนที่ 2 (เกมควรจะจบและหมาป่าชนะ เพราะเหลือ P01 กับ P03 = 1v1)
        engine.resolve_night()

        print("\n--- 7. Final Game State JSON (Ready for LLM) ---")
        print(engine.state.model_dump_json(indent=2))
        
    except Exception as e:
        print(f"Error: {e}")
