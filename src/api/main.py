from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
from src.core.engine import GameEngine
from src.core.models import GamePhase

# Initialize FastAPI App
app = FastAPI(
    title="Werewolf Moderator API",
    description="API Server for Physical Werewolf Game Engine",
    version="1.0.0"
)

# Setup CORS (อนุญาตให้ทุกระบบเชื่อมต่อเข้ามาได้)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # ใน Production ควรระบุ Domain ให้ชัดเจน
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==========================================
# 🛠️ Global Error Handler Logic
# ==========================================
def map_error_to_schema(error_msg: str) -> dict:
    """แปลง ValueError ภาษาไทยจาก Engine เป็น Standard Error Schema"""
    
    error_code = "ERR_INTERNAL_001"
    std_message = "An unexpected error occurred."

    # Mapping ตามตาราง Error Dictionary (WM-17)
    if "ไม่ตรงกับกติกา" in error_msg:
        error_code = "ERR_GAME_002"
        std_message = "Action not allowed: Insufficient players or invalid player count."
    elif "เกมกำลังดำเนินอยู่" in error_msg:
        error_code = "ERR_GAME_001"
        std_message = "Action not allowed: The game has already started."
    elif "ซ้ำ" in error_msg or "มีอยู่ในระบบ" in error_msg:
        error_code = "ERR_PLYR_001"
        std_message = "Player ID already exists in this game."
    elif "ที่นั่ง" in error_msg and "ถูกใช้งาน" in error_msg:
        error_code = "ERR_PLYR_002"
        std_message = "The selected seat index is already occupied."
    elif "ไม่พบรหัสผู้เล่น" in error_msg or "ไม่พบเป้าหมาย" in error_msg:
        error_code = "ERR_PLYR_003"
        std_message = "Target Player ID not found in the current game."
    elif "ตายไปแล้ว" in error_msg:
        error_code = "ERR_PLYR_004"
        std_message = "Invalid target: The target player is already dead."
    elif "เฉพาะในคืนแรก" in error_msg:
        error_code = "ERR_ROLE_001"
        std_message = "Role identification is only allowed during Night 1."
    elif "ครบตามจำนวน" in error_msg:
        error_code = "ERR_ROLE_002"
        std_message = "Identification failed: Role quota exceeded or role not present in this game."
    elif "ถูกระบุบทบาทไปแล้ว" in error_msg:
        error_code = "ERR_ROLE_003"
        std_message = "Identification failed: The player has already been assigned a role."
    elif "เฉพาะตอนกลางคืน" in error_msg:
        error_code = "ERR_ACT_001"
        std_message = "Action execution failed: Night phase actions can only be performed at night."
    elif "ตายหมดแล้ว" in error_msg:
        error_code = "ERR_ACT_002"
        std_message = "Action execution failed: The acting role has no living members."

    return {
        "status": "error",
        "data": None,
        "error": {
            "code": error_code,
            "message": std_message,
            "details": error_msg.replace("❌ ", "").replace("⚠️ ", "") # แนบ Error ต้นฉบับมาให้ Dev ดูด้วย
        }
    }

# ดักจับ ValueError ทั้งหมดที่เกิดจาก GameEngine
@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError):
    error_response = map_error_to_schema(str(exc))
    return JSONResponse(status_code=400, content=error_response)

# ==========================================
#  Game State Management (Multi-Game Support)
# ==========================================
class GameManager:
    """Manager  for multiple game instances"""
    def __init__(self):
        self.games = {}  # game_id -> GameEngine
    
    def get_game(self, game_id: str) -> GameEngine:
        """Get existing game or create new one"""
        if game_id not in self.games:
            self.games[game_id] = GameEngine(game_id=game_id)
        return self.games[game_id]
    
    def list_games(self) -> dict:
        """List all active games"""
        return {
            game_id: {
                "phase": engine.state.phase.value,
                "current_turn": engine.state.current_turn,
                "players_count": len(engine.state.players)
            }
            for game_id, engine in self.games.items()
        }

# Global GameManager instance
game_manager = GameManager()


# ==========================================
# 📝 API Models (Schema สำหรับรับข้อมูล Request)
# ==========================================
class PlayerRegisterRequest(BaseModel):
    player_id: str
    name: str
    seat_index: int

class IdentifyRequest(BaseModel):
    identified_role: str
    player_ids: List[str]

class ActionRequest(BaseModel):
    actor_role: str
    target_id: str


# ==========================================
# 🚪 Lobby Endpoints
# ==========================================

@app.post("/api/v1/{game_id}/lobby/register")
def register_player(game_id: str, request: PlayerRegisterRequest):
    """ลงทะเบียนผู้เล่นใหม่เข้าสู่ Lobby"""
    
    # Get or create game instance
    engine = game_manager.get_game(game_id)
    
    # Pass data to Engine (Global Handler will catch and convert to JSON)
    engine.register_player(request.player_id, request.name, request.seat_index)
    
    return {
        "status": "success",
        "data": {
            "message": "Player registered successfully.",
            "game_id": game_id,
            "player_id": request.player_id,
            "name": request.name,
            "seat_index": request.seat_index
        },
        "error": None
    }

