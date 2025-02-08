from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from backend.model import get_model, SUPPORTED_MODELS, get_model_download_status, download_model
import uvicorn

app = FastAPI()

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatRequest(BaseModel):
    model_id: str
    query: str
    history: Optional[List[tuple]] = None
    image_data: Optional[str] = None  # base64 编码的图片数据

class ChatResponse(BaseModel):
    response: str
    history: List[tuple]

class DownloadRequest(BaseModel):
    model_id: str
    source: str = "huggingface"

@app.get("/models")
def list_models():
    """获取支持的模型列表"""
    models = {}
    status = get_model_download_status()
    for model_id, info in SUPPORTED_MODELS.items():
        models[model_id] = {
            "id": model_id,
            "name": info["name"],
            "size": info["size"],
            "type": info.get("type", "unknown"),
            **status.get(model_id, {})
        }
    return models

@app.get("/model_status/{model_id:path}")
def get_model_status(model_id: str):
    """获取模型下载状态"""
    status = get_model_download_status()
    if model_id not in status:
        return {"downloaded": False, "downloading": False, "progress": 0}
    return status[model_id]

@app.post("/download_model")
def start_model_download(request: DownloadRequest):
    """开始下载模型"""
    return download_model(request.model_id, request.source)

@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    try:
        if request.model_id not in SUPPORTED_MODELS:
            raise HTTPException(status_code=400, detail=f"Unsupported model: {request.model_id}")
        
        model = get_model(request.model_id)
        response, history = model.chat(
            query=request.query,
            history=request.history,
            image_data=request.image_data
        )
        return ChatResponse(response=response, history=history)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)
