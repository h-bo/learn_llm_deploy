import os
import json
import torch
import shutil
from typing import List, Dict, Tuple, Optional
from transformers import AutoModel, AutoTokenizer, AutoProcessor, AutoModelForCausalLM
from transformers import Qwen2_5_VLForConditionalGeneration
from modelscope import snapshot_download
from huggingface_hub import snapshot_download as hf_download
import hashlib
import threading
import time
from PIL import Image
import base64
import io

# 缓存目录
CACHE_DIR = "models"
os.makedirs(CACHE_DIR, exist_ok=True)

# 支持的模型列表
SUPPORTED_MODELS = {
    "Qwen/Qwen2.5-VL-3B-Instruct": {
        "name": "Qwen2.5-VL-3B-Instruct",
        "size": "3B",
        "type": "qwen2"
    },
    "THUDM/chatglm3-6b": {
        "name": "ChatGLM3-6B",
        "size": "6B",
        "type": "causal"
    },
    "deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B": {
        "name": "DeepSeek-R1-Distill-1.5B",
        "size": "1.5B",
        "type": "causal"
    }
}

# 下载状态记录
model_download_status = {}
model_download_threads = {}

def get_model_class(model_id: str):
    """获取模型对应的类"""
    if "qwen2.5-vl" in model_id.lower():
        return Qwen2_5_VLForConditionalGeneration
    else:
        return AutoModelForCausalLM

def get_model_config(model_id: str):
    """获取模型配置"""
    if "qwen2.5-vl" in model_id.lower():
        return {
            "trust_remote_code": True,
            "device_map": "auto"
        }
    else:
        return {
            "trust_remote_code": True,
            "device_map": "auto",
            "torch_dtype": torch.float16
        }

def download_thread(model_id: str, source: str = "huggingface"):
    """模型下载线程"""
    try:
        # 获取模型配置
        model_config = get_model_config(model_id)
        model_class = get_model_class(model_id)
        
        # 清理缓存
        clean_model_cache(model_id)
        
        # 更新下载状态
        model_download_status[model_id] = {
            "status": "downloading",
            "progress": 0
        }
        
        # 下载模型
        cache_path = os.path.join(CACHE_DIR, model_id)
        if source == "modelscope":
            snapshot_download(model_id, cache_dir=cache_path)
        else:
            hf_download(model_id, local_dir=cache_path)
        
        # 验证模型
        try:
            # 尝试加载模型以验证下载是否成功
            model = model_class.from_pretrained(cache_path, **model_config)
            if "qwen2.5-vl" in model_id.lower():
                processor = AutoProcessor.from_pretrained(cache_path, trust_remote_code=True)
            else:
                tokenizer = AutoTokenizer.from_pretrained(cache_path, trust_remote_code=True)
            
            model_download_status[model_id] = {
                "status": "downloaded",
                "progress": 100
            }
        except Exception as e:
            print(f"Model validation failed: {e}")
            model_download_status[model_id] = {
                "status": "error",
                "error": str(e)
            }
            clean_model_cache(model_id)
            
    except Exception as e:
        print(f"Download failed: {e}")
        model_download_status[model_id] = {
            "status": "error",
            "error": str(e)
        }
        clean_model_cache(model_id)

def clean_model_cache(model_id: str):
    """清理模型缓存"""
    cache_path = os.path.join(CACHE_DIR, model_id)
    if os.path.exists(cache_path):
        shutil.rmtree(cache_path)

