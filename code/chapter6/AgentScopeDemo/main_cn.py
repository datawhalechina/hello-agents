# -*- coding: utf-8 -*-
"""
三国狼人杀 - 基于AgentScope的中文版狼人杀游戏
融合三国演义角色和传统狼人杀玩法
"""
import asyncio
import os
import json
import random
from pathlib import Path
from typing import List, Dict, Optional

from agentscope.agent import ReActAgent
from agentscope.model import OpenAIChatModel, DashScopeChatModel
from agentscope.pipeline import MsgHub, sequential_pipeline, fanout_pipeline
from agentscope.formatter import (
    DeepSeekMultiAgentFormatter,
    DeepSeekChatFormatter,
    DashScopeMultiAgentFormatter,
)
import logging as _logging

from prompt_cn import ChinesePrompts
from game_roles import GameRoles
from structured_output_cn import (
    get_vote_model_cn,
    WitchActionModelCN,
    get_seer_model_cn,
    get_hunter_model_cn,
    WerewolfKillModelCN
)
from utils_cn import (
    check_winning_cn,
    majority_vote_cn,
    get_chinese_name,
    format_player_list,
    GameModerator,
    MAX_GAME_ROUND,
    MAX_DISCUSSION_ROUND,
)

# 加载同级目录下的 .env（不覆盖已存在的系统环境变量；缺失则回退到系统环境变量）
try:
    from dotenv import load_dotenv

    _env_path = Path(__file__).resolve().parent / ".env"
    load_dotenv(_env_path)
except ImportError:
    pass  # 未安装 python-dotenv 时跳过，仍可依赖系统环境变量


# ============================================================
# 多模型供应商适配层
# ------------------------------------------------------------
# 关键点：百炼(DashScope)用的是自家私有协议，DeepSeek 用的是
# OpenAI 兼容协议，两者【不能】靠改 base_url 互换，必须换 SDK 类。
#   - 百炼   -> DashScopeChatModel + DashScopeMultiAgentFormatter
#   - DeepSeek -> OpenAIChatModel   + DeepSeekMultiAgentFormatter
# ============================================================

PROVIDER_CONFIG = {
    "deepseek": {
        "env_key": "DEEPSEEK_API_KEY",
        "default_model": "deepseek-v4-pro",
        "base_url": "https://api.deepseek.com/v1",
    },
    "dashscope": {
        "env_key": "DASHSCOPE_API_KEY",
        "default_model": "qwen-plus",
        # 百炼走 SDK 默认地址，绝对不要覆盖 base_http_api_url，
        # 否则 SDK 会把私有路径拼到错误的域名上，直接 404。
        "base_url": None,
    },
}


# ============================================================
# DeepSeek reasoning_content 回传补丁
# ------------------------------------------------------------
# 根因：deepseek-v4-pro 是推理模型，回复里带 reasoning_content。DeepSeek 规定
# 多轮对话中凡是含 thinking 的 assistant 消息，必须把 reasoning_content 原样
# 回传，否则报 400：reasoning_content must be passed back。
# 但 agentscope 1.0.2 的 DeepSeekChatFormatter 把 thinking 块直接丢弃
# （日志里 "Unsupported block type thinking ... skipped"），导致结构化输出
# （预言家/女巫/投票走 tools 路径）的第 2 次调用崩溃。
# 下面自定义 formatter 把 thinking 作为 reasoning_content 写回 assistant 消息。
# ============================================================

_REASONING_FMT_LOGGER = _logging.getLogger("ReasoningChatFormatter")


