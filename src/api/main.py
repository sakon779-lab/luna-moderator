from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

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