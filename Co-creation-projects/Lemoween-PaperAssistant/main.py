"""论文撰写助手入口"""
import logging
import sys
from pathlib import Path

from dotenv import load_dotenv

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-5s | %(name)s | %(message)s",
    datefmt="%H:%M:%S",
)

load_dotenv()

from agent import PaperAssistantAgent
from config import Configuration
from hello_agents import HelloAgentsLLM


def main():
    topic = sys.argv[1] if len(sys.argv) > 1 else (
        "大语言模型在学术写作辅助中的应用与挑战"
    )

    print("=" * 70)
    print(f"📝 论文主题：{topic}")
    print("=" * 70)

    config = Configuration.from_env()

    # LLM 信息从 HelloAgentsLLM 自动检测结果中读取
    try:
        llm = HelloAgentsLLM(temperature=0.0)
        llm_provider = llm.provider
        llm_model = llm.model
    except Exception as exc:
        llm_provider = "未配置"
        llm_model = f"（错误：{exc}）"

    # Paper Search MCP 命令
    mcp_command = config.resolve_paper_search_mcp_command()

    print(f"\n配置摘要：")
    print(f"  LLM Provider   : {llm_provider}")
    print(f"  LLM Model      : {llm_model}")
    print(f"  论文类型        : {config.paper_type.value}")
    print(f"  引用格式        : {config.citation_style.value}")
    print(f"  目标章节数      : {config.target_sections}")
    print(f"  每章目标字数    : {config.target_words_per_section}")
    print(f"  每章参考文献    : {config.max_references_per_section}")
    print(f"  论文库路径      : {config.paper_library_path}")
    print(f"  Notes 工作区    : {config.notes_workspace}")
    print(f"  Memory 用户     : {config.memory_user_id}")
    print(f"  PDF 下载        : {config.pdf_download_enabled}")
    print(f"  Paper Search MCP: {mcp_command or '（未配置）'}")

    assistant = PaperAssistantAgent(config=config)
    result = assistant.run(topic)

    # 输出
    print("\n" + "=" * 70)
    print("📊 撰写完成")
    print("=" * 70)
    print(f"  论文章节数      : {len(result.sections)}")
    print(f"  参考文献总数    : {len(result.references)}")
    print(f"  已下载 PDF      : "
          f"{sum(1 for r in result.references if r.get('indexed'))}")
    print(f"  审校意见长度    : {len(result.review_notes)} 字")

    stats = result.library_stats
    print(f"  论文库统计：")
    print(f"    - 命名空间    : {stats.get('rag_namespace')}")
    print(f"    - 已索引论文  : {stats.get('indexed_papers')}")

    # 保存
    output_dir = Path("./workspace/output")
    output_dir.mkdir(parents=True, exist_ok=True)

    safe_topic = "".join(c for c in topic[:30] if c.isalnum() or c in "-_")
    paper_file = output_dir / f"paper_{safe_topic}.md"
    review_file = output_dir / f"review_{safe_topic}.md"

    paper_file.write_text(result.paper_markdown, encoding="utf-8")
    review_file.write_text(result.review_notes, encoding="utf-8")

    print(f"\n📄 论文已保存：{paper_file}")
    print(f"📄 审校意见：  {review_file}")
    print("\n" + "=" * 70)
    print("论文预览（前 2000 字）：")
    print("=" * 70)
    print(result.paper_markdown[:2000])
    print("..." if len(result.paper_markdown) > 2000 else "")


if __name__ == "__main__":
    main()