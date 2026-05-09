#!/usr/bin/env node

const { spawn } = require('child_process');

let requestId = 0;
let responseHandlers = new Map();

const server = spawn('node', [__dirname + '/mcp-server.js'], {
  stdio: ['pipe', 'pipe', 'pipe']
});

server.stderr.on('data', (data) => {
  const lines = data.toString().trim().split('\n');
  for (const line of lines) {
    if (line) console.log(`[Server] ${line}`);
  }
});

server.stdout.on('data', (data) => {
  const lines = data.toString().trim().split('\n');
  for (const line of lines) {
    if (line.trim()) {
      try {
        const response = JSON.parse(line);
        handleResponse(response);
      } catch (e) {
        console.error('[Parse Error]', e.message);
      }
    }
  }
});

function send(method, params = {}) {
  return new Promise((resolve, reject) => {
    const id = ++requestId;
    const message = { jsonrpc: '2.0', id, method, params };
    
    responseHandlers.set(id, { resolve, reject });
    server.stdin.write(JSON.stringify(message) + '\n');
    
    setTimeout(() => {
      if (responseHandlers.has(id)) {
        responseHandlers.delete(id);
        reject(new Error('Request timeout'));
      }
    }, 5000);
  });
}

function handleResponse(response) {
  if (response.id === undefined) {
    console.error('[Notification]', response);
    return;
  }
  
  const handler = responseHandlers.get(response.id);
  if (handler) {
    responseHandlers.delete(response.id);
    if (response.error) {
      handler.reject(new Error(`${response.error.code}: ${response.error.message}`));
    } else {
      handler.resolve(response.result);
    }
  }
}

function log(label, data) {
  console.log('\n' + '='.repeat(60));
  console.log(label);
  console.log('='.repeat(60));
  console.log(JSON.stringify(data, null, 2));
}

async function runTests() {
  try {
    console.log('\n[MCP Client] Starting tests...\n');

    const init = await send('initialize', {
      protocolVersion: '2024-11-05',
      capabilities: {},
      clientInfo: { name: 'test-client', version: '1.0.0' }
    });
    log('1. Initialize Response', init);
    
    // notifications 不等待响应
    send('notifications/initialized').catch(() => {});

    const tools = await send('tools/list');
    log('2. List Tools', tools);

    const weather = await send('tools/call', {
      name: 'get_weather',
      arguments: { city: 'Beijing', units: 'celsius' }
    });
    log('3. Call get_weather', weather);

    const calc = await send('tools/call', {
      name: 'calculate',
      arguments: { expression: '2 + 3 * 4' }
    });
    log('4. Call calculate', calc);

    const echo = await send('tools/call', {
      name: 'calculate',
      arguments: { expression: 'invalid++' }
    });
    log('5. Call calculate (error case)', echo);

    const resources = await send('resources/list');
    log('6. List Resources', resources);

    const prompts = await send('prompts/list');
    log('7. List Prompts', prompts);

    const error = await send('unknown_method').catch(e => e.message);
    console.log('\n8. Error handling test:', error.includes('Method not found') ? 'PASS' : 'FAIL');

    console.log('\n' + '='.repeat(60));
    console.log('All tests completed!');
    console.log('='.repeat(60));

  } catch (error) {
    console.error('[Error]', error.message);
  } finally {
    server.kill();
    process.exit(0);
  }
}

runTests();
