import json
import os
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
from matplotlib.ticker import FuncFormatter

path_agent_history = '../../outputs/agent/'
filename_log_pssr = '../../outputs/log/log_pssr_agent.json'


def load_json(filename):
    """打开json文件并解析成dict"""
    with open(filename, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(data, filename):
    """将dict存储为json文件"""
    filename_bk = filename + '.bk'
    with open(filename_bk, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    if os.path.exists(filename):
        os.remove(filename)
    os.rename(filename_bk, filename)


def get_problem_level():
    """返回问题problem_id到问题难度的映射"""
    map_pid_to_level = {}
    for problem_id in load_json(filename_log_pssr)['total']:
        theorem_length = len(load_json(f'../../datasets/problems/{problem_id}.json')['theorem_seqs'])
        if theorem_length > 12:
            map_pid_to_level[problem_id] = 6
        else:
            map_pid_to_level[problem_id] = int(theorem_length / 2) + theorem_length % 2

    return map_pid_to_level


def get_avg_context_len():
    """
    按照问题难度，统计平均上下文长度。每个问题的上下文长度是 solving_history_pid.json 文件中，所有content长度的和; len(content)
    此外，还要分为 已求解的问题 和 其他问题
    """
    log = load_json(filename_log_pssr)
    map_pid_to_level = get_problem_level()
    solved_pids = {int(k) for k in log['solved']}

    # {level: [total_len, count]}
    solved_accum = {l: [0, 0] for l in range(1, 7)}
    others_accum = {l: [0, 0] for l in range(1, 7)}

    for pid in log['total']:
        level = map_pid_to_level.get(pid)
        if level is None:
            continue
        hist = load_json(f'{path_agent_history}solving_history_{pid}.json')
        ctx_len = sum(
            len(str(msg.get('content', '')))
            for round_msgs in hist.get('history', [])
            if isinstance(round_msgs, list)
            for msg in round_msgs
        )
        accum = solved_accum if pid in solved_pids else others_accum
        accum[level][0] += ctx_len
        accum[level][1] += 1

    # dict: key 为 problem_level; value 为 avg_context_length
    avg_context_len_solved = {
        l: (solved_accum[l][0] / solved_accum[l][1] if solved_accum[l][1] > 0 else None)
        for l in range(1, 7)
    }
    # unsolved + timeout + error; 如果当前等级的问题没有，则key 为 None
    avg_context_length_others = {
        l: (others_accum[l][0] / others_accum[l][1] if others_accum[l][1] > 0 else None)
        for l in range(1, 7)
    }

    return avg_context_len_solved, avg_context_length_others


def get_avg_epoch():
    """
        按照问题难度，统计平均交互次数。每个问题的交互次数存储在 solving_history_pid.json 文件中。
        此外，还要分为 已求解的问题 和 其他问题
    """
    log = load_json(filename_log_pssr)
    map_pid_to_level = get_problem_level()

    # {level: [total_epoch, count]}
    solved_accum = {l: [0, 0] for l in range(1, 7)}
    others_accum = {l: [0, 0] for l in range(1, 7)}

    for cat in ('solved', 'unsolved', 'timeout', 'error'):
        accum = solved_accum if cat == 'solved' else others_accum
        for pid_str, info in log[cat].items():
            level = map_pid_to_level.get(int(pid_str))
            if level is None:
                continue
            accum[level][0] += info['epoch']
            accum[level][1] += 1
    # dict: key 为 problem_level; value 为 avg_epoch
    avg_epoch_solved = {
        l: (solved_accum[l][0] / solved_accum[l][1] if solved_accum[l][1] > 0 else None)
        for l in range(1, 7)
    }
    # unsolved + timeout + error; 如果当前等级的问题没有，则key 为 None
    avg_epoch_others = {
        l: (others_accum[l][0] / others_accum[l][1] if others_accum[l][1] > 0 else None)
        for l in range(1, 7)
    }

    return avg_epoch_solved, avg_epoch_others


def get_tool_call():
    """
    按照问题难度，统计所有工具的平均调用次数。需要解析每个问题solving_history_pid.json 文件中 role 为 assistance 的消息
    当json解析出错时，记为error
    """
    tool_keys = ['apply', 'decompose', 'find', 'check', 'error']
    log = load_json(filename_log_pssr)
    map_pid_to_level = get_problem_level()
    solved_pids = {int(k) for k in log['solved']}

    # {level: {tool: total_count}}, {level: problem_count}
    solved_count = {l: {t: 0 for t in tool_keys} for l in range(1, 7)}
    others_count = {l: {t: 0 for t in tool_keys} for l in range(1, 7)}
    solved_n = {l: 0 for l in range(1, 7)}
    others_n = {l: 0 for l in range(1, 7)}

    for pid in log['total']:
        level = map_pid_to_level.get(pid)
        if level is None:
            continue
        hist = load_json(f'{path_agent_history}solving_history_{pid}.json')
        is_solved = pid in solved_pids
        count = solved_count[level] if is_solved else others_count[level]

        for round_msgs in hist.get('history', []):
            if not isinstance(round_msgs, list):
                continue
            for msg in round_msgs:
                if msg.get('role') != 'assistant':
                    continue
                try:
                    parsed = json.loads(str(msg.get('content', '')))
                    tool = parsed.get('action', '').split('(')[0].strip()

                    if tool in ['find_fact', 'find_goal']:
                        tool = 'find'

                    if tool in tool_keys:
                        count[tool] += 1
                except Exception:
                    count['error'] += 1

        if is_solved:
            solved_n[level] += 1
        else:
            others_n[level] += 1

    # dict: key 为 problem_level; value 为 平均tool_call次数
    avg_tool_call_solved = {
        l: ({t: solved_count[l][t] / solved_n[l] for t in tool_keys} if solved_n[l] > 0 else None)
        for l in range(1, 7)
    }
    # unsolved + timeout + error; 如果当前等级的问题没有，则key 为 None
    avg_tool_call_others = {
        l: ({t: others_count[l][t] / others_n[l] for t in tool_keys} if others_n[l] > 0 else None)
        for l in range(1, 7)
    }

    return avg_tool_call_solved, avg_tool_call_others


def draw_figure():
    """
    结合上述三个数据画图
    """
    avg_context_len_solved, avg_context_length_others = get_avg_context_len()
    avg_epoch_solved, avg_epoch_others = get_avg_epoch()
    avg_tool_call_solved, avg_tool_call_others = get_tool_call()

    levels = [1, 2, 3, 4, 5, 6]
    tool_keys = ['apply', 'decompose', 'find', 'check', 'error']
    n_tools = len(tool_keys)

    # 全局设置
    plt.rcParams.update({
        'font.family': 'serif',
        'font.size': 10,
        'axes.linewidth': 1.0,
        'xtick.direction': 'out',
        'ytick.direction': 'out',
        'xtick.major.size': 4,
        'ytick.major.size': 4,
        'figure.dpi': 150,
    })

    # 柱状图色板
    tool_colors = [
        '#55A868', '#5DA5DA', '#9970AB', '#E6AB02', '#E7298A',
    ]

    bar_width = 0.2
    level_spacing = n_tools * bar_width + 0.2
    x_centers = np.arange(len(levels)) * level_spacing

    fig, ax_bar = plt.subplots(figsize=(10, 4.2))
    ax_ctx = ax_bar.twinx()
    ax_epoch = ax_bar.twinx()

    ax_ctx.yaxis.set_label_position('left')
    ax_ctx.yaxis.tick_left()
    ax_bar.yaxis.set_visible(False)

    # 顶部封边
    ax_bar.spines['top'].set_visible(True)
    ax_ctx.spines['top'].set_visible(False)
    ax_epoch.spines['top'].set_visible(False)

    # --- 发散柱状图 ---
    for i, tool in enumerate(tool_keys):
        sv = [avg_tool_call_solved[l][tool] if avg_tool_call_solved[l] is not None else 0 for l in levels]
        ov = [avg_tool_call_others[l][tool] if avg_tool_call_others[l] is not None else 0 for l in levels]
        x_pos = x_centers + (i - n_tools / 2 + 0.5) * bar_width

        bars_s = ax_bar.bar(x_pos, [-v for v in sv], width=bar_width,
                            color=tool_colors[i], edgecolor='white', linewidth=0.3, zorder=2)
        bars_o = ax_bar.bar(x_pos, ov, width=bar_width,
                            color=tool_colors[i], edgecolor='white', linewidth=0.3,
                            hatch='////', alpha=0.75, zorder=2)

        # 柱子向下 (Solved) 的文本
        for bar, val in zip(bars_s, sv):
            ax_epoch.text(bar.get_x() + bar.get_width() / 2, -val - 0.05,
                          f'{val:.1f}', ha='center', va='top', fontsize=6,
                          color='#333333', fontfamily='sans-serif',
                          fontweight='bold',
                          zorder=10,
                          transform=ax_bar.transData)

        # 柱子向上 (Failed / Others) 的文本
        for bar, val in zip(bars_o, ov):
            ax_epoch.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.05,
                          f'{val:.1f}', ha='center', va='bottom', fontsize=6,
                          color='#333333', fontfamily='sans-serif',
                          fontweight='bold',
                          zorder=10,
                          transform=ax_bar.transData)

    ax_bar.axhline(0, color='#333333', linewidth=0.8, zorder=3)
    ax_bar.set_xticks(x_centers)
    ax_bar.set_xticklabels([f'Level {l}' for l in levels], fontsize=10, fontweight='bold')

    # --- 折线 ---
    def plot_line(ax, solved_dict, others_dict, color, label_s, label_o,
                  marker_s='o', marker_o='s'):
        s_pts = [(x_centers[j], v)
                 for j, (l, v) in enumerate(zip(levels, [solved_dict.get(l) for l in levels]))
                 if v is not None]
        o_pts = [(x_centers[j], v)
                 for j, (l, v) in enumerate(zip(levels, [others_dict.get(l) for l in levels]))
                 if v is not None]
        h1 = h2 = None
        if s_pts:
            xs, vs = zip(*s_pts)
            h1, = ax.plot(xs, vs, color=color, linestyle='-', linewidth=1.8,
                          marker=marker_s, markersize=6, markeredgecolor='white',
                          markeredgewidth=0.8, label=label_s, zorder=5)
        if o_pts:
            xo, vo = zip(*o_pts)
            h2, = ax.plot(xo, vo, color=color, linestyle='--', linewidth=1.8,
                          marker=marker_o, markersize=6, markeredgecolor='white',
                          markeredgewidth=0.8, label=label_o, zorder=5)
        return h1, h2

    h_ctx_s, h_ctx_o = plot_line(ax_ctx, avg_context_len_solved, avg_context_length_others,
                                 '#1A6FAF', 'Context Length (Solved)', 'Context Length (Failed)')
    ax_ctx.set_ylabel('Avg. Context Length', fontsize=11, color='black', labelpad=6, fontweight='bold')
    ax_ctx.tick_params(axis='y', labelcolor='black', labelsize=9)
    ax_ctx.spines['left'].set_edgecolor('black')

    def format_k(x, pos):
        return f'{x / 1000:g}k' if x >= 1000 else f'{x:g}'

    ax_ctx.yaxis.set_major_formatter(FuncFormatter(format_k))

    h_ep_s, h_ep_o = plot_line(ax_epoch, avg_epoch_solved, avg_epoch_others,
                               '#C0392B', 'Avg. Epoch (Solved)', 'Avg. Epoch (Failed)',
                               marker_s='^', marker_o='v')
    ax_epoch.set_ylabel('Avg. Epoch', fontsize=11, color='black', labelpad=6, fontweight='bold')
    ax_epoch.tick_params(axis='y', colors='black', labelsize=9)
    ax_epoch.spines['right'].set_edgecolor('black')

    # --- 图例 ---
    tool_patches = [mpatches.Patch(facecolor=tool_colors[i], edgecolor='#555555',
                                   linewidth=0.5, label=tool_keys[i])
                    for i in range(n_tools)]
    line_handles = [h for h in [h_ctx_s, h_ctx_o, h_ep_s, h_ep_o] if h is not None]

    all_handles = tool_patches + line_handles
    n_cols = 5
    ordered_handles = [h for i in range(n_cols) for h in all_handles[i::n_cols]]

    legend = ax_bar.legend(
        handles=ordered_handles,
        fontsize=8,
        loc='lower left',
        bbox_to_anchor=(0, 1.05, 1, 0.1),
        mode="expand",
        ncol=n_cols,
        framealpha=0.9,
        edgecolor='#CCCCCC',
        borderpad=0.6,
        borderaxespad=0.
    )
    for text in legend.get_texts():
        text.set_fontweight('bold')

    # 如果图例有标题，也加粗
    if legend.get_title():
        legend.get_title().set_fontweight('bold')

    plt.tight_layout()
    plt.savefig('../../outputs/fig-statistics.pdf', bbox_inches='tight')
    plt.show()


def draw_table(level=6, span=2, latex=True, show_complete=False):
    filenames = {
        'Backward-DFS': 'log_pssr_formalgeo7k-bw-dfs.json',  # symbolic solver
        'Backward-RS': 'log_pssr_formalgeo7k-bw-rs.json',
        'Backward-BFS': 'log_pssr_formalgeo7k-bw-bfs.json',
        'Forward-DFS': 'log_pssr_formalgeo7k-fw-dfs.json',
        'Forward-BFS': 'log_pssr_formalgeo7k-fw-bfs.json',
        'Forward-RS': 'log_pssr_formalgeo7k-fw-rs.json',

        'Kimi-K2': 'log_pssr_kimi-k2.json',  # neural solver
        'DeepSeek v3': 'log_pssr_deepseek-v3.json',
        'GPT-5 mini': [64.79, 74.11, 63.30, 64.66, 53.50, 53.23, 41.46],
        'Qwen3-VL': [65.93, 74.53, 65.43, 72.18, 50.96, 41.94, 36.67],
        'Doubao seed 1.8': [69.14, 74.11, 69.15, 71.43, 64.33, 50.00, 51.67],
        'GPT-5.2': [73.14, 80.38, 73.40, 74.81, 63.06, 59.68, 46.67],
        'Claude4.5 Sonnet': [75.79, 84.55, 73.94, 76.32, 67.52, 64.52, 48.33],

        'T5-small': 'log_pssr_t5-small_bs20_timeout600.json',  # neural-symbolic solver (training-based)
        'BART-base': 'log_pssr_bart-base_bs20_timeout600.json',
        'Inter-GPS': 'log_pssr_intergps.json',
        'DualGeoSolver': 'log_pssr_dualgeosolver_bs10_timeout600.json',
        'NGS': 'log_pssr_ngs_bs10_timeout600.json',
        'FGeo-DRL': 'log_pssr_fgeodrl.json',
        'FGeo-TP': [80.86, 96.43, 85.44, 76.12, 62.26, 48.88, 29.55],
        'FGeo-ISRL': 'log_pssr_res_bdrl.json',
        'HyperGNet': 'log_pssr_hypergnet_TTT_bs5_gb_tm600.json',
        'NSS': 'log_pssr_nss_FFFF_bs5_tm600.json',

        'Pri-TPG': [89.29, 99.16, 96.28, 87.92, 77.07, 66.13, 30.00],  # neural-symbolic solver (training-free)
        'Ours': 'log_pssr_agent.json'
    }
    last_methods = ["Forward-RS", "Claude4.5 Sonnet", "NSS", 'Ours']

    problem_level = {}  # map problem_id to level
    level_map = {}  # map t_length to level (start from 0)
    for i in range(level):
        for j in range(span):
            level_map[i * span + j + 1] = i + 1
    save_json({'info': 'map theorem_length to problem level.', 'map': level_map},
              '../../outputs/log/log_level_map.json')
    for pid in range(7000):
        pid += 1
        t_length = len(load_json(f'../../datasets/problems/{pid}.json')['theorem_seqs'])
        problem_level[pid] = level_map[t_length] if t_length <= level * span else level

    method_name_max_len = max([len(m) for m in filenames.keys()] + [6]) + 1

    outputs = []
    if not show_complete:
        head = ['Method' + "".join([" "] * (method_name_max_len - 6)),
                'Total', 'L1   ', 'L2   ', 'L3   ', 'L4   ', 'L5   ', 'L6   ']
        line = ''.join(['-'] * (7 * 8 + method_name_max_len))
    else:
        head = ['Method' + "".join([" "] * (method_name_max_len - 6)),
                '  A  ', '  T  ', 'Total', 'L1   ', 'L2   ', 'L3   ', 'L4   ', 'L5   ', 'L6   ']
        line = ''.join(['-'] * (9 * 8 + method_name_max_len))

    if latex:
        print(' & '.join(head))
        outputs.append(' & '.join(head))
    else:
        print(' | '.join(head))
        outputs.append(' | '.join(head))
    print(line)
    outputs.append(line)

    for method in filenames.keys():  # pssr_log
        lines = [method + "".join([" "] * (method_name_max_len - len(method)))]

        if isinstance(filenames[method], list):
            lines.extend(['  -  ', '  -  '])
            for r in filenames[method]:
                lines.append(str(r))
                lines[-1] = lines[-1] + ' ' * (5 - len(lines[-1]))
        else:
            pssr_log = load_json(f"../../outputs/log/{filenames[method]}")

            GT = (len(pssr_log["solved"]) + len(pssr_log["unsolved"]) +  # 事实求解成功率，分母为已求解的题目
                  len(pssr_log["timeout"]) + len(pssr_log["error"]))
            lines.append(str(round(GT / len(pssr_log["total"]) * 100, 2)))
            lines[-1] = lines[-1] + ' ' * (5 - len(lines[-1]))
            lines.append(str(round(len(pssr_log["solved"]) / GT * 100, 2)))
            lines[-1] = lines[-1] + ' ' * (5 - len(lines[-1]))

            total_level_count = [0 for _ in range(level + 1)]  # [total, l1, l2, ...]
            solved_level_count = [0 for _ in range(level + 1)]
            for pid in pssr_log["total"]:
                total_level_count[0] += 1
                total_level_count[problem_level[pid]] += 1
                if str(pid) in pssr_log["solved"]:
                    solved_level_count[0] += 1
                    solved_level_count[problem_level[pid]] += 1
            # print()
            # print(total_level_count)
            # print(solved_level_count)
            for i in range(level + 1):
                if total_level_count[i] == 0:
                    lines.append('Nan')
                else:
                    lines.append(str(round(solved_level_count[i] / total_level_count[i] * 100, 2)))

                lines[-1] = lines[-1] + ' ' * (5 - len(lines[-1]))

        if not show_complete:
            lines = [lines[0]] + lines[3:]

        if latex:
            print(' & '.join(lines))
            outputs.append(' & '.join(lines))
        else:
            print(' | '.join(lines))
            outputs.append(' | '.join(lines))

        if method in last_methods:
            print(line)
            outputs.append(line)

    with open('../../outputs/tab-main_results.txt', 'w', encoding='utf-8') as f:
        f.write('\n'.join(outputs))


def lmm_call_statistic():
    data = {'solved': [], 'unsolved': []}
    log = load_json('../../outputs/log/log_pssr_agent.json')

    for filename in os.listdir('../../outputs/agent'):
        count = 0
        for history in load_json(f'../../outputs/agent/{filename}')['history']:
            for msg in history:
                if msg['role'] == 'assistant':
                    count += 1
        pid = filename.split('.')[0].split('_')[-1]
        if pid in log['solved']:
            data['solved'].append(count)
        else:
            data['unsolved'].append(count)

    print('solved', sum(data['solved']) / len(data['solved']))
    print('unsolved', sum(data['unsolved']) / len(data['unsolved']))


if __name__ == '__main__':
    draw_figure()
    draw_table()
    lmm_call_statistic()
