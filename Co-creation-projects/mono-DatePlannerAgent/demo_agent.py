# -*- coding: utf-8 -*-
"""
HelloAgents 框架接入演示：HelloAgentsLLM + ReActAgent + 高德工具注册表。

用法：
    # 1) 配置 .env（项目根目录）
    #    AMAP_KEY=你的高德Key
    #    LLM_MODEL_ID=deepseek-chat          # 或 gpt-4o-mini / qwen-plus 等
    #    LLM_API_KEY=你的LLM Key
    #    LLM_BASE_URL=https://api.deepseek.com/v1   # OpenAI 兼容地址，可选

    # 2) 安装依赖
    #    pip install hello-agents requests

    # 3) 运行（不带参数演示默认任务；可传自定义任务文本）
    #    python demo_agent.py
    #    python demo_agent.py "帮我查北京今天的天气，找一家评分高的桌游店"

    # 无 LLM Key 时用 --dry-run 仅演示工具链（不需要任何 LLM 配置）
    #    python demo_agent.py --dry-run
"""
import os
import sys

# 项目根目录（demo_agent.py 所在目录）
ROOT = os.path.dirname(os.path.abspath(__file__))


def load_env():
    """读取项目根 .env，写入环境变量（供 AMapClient 与 HelloAgentsLLM 读取）。"""
    env_path = os.path.join(ROOT, ".env")
    if os.path.exists(env_path):
        for line in open(env_path, encoding="utf-8"):
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


SYSTEM_PROMPT = (
    "你是约会行程规划助手，擅长用高德真实数据帮用户安排约会路线。\n"
    "工作步骤：\n"
    "1. 用 amap_text_search 搜索候选地点（餐厅/展览/公园/桌游等）；\n"
    "2. 用 amap_detail 查询重点候选的详情（电话/营业时间/人均/评分）；\n"
    "3. 用 amap_weather 查当天天气，判断适合室内还是户外；\n"
    "4. 用 amap_distance 计算两地点间距离和耗时，保证路线衔接合理；\n"
    "5. 最后输出一份结构化方案：推荐地点 + 理由 + 路线 + 需要确认事项。\n"
    "规则：所有信息必须来自工具返回的真实数据，不编造；"
    "工具缺失的字段（如电话/营业时间）标注“需要确认”。"
)

DEFAULT_TASK = (
    "我在北京，想找一家评分高的西餐厅约会。请先查一下北京今天的天气，"
    "搜索几家西餐厅，推荐其中评分最高的一家，并给出地址和电话。"
)


def main():
    # Windows 终端默认 GBK，先切 UTF-8，避免框架内部 emoji 输出崩溃
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:  # noqa: BLE001
        pass
    load_env()
    from date_planner.hello_tools import build_registry

    registry = build_registry()
    tools = registry.list_tools()
    print(f"== 已注册 {len(tools)} 个高德工具: {', '.join(tools)} ==")

    dry_run = "--dry-run" in sys.argv
    if dry_run:
        # 不依赖 LLM：直接演示框架工具注册 + 工具调用链（无需任何 Key）
        print("\n== dry-run 模式：演示 HelloAgents 框架工具注册表 ==")
        print(registry.get_tools_description())
        print("\n== 演示工具调用 ==")
        res = registry.execute_tool("amap_text_search", {"keywords": "西餐厅", "city": "北京"})
        print("[搜索] ", res.text if hasattr(res, "text") else res)
        res = registry.execute_tool("amap_weather", {"city": "北京"})
        print("[天气] ", res.text if hasattr(res, "text") else res)
        print("\n提示：配置 AMAP_KEY 后工具将返回真实高德数据；"
              "再配置 LLM_MODEL_ID / LLM_API_KEY 后运行 python demo_agent.py 即可进入 LLM 自动规划。")
        return

    llm_model = os.environ.get("LLM_MODEL_ID", "").strip()
    llm_key = os.environ.get("LLM_API_KEY", "").strip()
    if not llm_model or not llm_key:
        print(
            "\n[提示] 缺少 LLM 配置（LLM_MODEL_ID / LLM_API_KEY）。\n"
            "  可先用 --dry-run 演示工具链，或参考 .env.example 配置任意 OpenAI 兼容模型。"
        )
        return

    from hello_agents import HelloAgentsLLM, ReActAgent

    llm = HelloAgentsLLM(
        model=llm_model,
        api_key=llm_key,
        base_url=os.environ.get("LLM_BASE_URL", "").strip() or None,
    )
    agent = ReActAgent(
        name="date-planner-agent",
        llm=llm,
        tool_registry=registry,
        system_prompt=SYSTEM_PROMPT,
        max_steps=8,
    )

    task = " ".join(sys.argv[1:]).strip() or DEFAULT_TASK
    print(f"\n== 任务：{task} ==\n")
    result = agent.run(task)
    print("\n===== Agent 输出 =====")
    print(result)


if __name__ == "__main__":
    main()
