# 代码审计报告

## 概览

| 项目 | 值 |
|---|---|
| 审计文件 | data/vulnerable_sample.py |
| 规则扫描命中数 | 10 |
| 污点链路数 | 6 |
| 研判后确认漏洞数 | 4（真阳性）/ 4（存疑）/ 1（误报） |

**严重/高危规则命中 8 条**，全部经 llm_verify 研判，结果如下表：

| 行号 | 规则 | 风险等级 | 研判结论 |
|---|---|---|---|
| 15 | VULN-SECRET | 低危 | 误报（示例占位符） |
| 16 | VULN-SECRET | 高危 | 真阳性 |
| 30 | VULN-CMDI | 高危 | 存疑 |
| 37 | VULN-EVAL | 严重 | 真阳性 |
| 43 | VULN-DESER | 严重 | 存疑 |
| 49 | VULN-SHELLTRUE | 中危 | 存疑 |
| 56 | VULN-YAML | 高危 | 真阳性 |
| 68 | VULN-TLS | 高危 | 真阳性 |

## 漏洞详情

### [1] 硬编码密钥（vulnerable_sample.py:15）
- 风险等级: 低危
- 研判结论: 误报
- 代码片段: `API_KEY = "sk-live-abcdef1234567890"`
- 风险说明: 字符串为 "sk-live-" 前缀加顺序字符 "abcdef1234567890"，明显是示例/占位符，并非真实有效密钥。
- 修复建议: 示例代码可保留，但建议改用 `os.environ["API_KEY"]` 读取环境变量，并加注释说明。

### [2] 硬编码数据库密码（vulnerable_sample.py:16）
- 风险等级: 高危
- 研判结论: 真阳性
- 代码片段: `DB_PASSWORD = "root123456"`
- 风险说明: 数据库密码明文写入源码，代码泄露后攻击者可直接连接数据库窃取或篡改数据。
- 修复建议: 将密码移入环境变量或密钥管理服务（Vault/KMS），并**立即更换该密码**。

### [3] 命令注入（vulnerable_sample.py:23，污点链路）
- 风险等级: 严重
- 研判结论: 真阳性（污点追踪确认）
- 代码片段: `cur.execute("SELECT * FROM users WHERE id = " + uid)`
- 风险说明: 污点追踪确认外部输入 `uid`（source: 行20）未经清洗直接拼接到 SQL 语句并执行（sink: 行23），存在 **SQL 注入** 风险，可绕过认证、拖库、篡改数据。
- 修复建议: 使用参数化查询：`cur.execute("SELECT * FROM users WHERE id = %s", (uid,))`，并对 uid 做类型/格式校验。

### [4] 命令注入（vulnerable_sample.py:30，污点链路）
- 风险等级: 高危
- 研判结论: 存疑（污点链路存在，但需确认 host 是否完全外部可控）
- 代码片段: `os.system("ping -c 1 " + host)`
- 风险说明: `host` 经污点追踪确认来源于外部输入，字符串拼接进 `os.system`，若未校验则攻击者可注入 `; rm -rf /` 等恶意命令。
- 修复建议: 对 host 做白名单/正则校验（如仅允许 IP 或合法域名），并改用 `subprocess.run(["ping", "-c", "1", host], shell=False)` 传参式调用。

### [5] 动态代码执行（vulnerable_sample.py:37，污点链路）
- 风险等级: 严重
- 研判结论: 真阳性
- 代码片段: `return str(eval(expr))`
- 风险说明: 污点追踪确认 `expr`（source: 行36）直接流入 `eval`，若来源可控则导致**任意代码执行**（RCE），完全控制服务器。
- 修复建议: 彻底移除 `eval`，改用 `ast.literal_eval` 解析常量表达式，或改用白名单映射实现业务逻辑。

### [6] 不安全反序列化（vulnerable_sample.py:43，污点链路）
- 风险等级: 严重
- 研判结论: 存疑（污点链路确认 data 来源外部，但需确认是否有完整性校验）
- 代码片段: `return pickle.loads(data)`
- 风险说明: 污点追踪确认 `data` 来源于外部输入，pickle 反序列化不可信数据可通过构造恶意 pickle 字节流实现**任意代码执行**。
- 修复建议: 避免用 pickle 处理不可信输入，改用 JSON 等安全格式；如必须使用，需对数据进行 HMAC 签名验证。

### [7] 危险 shell 调用（vulnerable_sample.py:49，污点链路）
- 风险等级: 中危
- 研判结论: 存疑
- 代码片段: `subprocess.call(cmd, shell=True)`
- 风险说明: `shell=True` 本身是危险编码习惯，且污点追踪显示 `cmd` 来源于外部输入，若包含 shell 元字符则存在命令注入。
- 修复建议: 改为 `shell=False` 并传递参数列表；若必须保留 shell，确保 cmd 为静态字符串且不拼接外部输入。

### [8] 不安全 YAML 反序列化（vulnerable_sample.py:56，污点链路）
- 风险等级: 高危
- 研判结论: 真阳性
- 代码片段: `return yaml.load(text)`
- 风险说明: `yaml.load` 未指定 `SafeLoader`，在 PyYAML < 5.4 中默认使用不安全 Loader，可构造任意 Python 对象导致 RCE。污点追踪确认 `text` 来源外部。
- 修复建议: 改用 `yaml.safe_load(text)`，或升级 PyYAML ≥ 5.4 并显式指定 `Loader=yaml.SafeLoader`。

### [9] TLS 证书验证关闭（vulnerable_sample.py:68）
- 风险等级: 高危
- 研判结论: 真阳性
- 代码片段: `return requests.get(url, verify=False).text`
- 风险说明: 关闭 TLS 证书校验使请求易受中间人攻击（MITM），导致传输中的敏感数据被窃取或篡改。
- 修复建议: 移除 `verify=False`（默认即为 `True`），或配置受信任 CA 证书路径：`verify="/path/to/ca-bundle.crt"`。

### [10] 弱随机数（vulnerable_sample.py:60）
- 风险等级: 低危
- 研判结论: 规则命中（低危，未达 llm_verify 阈值）
- 代码片段: `return str(random.randint(100000, 999999))`
- 风险说明: `random` 模块非密码学安全随机源，若用于验证码/Token 等安全场景可被预测。
- 修复建议: 安全场景改用 `secrets.randbelow(900000) + 100000` 或 `secrets.token_hex()`。

### [11] 弱哈希算法（vulnerable_sample.py:64）
- 风险等级: 中危
- 研判结论: 规则命中（中危，未达 llm_verify 阈值）
- 代码片段: `return hashlib.md5(pw.encode()).hexdigest()`
- 风险说明: MD5 已破解，不应用于密码哈希，彩虹表/碰撞攻击可轻易还原。
- 修复建议: 改用 `bcrypt`、`argon2` 或 `hashlib.pbkdf2_hmac`（加盐 + 高迭代次数）。

## 总结

`data/vulnerable_sample.py` 整体安全状况**较差**，存在 4 个确认的真阳性高危/严重漏洞（硬编码 DB 密码、eval 动态执行、不安全 YAML 反序列化、TLS 校验关闭）以及 4 个存疑漏洞（SQL 注入、命令注入、pickle 反序列化、shell=True），另有 2 个低/中危的弱随机数与弱哈希问题。文件几乎涵盖了 OWASP Top 10 中的大部分风险类别。最优先修复项为：**立即移除 eval() 调用（行37）、修复 SQL 注入改为参数化查询（行23）、移除硬编码 DB 密码（行16）、改用 yaml.safe_load（行56）**，这四项均可在短时间内完成且能消除最严重的攻击面。