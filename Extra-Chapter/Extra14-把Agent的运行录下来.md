# Extra14 - 把 Agent 的运行录下来：离线复现与排错

## 为什么需要这一章

写 Agent 的人都会遇到这两个问题：

**第一个**：「它刚才为什么把我那个文件改了？」你去问它，它会给你一段通顺的解释。但那段解释是它**根据自己上下文窗口里的印象**复述出来的，而那份印象里没有工具的返回值、没有 shell 的退出码、也没有那些没人提过但确实被改掉的文件。所以答案听起来很确定，有时候是错的——而「听起来很确定的错答案」比「不知道」更糟。

**第二个**：「昨天那次跑挂了，还能复现吗？」重跑一遍要花 token，而且模型未必再做同样的选择。你跑出来的是**另一次**运行，不是那一次。

这两个问题的共同点是：**没有证据**。日志是人挑着写的，transcript 是对话的投影，都不是那次运行本身。这一章讲的就是怎么把「那次运行本身」留下来。

## 思路：在模型请求这一层录，而不是在框架里埋点

常见做法是往框架里埋点：LangChain 的 callback handler、某个 SDK 的 tracing decorator、monkey patch 掉客户端。能用，但有三个结构性问题：

1. **每个框架都得写一套。** 而钩子接口的变化速度，往往比包装它们的集成层还快。
2. **录到的是「框架理解后的东西」**，不是线上真正发出去的内容。框架已经做过归一化、重试、流式分片合并了。
3. **它改变了被测程序本身。** 你录下来的那次运行，是「带着你的埋点」的运行。

换个位置：**在 Agent 与模型服务之间的那条 HTTP 边界上录**，而且在进程外录。

具体做法是把 Agent 当子进程启动，只给这个子进程改模型服务的地址，指向本地一个代理；代理把逐字节的请求与响应原样存下来。Agent 的代码一行都不用动。

