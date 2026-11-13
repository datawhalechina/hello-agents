import { useEffect, useRef, useState } from 'react';
import { useDialogFocus } from './FeatureDialog';
import { CustomProviderDialog } from './CustomProviderDialog';
import type { ModelSettings, SavedConnection } from './types';

type ConnectionResult = {
  status: 'success' | 'warning' | 'error';
  message: string;
  latency_ms?: number;
};

const providers = {
  deepseek: { label: 'DeepSeek', baseUrl: 'https://api.deepseek.com' },
  kimi: { label: 'Kimi', baseUrl: 'https://api.moonshot.cn/v1' },
};
type Provider = keyof typeof providers | 'custom' | '';
const normalizedAddress = (address: string) => address.trim().replace(/\/+$/, '');
function providerFor(address: string): Provider {
  const endpoint = normalizedAddress(address);
  if (endpoint === providers.deepseek.baseUrl || endpoint === providers.deepseek.baseUrl + '/v1')
    return 'deepseek';
  if (endpoint === providers.kimi.baseUrl) return 'kimi';
  return endpoint ? 'custom' : '';
}

export function SettingsDialog({
  settings,
  close,
  saved,
}: {
  settings: ModelSettings;
  close: () => void;
  saved: (value: ModelSettings) => void;
}) {
  const [form, setForm] = useState({ ...settings, api_key: '' });
  const [connections, setConnections] = useState<SavedConnection[]>([]);
  const [loadingConnections, setLoadingConnections] = useState(true);
  const [connectionNotice, setConnectionNotice] = useState('');
  const [provider, setProvider] = useState<Provider>(() => providerFor(settings.base_url));
  const [customAddress, setCustomAddress] = useState(() =>
    providerFor(settings.base_url) === 'custom' ? settings.base_url : '',
  );
  const [customOpen, setCustomOpen] = useState(false);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [models, setModels] = useState<string[]>([]);
  const [fetching, setFetching] = useState(false);
  const [manual, setManual] = useState(true);
  const [modelStatus, setModelStatus] = useState('');
  const [modelError, setModelError] = useState('');
  const [testing, setTesting] = useState(false);
  const [connectionResult, setConnectionResult] = useState<ConnectionResult | null>(null);
  const discoveryVersion = useRef(0);
  const connectionVersion = useRef(0);
  useEffect(() => {
    let active = true;
    void window.codeAssistant
      .request<{ connections: SavedConnection[] }>('GET', '/api/connections')
      .then((value) => {
        if (active) setConnections(value.connections);
      })
      .catch(() => {
        if (active) setError('无法加载配置列表，请关闭后重新打开。');
      })
      .finally(() => {
        if (active) setLoadingConnections(false);
      });
    return () => {
      active = false;
    };
  }, []);
  useEffect(
    () => () => {
      discoveryVersion.current++;
      connectionVersion.current++;
    },
    [],
  );
  const dialog = useDialogFocus<HTMLFormElement>(() => {
    if (!busy) close();
  });
  const update = (key: string, value: string | number) => {
    if (key === 'base_url' || key === 'api_key') {
      discoveryVersion.current++;
      connectionVersion.current++;
      setTesting(false);
      setConnectionResult(null);
      setFetching(false);
      setModels([]);
      setManual(true);
      setModelStatus('');
      setModelError('');
    }
    setForm((previous) => ({ ...previous, [key]: value }));
  };
  function loadConnection(next: ModelSettings) {
    setConnectionNotice('');
    discoveryVersion.current++;
    connectionVersion.current++;
    setFetching(false);
    setTesting(false);
    setModels([]);
    setManual(true);
    setModelStatus('');
    setModelError('');
    setConnectionResult(null);
    setError('');
    setForm({ ...next, api_key: '' });
    setProvider(providerFor(next.base_url));
    setCustomAddress(providerFor(next.base_url) === 'custom' ? next.base_url : '');
  }
  function newConnection() {
    loadConnection({
      connection_id: null,
      connection_name: '',
      base_url: '',
      model: '',
      has_api_key: false,
      key_storage: 'none',
      max_steps: 1000,
    });
  }
  async function useConnection(id: string) {
    if (busy) return;
    if (!id) {
      newConnection();
      return;
    }
    setBusy(true);
    discoveryVersion.current++;
    connectionVersion.current++;
    try {
      const next = await window.codeAssistant.request<ModelSettings>(
        'POST',
        `/api/connections/${id}/activate`,
      );
      loadConnection(next);
      saved(next);
    } catch (error) {
      setError(
        String(error instanceof Error ? error.message : error).replace(
          /^Error invoking remote method '[^']+': Error: /,
          '',
        ),
      );
    } finally {
      setBusy(false);
      setFetching(false);
      setTesting(false);
    }
  }
  async function deleteConnection() {
    if (busy || loadingConnections || !form.connection_id) return;
    setBusy(true);
    setError('');
    discoveryVersion.current++;
    connectionVersion.current++;
    setFetching(false);
    setTesting(false);
    try {
      const result = await window.codeAssistant.request<{
        settings: ModelSettings;
        connections: SavedConnection[];
      }>('DELETE', `/api/connections/${form.connection_id}`);
      setConnections(result.connections);
      loadConnection(result.settings);
      saved(result.settings);
      setConnectionNotice('已删除配置。');
    } catch (error) {
      setError(
        String(error instanceof Error ? error.message : error).replace(
          /^Error invoking remote method '[^']+': Error: /,
          '',
        ),
      );
    } finally {
      setBusy(false);
    }
  }
  function chooseEndpoint(next: Provider, endpoint: string) {
    const changed = normalizedAddress(endpoint) !== normalizedAddress(form.base_url);
    setProvider(next);
    update('base_url', endpoint);
    if (changed) setForm((previous) => ({ ...previous, model: '', api_key: '' }));
    setError('');
  }
  const usesSavedKey =
    !!form.connection_id &&
    form.has_api_key &&
    normalizedAddress(form.base_url) === normalizedAddress(settings.base_url);
  async function fetchModels() {
    if (fetching || testing || busy || !form.base_url.trim()) return;
    const version = ++discoveryVersion.current;
    setFetching(true);
    setModelError('');
    setModelStatus('正在获取可用模型…');
    try {
      const result = await window.codeAssistant.request<{ models: string[] }>(
        'POST',
        '/api/models',
        {
          base_url: form.base_url,
          api_key: form.api_key,
          connection_id: form.connection_id,
          use_saved_key: !!form.connection_id,
        },
      );
      if (version !== discoveryVersion.current) return;
      setModels(result.models);
      setManual(!result.models.length);
      setModelStatus(
        result.models.length
          ? `已获取 ${result.models.length} 个模型，请从列表选择。`
          : '此服务未返回可用模型，可手动填写模型名称。',
      );
    } catch (error) {
      if (version !== discoveryVersion.current) return;
      setModels([]);
      setManual(true);
      setModelStatus('');
      setModelError(
        String(error instanceof Error ? error.message : error).replace(
          /^Error invoking remote method '[^']+': Error: /,
          '',
        ),
      );
    } finally {
      if (version === discoveryVersion.current) setFetching(false);
    }
  }
  async function testConnection() {
    if (testing || fetching || busy || !form.base_url.trim()) return;
    const version = ++connectionVersion.current;
    setTesting(true);
    setConnectionResult(null);
    try {
      const result = await window.codeAssistant.request<ConnectionResult>(
        'POST',
        '/api/connection-test',
        {
          base_url: form.base_url,
          api_key: form.api_key,
          connection_id: form.connection_id,
          use_saved_key: !!form.connection_id,
        },
      );
      if (version === connectionVersion.current) setConnectionResult(result);
    } catch (error) {
      if (version !== connectionVersion.current) return;
      setConnectionResult({
        status: 'error',
        message: String(error instanceof Error ? error.message : error).replace(
          /^Error invoking remote method '[^']+': Error: /,
          '',
        ),
      });
    } finally {
      if (version === connectionVersion.current) setTesting(false);
    }
  }
  return (
    <div className="modal-shade settings-shade">
      <form
        ref={dialog}
        role="dialog"
        aria-modal="true"
        aria-label="模型设置"
        tabIndex={-1}
        className="settings-dialog"
        onSubmit={async (event) => {
          event.preventDefault();
          if (busy || fetching || testing) return;
          setBusy(true);
          setError('');
          try {
            saved(
              await window.codeAssistant.request<ModelSettings>('POST', '/api/connections', {
                ...form,
                id: form.connection_id,
                name: form.connection_name,
              }),
            );
            close();
          } catch (error) {
            setError(
              String(error instanceof Error ? error.message : error).replace(
                /^Error invoking remote method '[^']+': Error: /,
                '',
              ),
            );
          } finally {
            setBusy(false);
          }
        }}
      >
        <div className="dialog-heading">
          <div>
            <span className="feature-eyebrow">MODEL CONNECTION</span>
            <h2>连接你的模型</h2>
          </div>
          <button
            type="button"
            className="feature-close"
            onClick={close}
            disabled={busy}
            aria-label="关闭模型设置"
          >
            ×
          </button>
        </div>
        <div className="settings-body">
          <p className="muted">支持兼容 API 的云端服务与本地模型，配置保存在当前电脑。</p>
          <div className="connection-presets">
            <div className="connection-presets-heading">
              <label htmlFor="saved-connection">配置列表</label>
              <div className="connection-presets-actions">
                <button
                  type="button"
                  className="secondary"
                  disabled={busy || loadingConnections}
                  onClick={newConnection}
                >
                  新建配置
                </button>
                <button
                  type="button"
                  className="secondary connection-delete"
                  disabled={busy || loadingConnections || !form.connection_id}
                  onClick={() => void deleteConnection()}
                >
                  删除配置
                </button>
              </div>
            </div>
            <div className="connection-presets-fields">
              <select
                id="saved-connection"
                aria-label="配置列表"
                value={form.connection_id || ''}
                disabled={busy || loadingConnections}
                onChange={(event) => void useConnection(event.target.value)}
              >
                <option value="">
                  {loadingConnections ? '正在加载配置…' : '新配置（未保存）'}
                </option>
                {connections.map((item) => (
                  <option key={item.id} value={item.id}>
                    {item.name} · {item.model}
                    {settings.connection_id === item.id ? ' · 使用中' : ''}
                  </option>
                ))}
              </select>
              <input
                aria-label="配置名称"
                name="connection_name"
                maxLength={100}
                value={form.connection_name}
                disabled={busy}
                placeholder="配置名称（留空自动命名）"
                onChange={(event) => update('connection_name', event.target.value)}
              />
            </div>
            <p className="connection-presets-status" role="status">
              {connectionNotice}
              {settings.connection_id ? `当前使用：${settings.connection_name}。` : ''}
              {form.connection_id
                ? '选择配置即可切换，修改后点保存连接。'
                : '新配置保存后生效，不会覆盖已有配置。'}
            </p>
          </div>
          <div className="api-connection-field">
            <label htmlFor="api-provider">API 地址 / 服务商</label>
            <div className="api-address-row">
              <select
                id="api-provider"
                name="provider"
                required
                aria-label="API 服务商"
                value={provider}
                disabled={busy}
                aria-describedby="provider-address api-connection-status"
                onChange={(event) => {
                  const next = event.target.value as Provider;
                  if (next === 'custom') setCustomOpen(true);
                  else if (next === 'deepseek' || next === 'kimi')
                    chooseEndpoint(next, providers[next].baseUrl);
                }}
              >
                <option value="" disabled>
                  请选择服务商
                </option>
                {Object.entries(providers).map(([id, item]) => (
                  <option key={id} value={id}>
                    {item.label}
                  </option>
                ))}
                <option value="custom">自定义服务商</option>
              </select>
              <button
                type="button"
                className="secondary connection-test"
                disabled={busy || testing || fetching || !form.base_url.trim()}
                onClick={() => void testConnection()}
              >
                {testing ? '测试中…' : '测试连接'}
              </button>
            </div>
            <div className="provider-address" id="provider-address">
              <span title={form.base_url}>{form.base_url || '选择服务商后使用对应 API 地址'}</span>
              {provider === 'custom' && (
                <button
                  type="button"
                  className="model-entry-toggle"
                  disabled={busy}
                  onClick={() => setCustomOpen(true)}
                >
                  编辑地址
                </button>
              )}
            </div>
            <span
              id="api-connection-status"
              className={`api-connection-status ${connectionResult ? `is-${connectionResult.status}` : ''}`}
              role={connectionResult?.status === 'error' ? 'alert' : 'status'}
            >
              {testing
                ? '正在检查服务连接和访问权限…'
                : connectionResult
                  ? `${connectionResult.message}${connectionResult.latency_ms !== undefined ? `（${connectionResult.latency_ms} 毫秒）` : ''}`
                  : ''}
            </span>
          </div>
          <div className="model-field">
            <div className="model-field-heading">
              <label htmlFor="model-name">模型名称</label>
              {models.length > 0 && (
                <button
                  type="button"
                  className="model-entry-toggle"
                  disabled={busy || fetching}
                  onClick={() => setManual((previous) => !previous)}
                >
                  {manual ? '从列表选择' : '手动填写'}
                </button>
              )}
            </div>
            <div className="model-name-row">
              {manual || !models.length ? (
                <input
                  id="model-name"
                  required
                  name="model"
                  value={form.model}
                  disabled={busy}
                  onChange={(event) => update('model', event.target.value)}
                  placeholder="获取列表选择，或手动填写模型 ID"
                  aria-describedby="model-fetch-status"
                />
              ) : (
                <select
                  id="model-name"
                  required
                  name="model"
                  value={form.model}
                  disabled={busy}
                  onChange={(event) => update('model', event.target.value)}
                  aria-describedby="model-fetch-status"
                >
                  <option value="" disabled>
                    请选择模型
                  </option>
                  {form.model && !models.includes(form.model) && (
                    <option value={form.model}>{form.model}（当前填写）</option>
                  )}
                  {models.map((model) => (
                    <option key={model} value={model}>
                      {model}
                    </option>
                  ))}
                </select>
              )}
              <button
                type="button"
                className="secondary model-fetch"
                onClick={() => void fetchModels()}
                disabled={busy || fetching || testing || !form.base_url.trim()}
              >
                {fetching ? '获取中…' : '获取模型列表'}
              </button>
            </div>
            <span className="model-fetch-status" id="model-fetch-status" role="status">
              {modelStatus}
            </span>
            {modelError && (
              <span className="model-fetch-error" role="alert">
                {modelError}
              </span>
            )}
          </div>
          <label>
            API Key
            <input
              type="password"
              name="api_key"
              value={form.api_key}
              disabled={busy}
              onChange={(event) => update('api_key', event.target.value)}
              autoComplete="off"
              placeholder={
                usesSavedKey
                  ? '已设置，留空保留现有密钥'
                  : '填写此服务商的密钥，本地无鉴权服务可留空'
              }
            />
          </label>
          <label>
            单任务最大执行步数
            <input
              type="number"
              min="1"
              step="1"
              required
              value={form.max_steps}
              disabled={busy}
              onChange={(event) => update('max_steps', Number(event.target.value))}
            />
          </label>
          <p className="hint">任务不设执行时间上限，仅按步数限额，可随时手动停止。</p>
          <p className="hint">
            {settings.key_storage === 'memory'
              ? '当前密钥仅在本次服务会话中保存，重启后需重新填写。'
              : '密钥优先存入系统凭据库；环境不支持时仅保存在内存。'}
          </p>
          {error && (
            <div className="error-inline" role="alert">
              {error}
            </div>
          )}
        </div>
        <div className="dialog-actions">
          <button type="button" className="secondary" onClick={close} disabled={busy}>
            取消
          </button>
          <button className="primary" type="submit" disabled={busy || fetching || testing}>
            {busy ? '保存中…' : '保存连接'}
          </button>
        </div>
      </form>
      {customOpen && (
        <CustomProviderDialog
          initialAddress={customAddress}
          close={() => setCustomOpen(false)}
          confirm={(endpoint) => {
            setCustomAddress(endpoint);
            chooseEndpoint('custom', endpoint);
            setCustomOpen(false);
          }}
        />
      )}
    </div>
  );
}