@app.post("/api/v1/{game_id}/game/start")
def start_game(game_id: str):
    """เริ่มเกม: ล็อกห้อง สุ่มบทบาท และเข้าสู่การระบุตัวตนคืนแรก"""
    
    # Get game instance
    engine = game_manager.get_game(game_id)
    
    # Start game (if <5 players Global Handler will throw ERR_GAME_002)
    engine.start_game()
    
    # Get expected roles list
    expected_roles_str = [role.value for role in engine.expected_roles]
    
    return {
        "status": "success",
        "data": {
            "message": "Game started successfully. Please proceed to Night 1 identification.",
            "game_id": game_id,
            "phase": engine.state.phase.value,
            "current_turn": engine.state.current_turn,
            "expected_roles": expected_roles_str
        },
        "error": None
    }

@app.get("/api/v1/{game_id}/game/status")
def get_game_status(game_id: str):
    """Get current game status"""
    
    # Get game instance
    engine = game_manager.get_game(game_id)
    
    return {
        "status": "success",
        "data": {
            "game_id": game_id,
            "phase": engine.state.phase.value,
            "current_turn": engine.state.current_turn,
            "players_count": len(engine.state.players),
            "players": [
                {
                    "player_id": player_id,
                    "name": player.name,
                    "seat_index": player.seat_index,
                    "role": player.role.value,
                    "is_alive": player.is_alive
                }
                for player_id, player in engine.state.players.items()
            ]
        },
        "error": None
    }

@app.get("/api/v1/games/list")
def list_games():
    """List all active games"""
    
    return {
        "status": "success",
        "data": {
            "games": game_manager.list_games(),
            "total_games": len(game_manager.games)
        },
        "error": None
    }

# ==========================================
# 🎯 Hardware Endpoints (Night Phase)
# ==========================================

@app.post("/api/v1/{game_id}/hardware/identify")
def identify_role(game_id: str, request: IdentifyRequest):
    """ระบุตัวตนผู้เล่นสำหรับบทบาทต่างๆ (ใช้เฉพาะ Night 1)"""
    
    # Get game instance
    engine = game_manager.get_game(game_id)
    
    # Convert string role to Role enum
    from src.core.models import Role
    try:
        identified_role = Role(request.identified_role)
    except ValueError:
        raise ValueError(f"❌ บทบาท {request.identified_role} ไม่ถูกต้อง")
    
    # Call engine to identify players
    engine.identify_players_for_role(request.player_ids, identified_role)
    
    # Get pending roles
    pending_roles = engine.get_pending_roles()
    
    return {
        "status": "success",
        "data": {
            "identified_role": identified_role.value,
            "assigned_players": request.player_ids,
            "pending_roles": pending_roles,
            "game_id": game_id
        },
        "error": None
    }

@app.post("/api/v1/{game_id}/hardware/action")
def execute_action(game_id: str, request: ActionRequest):
    """บันทึกการใช้สกิลของแต่ละบทบาทในช่วงกลางคืน"""
    
    # Get game instance
    engine = game_manager.get_game(game_id)
    
    # Convert string role to Role enum
    from src.core.models import Role
    try:
        actor_role = Role(request.actor_role)
    except ValueError:
        raise ValueError(f"❌ บทบาท {request.actor_role} ไม่ถูกต้อง")
    
    # Execute action and get result (for Seer investigation)
    result = engine.execute_night_action(actor_role, request.target_id)
    
    # Build response
    response_data = {
        "message": "Action recorded successfully.",
        "game_id": game_id
    }
    
    # Add investigation result for Seer only
    if actor_role == Role.SEER and result:
        response_data["investigation_result"] = result
    
    return {
        "status": "success",
        "data": response_data,
        "error": None
    }

# ==========================================
# 🌅 Game Resolution Endpoints
# ==========================================

@app.post("/api/v1/{game_id}/game/resolve-night")
def resolve_night_phase(game_id: str):
    """ประมวลผลเหตุการณ์กลางคืนและเปลี่ยนเป็นช่วงกลางวัน"""
    
    # Get game instance
    engine = game_manager.get_game(game_id)
    
    # Conclude first night identification if still in Night 1
    if engine.state.phase == GamePhase.NIGHT and engine.state.current_turn == 1:
        engine.conclude_first_night_identification()
    
    # Resolve night actions
    engine.resolve_night()
    
    return {
        "status": "success",
        "data": {
            "new_phase": engine.state.phase.value,
            "current_turn": engine.state.current_turn,
            "game_id": game_id
        },
        "error": None
    }

# ==========================================
# 🚀 Root Endpoint (เช็คสถานะเซิร์ฟเวอร์)
# ==========================================
@app.get("/api/v1/health")
def health_check():
    return {
        "status": "success",
        "data": {
            "message": "Werewolf API is running!",
            "version": "1.0.0"
        },
        "error": None
    }