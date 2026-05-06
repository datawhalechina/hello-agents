#!/usr/bin/env node

const stdio = process.stdin;
const stdout = process.stdout;

let requestId = 0;
const pendingRequests = new Map();

stdio.setEncoding('utf-8');

stdio.on('data', (data) => {
  const lines = data.trim().split('\n');
  for (const line of lines) {
    if (line.trim()) {
      try {
        const message = JSON.parse(line);
        handleMessage(message);
      } catch (e) {
        sendError(null, -32700, 'Parse error');
      }
    }
  }
});

function handleMessage(message) {
  if (!message.jsonrpc || message.jsonrpc !== '2.0') {
    console.error('[MCP Server] Invalid JSON-RPC message');
    sendError(message.id, -32600, 'Invalid Request');
    return;
  }

  console.error(`[MCP Server] Handling: ${message.method}`);

  switch (message.method) {
    case 'initialize':
      handleInitialize(message.id, message.params);
      break;
    case 'tools/list':
      handleToolsList(message.id);
      break;
    case 'tools/call':
      handleToolsCall(message.id, message.params);
      break;
    case 'resources/list':
      handleResourcesList(message.id);
      break;
    case 'prompts/list':
      handlePromptsList(message.id);
      break;
    case 'ping':
      sendResponse(message.id, { status: 'ok' });
      break;
    case 'notifications/initialized':
      console.error('[MCP Server] Client initialized notification received');
      break;
    default:
      if (!message.id) return;
      sendError(message.id, -32601, `Method not found: ${message.method}`);
  }
}

function handleInitialize(id, params) {
  const response = {
    protocolVersion: '2024-11-05',
    capabilities: {
      tools: { listChanged: true },
      resources: { subscribe: true, listChanged: true },
      prompts: { listChanged: true }
    },
    serverInfo: {
      name: 'demo-mcp-server',
      version: '1.0.0'
    }
  };
  sendResponse(id, response);
}

function handleToolsList(id) {
  const tools = [
    {
      name: 'get_weather',
      description: 'Get weather for a city',
      inputSchema: {
        type: 'object',
        properties: {
          city: { type: 'string', description: 'City name' },
          units: { type: 'string', enum: ['celsius', 'fahrenheit'], default: 'celsius' }
        },
        required: ['city']
      }
    },
    {
      name: 'calculate',
      description: 'Perform basic calculations',
      inputSchema: {
        type: 'object',
        properties: {
          expression: { type: 'string', description: 'Math expression' }
        },
        required: ['expression']
      }
    },
    {
      name: 'echo',
      description: 'Echo back the input',
      inputSchema: {
        type: 'object',
        properties: {
          message: { type: 'string' }
        },
        required: ['message']
      }
    }
  ];
  sendResponse(id, { tools });
}

function handleToolsCall(id, params) {
  const { name, arguments: args } = params;
  console.error(`[MCP Server] Calling tool: ${name}`, JSON.stringify(args));

  try {
    let result;
    switch (name) {
      case 'get_weather':
        result = {
          content: [
            {
              type: 'text',
              text: JSON.stringify({
                city: args.city,
                temp: Math.round(Math.random() * 30),
                condition: ['sunny', 'cloudy', 'rainy'][Math.floor(Math.random() * 3)],
                units: args.units || 'celsius'
              }, null, 2)
            }
          ]
        };
        break;
      case 'calculate':
        try {
          const safeEval = new Function('return ' + args.expression);
          const value = safeEval();
          result = {
            content: [{ type: 'text', text: `${args.expression} = ${value}` }]
          };
        } catch {
          result = {
            content: [{ type: 'text', text: `Error: Invalid expression "${args.expression}"` }],
            isError: true
          };
        }
        break;
      case 'echo':
        result = {
          content: [{ type: 'text', text: `Echo: ${args.message}` }]
        };
        break;
      default:
        throw new Error(`Unknown tool: ${name}`);
    }
    sendResponse(id, result);
  } catch (error) {
    console.error(`[MCP Server] Error: ${error.message}`);
    sendError(id, -32603, error.message);
  }
}

function handleResourcesList(id) {
  const resources = [
    {
      uri: 'demo://config',
      name: 'config',
      description: 'Server configuration',
      mimeType: 'application/json'
    },
    {
      uri: 'demo://status',
      name: 'status',
      description: 'Server status',
      mimeType: 'text/plain'
    }
  ];
  sendResponse(id, { resources });
}

function handlePromptsList(id) {
  const prompts = [
    {
      name: 'code_review',
      description: 'Review code changes',
      arguments: [
        { name: 'language', description: 'Programming language', required: true }
      ]
    },
    {
      name: 'debug_helper',
      description: 'Help debug an issue',
      arguments: []
    }
  ];
  sendResponse(id, { prompts });
}

function sendResponse(id, result) {
  const response = { jsonrpc: '2.0', id, result };
  console.error(`[MCP Server] Sending response for id: ${id}`);
  stdout.write(JSON.stringify(response) + '\n');
}

function sendError(id, code, message, data = null) {
  const error = { jsonrpc: '2.0', id, error: { code, message } };
  if (data) error.error.data = data;
  console.error(`[MCP Server] Sending error response for id ${id}: ${code} ${message}`);
  stdout.write(JSON.stringify(error) + '\n');
}

console.error('[MCP Server] Started, listening on stdin...');
