"""端到端索引构建 benchmark：解析 PDF → 构建索引，带分阶段计时"""
import asyncio
import glob
import logging
import time

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

from backend.tools.parse_pdf import parse_pdf
from backend.tools.build_vector_index import build_vector_index


async def main():
    pdfs = sorted(glob.glob("data/uploads/*.pdf"))
    if not pdfs:
        print("没有找到 PDF")
        return
    pdf_path = pdfs[0]
    print(f"\n=== 测试 PDF: {pdf_path} ===\n")

    # 1. 解析 PDF
    t0 = time.perf_counter()
    parsed = await parse_pdf(file_path=pdf_path)
    t_parse = time.perf_counter()
    print(f"\n>>> parse_pdf: {t_parse - t0:.2f}s")
    print(f"    sections: {len(parsed.get('sections', []))}")
    total_chars = sum(len(s.get('content', '')) for s in parsed.get('sections', []))
    print(f"    total content chars: {total_chars}")

    # 2. 构建索引（带去重检查）
    print(f"\n>>> 开始 build_vector_index...")
    t1 = time.perf_counter()
    result = await build_vector_index(papers_json=[parsed])
    t_index = time.perf_counter()
    print(f"\n>>> build_vector_index: {t_index - t1:.2f}s")
    print(f"    result: {result}")

    # 3. 第二次（测试去重是否生效）
    print(f"\n>>> 第二次 build_vector_index（应命中去重）...")
    t2 = time.perf_counter()
    result2 = await build_vector_index(papers_json=[parsed])
    t_index2 = time.perf_counter()
    print(f"\n>>> build_vector_index (cached): {t_index2 - t2:.2f}s")
    print(f"    result: {result2}")


if __name__ == "__main__":
    asyncio.run(main())
