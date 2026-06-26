import { defineConfig } from 'vitepress'
import { withMermaid } from 'vitepress-plugin-mermaid'
import markdownItKatex from 'markdown-it-katex'
import fs from 'fs'



export default withMermaid(
  defineConfig({
    // GitHub Pages subpath deployment
    base: '/hello-agents/',

    // Clean URLs (no .html extension)
    cleanUrls: true,

    // Sitemap
    sitemap: {
      hostname: 'https://datawhalechina.github.io/hello-agents',
    },

    // Enable last updated timestamps from git
    lastUpdated: true,

    // Ignore dead link checks for localhost dev URLs
    ignoreDeadLinks: [
      /^http:\/\/localhost/,
    ],

    // Markdown configuration
    markdown: {
      config: (md) => {
        md.use(markdownItKatex)

        // Wrap rendered markdown HTML in <div v-pre> to bypass Vue template compilation
        const origRender = md.render.bind(md)
        md.render = (src, env) => {
          return `<div v-pre>${origRender(src, env)}</div>`
        }
      },
    },

    // Vite configuration
    vite: {
      plugins: [],
    },

    // Locales (i18n)
    locales: {
      '/': {
        lang: 'zh-CN',
        title: 'Hello-Agents',
        description: '从零开始构建智能体 - Datawhale社区系统性智能体学习教程',
      },
      '/en/': {
        lang: 'en-US',
        title: 'Hello-Agents',
        description:
          'Building Agent Systems from Scratch - A Systematic Agent Learning Tutorial from Datawhale Community',
      },
    },

    // Theme configuration
    themeConfig: {
      // Site logo
      logo: '/images/hello-agents.png',

      // Social links
      socialLinks: [
        {
          icon: 'github',
          link: 'https://github.com/datawhalechina/Hello-Agents',
        },
      ],

      // Dark mode toggle (default: true)
      darkMode: true,

      // Outline (table of contents) - h2 and h3
      outline: {
        level: [2, 3],
      },

      // Edit link to GitHub
      editLink: {
        pattern:
          'https://github.com/datawhalechina/Hello-Agents/edit/main/docs/:path',
      },

      // Last updated
      lastUpdated: {
        text: '最后更新',
      },

      // Local search
      search: {
        provider: 'local',
      },

      // Sidebar by locale
      sidebar: {
        // Chinese sidebar
        '/': [
          {
            text: 'Hello-Agents',
            items: [{ text: '前言', link: '/前言' }],
          },
          {
            text: '第一部分：智能体与语言模型基础',
            items: [
              {
                text: '第一章 初识智能体',
                link: '/chapter1/第一章 初识智能体',
              },
              {
                text: '第二章 智能体发展史',
                link: '/chapter2/第二章 智能体发展史',
              },
              {
                text: '第三章 大语言模型基础',
                link: '/chapter3/第三章 大语言模型基础',
              },
            ],
          },
          {
            text: '第二部分：构建你的大语言模型智能体',
            items: [
              {
                text: '第四章 智能体经典范式构建',
                link: '/chapter4/第四章 智能体经典范式构建',
              },
              {
                text: '第五章 基于低代码平台的智能体搭建',
                link: '/chapter5/第五章 基于低代码平台的智能体搭建',
              },
              {
                text: '第六章 框架开发实践',
                link: '/chapter6/第六章 框架开发实践',
              },
              {
                text: '第七章 构建你的Agent框架',
                link: '/chapter7/第七章 构建你的Agent框架',
              },
            ],
          },
          {
            text: '第三部分：高级知识扩展',
            items: [
              {
                text: '第八章 记忆与检索',
                link: '/chapter8/第八章 记忆与检索',
              },
              {
                text: '第九章 上下文工程',
                link: '/chapter9/第九章 上下文工程',
              },
              {
                text: '第十章 智能体通信协议',
                link: '/chapter10/第十章 智能体通信协议',
              },
              { text: '第十一章 Agentic-RL', link: '/chapter11/第十一章 Agentic-RL' },
              {
                text: '第十二章 智能体性能评估',
                link: '/chapter12/第十二章 智能体性能评估',
              },
            ],
          },
          {
            text: '第四部分：综合案例进阶',
            items: [
              {
                text: '第十三章 智能旅行助手',
                link: '/chapter13/第十三章 智能旅行助手',
              },
              {
                text: '第十四章 自动化深度研究智能体',
                link: '/chapter14/第十四章 自动化深度研究智能体',
              },
              {
                text: '第十五章 构建赛博小镇',
                link: '/chapter15/第十五章 构建赛博小镇',
              },
            ],
          },
          {
            text: '第五部分：毕业设计及未来展望',
            items: [
              {
                text: '第十六章 毕业设计',
                link: '/chapter16/第十六章 毕业设计',
              },
            ],
          },
        ],

        // English sidebar
        '/en/': [
          {
            text: 'Hello-Agents',
            items: [{ text: 'Preface', link: '/en/Preface' }],
          },
          {
            text: 'Part I: Fundamentals of Agents and Language Models',
            items: [
              {
                text: 'Chapter 1 Introduction to Agents',
                link: '/en/chapter1/Chapter1-Introduction-to-Agents',
              },
              {
                text: 'Chapter 2 History of Agents',
                link: '/en/chapter2/Chapter2-History-of-Agents',
              },
              {
                text: 'Chapter 3 Fundamentals of Large Language Models',
                link: '/en/chapter3/Chapter3-Fundamentals-of-Large-Language-Models',
              },
            ],
          },
          {
            text: 'Part II: Building Your LLM Agent',
            items: [
              {
                text: 'Chapter 4 Building Classic Agent Paradigms',
                link: '/en/chapter4/Chapter4-Building-Classic-Agent-Paradigms',
              },
              {
                text: 'Chapter 5 Building Agents with Low-Code Platforms',
                link: '/en/chapter5/Chapter5-Building-Agents-with-Low-Code-Platforms',
              },
              {
                text: 'Chapter 6 Framework Development Practice',
                link: '/en/chapter6/Chapter6-Framework-Development-Practice',
              },
              {
                text: 'Chapter 7 Building Your Agent Framework',
                link: '/en/chapter7/Chapter7-Building-Your-Agent-Framework',
              },
            ],
          },
          {
            text: 'Part III: Advanced Knowledge',
            items: [
              {
                text: 'Chapter 8 Memory and Retrieval',
                link: '/en/chapter8/Chapter8-Memory-and-Retrieval',
              },
              {
                text: 'Chapter 9 Context Engineering',
                link: '/en/chapter9/Chapter9-Context-Engineering',
              },
              {
                text: 'Chapter 10 Agent Communication Protocols',
                link: '/en/chapter10/Chapter10-Agent-Communication-Protocols',
              },
              {
                text: 'Chapter 11 Agentic-RL',
                link: '/en/chapter11/Chapter11-Agentic-RL',
              },
              {
                text: 'Chapter 12 Agent Performance Evaluation',
                link: '/en/chapter12/Chapter12-Agent-Performance-Evaluation',
              },
            ],
          },
          {
            text: 'Part IV: Comprehensive Case Studies',
            items: [
              {
                text: 'Chapter 13 Intelligent Travel Assistant',
                link: '/en/chapter13/Chapter13-Intelligent-Travel-Assistant',
              },
              {
                text: 'Chapter 14 Automated Deep Research Agent',
                link: '/en/chapter14/Chapter14-Automated-Deep-Research-Agent',
              },
              {
                text: 'Chapter 15 Building Cyber Town',
                link: '/en/chapter15/Chapter15-Building-Cyber-Town',
              },
            ],
          },
          {
            text: 'Part V: Graduation Project and Future Outlook',
            items: [
              {
                text: 'Chapter 16 Graduation Project',
                link: '/en/chapter16/Chapter16-Graduation-Project',
              },
            ],
          },
        ],
      },
    },

  })
)
