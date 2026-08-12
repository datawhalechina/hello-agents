document.addEventListener('DOMContentLoaded', () => {
    const chatContainer = document.getElementById('chat-container');
    const userInput = document.getElementById('user-input');
    const sendBtn = document.getElementById('send-btn');
    const projectUpload = document.getElementById('project-upload');
    const fileNameDisplay = document.getElementById('file-name');
    
    // 新增元素
    const sessionList = document.getElementById('session-list');
    const newSessionBtn = document.getElementById('new-session-btn');
    const currentSessionTitle = document.getElementById('current-session-title');
    const userLevelSelect = document.getElementById('user-level');
    const historyList = document.getElementById('history-list');

    let currentSessionId = null;

    // 自动滚动到底部
    function scrollToBottom() {
        chatContainer.scrollTop = chatContainer.scrollHeight;
    }

    // 添加消息到聊天界面
    function addMessage(text, isUser = false, toolCalls = null) {
        const msgDiv = document.createElement('div');
        msgDiv.className = `message ${isUser ? 'user-message' : 'bot-message'}`;

        // 如果有工具调用信息，先渲染工具调用块
        if (toolCalls && toolCalls.length > 0) {
            const toolsContainer = document.createElement('div');
            toolsContainer.className = 'tool-calls-container';
            
            toolCalls.forEach(tc => {
                const tcDiv = document.createElement('div');
                tcDiv.className = 'tool-call-block';
                
                // 尝试格式化参数和结果
                let formattedArgs = tc.arguments;
                try {
                    formattedArgs = JSON.stringify(JSON.parse(tc.arguments), null, 2);
                } catch (e) {}
                
                let formattedResult = tc.result;
                try {
                    formattedResult = JSON.stringify(JSON.parse(tc.result), null, 2);
                } catch (e) {}

                tcDiv.innerHTML = `
                    <div class="tool-call-header">
                        <span class="tool-icon">🛠️</span>
                        <span class="tool-name">调用工具: <strong>${tc.name}</strong></span>
                    </div>
                    <div class="tool-call-details">
                        <div class="tool-args">
                            <div class="tool-label">输入参数:</div>
                            <pre><code>${formattedArgs}</code></pre>
                        </div>
                        <div class="tool-result">
                            <div class="tool-label">执行结果:</div>
                            <pre><code>${formattedResult || '无返回结果'}</code></pre>
                        </div>
                    </div>
                `;
                toolsContainer.appendChild(tcDiv);
            });
            msgDiv.appendChild(toolsContainer);
        }

        // 简单处理 markdown 换行
        const textDiv = document.createElement('div');
        textDiv.className = 'message-text';
        const formattedText = text.replace(/\n/g, '<br>');
        textDiv.innerHTML = formattedText;
        msgDiv.appendChild(textDiv);

        chatContainer.appendChild(msgDiv);
        scrollToBottom();
    }

    // 显示加载状态
    function showLoading() {
        const loadingDiv = document.createElement('div');
        loadingDiv.className = 'message loading';
        loadingDiv.id = 'loading-msg';
        loadingDiv.textContent = '助手正在思考...';
        chatContainer.appendChild(loadingDiv);
        scrollToBottom();
    }

    // 移除加载状态
    function removeLoading() {
        const loadingDiv = document.getElementById('loading-msg');
        if (loadingDiv) {
            loadingDiv.remove();
        }
    }

    // 加载会话列表
    async function loadSessions() {
        try {
            const response = await fetch('/api/sessions');
            const data = await response.json();
            sessionList.innerHTML = '';
            
            data.sessions.forEach(session => {
                const div = document.createElement('div');
                div.className = `session-item ${session.id === currentSessionId ? 'active' : ''}`;
                
                const titleSpan = document.createElement('span');
                titleSpan.textContent = session.title;
                titleSpan.className = 'session-title';
                
                const deleteBtn = document.createElement('button');
                deleteBtn.innerHTML = '🗑️';
                deleteBtn.className = 'delete-session-btn';
                deleteBtn.title = '删除会话';
                deleteBtn.onclick = (e) => {
                    e.stopPropagation(); // 阻止触发切换会话
                    deleteSession(session.id, div);
                };
                
                div.appendChild(titleSpan);
                div.appendChild(deleteBtn);
                div.onclick = () => switchSession(session.id, session.title);
                
                sessionList.appendChild(div);
            });
        } catch (error) {
            console.error('加载会话列表失败:', error);
        }
    }

    // 删除会话
    async function deleteSession(sessionId, element) {
        if (!confirm('确定要删除这个会话吗？删除后无法恢复。')) return;
        
        try {
            const response = await fetch(`/api/sessions/${sessionId}`, {
                method: 'DELETE'
            });
            
            if (response.ok) {
                // 添加淡出动画
                element.style.opacity = '0';
                setTimeout(() => {
                    element.remove();
                    // 如果删除的是当前会话，新建一个会话
                    if (sessionId === currentSessionId) {
                        createNewSession();
                    }
                }, 300);
            } else {
                alert('删除失败');
            }
        } catch (error) {
            console.error('删除会话失败:', error);
            alert('网络错误，删除失败');
        }
    }

    // 切换会话
    async function switchSession(sessionId, title) {
        currentSessionId = sessionId;
        currentSessionTitle.textContent = title;
        chatContainer.innerHTML = '';
        
        // 更新侧边栏高亮
        document.querySelectorAll('.session-item').forEach(item => {
            item.classList.remove('active');
            if (item.textContent === title) {
                item.classList.add('active');
            }
        });

        try {
            const response = await fetch(`/api/sessions/${sessionId}`);
            const data = await response.json();
            
            if (data.messages && data.messages.length > 0) {
                data.messages.forEach(msg => {
                    addMessage(msg.text, msg.isUser, msg.tool_calls);
                });
            } else {
                addMessage('你好！我是你的软件开发学习助手。我可以根据你的水平出题，或者帮你测试代码。请问有什么我可以帮你的？');
            }
        } catch (error) {
            console.error('加载会话历史失败:', error);
            addMessage('加载历史记录失败');
        }
    }

    // 新建会话 (仅前端状态)
    function createNewSession() {
        currentSessionId = null;
        currentSessionTitle.textContent = '👨‍💻 SoftwareDevHelper';
        chatContainer.innerHTML = '';
        document.querySelectorAll('.session-item').forEach(item => item.classList.remove('active'));
        addMessage('你好！我是你的软件开发学习助手。我可以根据你的水平出题，提供开发建议，并测试你的代码。你想从哪里开始？');
    }

    // 发送文本消息
    async function sendMessage() {
        const text = userInput.value.trim();
        if (!text) return;

        userInput.value = '';
        addMessage(text, true);
        showLoading();
        sendBtn.disabled = true;

        try {
            const response = await fetch('/api/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ 
                    message: text,
                    session_id: currentSessionId || ''
                })
            });

            const data = await response.json();
            removeLoading();
            
            if (response.ok) {
                addMessage(data.response, false, data.tool_calls);
                // 如果是新会话，更新当前 session_id 并刷新列表
                if (!currentSessionId) {
                    currentSessionId = data.session_id;
                    currentSessionTitle.textContent = text.substring(0, 15) + (text.length > 15 ? '...' : '');
                }
                loadSessions();
                loadUserMemory(); // 聊天后可能更新了记忆
            } else {
                addMessage(`错误: ${data.detail || '请求失败'}`);
            }
        } catch (error) {
            removeLoading();
            addMessage(`网络错误: ${error.message}`);
        } finally {
            sendBtn.disabled = false;
            userInput.focus();
        }
    }

    // 处理文件上传
    async function handleFileUpload(event) {
        const file = event.target.files[0];
        if (!file) return;

        fileNameDisplay.textContent = file.name;
        
        const formData = new FormData();
        formData.append('file', file);
        formData.append('session_id', currentSessionId || '');

        addMessage(`[上传项目] ${file.name}`, true);
        showLoading();
        
        projectUpload.value = '';

        try {
            const response = await fetch('/api/upload_project', {
                method: 'POST',
                body: formData
            });

            const data = await response.json();
            removeLoading();
            
            if (response.ok) {
                addMessage(data.response, false, data.tool_calls);
                if (!currentSessionId) {
                    currentSessionId = data.session_id;
                    currentSessionTitle.textContent = "上传项目测试";
                }
                loadSessions();
                loadUserMemory();
            } else {
                addMessage(`上传失败: ${data.detail || '未知错误'}`);
            }
        } catch (error) {
            removeLoading();
            addMessage(`上传出错: ${error.message}`);
        } finally {
            fileNameDisplay.textContent = '未选择文件';
        }
    }

    // 加载用户记忆
    async function loadUserMemory() {
        try {
            const response = await fetch('/api/user_memory');
            const data = await response.json();
            
            userLevelSelect.value = data.level || 'beginner';
            
            historyList.innerHTML = '';
            if (data.history && data.history.length > 0) {
                data.history.forEach(record => {
                    const li = document.createElement('li');
                    li.textContent = record;
                    historyList.appendChild(li);
                });
            } else {
                const li = document.createElement('li');
                li.textContent = '暂无做题记录';
                li.style.color = '#999';
                historyList.appendChild(li);
            }
        } catch (error) {
            console.error('加载用户记忆失败:', error);
        }
    }

    // 更新用户水平
    async function updateUserLevel() {
        const newLevel = userLevelSelect.value;
        try {
            await fetch('/api/user_memory/level', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ level: newLevel })
            });
        } catch (error) {
            console.error('更新用户水平失败:', error);
        }
    }

    // 清空用户记忆记录
    async function resetUserMemory() {
        if (confirm('确定要清空所有的做题记录吗？这会将你的水平重置为入门（Beginner）。')) {
            try {
                await fetch('/api/user_memory', {
                    method: 'DELETE'
                });
                loadUserMemory();
                addMessage('您的做题记录已清空，水平已重置。', false);
            } catch (error) {
                console.error('清空记录失败:', error);
            }
        }
    }

    // 事件绑定
    sendBtn.addEventListener('click', sendMessage);
    
    userInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });

    projectUpload.addEventListener('change', handleFileUpload);
    newSessionBtn.addEventListener('click', createNewSession);
    userLevelSelect.addEventListener('change', updateUserLevel);
    
    const resetMemoryBtn = document.getElementById('reset-memory-btn');
    if (resetMemoryBtn) {
        resetMemoryBtn.addEventListener('click', resetUserMemory);
    }

    // 初始化
    loadSessions();
    loadUserMemory();
    createNewSession();
});