class ChatModel:
    def __init__(self, model_id: str):
        """初始化聊天模型"""
        self.model_id = model_id
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        
        # 获取模型配置和类
        model_config = get_model_config(model_id)
        model_class = get_model_class(model_id)
        
        try:
            # 加载模型
            self.model = model_class.from_pretrained(
                os.path.join(CACHE_DIR, model_id),
                **model_config
            )
            
            # 加载处理器或分词器
            if "qwen2.5-vl" in model_id.lower():
                self.processor = AutoProcessor.from_pretrained(
                    os.path.join(CACHE_DIR, model_id),
                    trust_remote_code=True
                )
            else:
                self.tokenizer = AutoTokenizer.from_pretrained(
                    os.path.join(CACHE_DIR, model_id),
                    trust_remote_code=True
                )
        except Exception as e:
            print(f"Error loading model: {e}")
            raise

    def process_image(self, image_data: str) -> Image.Image:
        """处理图片数据"""
        if image_data.startswith('data:image'):
            # 处理 base64 格式的图片
            image_data = image_data.split(',')[1]
        
        # 将 base64 转换为图片
        image_bytes = base64.b64decode(image_data)
        image = Image.open(io.BytesIO(image_bytes))
        return image

    def chat(self, query: str, history: List[Tuple[str, str]] = None, image_data: str = None) -> Tuple[str, List[Tuple[str, str]]]:
        """聊天函数"""
        if history is None:
            history = []
            
        if "qwen2.5-vl" in self.model_id.lower():
            # Qwen2.5-VL 的处理方式
            messages = []
            
            # 添加历史对话
            for h in history:
                messages.append({"role": "user", "content": h[0]})
                messages.append({"role": "assistant", "content": h[1]})
            
            # 添加当前查询
            current_message = {"role": "user", "content": []}
            
            # 如果有图片，添加图片
            if image_data:
                image = self.process_image(image_data)
                current_message["content"].append({
                    "type": "image",
                    "image": image
                })
            
            # 添加文本
            current_message["content"].append({
                "type": "text",
                "text": query
            })
            
            messages.append(current_message)
            
            # 准备推理
            text = self.processor.apply_chat_template(
                messages,
                tokenize=False,
                add_generation_prompt=True
            )
            
            # 处理输入
            inputs = self.processor(
                text=[text],
                images=[image] if image_data else None,
                padding=True,
                return_tensors="pt"
            )
            
            # 将输入移到正确的设备上
            inputs = {k: v.to(self.device) for k, v in inputs.items()}
            
            # 生成回答
            generated_ids = self.model.generate(
                **inputs,
            )
            
            # 解码输出
            generated_ids_trimmed = [
                out_ids[len(in_ids):] for in_ids, out_ids in zip(inputs.input_ids, generated_ids)
            ]
            response = self.processor.batch_decode(
                generated_ids_trimmed,
                skip_special_tokens=True,
                clean_up_tokenization_spaces=False
            )[0]
            
            history = history + [(query, response)]
            return response, history
        else:
            # ChatGLM的默认处理方式
            response, history = self.model.chat(
                self.tokenizer,
                query,
                history=history
            )
            return response, history

# 全局模型实例字典
model_instances = {}

def get_model(model_name="deepseek-r1-1.5b"):
    if model_name not in model_instances:
        model_instances[model_name] = ChatModel(model_name)
    return model_instances[model_name]

def download_model(model_id: str, source: str = "huggingface"):
    """开始下载模型"""
    if model_id not in SUPPORTED_MODELS:
        return {"error": f"不支持的模型: {model_id}"}
    
    # 检查是否已经在下载
    if model_id in model_download_status and not model_download_status[model_id].get("error"):
        return {"error": "模型正在下载中"}
    
    # 清理可能存在的不完整文件
    clean_model_cache(model_id)
    
    # 初始化下载进度
    model_download_status[model_id] = {"progress": 0, "error": None}
    
    # 在新线程中开始下载
    thread = threading.Thread(target=download_thread, args=(model_id, source))
    thread.start()
    
    return {"status": "started"}

def get_model_download_status() -> Dict[str, dict]:
    """获取每个模型的下载状态和进度"""
    status = {}
    for model_id, info in SUPPORTED_MODELS.items():
        # 检查模型文件是否完整
        is_downloaded = os.path.exists(os.path.join(CACHE_DIR, model_id))
        
        # 获取下载进度
        progress = model_download_status.get(model_id, {})
        current_progress = progress.get("progress", 0) if not is_downloaded else 100
        error = progress.get("error", None)
        
        status[model_id] = {
            "downloaded": is_downloaded,
            "progress": current_progress,
            "error": error,
            "downloading": model_id in model_download_status and not error and not is_downloaded
        }
    return status