这不是新发明——Ruby 的 [VCR](https://github.com/vcr/vcr)、JavaScript 的 [Polly.JS](https://github.com/Netflix/pollyjs) 二十年来一直用这招给 HTTP 测试做「磁带」。只是现在有了一条所有 Agent 框架都共有的边界：调模型。

## 一次完整的录制与重放

以 [OrcaReplay](https://github.com/Continuum-AI-Corp/OrcaReplay)（Apache-2.0，Node 20+）为例：

```bash
npm i -g orcareplay          # 装完的命令名是 orca，不是 orcareplay
```

录：

```console
$ orca record generic-openai -- python my_agent.py
info recorded run=run_8f21c3 events=41 exit=0
```

放：

```console
$ orca replay last
info replaying exchanges=6 egress=blocked
info replay.done reused=6/6 exact=6 divergences=0 exit=0
```

第二条命令里**一次模型都没调、也不需要 API key**。Agent 自己的代码、控制流、工具调用全都真跑了一遍，只有模型的回复是从录像里取的。

最后那行数字是可以核对的结论，不是感觉：

- `reused=6/6` —— 6 次交换全部命中录像；
- `exact=6` —— 6 次请求与录下来的**逐字节相同**；
- `divergences=0` —— 没有漂移。

如果某次请求和录像对不上，它会报出来并说差了多少字符，而不是悄悄放过。这一点很重要：**如果比对前先做归一化，那「完全一致」和「碰巧蒙对」就分不出来了。**

## 一个容易被忽略的细节：每个框架读的环境变量不一样

这是实际做适配时最费时间的地方，也是这一章真正值钱的部分。「把模型地址指向代理」听起来只有一种做法，其实至少有三类：

**第一类：读标准环境变量的。** 大多数 Python 框架最终落到 `OpenAI()` 且不传 `base_url`，于是 SDK 读 `OPENAI_BASE_URL`。Haystack、Google ADK（走 LiteLlm）、promptflow 的 prompty（`type: openai` 走 `OpenAIConnection.from_env()`）都属于这一类，零改动就能录。

**第二类：自己手写了优先级的。** 这类最容易踩坑，因为它和 SDK 的默认行为**不一致**：

- **PraisonAI** 在 `openai_client.py` 里写的是
  `base_url or os.environ.get("OPENAI_API_BASE") or os.environ.get("OPENAI_BASE_URL")`
  —— `OPENAI_API_BASE` **优先于** `OPENAI_BASE_URL`。两个都设了的话，生效的是前者。
- **goose** 则是 `OPENAI_HOST` 压过 `OPENAI_BASE_URL`；Anthropic 那侧只认 `ANTHROPIC_HOST`。

只看 SDK 文档的人，会在这里调错变量并怀疑人生。

**第三类：地址写死在自己的配置里，根本不读环境变量的。** 比如 **nanobot**：它的 `ProviderConfig` 直接把 `api_base` 存在 `config.json` 里，整个包里 `OPENAI_BASE_URL` 一次都没出现；**mistral-vibe** 同理，默认 `https://api.mistral.ai/v1` 写在 schema 里。Cursor、Kilo 也是这一类。

第三类的解法不是放弃，而是**换一个方向**：不去改 Agent 的环境，而是起一个固定端口的代理，然后在 Agent 自己的配置里把 provider 指过去。

```bash
orca attach --port 8080       # 代理监听在一个你指定的端口
```

然后在框架自己的配置里把 provider 的 `api_base` 填成 `http://127.0.0.1:8080/v1` 就行。有些框架甚至天然给你留了口子——mistral-vibe 内置了一个指向 `http://127.0.0.1:8080/v1` 的 `llamacpp` provider，把活跃模型切到它，**一行配置都不用改**就能录。

> **小结**：适配一个新框架时，第一件事不是写代码，是去它的源码里 `grep base_url`，看它属于上面哪一类。

## 录下来之后能干什么

### 1. 把「为什么」变成有证据的回答

录像里有因果边。问「哪一步把这个文件改了」时，不要去读整条两百个事件的时间线，而是沿因果链直接定位：

```
14  TOOL   file_editor   {"command":"str_replace","path":".../tsconfig.json"}
15  SHELL  npm run build  exit 2
16  FILE   tsconfig.json  modified +2 −2
```

这里有个值得学的工程习惯：好的实现会把每条因果边标成 **`recorded`（录到的）** 还是 **`inferred`（查询时按某条规则推出来的）**，并要求回答时把两者分开：

> ✅「录像显示第 14 步的 `rm` 删掉了它。」
> ✅「从时间上看像是第 14 步的 `rm`——这条边是推断的，不是录到的。」
> ❌「第 14 步删掉了它。」（当这条边其实是推断出来的时候）

把「观察到的」和「推出来的」压成同一句自信的话，正是这套工具要防的事。

### 2. 把一次翻车变成别人能跑的东西

录像是文件。同事、或者 issue 里的维护者，**不用你的 key、不花钱**就能把那次会话原样再跑一遍。Bug 报告从「一段描述」变成「一个可执行的产物」。

### 3. 把它放进 CI 当回归用例

重放不花钱、不联网，所以可以每次提交都跑。带 LLM 的链路平时最难做的就是这块——真调模型既贵又不稳定，于是大家干脆不测。

## 三条必须说清楚的边界

这一章如果只讲好处就是不诚实的。有三件事一定要知道：

**一、`egress=blocked` 挡的是模型侧出网，不是网络隔离。** 重放时模型不会被调用，但 **Agent 录下来的工具调用会真的再执行一次**。那次跑过 `curl`、装过包、写过数据库的，重放会再干一遍。**它不是沙箱。** 真要隔离，得把它放进网络隔离的容器里跑。

**二、重放成功 ≠ 确定性结论。** 模型并没有被重新提问，是把录下的回复喂回去。所以它能回答「录下的那次还能不能复现」，答不了「重新跑一次是不是还会失败」——后者需要真的跑几次。

**三、录像里有那次运行的全部内容。** 提示词、返回值、你贴进去的东西，全在里面。往外发之前必须先脱敏，而且脱敏工具只能匹配已知的密钥形态和高熵字符串，**它不知道某个内网域名或客户名字是机密**。所以脱敏之后还要人看一眼。

另外还有两个能力边界：模型地址写死且会校验证书的 Agent，需要 TLS 拦截甚至根本录不到；**没录过的会话是找不回来的**——这也是为什么值得在事情还没出问题的时候就开始录。

## 动手练习

1. 挑一个你正在用的 Agent 框架，去源码里 `grep -rn "base_url\|OPENAI_BASE_URL"`，判断它属于上面三类中的哪一类。
2. 录一次会话，然后**把网络断掉**再重放，看 `reused` / `exact` / `divergences` 三个数。
3. 故意改一下 prompt 里的一个字再重放，观察它是否报出 divergence、差了多少字符——体会一下「逐字节比对」和「归一化后比对」的区别。

## 参考

- [VCR](https://github.com/vcr/vcr) —— 最早把 HTTP 录制/回放做成测试基础设施的库
- [Polly.JS](https://github.com/Netflix/pollyjs) —— Netflix 的 JavaScript 版本，带请求匹配规则
- [OrcaReplay](https://github.com/Continuum-AI-Corp/OrcaReplay) —— 本章示例所用的实现，Apache-2.0