class _ReasoningChatFormatter(DeepSeekChatFormatter):
    """在 DeepSeekChatFormatter 基础上保留 thinking -> reasoning_content。"""

    async def _format(self, msgs):
        self.assert_list_of_msgs(msgs)
        messages: list[dict] = []
        for msg in msgs:
            content_blocks: list = []
            tool_calls = []
            reasoning = None

            for block in msg.get_content_blocks():
                typ = block.get("type")
                if typ == "text":
                    content_blocks.append({**block})
                elif typ == "thinking":
                    # 关键：保留推理内容，供 DeepSeek 多轮回传
                    reasoning = block.get("thinking")
                elif typ == "tool_use":
                    tool_calls.append(
                        {
                            "id": block.get("id"),
                            "type": "function",
                            "function": {
                                "name": block.get("name"),
                                "arguments": json.dumps(
                                    block.get("input", {}),
                                    ensure_ascii=False,
                                ),
                            },
                        },
                    )
                elif typ == "tool_result":
                    messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": block.get("id"),
                            "content": self.convert_tool_result_to_string(
                                block.get("output"),
                            ),
                            "name": block.get("name"),
                        },
                    )
                else:
                    _REASONING_FMT_LOGGER.warning(
                        "Unsupported block type %s in the message, skipped.",
                        typ,
                    )

            content_msg = "\n".join(
                content.get("text", "") for content in content_blocks
            )
            msg_deepseek = {
                "role": msg.role,
                "content": content_msg or None,
            }

            # DeepSeek 推理模型（deepseek-v4 等）硬性要求：所有 assistant 消息
            # 都必须回传 reasoning_content。本 formatter 仅用于 DeepSeek 通道。
            # - 消息本身带 thinking 块：原样回传；
            # - 历史消息原始 thinking 为空（未捕获到 thinking 块，例如某次模型
            #   仅返回 tool_use、没有 thinking/text）：用空串兜底，否则触发 400:
            #   "The reasoning_content in the thinking mode must be passed back".
            if msg.role == "assistant":
                if reasoning:
                    msg_deepseek["reasoning_content"] = reasoning
                else:
                    msg_deepseek["reasoning_content"] = ""

            if tool_calls:
                msg_deepseek["tool_calls"] = tool_calls

            if msg_deepseek["content"] or msg_deepseek.get("tool_calls"):
                messages.append(msg_deepseek)

        return messages


class ReasoningMultiAgentFormatter(DeepSeekMultiAgentFormatter):
    """多智能体 formatter：在 tools 序列路径使用上述补丁 formatter。"""

    async def _format_tool_sequence(self, msgs):
        return await _ReasoningChatFormatter().format(msgs)


def resolve_provider() -> tuple[str, str, str]:
    """确定使用哪个供应商。

    优先级：显式指定 LLM_PROVIDER > 自动探测已配置的 API Key。

    Returns:
        (provider, api_key, model_name)
    """
    provider = os.getenv("LLM_PROVIDER", "").strip().lower()

    # 未显式指定则自动探测：谁配了 key 就用谁，DeepSeek 优先
    if not provider:
        for name in ("deepseek", "dashscope"):
            if os.getenv(PROVIDER_CONFIG[name]["env_key"]):
                provider = name
                break

    if not provider:
        raise ValueError(
            "未检测到任何可用的 API Key，请至少配置 "
            + " 或 ".join(c["env_key"] for c in PROVIDER_CONFIG.values())
        )

    if provider not in PROVIDER_CONFIG:
        raise ValueError(
            f"未识别的供应商 {provider!r}，可选值：{list(PROVIDER_CONFIG)}"
        )

    cfg = PROVIDER_CONFIG[provider]
    api_key = os.getenv(cfg["env_key"])
    if not api_key:
        raise ValueError(f"请先设置环境变量 {cfg['env_key']}")

    model_name = os.getenv("LLM_MODEL") or cfg["default_model"]
    return provider, api_key, model_name


def build_model_and_formatter(provider: str, api_key: str, model_name: str):
    """按供应商构造匹配的 model 与 formatter（两者必须配套）。"""
    if provider == "deepseek":
        model = OpenAIChatModel(
            model_name=model_name,
            api_key=api_key,
            stream=True,
            client_args={"base_url": PROVIDER_CONFIG["deepseek"]["base_url"]},
        )
        return model, ReasoningMultiAgentFormatter()

    # dashscope
    model = DashScopeChatModel(
        model_name=model_name,
        api_key=api_key,
        stream=True,
        # enable_thinking 是百炼专属参数，仅 Qwen3 / QwQ / DeepSeek-R1 支持
        enable_thinking=os.getenv("ENABLE_THINKING", "").lower() == "true",
    )
    return model, DashScopeMultiAgentFormatter()


