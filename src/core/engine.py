import random
from src.core.models import GameState, Player, Role, GamePhase

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
        """ฟังก์ชันตรวจสอบเงื่อนไข แจกไพ่ และเริ่มเกม"""
        
        # 1. Validation (ตรวจสอบเงื่อนไขก่อนเริ่มเกม)
        if self.state.phase != GamePhase.LOBBY:
            raise ValueError("❌ เกมกำลังดำเนินอยู่ ไม่สามารถกดเริ่มซ้ำได้")
        
        player_count = len(self.state.players)
        if player_count < 5:
            raise ValueError(f"❌ ผู้เล่นไม่พอ! ต้องการอย่างน้อย 5 คน (ตอนนี้มี {player_count} คน)")
        if player_count not in ROLE_MATRIX:
            raise ValueError(f"❌ ยังไม่มี Config สัดส่วนบทบาทสำหรับผู้เล่น {player_count} คน")

        # 2. Get Role Config
        roles_to_assign = ROLE_MATRIX[player_count].copy()
        
        # 3. Shuffle & Assign (สุ่มแจกไพ่)
        random.shuffle(roles_to_assign) # สลับไพ่
        
        # เรียงลำดับผู้เล่นตามที่นั่งก่อนแจก เพื่อความเป็นระเบียบ
        sorted_players = sorted(self.state.players.values(), key=lambda p: p.seat_index)
        
        for i, player in enumerate(sorted_players):
            player.role = roles_to_assign[i]
        
        # 4. State Transition (อัปเดตสถานะเกมเป็นกลางคืน)
        self.state.phase = GamePhase.NIGHT
        self.state.current_turn = 1
        self.state.history_log.append("Game started. Roles assigned. Entering Night 1.")
        
        print("\n✅ Game Started Successfully!")
        print(f"🌙 Phase changed to: {self.state.phase.value} (Turn {self.state.current_turn})")

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
        
        print("\n🤫 Secret Role Reveal:")
        werewolf_id = None
        villager_ids = []
        
        for p_id, p in engine.state.players.items():
            print(f"Seat {p.seat_index} ({p.name}): {p.role.value}")
            # เก็บ ID หมาป่าและชาวบ้านไว้ใช้ทำ Mocking การฆ่า
            if p.role == Role.WEREWOLF:
                werewolf_id = p_id
            else:
                villager_ids.append(p_id)
                
        print("\n--- 3. Simulating Game Flow ---")
        # จำลองคืนที่ 1: หมาป่าฆ่าชาวบ้านคนแรก
        print("\n[Action] หมาป่าลงมือ...")
        engine.eliminate_player(villager_ids[0], "ถูกหมาป่ากัดในคืนที่ 1")
        
        # เปลี่ยนเป็นกลางวัน
        engine.next_phase() 
        
        # จำลองกลางวันที่ 1: โหวตชาวบ้านอีกคนออก (โหวตพลาด)
        print("\n[Action] โหวตตอนกลางวัน...")
        engine.eliminate_player(villager_ids[1], "ถูกโหวตออกจากหมู่บ้าน")
        
        # เปลี่ยนเป็นกลางคืนที่ 2
        engine.next_phase()
        
        # จำลองคืนที่ 2: หมาป่าฆ่าชาวบ้านอีกคน (ตอนนี้หมาป่า 1, ชาวบ้าน 1 -> หมาป่าชนะ)
        print("\n[Action] หมาป่าลงมืออีกครั้ง...")
        engine.eliminate_player(villager_ids[2], "ถูกหมาป่ากัดในคืนที่ 2")
        
        # เปลี่ยนเป็นกลางวัน (ระบบควรจะจับได้ว่าเกมจบแล้วและประกาศผล)
        engine.next_phase()

        print("\n--- 4. Final Game State JSON (Ready for LLM) ---")
        print(engine.state.model_dump_json(indent=2))
        
    except Exception as e:
        print(f"Error: {e}")