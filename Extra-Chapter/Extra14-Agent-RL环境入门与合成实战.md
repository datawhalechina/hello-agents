# Agent RL 环境入门：从一个任务目录到批量合成

如果你学过第十一章的 Agentic RL，应该记得 reward 函数长什么样：把模型的答案和标准答案比一比。放到 GSM8K 这种题目上，这样就够了。

真实的 Agent 不太一样。它要修代码、改配置、操作数据库，最后交上来的不是一个答案，而是一个被改过的世界。问题也跟着变了：这个世界现在对不对？谁来判断？Agent 有没有投机取巧？同样的判断能不能重复做？

回答这些问题的那套东西，就是 RL 环境。

这篇写给懂 Agent、但没接触过 RL 环境的读者，不需要强化学习基础。读完你应该能：

- 说清楚 RL 环境是什么，它和评测集、沙箱是什么关系
- 用 [Harbor](https://github.com/harbor-framework/harbor) 写出一个能跑、判分靠谱的环境
- 知道批量合成环境的流程，以及最容易在哪里翻车

关于案例：文中的经验来自我们批量合成和审查任务时踩过的坑，都做了脱敏和简化，不对应具体项目。贴出来的运行结果全部来自配套的小任务，你可以自己复现。配套代码在 [code/extra14_rl_env](../code/extra14_rl_env)，只需要 Docker，不需要 API key。

---

## 目录

- [第一章：什么都没做，也能拿 0.75 分](#第一章什么都没做也能拿-075-分)
- [第二章：RL 环境到底是什么](#第二章rl-环境到底是什么)
- [第三章：Harbor 是什么](#第三章harbor-是什么)
- [第四章：动手写第一个环境](#第四章动手写第一个环境)
- [第五章：Verifier 要过四道检查](#第五章verifier-要过四道检查)
- [第六章：怎么批量合成环境](#第六章怎么批量合成环境)
- [第七章：难度与公平](#第七章难度与公平)
- [第八章：接到评测和训练](#第八章接到评测和训练)
- [这次留下来的经验](#这次留下来的经验)
- [上线前检查清单](#上线前检查清单)
- [这一版还没覆盖的内容](#这一版还没覆盖的内容)
- [参考资料与图片来源](#参考资料与图片来源)

---

## 第一章：什么都没做，也能拿 0.75 分

我们审查任务时碰到过这样一种情况：跑一个什么都不做的空 agent，得分居然不是 0。翻开 verifier 一看，有几条测试根本没运行 agent 的代码，只是在测 verifier 自己的辅助函数，等于固定送分。

这个坑太典型了，我把它还原成一个小任务。任务是修一个订单统计脚本：退款应该从总额里扣除，脚本却把它加上去了。verifier 写了 4 条检查（注释是为了讲解加的）：

```python
def check_parser():          # 只测 verifier 自己的解析函数
    return parse_output('{"alice": 70.0}') == {"alice": 70.0}

def check_data_exists():     # 只看示例数据还在不在
    return os.path.exists("/app/orders.csv")

def check_output_is_json():  # 没修的脚本也能输出 JSON
    return isinstance(run_stats(), dict)

def check_alice_total():     # 只有这一条在测需求
    return run_stats().get("alice") == 70.0
```

单看每一条都不算离谱。现在让空 agent 跑一次：

```bash
harbor run -p tasks/order-stats-v1 -a nop
```

```text
check_parser: PASS
check_data_exists: PASS
check_output_is_json: PASS
check_alice_total: FAIL

┏━━━━━━━━┳━━━━━━━┓
┃ Reward ┃ Count ┃
┡━━━━━━━━╇━━━━━━━┩
│ 0.75   │     1 │
└────────┴───────┘
```

什么都没做，0.75 分。

如果这是评测，所有模型的分数都被白白抬高了；如果这是训练，模型什么都不学也能拿到大部分奖励。**reward 是 Agent 的学习目标，它错了，后面的一切都会稳定地学错。** 所以 RL 环境值得单独写一章。

---

## 第二章：RL 环境到底是什么

先看经典的强化学习循环。Agent 做一个动作，环境返回观测和奖励，如此往复：

<div align="center">
  <img src="./images/Extra14-figures/web-gymnasium-agent-environment-loop.png" alt="经典强化学习的 Agent 与环境交互循环" width="48%"/>
  <p><strong>图 1</strong> 经典 RL 循环。图片来源：<a href="https://github.com/Farama-Foundation/Gymnasium">Gymnasium 文档</a>（MIT 许可证）</p>
</div>

Gymnasium 把它定义成两个函数，这几乎是 RL 环境的标准接口：

```python
observation, info = env.reset(seed=42)
observation, reward, terminated, truncated, info = env.step(action)
```

这些词你其实都见过，只是在 Agent 的世界里换了个说法：

<div align="center">
  <img src="./images/Extra14-figures/01-Agent与RL术语对照.png" alt="Agent 术语和 RL 术语的对照" width="88%"/>
  <p><strong>图 2</strong> 同一件事的两套说法</p>
</div>

有三个地方初学时很容易想偏。

**第一，多数 Agent 环境只在结束时给一次 reward。** 这和上面的 `step` 不太一样。Agent 可能跑几十步、调几十次工具，中间没有人打分，等它结束后才由 verifier 统一判一次。所以写这类环境时，你通常不用实现 `step`，主要精力都在“最后怎么判”。

**第二，评测集和训练环境常常是同一批任务。** 同样的任务，跑完只看分数就是评测，把轨迹和 reward 喂给训练框架就是 RL，挑出高分轨迹就成了监督学习数据。Harbor 的 README 也把这些用途列在一起：评测 agent、构建自己的 benchmark，以及生成用于 RL 优化的 rollout。

**第三，环境不等于沙箱。** 沙箱只负责隔离。环境还包括任务说明、初始状态和判分逻辑。没有 verifier 的沙箱，只是一台干净的电脑。

什么样的环境算好？我会看这四条：

| 条件 | 意思 | 做不到会怎样 |
| --- | --- | --- |
| 可重复 | 同一个任务多跑几次，初始状态和判分标准都不变 | 分数变了，说不清是模型变了还是环境变了 |
| 隔离 | Agent 碰不到答案和判分逻辑 | 模型学会的是找答案，而不是解题 |
| 验证比解题容易 | 解题可以很难，判对错要便宜、稳定 | 判分本身不可靠，reward 就成了噪声 |
| 有区分度 | 不是谁都能过，也不是谁都过不了 | 分数不提供任何信号 |

第三条在 [EvoEnv](https://arxiv.org/abs/2605.14392) 论文里叫 solve-verify asymmetry。排序就是最直观的例子：把一堆数排好可能要费点功夫，检查排得对不对却很简单。

---

## 第三章：Harbor 是什么

[Harbor](https://github.com/harbor-framework/harbor) 是 Terminal-Bench 团队做的开源框架（Apache-2.0），用来在容器里评测和优化 agent。

对入门的人来说，它最省心的地方是不用自己写 `reset` 和 `step`。你把任务打包成一个目录，它负责启动容器、让 agent 跑完、再调用你的判分脚本。Claude Code、Codex CLI 这类命令行 agent 都已经内置支持。

先记住五个词：

| 概念 | 含义 |
| --- | --- |
| Task | 一个任务，就是一个目录 |
| Dataset | 一批任务 |
| Agent | 完成任务的程序 |
| Trial | 一个 agent 对一个任务的一次尝试，产出一个 reward |
| Job | 一批 trial，可以组合多个任务、agent 和模型 |

一个 Task 的目录长这样：

<div align="center">
  <img src="./images/Extra14-figures/02-Harbor-Task目录结构.png" alt="Harbor Task 的目录结构，以及每个部分谁能接触" width="88%"/>
  <p><strong>图 3</strong> Task 目录结构</p>
</div>

判分脚本的约定很简单：把分数写到 `/logs/verifier/reward.txt`，或者把多个分项写到 `reward.json`。

Harbor 还内置了两个特别有用的 agent，全程不调模型，也就不花 API 费用：

- **`oracle`**：运行任务自带的 `solution/solve.sh`，用来证明这道题做得出来
- **`nop`**：什么也不做，用来证明空解拿不到分

一次 Trial 的过程如下，注意两个容器之间的边界：

<div align="center">
  <img src="./images/Extra14-figures/03-Trial生命周期.png" alt="一次 Trial 的生命周期，分为 Agent 容器和 Verifier 容器两个阶段" width="88%"/>
  <p><strong>图 4</strong> 一次 Trial 里发生了什么</p>
</div>

这就是 Harbor 的 separate verifier 模式：验证时启动一个全新的容器，只放入 `tests/` 和你声明过的 artifacts。用 `harbor init` 新建任务时，默认就是这个模式。

为什么这样设计？我们吃过相反做法的亏。早期有的任务把标准答案直接打进镜像，靠文件权限和非 root 用户来防止 agent 偷看。这条防线选错了地方：答案只要和 agent 待在同一个镜像里，就总有办法漏出去，比如日志、报错信息、打包时带进去的文件。把答案挡在 agent 的容器之外，才是更稳的做法。

最后简单看一下 Harbor 在生态里的位置，这几个项目经常被放在一起讨论：

| 项目 | 定位 |
| --- | --- |
| [Gymnasium](https://github.com/Farama-Foundation/Gymnasium) | 经典 RL 的标准环境接口 |
| [OpenEnv](https://github.com/openenv/OpenEnv) | 面向 agentic RL 的隔离执行环境，提供 Gymnasium 风格的 API |
| [Prime Intellect verifiers](https://github.com/PrimeIntellect-ai/verifiers) | RL 环境与评测库 |
| [Harbor](https://github.com/harbor-framework/harbor) | 把任务打包成目录，在容器里运行各种 agent 并打分 |
| [SkyRL](https://github.com/NovaSky-AI/SkyRL) | 面向 LLM 的全栈 RL 库，负责训练这一侧，可以把 Harbor 当作环境和 reward 来源 |

本篇用 Harbor 来讲。后面讲的判分和合成思路，换到别的框架上同样适用。

---

## 第四章：动手写第一个环境

### 准备

只需要 Docker 和 Harbor。下面的结果都基于 Harbor v0.25.0。

```bash
uv tool install harbor    # 或者 pip install harbor
git clone https://github.com/datawhalechina/hello-agents.git
cd hello-agents/code/extra14_rl_env
```

### 任务长什么样

第一章的任务就在 `tasks/order-stats-v1`：

```text
order-stats-v1/
├── task.toml             # 配置
├── instruction.md        # agent 看到的任务说明
├── environment/
│   ├── Dockerfile
│   ├── stats.py          # 有 bug 的统计脚本
│   └── orders.csv        # 示例数据
├── solution/
│   └── solve.sh          # 参考解
└── tests/
    ├── test.sh           # verifier 入口
    └── check.py          # 判分逻辑
```

分别跑一下空解和参考解：

```bash
harbor run -p tasks/order-stats-v1 -a nop      # 0.75
harbor run -p tasks/order-stats-v1 -a oracle   # 1.0
```

结果保存在 `jobs/<时间>/<trial>/` 下，`verifier/reward.txt` 是分数，`verifier/test-stdout.txt` 是判分脚本的输出。

Harbor 自带的静态检查已经看出了一个问题：

```text
$ harbor lint tasks/order-stats-v1
tasks/order-stats-v1/task.toml [shared-verifier] Verifier shares the agent sandbox; set verifier.environment_mode = "separate", including shared step overrides.
```

### 用探针戳一戳 verifier

接下来是我很喜欢的一个小技巧。

既然 `oracle` 只是运行 `solve.sh`，那么换掉 `solve.sh`，就能**不花一分钱模拟各种 agent 行为**。配套的 `probe.py` 就是这么做的，它会跑这几类解法：

- `variant`：另一种正确写法，应该满分
- `shortcut`：取巧的解法，比如写死示例答案，或者不改代码只改数据，应该 0 分
- `mutant`：故意改坏一个地方，比如把退款跳过而不是扣除，不应该满分

```bash
python3 probe.py tasks/order-stats-v1
```

```text
probe                   expect  reward  result
oracle                  == 1    1.00    ok
nop                     == 0    0.75    WRONG
mutant_clamp_negative   < 1     1.00    WRONG
mutant_ignore_refund    < 1     0.75    ok
mutant_truncate         < 1     1.00    WRONG
shortcut_edit_data      == 0    1.00    WRONG
shortcut_hardcode       == 0    1.00    WRONG
variant_rewrite         == 1    1.00    ok

5 probe(s) judged wrongly
```

注意 `shortcut_edit_data`：它一行代码都没改，只是把 `orders.csv` 里的退款行抹平，就拿了满分。原因是 verifier 读的正是 agent 可以修改的那份数据。

### 修成 v2

`tasks/order-stats-v2` 改了三件事。

**第一，换成 separate verifier，只把要判的文件带过去。** agent 改的其他东西都带不进验证容器：

```toml
schema_version = "1.4"
artifacts = ["/app/stats.py"]

[verifier]
timeout_sec = 60.0
environment_mode = "separate"
```

**第二，判分数据放进 `tests/`，每条用例都含退款行。** agent 看不到这些数据，没修的脚本一条也过不了，写死示例答案也没用：

```python
CASES = {
    "refund_is_subtracted": ("basic.csv", {"dave": 170.0, "erin": 40.0}),
    "refund_only_user_goes_negative": ("refund_only.csv", {"frank": -25.0, "grace": 5.0}),
    "decimal_amounts": ("decimals.csv", {"heidi": 15.25}),
    "refund_before_order": ("refund_first.csv", {"ivan": 90.0}),
}
```

**第三，每条检查都必须真正运行候选代码。** 另外还有几个细节：

```python
def run_candidate(csv_path):
    # -I 让候选代码目录里的同名模块无法劫持解释器
    out = subprocess.run(
        [sys.executable, "-I", "/app/stats.py", csv_path],
        capture_output=True, text=True, timeout=10, cwd="/tmp",
    )
    return json.loads(out.stdout)

def matches(actual, expected):
    if set(actual) != set(expected):
        return False
    # 浮点数用容差比较，别因为精度差异冤枉正确答案
    return all(math.isclose(actual[k], expected[k], abs_tol=1e-6) for k in expected)
```

同一批探针再跑一遍：

```text
probe                   expect  reward  result
oracle                  == 1    1.00    ok
nop                     == 0    0.00    ok
mutant_clamp_negative   < 1     0.75    ok
mutant_ignore_refund    < 1     0.00    ok
mutant_truncate         < 1     0.75    ok
shortcut_edit_data      == 0    0.00    ok
shortcut_hardcode       == 0    0.00    ok
variant_rewrite         == 1    1.00    ok

0 probe(s) judged wrongly
```

<div align="center">
  <img src="./images/Extra14-figures/04-两版Verifier实测对比.png" alt="8 种解法在 v1 和 v2 两版 verifier 上的实测得分对比" width="88%"/>
  <p><strong>图 5</strong> 同样 8 种解法，v1 判错 5 种，v2 全部判对</p>
</div>

顺便看 `mutant_clamp_negative` 和 `mutant_truncate`，它们都只丢了一条检查的分（0.75），丢的正好是对应的那一条。这正是我们想要的：**改坏哪里，就只有哪里报错。**

### 看看结果

`harbor view jobs` 会启动一个网页，可以逐步查看轨迹、verifier 输出和 artifacts：

<div align="center">
  <img src="./images/Extra14-figures/web-harbor-viewer-verifier.png" alt="Harbor 结果查看页面的 Verifier 标签页" width="88%"/>
  <p><strong>图 6</strong> Harbor 的结果查看页面。图片来源：<a href="https://github.com/harbor-framework/harbor">Harbor 文档</a>（Apache-2.0 许可证），有裁剪</p>
</div>

想换成真实 agent，把 `-a` 和 `-m` 换掉就行，比如下面这条。这一步需要你自己的 API key，本篇没有跑。

```bash
harbor run -p tasks/order-stats-v2 -a claude-code -m <模型名>
```

---

## 第五章：Verifier 要过四道检查

从上一章可以提炼出四道检查，建议每个任务都过一遍：

| 检查 | 期望 | 抓的是什么 |
| --- | --- | --- |
| 参考解 | 满分 | 题目做不出来，或者 verifier 写错了 |
| 空解 | 不得分 | 白送的分数 |
| 另一种正确写法 | 也能满分 | verifier 太严，只认一种写法 |
| 单点改坏 | 只有对应的检查失败 | verifier 太松，错了也发现不了 |

很多流程只做前两道。但参考解满分只能说明“有一条路走得通”，空解零分只能说明“躺平拿不到分”，这两条都是必要条件，还不够。后两道才是在检验 verifier 判得准不准。

下面是几个我们真实碰到过的情况。

### 案例：空解拿部分分

有些测试本身没有错，比如检查基线文件还在、网络隔离生效。问题是它们通过时会加分，于是空解也能得分。

我们后来定的规则是：**这类检查通过不得分，不通过扣分。** 写成代码，就是把它们当前置条件：

```python
# 不好：环境检查和功能检查一起算分
checks = [check_env_ok, check_baseline_intact, check_feature_a, check_feature_b]
reward = sum(c() for c in checks) / len(checks)

# 更好：前置条件没过直接 0 分，过了也不加分
if not (check_env_ok() and check_baseline_intact()):
    reward = 0.0
else:
    feature_checks = [check_feature_a, check_feature_b]
    reward = sum(c() for c in feature_checks) / len(feature_checks)
```

有两点要注意。不要为了让空解变成 0 分就删功能测试，那是在掩盖问题。另外，判分脚本要把每条检查的结果都打印出来，不然空解拿了分，你都不知道是哪一条给的。

### 案例：verifier 相信了 agent 能改的东西

只要是 agent 能写的地方，都不能当证据。我们踩过的有这些：

| 表面上 | 实际上 | 修法 |
| --- | --- | --- |
| 明明有只读副本 | 测试读的却是 agent 能改的那份 | 只读 `tests/` 里的数据 |
| 用 pytest 跑测试 | 工作目录里的 `pytest.py`、`sitecustomize.py` 可以劫持它 | 换干净的容器，或者用 `python -I` |
| 用测试报告算分 | 报告缺失时按退出码推断为通过 | 报告缺失一律按失败处理 |
| 和快照对比 | 快照是 agent 跑完才拍的 | 快照提前生成，放进 `tests/` |

还有一条流程上的经验。审查报告里，**“实际发生过”和“理论上可能”要分开写**。我们有过这样的情况：审查报告说某个任务可以被攻击，分数可能虚高，可回头查轨迹，这条攻击路径根本没人走过。结构性风险该修，但不能和真实的误判混在一起统计。

### 其他常见错误

| 现象 | 问题在哪 | 怎么改 |
| --- | --- | --- |
| 报错写着 `expected X but got Y` | 只要 agent 够得着，这就是一台答案查询机 | 只写哪一项不对，不写期望值 |
| 任务目录里混进了内部清单和审查笔记 | 这些文件相当于答案，也会被打包带走 | 打包前专门扫描。agent 能读到的，都算公开内容 |
| 公式声明两项平均，实际结果却等于其中一项 | 聚合代码把 0 分项丢掉了 | 写分数时断言它等于声明的公式 |
| 测试只要求“报错就行” | 候选代码是因为另一个无关错误才报错的，也算过 | 断言错误的原因，不只断言出错 |
| 只接受一种合法顺序，或者要求题面没写的字段 | 冤枉了正确答案 | 写进题面，或者放宽判断 |

### Rule 和 Judge 怎么分工

有些东西代码判不了，比如一份报告写得好不好，这时会用 LLM 当 judge。分工原则很简单：**代码能判的，就不要交给 LLM。**

两者的结果怎么合起来，也要想清楚。假设规则检查只过了一小部分，judge 却给了满分，直接平均，分数就被抬高了。Judge 不应该能给没过的事实“洗白”。常见的做法是先过硬门槛，门槛没过就不再看 judge。

只看最终结果也不一定够。[PAE](https://arxiv.org/abs/2603.03116) 论文在 tau-bench 上做了分析：benchmark 报告的成功案例里，有 27–78% 其实存在过程违规，它们管这叫 corrupt success。加上过程门槛之后，模型的排名都变了。如果你的场景很在意过程（比如客服、金融），高风险的违规应该直接判失败，而不是扣一点分。

Harbor 提供了 [Rewardkit](https://github.com/harbor-framework/harbor/tree/main/docs-mintlify/rewardkit)，内置了常见的判分条件和 LLM judge，任务复杂时可以直接用，不必从零写。

---

## 第六章：怎么批量合成环境

训练需要足够多、足够不一样的环境，手写跟不上，于是就有了合成。

### 通用流水线

不同领域的做法有差异，但骨架大体相同：

<div align="center">
  <img src="./images/Extra14-figures/05-批量合成流水线.png" alt="批量合成环境的十步流水线，用颜色区分确定性程序、LLM 和人工判断" width="88%"/>
  <p><strong>图 7</strong> 批量合成环境的通用流水线</p>
</div>

这张图的重点是颜色。**出题可以放手交给 LLM，判断“这题合不合格”要尽量靠确定性程序**，最后再由独立的审查和人工把关。

学术界也有类似的工作，这两篇值得一读。

[Agent-World](https://arxiv.org/abs/2604.18292) 从真实主题出发，挖掘数据库、生成并验证工具，再合成可验证的任务。它讲了两种合成方法：graph-based 先得到一条合法的工具调用序列，再反推用户问题；programmatic 则直接写解题代码，用来覆盖条件分支、循环这类线性序列表达不了的逻辑。

<div align="center">
  <img src="./images/Extra14-figures/paper-agent-world-figure2.png" alt="Agent-World 论文中的环境与任务发现流水线" width="92%"/>
  <p><strong>图 8</strong> Agent-World 的环境与任务发现流水线。图片引自 <a href="https://arxiv.org/abs/2604.18292">Agent-World 论文</a> Figure 2，版权归原作者所有</p>
</div>

[EvoEnv](https://arxiv.org/abs/2605.14392) 让模型自己写环境，候选环境必须通过一层层校验才能进入训练池：先是 L1–L5 的机械检查，再是语义审查，然后按当前模型校准难度，最后去重。其中 L5 很值得借鉴：参考答案必须得分，而被扰动过的答案、格式错误的答案和类型不对的答案都不能得分，解析过程也不能泄露隐藏答案。这和上一章的四道检查是同一个思路。

<div align="center">
  <img src="./images/Extra14-figures/paper-evoenv-figure1.png" alt="EvoEnv 论文中的环境合成与准入流程总览" width="92%"/>
  <p><strong>图 9</strong> EvoEnv 总览，第 4 步是准入校验。图片引自 <a href="https://arxiv.org/abs/2605.14392">EvoEnv 论文</a> Figure 1（CC BY-NC-ND 4.0）</p>
</div>

### 跑一个最小的合成脚本

配套的 `synth/synthesize.py` 演示了这条流程的骨架。真实流水线里，“写任务包”通常由 LLM 完成；这里用模板代替，这样不需要 API key，重点放在门禁上。

种子长这样，每个种子描述一种业务规则：

```json
{"id": "refund", "event": "refund", "meaning": "退款，应从总额中扣除", "multiplier": -1}
```

我故意混进去 3 个有问题的种子，然后运行：

```bash
python3 synth/synthesize.py synth/seeds.json
```

```text
seed          static  dedup  oracle  nop   shortcut  decision
refund        ok      ok     1.00    0.00  0.00      accept
cancelled     ok      ok     1.00    0.00  0.00      accept
promo         ok      ok     1.00    0.00  0.00      accept
voided        ok      dup    -       -     -         reject: same behavior as cancelled
no-bug        ok      ok     1.00    1.00  -         reject: doing nothing scores
bad-solution  ok      ok     0.00    -     -         reject: reference solution fails
```

三个问题种子都被拦下来了：

- **`voided`**：换了个说法，行为和 `cancelled` 完全一样，算重复
- **`no-bug`**：题目本身没有 bug，空解直接满分
- **`bad-solution`**：参考解和判分标准对不上

还有一个细节：隐藏用例的答案由 `gold()` 函数算出来，而不是由作者手写。能用程序算答案的地方，都尽量这么做。

### 案例：修复漂移

这是我们印象最深的一个坑。

任务生成之后，如果 oracle 没过，流程会让 agent 自动修。我们当时写的修复目标是“让 reward 变成 1”，可改的范围也没限制好，而任务、参考解和测试本来就出自同一个 agent。结果就是，分数上去了，verifier 和任务说明却慢慢对不上了。它修出了一个自洽的世界，只是这个世界已经不是题面说的那个了。

后来我们定了两条规则：

- **`instruction.md` 是唯一的真相。** Agent 能看到的只有题面，所以判分要以题面为准。任何中间产物，比如生成流程自己写的合同文档，都不能凌驾于题面之上。
- **修复的目标不能是分数。** 修复时必须读题面，并且要限定能改什么。

### 案例：oracle 的盲区

Oracle 通过，只能证明这条参考路径走得通。如果参考解走了一条 agent 没有的捷径，这个证明就没什么用了。

我们见过这几种情况：

- GUI 任务的参考解直接调应用的 API，全部通过，却完全没证明点界面能不能做到
- 多服务任务的参考解直接访问后端，绕过了 agent 实际使用的工具
- 策略对话任务的参考解直接注入标准动作，没读过知识库，后来真实 agent 跑起来才发现，知识库里写的日期格式和标准答案根本不一样，有些枚举值也没有写在文档里

所以**参考解要走 agent 能走的路**。对于知识类任务，还要多问一句：一个老实读文档的 agent，能不能学到标准答案？

### 其他教训

| 教训 | 说明 |
| --- | --- |
| 修复次数要设上限 | 一直修下去，每轮的产出会越来越少，测试却越写越长。修不好就重新设计，或者淘汰 |
| 修不动时换证据来源 | 反复往测试里加关键词没用。缺的通常是独立的期望值来源，或者正确变体和单点改坏这类反例 |
| 不要信作者的自我报告 | 让生成任务的 agent 自己说“已修好”并不可靠。要有独立的审查和实际运行结果 |
| 按决定任务的东西去重 | 换个说法、行为相同，还是同一道题。文本相似度只能当线索 |
| 已有题解不要放在作者旁边 | 让作者 agent 能读到已有任务和答案，它就会照着抄 |
| 在目标环境上验证 | 本地 Docker 全过，不代表目标沙箱能过。代理、证书、内核差异都可能带来一批失败 |
| mock 要测错误路径 | 只比较正常路径的 GET 响应，会漏掉很多差异。错误码、各种 HTTP 方法、写操作和完整的创建删除流程都要覆盖 |

不同类型的环境，判分方式和常见的坑也不一样：

| 环境类型 | 通常怎么判分 | 最容易踩的坑 |
| --- | --- | --- |
| 终端、代码 | 跑测试，检查最终状态 | 测试太松，或者只认一种写法 |
| 多服务 mock | 比较服务状态的变化 | mock 和真实 API 行为不一致 |
| 办公文档 | 规则检查加 LLM 评审 | 为了迁就结果去调权重 |
| GUI、Web | 检查产物，再到界面里复核 | 参考解走 API，证明不了界面能操作 |
| 策略对话 | 回放参考动作，比较数据库状态 | 知识库里其实查不到标准答案 |

---

## 第七章：难度与公平

有了能判对错的环境，下一个问题是：它有没有用？

如果所有模型都能满分，或者都是 0 分，这个环境就提供不了信号。EvoEnv 的准入条件很直白：通过率必须在 0 和 1 之间。它把目标通过率设在 0.3 左右，让当前模型既能拿到一些正反馈，又还有提升空间。这是那篇论文的设定，不是通用标准，但思路值得参考。

不过比难度更重要的是公平：

<div align="center">
  <img src="./images/Extra14-figures/06-难度与公平四象限.png" alt="按是否公平和是否有区分度划分的四个象限" width="88%"/>
  <p><strong>图 10</strong> 先问公平不公平，再谈难度</p>
</div>

| 提高难度的正当做法 | 不该用的做法 |
| --- | --- |
| 在已公开的输入范围内，增加边界值和随机用例 | 考题面没写的公式、隐藏数据格式 |
| 检查题面写了、但之前没测的性质 | 检查类名、源码字符串，或者某个模型的习惯写法 |
| 真实的系统上下文，需要跨模块定位问题 | 只是堆更多文件和数据，或者把题面写模糊 |
| 多个来源相互冲突，题面写明谁说了算 | 依赖不可达的工具、随机的网络失败 |
| 全局约束，让贪心解法行不通 | 看着某个模型的代码来针对性出题 |

下面几个判断，都是我们在真实审查中反复碰到的。这里的“强模型”“弱模型”只表示相对能力。

**修 bug 不等于提难度。** 强模型和弱模型都只差一条检查，这条检查是在卡代码形式，我们把它换成了行为检查。这是正确的修复，但两个模型都会因此通过，难度并没有提高。这两件事要分开记录，否则你会以为任务变难了。

**先审失败，再算区分度。** 弱模型分数偏低，看起来区分度很好。逐条看失败才发现，全部都是 verifier 误判，有一条匹配规则连题面自己的措辞都不认。修好之后这个任务就不再达标了，但这才是真实情况，只能接受。

**不能为了区分度删掉唯一失败的测试。** 如果强模型只因为一条测试没满分，删掉它就能达标，这很诱人。但如果这条测试考的是题面的核心要求，删掉就是不公平。两个模型都犯同一个核心错误时，也没法只给其中一个放宽。

**在公开要求之内加强，是可以的。** 如果弱模型也能全过，可以对比它的产物和题面，找真实的缺口。比如题面写了取整规则，但测试没覆盖刚好在中点的值，那就加一个。加完记得让参考解也重新验证一遍。而如果公开要求里已经找不到缺口，就老实承认“公平，但没有区分度”，不要硬加隐藏要求。

**“太简单”通常不是 verifier 的问题。** 有一批任务反复调难度都没效果。逐个审查后发现，主要原因是任务在生成时压缩掉了真实系统的复杂度，或者丢掉了种子本来难的地方，有的甚至在任务里泄露了问题根因。这时候继续调 verifier 没用，要回到种子和环境上。一个本来就很简单的种子，再怎么包装也变不难，不如换掉。

**数字再漂亮，证据脏了也不算数。** 有一次弱模型全失败、强模型能通过，数字非常理想。后来发现环境里留着修复用的脚手架，轨迹已经被污染了。修好环境后，旧的轨迹都不能再用，只能重跑。

---

## 第八章：接到评测和训练

任务写好了，要批量跑起来。这里有三件事容易出错。

### 不是所有失败都算 agent 的

沙箱没启动、模型 API 被限流，这些都不是 agent 的能力问题。把它们算成 0 分，会污染评测，也会污染训练。

Harbor 用 `reward_valid` 来区分这一点：

<div align="center">
  <img src="./images/Extra14-figures/web-harbor-error-classification.png" alt="Harbor 判断 reward 是否有效的决策流程图" width="72%"/>
  <p><strong>图 11</strong> Harbor 如何判断 reward 是否有效。图片来源：<a href="https://github.com/harbor-framework/harbor/blob/main/docs-mintlify/jobs/error-classification.mdx">Harbor 文档</a>（Apache-2.0 许可证）</p>
</div>

| 情况 | 例子 | 是否判分 | reward 是否有效 |
| --- | --- | --- | --- |
| agent 自己的问题 | 超时、上下文超长 | 判 | 有效，0 分也算数 |
| 环境没起来 | 沙箱构建失败、健康检查失败 | 不判 | 无效 |
| 模型服务出问题 | API 限流、连接中断 | 判 | 无效 |

注意，0 分也可能是有效的信号。

这种分类自己做的话，两个方向都可能出错。我们遇到过 mock 服务不健康被当成偶发故障重跑，直到多个任务接连失败，才开始怀疑是镜像本身的问题。也遇到过相反的情况：明明是任务格式错误，却被归类成可以重跑的基础设施问题。所以分类逻辑本身也要测试，而且两个方向都要测。

### 回放还是重跑

改了任务之后，旧的分数还能不能用？

<div align="center">
  <img src="./images/Extra14-figures/07-回放还是重跑.png" alt="根据修改内容决定回放还是重跑的决策树" width="88%"/>
  <p><strong>图 12</strong> 改完任务之后，回放还是重跑</p>
</div>

只改 verifier 时可以回放。我实测了一次：故意把 v2 的一条期望值写错，参考解只拿到 0.75，修好 verifier 后用旧结果回放，不用再跑 agent。

```bash
harbor job regrade jobs/<job目录> -p tasks/order-stats-v2
```

```text
Regrade delta over 1 trial(s): 1 changed (1 up, 0 down), mean reward 0.750 → 1.000
```

回放依赖 separate verifier 和 artifacts：verifier 需要的所有文件，当初都得收集下来。这件事要在跑之前就想好，**老数据是补不回来的**。

还有一条底线：改了 agent 能看到的东西，就要让所有模型都在新版本上重跑。只重跑一个模型，或者把不同版本的分数放在一起比，都不公平。同样的道理，也不能把历史运行里通过的结果拼进当前成绩，这样的分数不代表任何一次真实运行。

### 接到训练框架

环境是 reward 的来源，真正的训练交给 RL 框架。以 SkyRL 为例，它的官方文档专门讲了 [Harbor 集成](https://github.com/NovaSky-AI/SkyRL/blob/main/docs/content/docs/harbor/index.mdx)，把 Harbor 用作训练时的环境和 reward 来源：SkyRL 负责生成模型输出，Harbor 负责在沙箱里运行 agent 并验证结果，得到的 reward 再用来更新模型。

<div align="center">
  <img src="./images/Extra14-figures/web-skyrl-system-overview.png" alt="SkyRL 系统架构图，Environment 为 Generator 提供观测和奖励" width="80%"/>
  <p><strong>图 13</strong> 环境在训练系统里的位置：右下角的 Environment 提供观测和奖励。图片来源：<a href="https://github.com/NovaSky-AI/SkyRL">SkyRL 文档</a>（Apache-2.0 许可证）</p>
</div>

训练本身的内容不再展开，可以接着看[第十一章](../docs/chapter11/第十一章%20Agentic-RL.md)和 [Extra12 旅行助手后训练实战](./Extra12-旅行助手后训练实战.md)。

---

## 这次留下来的经验

1. **reward 是学习目标。** 它错了，后面的一切都会稳定地学错。
2. **Agent 能写的地方都不是证据，能读的地方都算公开。** 不要指望靠约定保密。
3. **参考解满分、空解零分只是必要条件。** 还要有正确变体和单点改坏这两类反例。
4. **题面是唯一的真相。** 太严可以，但要和题面对得上。
5. **出题可以交给 LLM，判卷尽量用程序。** 让 LLM 判的部分要有明确的标准。
6. **修复要有上限，目标不能是分数。** 否则修出来的只是一个自洽的错误。
7. **先问公平，再谈难度。** 难度应该来自真实的复杂度，而不是隐藏要求。
8. **改了什么决定回放还是重跑。** 不同版本的分数不要混在一起。

---

## 上线前检查清单

**任务本身**

- [ ] 题面写清了输入、输出和判断标准，判分用到的要求都能在题面找到
- [ ] 参考解走的是 agent 能走的路
- [ ] 同样的任务多跑几次，初始状态和判分结果一致

**判分**

- [ ] 参考解满分，空解不得分
- [ ] 另一种正确写法也能满分
- [ ] 单点改坏时，只有对应的检查失败
- [ ] 每条计分的检查都真正运行了候选代码
- [ ] 判分数据不在 agent 能修改的地方
- [ ] 报错和日志不包含期望值
- [ ] 最终分数和声明的公式一致

**隔离和打包**

- [ ] 使用 separate verifier，并声明了判分需要的 artifacts
- [ ] 答案、参考解、内部笔记都不在 agent 能读到的地方
- [ ] `harbor lint` 没有报错

**批量运行**

- [ ] 基础设施失败不计入 reward
- [ ] 失败都审查过原因，确认是能力差距，而不是误判或环境问题
- [ ] 同一张对比表里的分数都来自同一个任务版本

---

## 这一版还没覆盖的内容

这是一个基础版本，下面这些内容后续可以继续补充：

- 把 HelloAgents 接入 Harbor，用真实模型跑一遍配套任务
- 真正用 LLM 生成任务包的 prompt 设计和质量对比
- 多服务 mock、GUI 这类复杂环境的完整搭建过程
- Rewardkit 和 LLM judge 的详细用法

---

## 参考资料与图片来源

**项目与文档**

- [Harbor](https://github.com/harbor-framework/harbor)，以及 [Harbor Cookbook](https://github.com/harbor-framework/harbor-cookbook)，里面有多容器、多步骤、MCP 工具等更完整的示例
- [Gymnasium](https://github.com/Farama-Foundation/Gymnasium)
- [OpenEnv](https://github.com/openenv/OpenEnv)
- [Prime Intellect verifiers](https://github.com/PrimeIntellect-ai/verifiers)
- [SkyRL](https://github.com/NovaSky-AI/SkyRL)

**论文**

- [Learning to Build the Environment: Self-Evolving Reasoning RL via Verifiable Environment Synthesis](https://arxiv.org/abs/2605.14392)（EvoEnv）
- [Agent-World: Scaling Real-World Environment Synthesis for Evolving General Agent Intelligence](https://arxiv.org/abs/2604.18292)
- [Beyond Task Completion: Revealing Corrupt Success in LLM Agents through Procedure-Aware Evaluation](https://arxiv.org/abs/2603.03116)（PAE）

**图片来源**

图 2、3、4、5、7、10、12 为本章原创。其余图片的来源如下，版权归原作者所有：

| 图 | 来源 | 许可 |
| --- | --- | --- |
| 图 1 | [Gymnasium 文档](https://github.com/Farama-Foundation/Gymnasium) | MIT |
| 图 6 | [Harbor 文档](https://github.com/harbor-framework/harbor)，有裁剪 | Apache-2.0 |
| 图 8 | [Agent-World 论文](https://arxiv.org/abs/2604.18292) Figure 2 | 学术引用 |
| 图 9 | [EvoEnv 论文](https://arxiv.org/abs/2605.14392) Figure 1 | CC BY-NC-ND 4.0 |
| 图 11 | [Harbor 文档](https://github.com/harbor-framework/harbor/blob/main/docs-mintlify/jobs/error-classification.mdx) | Apache-2.0 |
| 图 13 | [SkyRL 文档](https://github.com/NovaSky-AI/SkyRL) | Apache-2.0 |