class ThreeKingdomsWerewolfGame:
    """三国狼人杀游戏主类"""
    
    def __init__(self):
        # 全局解析一次供应商配置，所有玩家共用同一套
        self.provider, self.api_key, self.model_name = resolve_provider()
        print(f"🔌 使用供应商：{self.provider} | 模型：{self.model_name}")

        self.players: Dict[str, ReActAgent] = {}
        self.roles: Dict[str, str] = {}
        self.moderator = GameModerator()
        self.alive_players: List[ReActAgent] = []
        self.werewolves: List[ReActAgent] = []
        self.villagers: List[ReActAgent] = []
        self.seer: List[ReActAgent] = []
        self.witch: List[ReActAgent] = []
        self.hunter: List[ReActAgent] = []
        
        # 女巫道具状态
        self.witch_has_antidote = True
        self.witch_has_poison = True
        
    async def create_player(self, role: str, character: str) -> ReActAgent:
        """创建具有三国背景的玩家"""
        name = get_chinese_name(character)
        self.roles[name] = role
        
        model, formatter = build_model_and_formatter(
            self.provider, self.api_key, self.model_name
        )

        agent = ReActAgent(
            name=name,
            sys_prompt=ChinesePrompts.get_role_prompt(role, character),
            model=model,
            formatter=formatter,
        )
        
        # 角色身份确认
        await agent.observe(
            await self.moderator.announce(
                f"【{name}】你在这场三国狼人杀中扮演{GameRoles.get_role_desc(role)}，"
                f"你的角色是{character}。{GameRoles.get_role_ability(role)}"
            )
        )
        
        self.players[name] = agent
        return agent
    
    async def setup_game(self, player_count: int = 6):
        """设置游戏"""
        print("🎮 开始设置三国狼人杀游戏...")
        
        # 获取角色配置
        roles = GameRoles.get_standard_setup(player_count)
        characters = random.sample([
            "刘备", "关羽", "张飞", "诸葛亮", "赵云",
            "曹操", "司马懿", "周瑜", "孙权"
        ], player_count)
        
        # 创建玩家
        for i, (role, character) in enumerate(zip(roles, characters)):
            agent = await self.create_player(role, character)
            self.alive_players.append(agent)
            
            # 分配到对应阵营
            if role == "狼人":
                self.werewolves.append(agent)
            elif role == "预言家":
                self.seer.append(agent)
            elif role == "女巫":
                self.witch.append(agent)
            elif role == "猎人":
                self.hunter.append(agent)
            else:
                self.villagers.append(agent)
        
        # 游戏开始公告
        await self.moderator.announce(
            f"三国狼人杀游戏开始！参与者：{format_player_list(self.alive_players)}"
        )
        
        print(f"✅ 游戏设置完成，共{len(self.alive_players)}名玩家")
    
    async def werewolf_phase(self, round_num: int):
        """狼人阶段"""
        if not self.werewolves:
            return None
            
        await self.moderator.announce(f"🐺 狼人请睁眼，选择今晚要击杀的目标...")
        
        # 狼人讨论
        async with MsgHub(
            self.werewolves,
            enable_auto_broadcast=True,
            announcement=await self.moderator.announce(
                f"狼人们，请讨论今晚的击杀目标。存活玩家：{format_player_list(self.alive_players)}"
            ),
        ) as werewolves_hub:
            # 讨论阶段：纯自然语言讨论，不再强制结构化输出
            # （DiscussionModelCN 的结构化结果从未被读取，且 deepseek-v4-pro
            #  在 response_format 约束+思考模式下易退化成 ['response'] 导致
            #  "Error in block input ['response']" 重试噪音，去掉后讨论更自然）
            for _ in range(MAX_DISCUSSION_ROUND):
                for wolf in self.werewolves:
                    await wolf()
            
            # 投票击杀
            werewolves_hub.set_auto_broadcast(False)
            kill_votes = await fanout_pipeline(
                self.werewolves,
                msg=await self.moderator.announce("请选择击杀目标"),
                structured_model=WerewolfKillModelCN,
                enable_gather=False,
            )
            
            # 统计投票
            votes = {}
            # 合法的击杀目标：存活且不是狼人（不能刀自己人、不能刀已出局者）
            valid_targets = [p.name for p in self.alive_players if p.name not in [w.name for w in self.werewolves]]
            for i, vote_msg in enumerate(kill_votes):
                # 检查vote_msg是否为None或metadata是否存在
                if vote_msg is not None and hasattr(vote_msg, 'metadata') and vote_msg.metadata is not None:
                    target = vote_msg.metadata.get("target")
                    # 校验：目标必须是存活的好人（不能是狼人、不能是已出局、不能是空）
                    if target and target in valid_targets:
                        votes[self.werewolves[i].name] = target
                    else:
                        print(f"⚠️ {self.werewolves[i].name} 的击杀目标无效({target})，随机选择有效目标")
                        votes[self.werewolves[i].name] = random.choice(valid_targets) if valid_targets else None
                else:
                    # 如果返回无效,随机选择一个目标
                    print(f"⚠️ {self.werewolves[i].name} 的击杀投票无效,随机选择目标")
                    votes[self.werewolves[i].name] = random.choice(valid_targets) if valid_targets else None
            
            killed_player, _ = majority_vote_cn(votes)
            return killed_player
    
    async def seer_phase(self):
        """预言家阶段"""
        if not self.seer:
            return
            
        seer_agent = self.seer[0]
        await self.moderator.announce("🔮 预言家请睁眼，选择要查验的玩家...")
        
        check_result = await seer_agent(
            structured_model=get_seer_model_cn(self.alive_players)
        )

        # 检查返回结果是否有效
        if check_result is None or not hasattr(check_result, 'metadata') or check_result.metadata is None:
            print(f"⚠️ 预言家查验失败,跳过此阶段")
            return

        target_name = check_result.metadata.get("target")
        if not target_name:
            print(f"⚠️ 预言家未选择查验目标,跳过此阶段")
            return

        # 校验：目标必须是存活的其他玩家（不能是自己、不能是已出局、必须是已知玩家）
        alive_names = {p.name for p in self.alive_players}
        if target_name not in self.roles or target_name not in alive_names:
            print(f"⚠️ 预言家查验目标无效({target_name})，跳过此阶段")
            return
        if target_name == seer_agent.name:
            print(f"⚠️ 预言家不能查验自己({target_name})，跳过此阶段")
            return

        target_role = self.roles.get(target_name, "村民")
        
        # 告知预言家结果
        result_msg = f"查验结果：{target_name}是{'狼人' if target_role == '狼人' else '好人'}"
        await seer_agent.observe(await self.moderator.announce(result_msg))
    
    async def witch_phase(self, killed_player: str):
        """女巫阶段"""
        if not self.witch:
            return killed_player, None
            
        witch_agent = self.witch[0]
        await self.moderator.announce("🧙‍♀️ 女巫请睁眼...")
        
        # 告知女巫死亡信息
        death_info = f"今晚{killed_player}被狼人击杀" if killed_player else "今晚平安无事"
        await witch_agent.observe(await self.moderator.announce(death_info))
        
        # 女巫行动
        witch_action = await witch_agent(structured_model=WitchActionModelCN)

        saved_player = None
        poisoned_player = None

        # 检查返回结果是否有效
        if witch_action is None or not hasattr(witch_action, 'metadata') or witch_action.metadata is None:
            print(f"⚠️ 女巫行动失败,视为不使用技能")
        else:
            if witch_action.metadata.get("use_antidote") and self.witch_has_antidote:
                if killed_player:
                    saved_player = killed_player
                    self.witch_has_antidote = False
                    await witch_agent.observe(await self.moderator.announce(f"你使用解药救了{killed_player}"))

            if witch_action.metadata.get("use_poison") and self.witch_has_poison:
                poisoned_player = witch_action.metadata.get("target_name")
                if poisoned_player:
                    # 校验：毒杀目标必须是仍然存活的玩家，避免毒已出局之人（重复计死）
                    if poisoned_player in {p.name for p in self.alive_players}:
                        self.witch_has_poison = False
                        await witch_agent.observe(await self.moderator.announce(f"你使用毒药毒杀了{poisoned_player}"))
                    else:
                        print(f"⚠️ 女巫毒杀目标无效({poisoned_player})，已出局或不存在，毒药保留")
                        poisoned_player = None
        
        # 确定最终死亡玩家
        final_killed = killed_player if not saved_player else None
        
        return final_killed, poisoned_player
    
    async def hunter_phase(self, shot_by_hunter: str):
        """猎人阶段"""
        if not self.hunter:
            return None
            
        hunter_agent = self.hunter[0]
        if hunter_agent.name == shot_by_hunter:
            await self.moderator.announce("🏹 猎人发动技能，可以带走一名玩家...")
            
            hunter_action = await hunter_agent(
                structured_model=get_hunter_model_cn(self.alive_players)
            )

            # 检查返回结果是否有效
            if hunter_action is None or not hasattr(hunter_action, 'metadata') or hunter_action.metadata is None:
                print(f"⚠️ 猎人技能使用失败,视为放弃开枪")
                return None

            if hunter_action.metadata.get("shoot"):
                target = hunter_action.metadata.get("target")
                if target:
                    await self.moderator.announce(f"猎人{hunter_agent.name}开枪带走了{target}")
                    return target
                else:
                    print(f"⚠️ 猎人选择开枪但未指定目标,视为放弃")
                    return None
        
        return None
    
    def update_alive_players(self, dead_players: List[str]):
        """更新存活玩家列表"""
        for dead_name in dead_players:
            if dead_name:
                # 从存活列表移除
                self.alive_players = [p for p in self.alive_players if p.name != dead_name]
                # 从各阵营移除
                self.werewolves = [p for p in self.werewolves if p.name != dead_name]
                self.villagers = [p for p in self.villagers if p.name != dead_name]
                self.seer = [p for p in self.seer if p.name != dead_name]
                self.witch = [p for p in self.witch if p.name != dead_name]
                self.hunter = [p for p in self.hunter if p.name != dead_name]
    
    async def day_phase(self, round_num: int):
        """白天阶段"""
        await self.moderator.day_announcement(round_num)
        
        # 讨论阶段
        async with MsgHub(
            self.alive_players,
            enable_auto_broadcast=True,
            announcement=await self.moderator.announce(
                f"现在开始自由讨论。存活玩家：{format_player_list(self.alive_players)}"
            ),
        ) as all_hub:
            # 每人发言一轮
            await sequential_pipeline(self.alive_players)
            
            # 投票阶段
            all_hub.set_auto_broadcast(False)
            vote_msgs = await fanout_pipeline(
                self.alive_players,
                await self.moderator.announce("请投票选择要淘汰的玩家"),
                structured_model=get_vote_model_cn(self.alive_players),
                enable_gather=False,
            )
            
            # 统计投票
            votes = {}
            for i, vote_msg in enumerate(vote_msgs):
                # 检查vote_msg是否为None或metadata是否存在
                if vote_msg is not None and hasattr(vote_msg, 'metadata') and vote_msg.metadata is not None:
                    votes[self.alive_players[i].name] = vote_msg.metadata.get("vote")
                else:
                    # 如果返回无效,默认弃票
                    print(f"⚠️ {self.alive_players[i].name} 的投票无效,视为弃票")
                    votes[self.alive_players[i].name] = None
            
            voted_out, vote_count = majority_vote_cn(votes)
            await self.moderator.vote_result_announcement(voted_out, vote_count)
            
            return voted_out
    
    async def run_game(self):
        """运行游戏主循环"""
        try:
            await self.setup_game()
            
            for round_num in range(1, MAX_GAME_ROUND + 1):
                print(f"\n🌙 === 第{round_num}轮游戏开始 ===")
                
                # 夜晚阶段
                await self.moderator.night_announcement(round_num)
                
                # 狼人击杀
                killed_player = await self.werewolf_phase(round_num)
                
                # 预言家查验
                await self.seer_phase()
                
                # 女巫行动
                final_killed, poisoned_player = await self.witch_phase(killed_player)
                
                # 更新死亡玩家
                night_deaths = [p for p in [final_killed, poisoned_player] if p]
                self.update_alive_players(night_deaths)
                
                # 死亡公告
                await self.moderator.death_announcement(night_deaths)
                
                # 检查胜利条件
                winner = check_winning_cn(self.alive_players, self.roles)
                if winner:
                    await self.moderator.game_over_announcement(winner)
                    return
                
                # 白天阶段
                voted_out = await self.day_phase(round_num)
                
                # 猎人技能
                hunter_shot = await self.hunter_phase(voted_out)
                
                # 更新死亡玩家
                day_deaths = [p for p in [voted_out, hunter_shot] if p]
                self.update_alive_players(day_deaths)
                
                # 检查胜利条件
                winner = check_winning_cn(self.alive_players, self.roles)
                if winner:
                    await self.moderator.game_over_announcement(winner)
                    return
                
                print(f"第{round_num}轮结束，存活玩家：{format_player_list(self.alive_players)}")
        
        except Exception as e:
            print(f"❌ 游戏运行出错：{e}")
            import traceback
            traceback.print_exc()


async def main():
    """主函数"""
    print("🎮 欢迎来到三国狼人杀！")

    # 创建并运行游戏（供应商配置在 __init__ 里解析，缺 key 会直接报错）
    try:
        game = ThreeKingdomsWerewolfGame()
    except ValueError as e:
        print(f"❌ {e}")
        print("\n配置方式（PowerShell）：")
        print("  DeepSeek: $env:DEEPSEEK_API_KEY='sk-xxx'")
        print("  百炼:     $env:DASHSCOPE_API_KEY='sk-xxx'")
        print("  可选：$env:LLM_PROVIDER='deepseek'|'dashscope' 强制指定")
        print("  可选：$env:LLM_MODEL='xxx' 覆盖默认模型")
        return

    await game.run_game()


if __name__ == "__main__":
    asyncio.run(main())
