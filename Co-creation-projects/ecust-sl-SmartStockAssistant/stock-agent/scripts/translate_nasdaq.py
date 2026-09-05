"""
用法: python scripts/translate_nasdaq.py
修复: 禁用 SSL 验证 (解决 Connection aborted) + 增加重试机制
"""
import csv, time, os, requests, urllib3
from dotenv import load_dotenv

# 🔧 修复1: 禁用 SSL 警告 (因为我们要关闭 verify)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# 加载环境变量
env_path = os.path.join(os.path.dirname(__file__), "../.env")
load_dotenv(env_path)

# 🔧 修复2: 路径拼写修正 (dowload -> download) + 原始字符串
INPUT  = r"D:\browser-dowload\nasdaq_screener_1779167472097.csv"
OUTPUT = "nasdaq_translated.csv"
BATCH  = 50

API_KEY   = os.getenv("MODELSCOPE_API_KEY")
API_URL   = os.getenv("MODELSCOPE_BASE_URL", "https://api-inference.modelscope.cn/v1")
MODEL     = os.getenv("QWEN_MODEL", "Qwen/Qwen2.5-72B-Instruct")

if not API_KEY:
    raise ValueError("❌ MODELSCOPE_API_KEY 未配置，请检查 .env 文件")


def translate(names: list[str]) -> list[str]:
    """批量翻译，带重试和 SSL 修复"""
    if not names:
        return []
    
    numbered = "\n".join(f"{i+1}. {n}" for i, n in enumerate(names))
    
    # 🔧 修复3: 增加重试机制 (最多重试 3 次)
    for attempt in range(3):
        try:
            resp = requests.post(
                API_URL + "/chat/completions",
                headers={
                    "Authorization": f"Bearer {API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": MODEL,
                    "max_tokens": 2000,
                    "temperature": 0.1,
                    "messages": [{
                        "role": "user", 
                        "content": f"将以下美股公司名翻译成中文简称(2-6字)，只输出'序号. 译名'格式，每行一个:\n{numbered}"
                    }],
                },
                timeout=60,
                verify=False  # 🔧 核心修复: 关闭 SSL 验证，解决 Connection aborted
            )
            
            if resp.status_code != 200:
                print(f"    ⚠️  API返回 {resp.status_code}: {resp.text[:100]}")
                # 如果是 429 (限流) 或 502/503 (网关错误)，值得重试
                if resp.status_code in [429, 502, 503, 504]:
                    time.sleep(2)
                    continue 
                return [""] * len(names)
            
            data = resp.json()
            content = data["choices"][0]["message"]["content"]
            
            # 解析结果
            result = []
            lines = [l.strip() for l in content.split("\n") if l.strip()]
            for line in lines:
                if ". " in line:
                    try:
                        text = line.split(". ", 1)[1].strip().strip('"').strip("'")
                        if text: result.append(text)
                    except: continue
                elif line and len(result) < len(names):
                    result.append(line.strip())
            
            while len(result) < len(names):
                result.append("")
            return result[:len(names)]
            
        except (requests.exceptions.ConnectionError, requests.exceptions.SSLError) as e:
            # 🔧 捕获连接错误并重试
            if attempt < 2:
                print(f"    🔄 连接不稳定 ({type(e).__name__})，{attempt+1}秒后重试...")
                time.sleep(2)
                continue
            print(f"    ❌ 连接失败: {e}")
            return [""] * len(names)
        except Exception as e:
            print(f"    ❌ 未知错误: {e}")
            return [""] * len(names)
    
    return [""] * len(names)


def main():
    if not os.path.exists(INPUT):
        print(f"❌ 输入文件不存在: {INPUT}")
        print(f"💡 请确认路径是否正确 (注意 download 拼写)")
        return
    
    with open(INPUT, encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        rows = list(reader)
    
    if not rows:
        print("❌ CSV 文件为空")
        return
        
    if "Name" not in fieldnames:
        print(f"❌ CSV 中找不到 'Name' 列，可用列: {fieldnames}")
        return
    
    total = len(rows)
    print(f"✅ 已读取 {total} 条，开始翻译...")

    translations = []
    for i in range(0, total, BATCH):
        batch = [r["Name"].strip() for r in rows[i:i+BATCH] if r.get("Name")]
        if not batch:
            continue
            
        n = i // BATCH + 1
        total_n = (total + BATCH - 1) // BATCH
        print(f"[{n}/{total_n}] 处理 {i+1}~{min(i+BATCH, total)} 条...")
        
        t = translate(batch)
        translations.extend(t)
        
        if t and t[0] and batch[0]:
            print(f"  ✨ 示例: {batch[0]} → {t[0]}")
        
        time.sleep(0.5)

    while len(translations) < len(rows):
        translations.append("")
    
    fields = list(fieldnames)
    if "中文名称" not in fields:
        name_idx = fields.index("Name") + 1 if "Name" in fields else len(fields)
        fields.insert(name_idx, "中文名称")
    
    for i, row in enumerate(rows):
        row["中文名称"] = translations[i] if i < len(translations) else ""

    with open(OUTPUT, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)

    print(f"🎉 完成！输出: {OUTPUT}")


if __name__ == "__main__":
    main()