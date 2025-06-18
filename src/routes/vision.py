from fastapi import APIRouter, UploadFile, File, Request
from fastapi.responses import JSONResponse

vision_router = APIRouter(
    prefix="/api/v1/vision",
    tags=["api_v1", "vision"],
)

@vision_router.post("/explain-image")
async def explain_image(request: Request, file: UploadFile = File(...)):
    if not file.content_type.startswith("image"):
        return JSONResponse(status_code=400, content={"error": "Only image files are supported."})

    image_bytes = await file.read()
    try:
        caption = request.app.vision_client.caption_image(image_bytes=image_bytes)  # ✅ proper injection
        return {"caption": caption}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})
