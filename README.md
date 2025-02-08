# ChatGLM Web Deploy

这是一个使用 FastAPI 部署 ChatGLM3-6B 模型的示例项目，包含前后端完整实现。

## 项目结构

```
.
├── backend/           # 后端代码
│   ├── main.py       # FastAPI 主程序
│   └── model.py      # 模型加载与推理
├── frontend/         # 前端代码
│   ├── index.html
│   ├── style.css
│   └── script.js
└── requirements.txt  # Python 依赖
```

## 安装与运行

1. 安装依赖：
```bash
pip install -r requirements.txt
```

2. 运行后端服务：
```bash
cd backend
uvicorn main:app --reload
```

3. 打开前端页面：
直接在浏览器中打开 frontend/index.html

## API 文档

启动服务后访问 http://localhost:8000/docs 查看完整 API 文档。

## 项目说明文档

### Qwen2.5-VL Web Demo

这是一个基于 Qwen2.5-VL 模型的 Web 演示应用。支持文本对话和图像理解功能。

#### 功能特点

- 支持多个模型（Qwen2.5-VL、ChatGLM3等）
- 支持从 HuggingFace 和 ModelScope 下载模型
- 支持文本对话
- 支持图片理解
- 实时显示模型下载进度
- 美观的用户界面

#### 技术栈

##### 后端
- Python
- FastAPI
- Transformers
- PyTorch
- ModelScope

##### 前端
- HTML5
- CSS3
- JavaScript (原生)

#### 安装

1. 克隆仓库：
```bash
git clone <repository-url>
cd web_deploy
```

2. 安装依赖：
```bash
pip install -r requirements.txt
```

#### 运行

1. 启动后端服务：
```bash
python -m uvicorn backend.main:app --reload --port 8001
```

2. 在浏览器中打开 `frontend/index.html`

#### 使用说明

1. 从下拉列表中选择一个模型
2. 选择下载源（HuggingFace 或 ModelScope）
3. 点击"下载模型"按钮开始下载
4. 等待下载完成
5. 输入文本或选择图片进行对话

#### 目录结构

```
web_deploy/
├── backend/
│   ├── __init__.py
│   ├── main.py      # FastAPI 应用
│   └── model.py     # 模型处理逻辑
├── frontend/
│   ├── index.html   # 主页面
│   ├── script.js    # 前端逻辑
│   └── style.css    # 样式表
├── models/          # 模型文件目录
├── requirements.txt # Python 依赖
└── README.md       # 项目说明
```

#### 许可证

MIT License
