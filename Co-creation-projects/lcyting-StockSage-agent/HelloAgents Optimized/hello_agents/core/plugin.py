"""插件系统 — Plugin 基类、PluginRegistry、钩子系统"""

from __future__ import annotations
import importlib.metadata
import logging
from typing import TYPE_CHECKING, Callable, Dict, List, Type

if TYPE_CHECKING:
    from .agent import Agent
    from ..tools.base import Tool

logger = logging.getLogger(__name__)


HOOK_BEFORE_AGENT_RUN = "agent_before_run"
HOOK_AFTER_AGENT_RUN = "agent_after_run"
HOOK_BEFORE_TOOL_EXEC = "tool_before_exec"
HOOK_AFTER_TOOL_EXEC = "tool_after_exec"
HOOK_BEFORE_LLM_CALL = "llm_before_call"
HOOK_AFTER_LLM_CALL = "llm_after_call"

ALL_HOOKS = frozenset(
    {
        HOOK_BEFORE_AGENT_RUN,
        HOOK_AFTER_AGENT_RUN,
        HOOK_BEFORE_TOOL_EXEC,
        HOOK_AFTER_TOOL_EXEC,
        HOOK_BEFORE_LLM_CALL,
        HOOK_AFTER_LLM_CALL,
    }
)


class Plugin:
    """插件基类。第三方插件应继承此类。"""

    name: str = ""
    version: str = "0.1.0"
    description: str = ""

    def on_load(self, registry: "PluginRegistry") -> None:
        """插件加载时回调。在此注册 Agent、Tool、Hook 等。"""

    def on_unload(self, registry: "PluginRegistry") -> None:
        """插件卸载时回调。清理注册的资源。"""


class PluginRegistry:
    """插件注册中心 — 管理 Agent/Tool/Provider 工厂 + 钩子"""

    def __init__(self):
        self.agents: Dict[str, Type["Agent"]] = {}
        self.tools: Dict[str, Type["Tool"]] = {}
        self.providers: Dict[str, Type] = {}
        self._plugins: Dict[str, Plugin] = {}
        self._hooks: Dict[str, List[Callable]] = {h: [] for h in ALL_HOOKS}

    # ── 注册 ──

    def register_agent(self, name: str, cls: Type["Agent"]) -> None:
        self.agents[name] = cls
        logger.info(f"插件注册 Agent: {name} → {cls.__module__}.{cls.__qualname__}")

    def register_tool(self, name: str, cls: Type["Tool"]) -> None:
        self.tools[name] = cls
        logger.info(f"插件注册 Tool: {name} → {cls.__module__}.{cls.__qualname__}")

    def register_provider(self, name: str, cls: Type) -> None:
        self.providers[name] = cls
        logger.info(f"插件注册 Provider: {name} → {cls.__module__}.{cls.__qualname__}")

    def register_hook(self, hook_name: str, fn: Callable) -> None:
        if hook_name not in ALL_HOOKS:
            logger.warning(f"未知钩子: {hook_name}，可用: {sorted(ALL_HOOKS)}")
            return
        self._hooks[hook_name].append(fn)

    def unregister_hook(self, hook_name: str, fn: Callable) -> None:
        if hook_name in self._hooks:
            self._hooks[hook_name] = [h for h in self._hooks[hook_name] if h is not fn]

    # ── 工厂 ──

    def create_agent(self, plugin_name: str, **kwargs) -> "Agent":
        cls = self.agents.get(plugin_name)
        if not cls:
            raise KeyError(
                f"未知的 Agent 类型: {plugin_name}，已注册: {list(self.agents)}"
            )
        return cls(**kwargs)

    def create_tool(self, plugin_name: str, **kwargs) -> "Tool":
        cls = self.tools.get(plugin_name)
        if not cls:
            raise KeyError(
                f"未知的 Tool 类型: {plugin_name}，已注册: {list(self.tools)}"
            )
        return cls(**kwargs)

    # ── 钩子触发 ──

    def trigger(self, hook_name: str, *args, **kwargs) -> None:
        if hook_name not in self._hooks:
            return
        for fn in self._hooks[hook_name]:
            try:
                fn(*args, **kwargs)
            except Exception:
                logger.exception(f"钩子 {hook_name} 回调 {fn} 抛出异常")

    # ── 插件生命周期 ──

    def load_plugin(self, plugin: Plugin) -> None:
        if plugin.name in self._plugins:
            logger.warning(f"插件 {plugin.name} 已加载，跳过")
            return
        try:
            plugin.on_load(self)
            self._plugins[plugin.name] = plugin
            logger.info(f"插件加载成功: {plugin.name} v{plugin.version}")
        except Exception:
            logger.exception(f"插件 {plugin.name} 加载失败")

    def unload_plugin(self, name: str) -> bool:
        plugin = self._plugins.pop(name, None)
        if not plugin:
            return False
        try:
            plugin.on_unload(self)
            logger.info(f"插件卸载成功: {name}")
        except Exception:
            logger.exception(f"插件 {name} 卸载回调异常")
        return True

    def get_loaded_plugins(self) -> List[Plugin]:
        return list(self._plugins.values())

    # ── 自动发现 ──

    def scan_entry_points(self) -> None:
        """扫描所有已安装包的 entry_points，自动注册 Agent/Tool/Provider/Plugin"""
        groups = {
            "hello_agents.agents": ("register_agent", self.register_agent),
            "hello_agents.tools": ("register_tool", self.register_tool),
            "hello_agents.providers": ("register_provider", self.register_provider),
            "hello_agents.plugins": ("load_plugin", self.load_plugin),
        }

        for group, (action, method) in groups.items():
            try:
                eps = importlib.metadata.entry_points(group=group)
            except TypeError:
                eps = importlib.metadata.entry_points().get(group, [])

            for ep in eps:
                try:
                    loaded = ep.load()
                    if action == "load_plugin":
                        if isinstance(loaded, type) and issubclass(loaded, Plugin):
                            method(loaded())
                        elif isinstance(loaded, Plugin):
                            method(loaded)
                        else:
                            logger.warning(f"插件入口点 {ep.name} 不是 Plugin 实例")
                    else:
                        method(ep.name, loaded)
                except Exception:
                    logger.exception(f"加载 entry_point {group}:{ep.name} 失败")


# 全局单例
registry = PluginRegistry()
