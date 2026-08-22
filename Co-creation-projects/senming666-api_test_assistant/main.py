"""
智能API测试助手 - 命令行入口

把五个 Agent 串成完整流程：
解析 → 生成 → 执行 → 验证 → 报告
"""

import sys

# Windows 中文控制台默认是 GBK，先重配为 UTF-8，否则打印中文会崩
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

import argparse
from dotenv import load_dotenv

# 关键：先加载 .env，再 import Agent（Agent 实例化时要读环境变量）
load_dotenv()

from src.agents.parser_agent import ParserAgent
from src.agents.generator_agent import GeneratorAgent
from src.agents.executor_agent import ExecutorAgent
from src.agents.validator_agent import ValidatorAgent
from src.agents.reporter_agent import ReporterAgent
from src.config import REPORT_OUTPUT_DIR


def run_test(base_url, openapi_file=None, openapi_url=None, headers=None):
    """执行完整的 API 测试流程

    Args:
        base_url: 目标 API 的基础地址
        openapi_file: OpenAPI 文档路径（本地文件）
        openapi_url: OpenAPI 文档网址（从网络抓取），与 file 二选一
        headers: 全局请求头（可选），如认证信息

    Returns:
        报告文件的保存路径
    """
    print("=" * 50)
    print("开始 API 测试流程")
    print("=" * 50)

    # ① 解析文档（优先用 URL，否则用本地文件）
    parser = ParserAgent()
    if openapi_url:
        endpoints = parser.parse_url(openapi_url)
    else:
        endpoints = parser.parse_file(openapi_file)

    # 没有解析出任何接口，说明文档抓取/解析失败，直接退出
    if not endpoints:
        print("❌ 未能解析出任何接口，请检查文档地址或内容是否正确")
        return None

    print(f"[1/5] 解析完成：发现 {len(endpoints)} 个接口")

    # ② 生成用例（每个接口都生成，用 extend 合并成一个大列表）
    generator = GeneratorAgent()
    all_cases = []
    for endpoint in endpoints:
        cases = generator.generate(endpoint)
        all_cases.extend(cases)
    print(f"[2/5] 生成完成：共 {len(all_cases)} 个测试用例")

    # ③ 执行测试（传入认证头）
    executor = ExecutorAgent()
    execution_results = executor.execute(all_cases, base_url, headers=headers)
    print(f"[3/5] 执行完成：已发送 {len(execution_results)} 个请求")

    # ④ 验证结果
    validator = ValidatorAgent()
    validated_results = validator.validate(execution_results)
    print(f"[4/5] 验证完成")

    # ⑤ 生成并保存报告（HTML + Markdown 两种格式）
    reporter = ReporterAgent()
    summary = reporter.summarize(validated_results)
    html = reporter.generate_html(validated_results)
    markdown = reporter.generate_markdown(validated_results)

    import os
    os.makedirs(REPORT_OUTPUT_DIR, exist_ok=True)
    html_path = os.path.join(REPORT_OUTPUT_DIR, "report.html")
    md_path = os.path.join(REPORT_OUTPUT_DIR, "report.md")
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html)
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(markdown)

    print(f"[5/5] 报告已生成：{html_path} 和 {md_path}")
    print("=" * 50)
    print(f"测试结果：总数 {summary['total']}，"
          f"通过 {summary['passed']}，失败 {summary['failed']}，"
          f"通过率 {summary['pass_rate']}%")
    print("=" * 50)

    return html_path


def main():
    # 解析命令行参数
    parser = argparse.ArgumentParser(description="智能API测试助手")
    parser.add_argument("--file", help="OpenAPI 文档路径（本地文件）")
    parser.add_argument("--url", help="OpenAPI 文档网址（从网络抓取）")
    parser.add_argument("--base-url", required=True, help="目标 API 基础地址")
    parser.add_argument("--header", action="append",
                        help="自定义请求头，格式 'Key: Value'，可多次使用，如 --header 'Authorization: Bearer xxx'")
    args = parser.parse_args()

    # --file 和 --url 必须二选一
    if not args.file and not args.url:
        parser.error("必须提供 --file 或 --url 之一")
    if args.file and args.url:
        parser.error("--file 和 --url 只能选一个")

    # 解析请求头 "Key: Value" → dict
    headers = {}
    if args.header:
        for h in args.header:
            if ":" in h:
                key, value = h.split(":", 1)
                headers[key.strip()] = value.strip()
            else:
                parser.error(f"请求头格式错误（应为 'Key: Value'）：{h}")

    run_test(base_url=args.base_url, openapi_file=args.file,
             openapi_url=args.url, headers=headers)


if __name__ == "__main__":
    main()
