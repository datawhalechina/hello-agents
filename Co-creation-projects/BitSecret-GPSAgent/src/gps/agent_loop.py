from symbolic_solver import SymbolicSolver
from utils import parse_gdl, parse_cdl, load_json, save_json, get_theorems, make_train_val_test_split
from multiprocessing import Process, Queue
from dotenv import load_dotenv
from hello_agents import HelloAgentsLLM
import time
import os
import json
import random
import warnings

warnings.filterwarnings("ignore")
debug = False
load_dotenv()


def dprint(msg):
    if debug:
        print(msg)


class Agent:
    def __init__(self, api_key, base_url, model_name):
        self.hello_agents_llm = HelloAgentsLLM(model=model_name, api_key=api_key, base_url=base_url)
        self.model_name = model_name
        self.history = []
        self.memory = []
        self.context_length = 0
        self.timing = time.time()

    def run(self, time_sleep=15, max_epoch=6):
        dprint(f'⏳ 正在调用{self.model_name}...\n')
        epoch = 0
        response = '{' + f'"thinking":"尝试调用{max_epoch}次模型，均发生异常。","action":"finish()"' + '}'
        while epoch < max_epoch:
            epoch += 1
            try:
                response = self.hello_agents_llm.invoke(
                    messages=self.memory,
                    response_format={'type': 'json_object'}
                ).content
                if len(response) == 0:
                    max_epoch += 1
                    raise Exception('模型输出内容为空，服务器负载过大，不计入调用次数。')
            except Exception as e:
                if epoch < max_epoch:
                    dprint(f'❌ 第({epoch}/{max_epoch})次调用模型时发生异常：{repr(e)}。{time_sleep}s后重试...')
                    time.sleep(time_sleep)
                else:
                    response = '{' + f'"thinking":"尝试调用{max_epoch}次模型，均发生异常。","action":"finish()"' + '}'
                    dprint(f'❌ 第({epoch}/{max_epoch})次调用模型时发生异常：{repr(e)}。')
            else:
                break

        self.add_memory(role='assistant', content=response)

        return response

    def add_memory(self, role, content):
        self.context_length += len(content)

        if role == 'system':
            dprint(f'📋 System (contex={self.context_length}, timing={round(time.time() - self.timing, 3)}s):')
            dprint(content + '\n')
        elif role == 'user':
            if content.startswith('调用工具时发生错误'):
                dprint(f'❌ Tool (contex={self.context_length}, timing={round(time.time() - self.timing, 3)}s):')
                dprint(content + '\n')
            elif content.startswith('工具执行结果'):
                dprint(f'🛠️ Tool (contex={self.context_length}, timing={round(time.time() - self.timing, 3)}s):')
                dprint(content + '\n')
            else:
                dprint(f'🙋 User (contex={self.context_length}, timing={round(time.time() - self.timing, 3)}s):')
                dprint(content + '\n')
        else:
            dprint(f'🤖 Assistant (contex={self.context_length}, timing={round(time.time() - self.timing, 3)}s):')
            dprint(content + '\n')

        self.memory.append({"role": role, "content": content})

    def summarize(self, user_prompt, summary):
        self.history.append(self.memory)
        self.memory = self.memory[:1]  # 清空记忆
        self.context_length = len(self.memory[0]['content'])
        dprint('----------------------------------------------------------------------------------------------------\n')
        self.add_memory('user', user_prompt)
        self.add_memory('assistant', summary)

    def save_history(self, filename):
        save_json(
            data={
                'timing': time.time() - self.timing,
                'model_name': self.model_name,
                'history': self.history + [self.memory]
            },
            filename=filename
        )


def get_system_prompt(gdl):
    relation_prompt = []
    for relation in gdl['Relations']:
        relation_prompt.append(
            relation + ':' + gdl['Relations'][relation]['geometric_constraints']
        )
    attribution_prompt = []
    for attribution in gdl['Attributions']:
        if attribution in {'XOfPoint(A)', 'YOfPoint(A)'}:
            continue
        attribution_prompt.append(
            attribution + ':' + gdl['Attributions'][attribution]['sym']
        )
    theorem_prompt = []
    theorems = get_theorems()
    for theorem in gdl['Theorems']:
        if theorem.split('(')[0] not in theorems:
            continue
        theorem_prompt.append(
            theorem + ':' + gdl['Theorems'][theorem]['premises'] + '->' + gdl['Theorems'][theorem]['conclusion']
        )

    with open('../../datasets/system_prompt.txt', 'r', encoding='utf-8') as f:
        system_prompt = f.read()
        system_prompt = system_prompt.replace('{relation}', '\n'.join(relation_prompt))
        system_prompt = system_prompt.replace('{attribution}', '\n'.join(attribution_prompt))
        system_prompt = system_prompt.replace('{theorem}', '\n'.join(theorem_prompt))

    return system_prompt


def get_summarize_prompt():
    with open('../../datasets/summarize_prompt.txt', 'r', encoding='utf-8') as f:
        summarize_prompt = f.read()
    return summarize_prompt


def parse_response(response):
    response = json.loads(response)
    tool_name, args = response['action'].split('(', 1)
    if tool_name == 'summarize':
        args = response['thinking']
    else:
        args = args[:-1]
    return tool_name, args


