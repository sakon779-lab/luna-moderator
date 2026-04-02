from enum import Enum
from typing import Dict, List, Optional
from pydantic import BaseModel, Field

# ==========================================
# Enums: กำหนดค่าคงที่เพื่อป้องกัน Typo
# ==========================================
class Role(str, Enum):
    UNASSIGNED = "Unassigned"
    VILLAGER = "Villager"
    WEREWOLF = "Werewolf"
    SEER = "Seer"
    BODYGUARD = "Bodyguard"

class GamePhase(str, Enum):
    LOBBY = "Lobby"
    NIGHT = "Night"
    DAY = "Day"
    GAME_OVER = "Game Over"

# ==========================================
# Models: โครงสร้างข้อมูล (Data Schema)
# ==========================================
class NightActionState(BaseModel):
    kill_target: Optional[str] = None    # ID คนที่หมาป่าเลือกฆ่า
    protect_target: Optional[str] = None # ID คนที่บอดี้การ์ดเลือกคุ้มครอง
    checked_target: Optional[str] = None # ID คนที่ Seer เลือกส่อง

class Player(BaseModel):
    player_id: str
    name: str
    seat_index: int
    role: Role = Role.UNASSIGNED
    is_alive: bool = True
    # เก็บ Status พิเศษ เช่น โดนพิษ, ถูกคุ้มครอง
    status_effects: List[str] = Field(default_factory=list) 

class GameState(BaseModel):
    game_id: str
    phase: GamePhase = GamePhase.LOBBY
    current_turn: int = 0  # นับวันที่/คืนที่ เท่าไหร่
    # ใช้ Dict เพื่อให้ค้นหาผู้เล่นด้วย player_id ได้ไวระดับ O(1)
    players: Dict[str, Player] = Field(default_factory=dict)
    # เก็บประวัติเหตุการณ์ที่เกิดขึ้นในแต่ละเทิร์น (เอาไว้ส่งให้ LLM)
    history_log: List[str] = Field(default_factory=list)
    # เพิ่มส่วนนี้เพื่อเก็บข้อมูล Action ของคืนปัจจุบัน
    night_actions: NightActionState = Field(default_factory=NightActionState)

# ==========================================
# ตัวอย่างการใช้งานและแปลงเป็น JSON (เอาไว้เทสต์ดูผลลัพธ์)
# ==========================================
if __name__ == "__main__":
    # 1. ลองสร้างตัวละคร
    player1 = Player(player_id="P01", name="Golf", seat_index=1)
    
    # 2. ลองสร้าง State เกมและจับผู้เล่นใส่ลงไป
    state = GameState(game_id="GAME_001")
    state.players[player1.player_id] = player1
    
    # 3. ลอง Print เป็น JSON (ตรงตาม Definition of Done)
    print("--- Game State JSON ---")
    print(state.model_dump_json(indent=2))