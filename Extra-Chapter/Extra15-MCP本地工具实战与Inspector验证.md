# Extra15 - 从零搭建 MCP 本地工具并用 Inspector 验证

> 本教程把一个静态阅读清单注册为 MCP 工具，并用 MCP Inspector 发现和调用。数据只保存在代码中，不访问网络、不需要模型 API Key，也不会改写文件。检查现有 Extra Chapter 后，选择尚未覆盖的“MCP 服务端到 Inspector 调试”主题。

## 目标与前置条件

完成后可以按状态列出书目、按关键词搜索。MCP Host 通过标准输入输出（stdio）启动本地进程，并用 JSON-RPC 与服务通信；MCP Server 本身不带大模型。

需要 Node.js 22.19 或更新版本、npm，以及联网安装 npm 包的环境。此版本门槛同时满足当前 Inspector 的 Node 要求。Windows 使用 PowerShell，macOS/Linux 使用终端；所有命令都从项目根目录执行。

## 第 1 步：确认环境

**为什么：** 先检查 Node 与 npm，避免依赖安装后才遇到运行时版本错误。

~~~bash
node --version
npm --version
~~~

**应看到：** Node 版本不低于 `v22.19.0`，npm 命令也返回版本号。若命令不存在，从 Node.js 官方网站安装当前 LTS 并重开终端。

**完成标记：** 两条命令都返回版本号。

## 第 2 步：创建项目

**为什么：** 使用独立目录和本地依赖，方便复现并交给 Host 启动。

~~~bash
mkdir mcp-reading-list
cd mcp-reading-list
npm init -y
npm pkg set type=module
npm install @modelcontextprotocol/server@2.3.1 zod@4.6.7 tsx@4.23.15
mkdir src
~~~

**应看到：** 生成 `package.json` 和 `node_modules`，npm 安装成功。`type=module` 与 SDK 的 ES Module 导入方式一致。

**完成标记：** `npm ls @modelcontextprotocol/server zod tsx` 列出三个依赖。

## 第 3 步：实现两个只读工具

**为什么：** 一个 MCP 工具由名称、说明、输入 Schema 和处理函数构成。Schema 约束输入，也让 Host 知道参数怎样填写。

创建 `src/index.ts`，完整粘贴。示例书目为虚构数据：

~~~ts
import { McpServer } from '@modelcontextprotocol/server';
import { serveStdio } from '@modelcontextprotocol/server/stdio';
import * as z from 'zod/v4';

const books = [
  { title: '深度学习入门', author: '斋藤康毅', status: '在读', note: '第 3 章' },
  { title: '置身事内', author: '兰小欢', status: '想读', note: '借阅前先看目录' },
  { title: '人月神话', author: 'Frederick P. Brooks Jr.', status: '已读', note: '团队协作主题' },
] as const;

function createServer(): McpServer {
  const server = new McpServer({ name: 'reading-list-demo', version: '1.0.0' });

  server.registerTool(
    'list_books',
    {
      description: '列出示例阅读清单，可按阅读状态筛选',
      inputSchema: z.object({
        status: z.enum(['想读', '在读', '已读']).optional().describe('可选阅读状态；省略时返回全部'),
      }),
    },
    async ({ status }) => {
      const matches = books.filter((book) => !status || book.status === status);
      const text = matches.length
        ? matches.map((book) => book.title + '｜' + book.status + '｜' + book.note).join('\n')
        : '没有匹配的书目。';
      return { content: [{ type: 'text', text }] };
    },
  );

  server.registerTool(
    'search_books',
    {
      description: '按书名或作者关键词搜索示例书目',
      inputSchema: z.object({
        keyword: z.string().trim().min(1).max(30).describe('1 到 30 个字符的书名或作者关键词'),
      }),
    },
    async ({ keyword }) => {
      const query = keyword.toLocaleLowerCase();
      const matches = books.filter(
        (book) => book.title.toLocaleLowerCase().includes(query) || book.author.toLocaleLowerCase().includes(query),
      );
      const text = matches.length
        ? matches.map((book) => book.title + '｜' + book.author + '｜' + book.status + '｜' + book.note).join('\n')
        : '没有匹配的书目。';
      return { content: [{ type: 'text', text }] };
    },
  );

  return server;
}

void serveStdio(createServer);
console.error('reading-list MCP server running on stdio');
~~~

逐段看：`registerTool` 注册工具；`inputSchema` 校验输入；处理函数返回 `content` 文本块；`serveStdio` 连接 stdin/stdout。stdout 是协议通道，启动提示要用 `console.error`，不要使用 `console.log` 输出日志。

**完成标记：** `src/index.ts` 已保存。

## 第 4 步：启动并验证

