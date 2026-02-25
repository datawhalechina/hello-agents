# main.py

import threading
import time
import gradio as gr
import json
from src.agents.sleep_agent import sleep_agent
from src.agents.mind_echo_agent import create_mind_echo_agent

# 启动 SleepAgent A2A 服务（后台线程）
threading.Thread(target=lambda: sleep_agent.run(port=6000), daemon=True).start()
time.sleep(1)

mind_agent = create_mind_echo_agent()

def extract_music_info(response_text):
    """从智能体响应中提取音乐信息"""
    try:
        # 尝试查找JSON格式的音乐数据
        start_idx = response_text.find('{')
        end_idx = response_text.rfind('}') + 1

        if start_idx != -1 and end_idx > start_idx:
            json_str = response_text[start_idx:end_idx]
            data = json.loads(json_str)

            if "tracks" in data and data["tracks"]:
                # 提取第一首歌曲信息
                first_track = data["tracks"][0]
                return {
                    "title": first_track.get("title", "未知歌曲"),
                    "artist": first_track.get("artist", "未知艺术家"),
                    "playlist_count": data.get("total_tracks", 0),
                    "mood": data.get("mood", ""),
                    "full_data": data
                }
    except Exception:
        pass

    # 如果没有找到音乐数据，返回默认信息
    return {
        "title": "放松音乐推荐",
        "artist": "MindEchoAI",
        "playlist_count": 3,
        "mood": "放松"
    }

def chat(user_input: str):
    """处理用户输入并返回响应"""
    response = mind_agent.run(user_input)
    music_info = extract_music_info(response)

    # 返回响应文本和音乐信息
    return response, music_info

def update_music_player(music_info):
    """更新音乐播放器显示"""
    if not music_info:
        return gr.update(visible=False), gr.update(visible=False)

    # 构建播放器显示文本
    player_text = f"""
    🎵 **正在播放：{music_info['title']}**
    👤 艺术家：{music_info['artist']}
    💫 心情：{music_info['mood']}
    📊 播放列表：{music_info['playlist_count']} 首歌曲

    *注：此为模拟播放器，实际音乐服务需后续集成*
    """

    return gr.update(value=player_text, visible=True), gr.update(visible=True)

with gr.Blocks(
    title="MindEchoAgent · 心境回响",
    theme=gr.themes.Soft(),
    css="""
    .music-player {
        border: 1px solid #e0e0e0;
        border-radius: 12px;
        padding: 16px;
        margin-top: 20px;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        box-shadow: 0 4px 12px rgba(0,0,0,0.1);
    }
    .music-player h3 {
        margin-top: 0;
        color: white;
        border-bottom: 1px solid rgba(255,255,255,0.2);
        padding-bottom: 8px;
    }
    .player-controls {
        display: flex;
        justify-content: center;
        gap: 12px;
        margin-top: 12px;
    }
    .player-controls button {
        background: rgba(255,255,255,0.2);
        border: none;
        border-radius: 50%;
        width: 44px;
        height: 44px;
        cursor: pointer;
        color: white;
        font-size: 18px;
        transition: all 0.3s ease;
    }
    .player-controls button:hover {
        background: rgba(255,255,255,0.3);
        transform: scale(1.05);
    }
    """
) as demo:

    # 标题区
    gr.Markdown("""
    # 🧠🎵 MindEchoAgent · 心境回响
    ### 情绪陪伴 + 音乐推荐 + 必要时升级睡眠专家
    """)

    with gr.Row():
        with gr.Column(scale=2):
            # 输入区
            with gr.Group():
                gr.Markdown("### 💭 分享你的心境")
                inp = gr.Textbox(
                    label="",
                    placeholder="例如：我最近晚上睡不着，很焦虑... 或者 需要一些放松的音乐",
                    lines=3,
                    container=False
                )

            # 发送按钮
            btn = gr.Button("✨ 发送", variant="primary", size="lg")

            # 响应输出区
            with gr.Group():
                gr.Markdown("### 🤖 AI 回响")
                out = gr.Textbox(
                    label="",
                    lines=8,
                    interactive=False,
                    container=False,
                    show_copy_button=True
                )

        with gr.Column(scale=1):
            # 音乐播放器面板
            gr.Markdown("### 🎧 音乐推荐")

            # 音乐播放器
            music_player = gr.HTML(
                value="<div style='text-align: center; padding: 20px; color: #666;'>等待推荐音乐...</div>",
                visible=False,
                elem_classes="music-player"
            )

            # 播放器控制按钮（隐藏，通过JavaScript控制）
            player_controls = gr.HTML("""
            <div class="player-controls" style="display: none;">
                <button onclick="playerControl('prev')">⏮️</button>
                <button onclick="playerControl('play')">▶️</button>
                <button onclick="playerControl('pause')">⏸️</button>
                <button onclick="playerControl('next')">⏭️</button>
                <button onclick="playerControl('volume_up')">🔊</button>
                <button onclick="playerControl('volume_down')">🔉</button>
            </div>
            """, visible=False)

    # 交互逻辑
    btn.click(
        fn=chat,
        inputs=inp,
        outputs=[out, music_player]
    ).then(
        fn=update_music_player,
        inputs=music_player,
        outputs=[music_player, player_controls]
    )

    # JavaScript控制函数
    demo.load(
        fn=None,
        inputs=None,
        outputs=None,
    )

    # 示例输入
    gr.Examples(
        examples=[
            ["今天工作压力好大，想听点放松的音乐"],
            ["心情特别开心，想要有活力的歌"],
            ["晚上睡不着，有点焦虑"],
            ["需要专注工作的背景音乐"],
            ["运动时想听兴奋的音乐"]
        ],
        inputs=inp,
        outputs=[out, music_player],
        fn=chat,
        cache_examples=True,
        label="💡 快速示例"
    )

    # 页脚
    gr.Markdown("---")
    gr.Markdown(
        """
        <div style="text-align: center; color: #888; font-size: 0.9em;">
        🎵 用AI感知情绪，用音乐温暖心灵 · MindEchoAgent v1.0<br>
        ⚠️ 音乐播放为模拟演示，实际播放功能需后续集成
        </div>
        """
    )

if __name__ == "__main__":
    demo.queue().launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=False,
        show_error=True
    )