def solve(api_key, base_url, model_name, max_epoch, max_context, problem_id, debug_mode):
    if debug_mode:
        global debug
        debug = True

    dprint(f"📋 调用'{model_name}'求解问题 {problem_id} (max_epoch={max_epoch}, max_context={max_context}) ...\n")
    timing = time.time()
    epoch_count = 0
    agent = Agent(api_key=api_key, base_url=base_url, model_name=model_name)

    try:
        gdl = load_json('../../datasets/gdl.json')
        cdl = load_json(f'../../datasets/problems/{problem_id}.json')
        solver = SymbolicSolver(parse_gdl(gdl), parse_cdl(cdl))

        agent.add_memory(role='system', content=get_system_prompt(gdl))
        agent.add_memory(role='user', content=solver.state())

        try:
            while epoch_count < max_epoch:
                epoch_count += 1

                response = agent.run()

                try:  # tool calls
                    tool_name, args = parse_response(response)
                    if tool_name == 'apply':
                        tool_call = '工具执行结果：\n' + solver.apply(args)
                    elif tool_name == 'decompose':
                        tool_call = '工具执行结果：\n' + solver.decompose(args)
                    elif tool_name == 'find_fact':
                        tool_call = '工具执行结果：\n' + solver.find_fact(args)
                    elif tool_name == 'find_goal':
                        tool_call = '工具执行结果：\n' + solver.find_goal(args)
                    elif tool_name == 'check':
                        tool_call = '工具执行结果：\n' + solver.check()
                    elif tool_name == 'summarize':
                        agent.summarize(solver.state(), args)
                        continue
                    elif tool_name == 'finish':
                        break
                    else:
                        raise Exception(f'工具未定义: {tool_name}.')
                except Exception as e:
                    tool_call = f"调用工具时发生错误：{repr(e)}"

                agent.add_memory(role='user', content=tool_call)

                if solver.status_of_goal[0] == 1:
                    agent.add_memory(role='user', content='检测到问题已求解，自动结束。')
                    break

                if agent.context_length > max_context:
                    agent.add_memory(role='user', content=get_summarize_prompt())

        except KeyboardInterrupt:
            agent.add_memory(role='user', content="用户主动介入中断（KeyboardInterrupt）。")

        if solver.status_of_goal[0] == 1:
            result = 'solved'
            agent.add_memory(role='user', content="求解结束：成功✅")
        elif epoch_count >= max_epoch:
            result = 'timeout'
            agent.add_memory(role='user', content="求解结束：超时❌")
        else:
            result = 'unsolved'
            agent.add_memory(role='user', content="求解结束：失败❌")

    except Exception as e:
        result = 'error'
        agent.add_memory(role='user', content=f"智能体执行期间发生异常：{repr(e)}")
        agent.add_memory(role='user', content="求解结束：异常❌")

    agent.save_history(f'../../outputs/agent/solving_history_{problem_id}.json')

    return result, epoch_count, time.time() - timing


def multiprocess_solve(task_queue, reply_queue, api_key, base_url, model_name, max_epoch, max_context, debug_mode):
    while not task_queue.empty():
        problem_id = task_queue.get()
        # reply_queue.put((os.getpid(), "start", time.time(), (problem_id, model_name)))
        result, epoch_count, timing = solve(
            api_key, base_url, model_name, max_epoch, max_context, problem_id, debug_mode
        )
        reply_queue.put((os.getpid(), "end", time.time(), (problem_id, model_name, result, epoch_count, timing)))


def main(test_pids, log_path, model_names, max_epoch, max_context, solve_again, debug_mode):
    log = {"total": test_pids, "solved": {}, "unsolved": {}, "timeout": {}, "error": {}}
    if os.path.exists(log_path):
        log = load_json(log_path)
        if solve_again:
            log["unsolved"] = {}
            log["timeout"] = {}
            log["error"] = {}

    problem_ids = []
    for problem_id in test_pids:
        if str(problem_id) in log["solved"]:
            continue
        if str(problem_id) in log["unsolved"]:
            continue
        if str(problem_id) in log["timeout"]:
            continue
        if str(problem_id) in log["error"]:
            continue
        problem_ids.append(problem_id)
    random.shuffle(problem_ids)

    task_queue = Queue()
    for problem_id in problem_ids:
        task_queue.put(problem_id)

    all_process = []
    reply_queue = Queue()
    for model_name in model_names:
        if task_queue.empty():
            break
        process = Process(
            target=multiprocess_solve,
            args=(
                task_queue, reply_queue, os.getenv(f'{model_name}_API_KEY'), os.getenv(f'{model_name}_BASE_URL'),
                os.getenv(f'{model_name}_MODEL_ID'), max_epoch, max_context, debug_mode
            )
        )
        process.start()
        all_process.append(process)

    output_format = '{0:<15}{1:<8}{2:<23}{3:<10}'
    print(output_format.format('process_id', 'flag', 'time', 'info'))
    while True:
        try:
            if not reply_queue.empty():  # directly calling .get() will block process
                process_id, flag, log_time, info = reply_queue.get()
                log_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(log_time))
                if flag == 'start':
                    problem_id, model_name = info
                    info = f"Use '{model_name}' solve problem {problem_id}."
                else:
                    problem_id, model_name, result, epoch_count, timing = info
                    log[result][problem_id] = {"epoch": epoch_count, "timing": timing}
                    save_json(log, log_path)
                    info = (f"'{model_name}' solve problem {problem_id} end: "
                            f"result='{result}', epoch={epoch_count}, timing={round(timing, 3)}s.")
                print(output_format.format(process_id, flag, log_time, info))
        except BaseException as e:
            print(f"多线程求解过程中发生异常'{repr(e)}'，关闭所有子进程({len(all_process)})后结束。")
            for process in all_process:
                if process.is_alive():
                    process.kill()
                    process.join(timeout=0.5)
                print(f'已关闭子进程 {process.pid}')
            exit(0)


if __name__ == '__main__':
    main(
        test_pids=make_train_val_test_split()['test'],
        log_path="../../outputs/log/log_pssr_agent.json",
        model_names=['Deepseek'],
        max_epoch=50,
        max_context=80000,
        solve_again=True,
        debug_mode=True
    )