**为什么：** 先确认服务能启动，再用 Inspector 握手、列工具和调用，定位问题更容易。

~~~bash
npx tsx src/index.ts
~~~

**应看到：** stderr 显示 `reading-list MCP server running on stdio`，进程保持等待。这是正常现象，stdio 服务等待客户端握手。按 `Ctrl+C` 停止。

在项目根目录运行 Inspector CLI 列出工具：

~~~bash
npx @modelcontextprotocol/inspector@2.10.1 --cli npx tsx src/index.ts --method tools/list
~~~

**应看到：** `tools` 列表包含 `list_books` 与 `search_books`；后者有 `keyword` 参数。

调用搜索：

~~~bash
npx @modelcontextprotocol/inspector@2.10.1 --cli npx tsx src/index.ts --method tools/call --tool-name search_books --tool-arg keyword=人月
~~~

**应看到：** 结果包含 `人月神话｜Frederick P. Brooks Jr.｜已读｜团队协作主题`。

按状态筛选：

~~~bash
npx @modelcontextprotocol/inspector@2.10.1 --cli npx tsx src/index.ts --method tools/call --tool-name list_books --tool-arg status=在读
~~~

**应看到：** 仅返回 `深度学习入门｜在读｜第 3 章`。搜索不存在的词则返回 `没有匹配的书目。`；空关键词或无效状态会被 Schema 拒绝。

**完成标记：** 工具列表与两个调用结果均符合预期。交互式 Web 面板也可用 `npx @modelcontextprotocol/inspector@2.10.1 npx tsx src/index.ts` 启动；在本地页面连接后，从 Tools 面板选工具、填参数并运行。

## 第 5 步（可选）：接入 VS Code

**为什么：** Inspector 验证协议后，再让真实 Host 启动服务。Host 读取相同 Schema，不需另写客户端。

在工作区根目录创建 `.vscode/mcp.json`：

~~~json
{
  "servers": {
    "reading-list": {
      "type": "stdio",
      "command": "npx",
      "args": ["tsx", "src/index.ts"]
    }
  }
}
~~~

VS Code 打开 `mcp-reading-list` 项目根目录，安装并登录 GitHub Copilot。在命令面板运行 `MCP: List Servers`，确认 `reading-list` 运行，再在 Copilot Chat 的 Agent 模式提问：“请搜索阅读清单中关于人月的书”。Host 提示调用时先检查参数，再批准这次本地只读调用。应得到匹配的虚构书目。菜单或版本有变化时，以官方 Host 配置指南为准。

**完成标记：** VS Code 列表出现运行中的服务。此步骤可选，Inspector 调用已形成核心闭环。

## 常见报错

| 现象 | 检查与处理 |
| --- | --- |
| `node`、`npm` 或 `npx` 找不到 | 安装 Node.js LTS 并重开终端；确认 npm 的安装目录在 PATH |
| `Cannot find package` | 回项目根目录运行 `npm install`，再检查 `npm ls` |
| `spawn npx ENOENT` | Inspector 或 Host 找不到 npx；终端先运行 `npx --version`，必要时在 Host 配置写 npx 绝对路径 |
| 连接后立即断开、提示无效 JSON | 检查是否用 `console.log` 写了服务日志；改为 `console.error`，stdout 只留协议消息 |
| `tools/list` 没有工具 | 确认工作目录、`src/index.ts` 路径以及 `registerTool` 是否执行 |
| 输入校验失败 | `status` 只能是“想读/在读/已读”；`keyword` 需为 1–30 个字符 |

## 复现边界与延伸

该示例证明本地服务能启动、工具能被发现并按 Schema 校验和调用；它没有大模型，也不代表模型一定会选对工具。真实业务接入时应使用最小权限、限制副作用，并让用户核对有影响的操作。可将静态数组替换为授权的数据库查询，再单独设计写入工具与人工确认流程。

## 参考资料

- [Hello-Agents 第十六章：毕业设计与社区协作](https://github.com/datawhalechina/hello-agents/blob/main/docs/chapter16/Chapter16-Graduation-Project.md)
- [MCP TypeScript SDK：Build your first server](https://github.com/modelcontextprotocol/typescript-sdk/blob/main/docs/get-started/first-server.md)
- [SDK 包与导入路径](https://github.com/modelcontextprotocol/typescript-sdk/blob/main/docs/get-started/packages.md)
- [MCP Inspector 官方文档](https://github.com/modelcontextprotocol/modelcontextprotocol/blob/main/docs/docs/2026-07-28/tools/inspector.mdx)
- [VS Code Host 配置示例](https://github.com/modelcontextprotocol/typescript-sdk/blob/main/docs/get-started/real-host.md)


