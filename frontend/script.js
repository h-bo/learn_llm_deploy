// 全局变量
let currentModel = '';
let chatHistory = [];
let statusCheckInterval = null;

// 获取模型列表
async function getModels() {
    try {
        const response = await fetch('http://localhost:8001/models');
        const models = await response.json();
        const modelSelect = document.getElementById('model-select');
        modelSelect.innerHTML = '';
        
        // 添加一个空选项
        const emptyOption = document.createElement('option');
        emptyOption.value = '';
        emptyOption.textContent = '请选择模型...';
        modelSelect.appendChild(emptyOption);
        
        // 添加模型选项
        for (const [id, info] of Object.entries(models)) {
            const option = document.createElement('option');
            option.value = id;
            option.textContent = `${info.name} (${info.size})`;
            modelSelect.appendChild(option);
            
            // 如果这个模型已经下载了，就选中它
            if (info.downloaded) {
                currentModel = id;
                modelSelect.value = id;
            }
        }
        
        // 如果没有已下载的模型，就选中第一个
        if (!currentModel && modelSelect.options.length > 1) {
            currentModel = modelSelect.options[1].value;
            modelSelect.value = currentModel;
        }
        
        // 更新模型状态
        if (currentModel) {
            await updateModelStatus(currentModel);
        }
    } catch (error) {
        console.error('Error fetching models:', error);
    }
}

// 更新模型状态
async function updateModelStatus(modelId) {
    if (!modelId) return;
    
    try {
        const response = await fetch(`http://localhost:8001/model_status/${encodeURIComponent(modelId)}`);
        const status = await response.json();
        
        // 更新下载状态显示
        const downloadStatus = document.getElementById('download-status');
        if (status.downloading) {
            downloadStatus.textContent = `下载中... ${status.progress}%`;
        } else if (status.downloaded) {
            downloadStatus.textContent = '模型已下载';
            stopStatusCheck();  // 下载完成后停止检查
        } else if (status.error) {
            downloadStatus.textContent = `下载失败: ${status.error}`;
            stopStatusCheck();  // 发生错误时停止检查
        } else {
            downloadStatus.textContent = '模型未下载';
        }
        
        return status;
    } catch (error) {
        console.error('Error updating model status:', error);
        stopStatusCheck();  // 发生错误时停止检查
        return { error: error.message };
    }
}

// 开始状态检查
function startStatusCheck() {
    if (statusCheckInterval) {
        clearInterval(statusCheckInterval);
    }
    statusCheckInterval = setInterval(async () => {
        if (currentModel) {
            const status = await updateModelStatus(currentModel);
            if (status.downloaded || status.error) {
                stopStatusCheck();
            }
        }
    }, 1000);
}

// 停止状态检查
function stopStatusCheck() {
    if (statusCheckInterval) {
        clearInterval(statusCheckInterval);
        statusCheckInterval = null;
    }
}

// 下载模型
async function downloadModel(source = 'huggingface') {
    if (!currentModel) {
        alert('请先选择一个模型');
        return;
    }
    
    try {
        const response = await fetch('http://localhost:8001/download_model', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                model_id: currentModel,
                source: source
            })
        });
        
        const result = await response.json();
        
        if (result.error) {
            alert(result.error);
            return;
        }
        
        console.log('Download started:', result);
        startStatusCheck();  // 开始检查下载状态
        
    } catch (error) {
        console.error('Error starting download:', error);
        alert('启动下载失败: ' + error.message);
    }
}

// 发送消息
async function sendMessage() {
    if (!currentModel) {
        alert('请先选择并下载一个模型');
        return;
    }
    
    const input = document.getElementById('message-input');
    const message = input.value.trim();
    const imageInput = document.getElementById('image-input');
    const chatBox = document.getElementById('chat-box');
    const sendButton = document.getElementById('send-button');
    
    if (!message && !imageInput.files[0]) {
        alert('请输入消息或选择图片');
        return;
    }
    
    // 禁用发送按钮
    sendButton.disabled = true;
    
    try {
        // 显示用户消息
        chatBox.innerHTML += `<div class="message user-message">${message}</div>`;
        input.value = '';
        
        let imageData = null;
        
        // 如果有选择图片，将其转换为 base64
        if (imageInput.files[0]) {
            imageData = await new Promise((resolve) => {
                const reader = new FileReader();
                reader.onloadend = () => resolve(reader.result);
                reader.readAsDataURL(imageInput.files[0]);
            });
            
            // 显示上传的图片
            chatBox.innerHTML += `<div class="message user-message"><img src="${imageData}" style="max-width: 200px;"></div>`;
        }
        
        // 发送请求
        const response = await fetch('http://localhost:8001/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                model_id: currentModel,
                query: message,
                history: chatHistory,
                image_data: imageData
            }),
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        
        // 显示助手回复
        chatBox.innerHTML += `<div class="message assistant-message">${data.response}</div>`;
        
        // 更新历史记录
        chatHistory = data.history;
        
        // 清除图片选择
        imageInput.value = '';
        
        // 滚动到底部
        chatBox.scrollTop = chatBox.scrollHeight;
        
    } catch (error) {
        console.error('Error sending message:', error);
        chatBox.innerHTML += `<div class="message error-message">发送失败: ${error.message}</div>`;
    } finally {
        // 重新启用发送按钮
        sendButton.disabled = false;
    }
}

// 监听模型选择变化
document.getElementById('model-select').addEventListener('change', (event) => {
    currentModel = event.target.value;
    if (currentModel) {
        updateModelStatus(currentModel);
    } else {
        document.getElementById('download-status').textContent = '请选择模型';
    }
});

// 监听发送按钮点击
document.getElementById('send-button').addEventListener('click', sendMessage);

// 监听输入框回车
document.getElementById('message-input').addEventListener('keypress', (event) => {
    if (event.key === 'Enter' && !event.shiftKey) {
        event.preventDefault();
        sendMessage();
    }
});

// 监听下载源选择
document.getElementById('source-select').addEventListener('change', (event) => {
    const source = event.target.value;
    const downloadButton = document.querySelector('button[onclick^="downloadModel"]');
    downloadButton.onclick = () => downloadModel(source);
});

// 初始化
getModels();
