import { useEffect, useState } from 'react';
import { useDialogFocus } from './FeatureDialog';

export function CustomProviderDialog({
  initialAddress,
  confirm,
  close,
}: {
  initialAddress: string;
  confirm: (address: string) => void;
  close: () => void;
}) {
  const [address, setAddress] = useState(initialAddress);
  const [error, setError] = useState('');
  const dialog = useDialogFocus<HTMLFormElement>(close);
  useEffect(() => {
    dialog.current?.querySelector<HTMLInputElement>('input')?.focus();
  }, [dialog]);
  return (
    <div className="custom-provider-shade">
      <form
        ref={dialog}
        className="custom-provider-dialog"
        role="dialog"
        aria-modal="true"
        aria-label="自定义服务商"
        tabIndex={-1}
        noValidate
        onSubmit={(event) => {
          event.preventDefault();
          const endpoint = address.trim().replace(/\/+$/, '');
          try {
            const parsed = new URL(endpoint);
            if (
              !['http:', 'https:'].includes(parsed.protocol) ||
              !parsed.hostname ||
              parsed.username ||
              parsed.password ||
              parsed.search ||
              parsed.hash ||
              /\s/.test(endpoint)
            )
              throw new Error();
          } catch {
            setError('请输入有效的 HTTP(S) API 地址，不要包含用户名、密码或查询参数。');
            return;
          }
          confirm(endpoint);
        }}
      >
        <div className="dialog-heading">
          <div>
            <span className="feature-eyebrow">CUSTOM PROVIDER</span>
            <h2>自定义服务商</h2>
          </div>
          <button
            type="button"
            className="feature-close"
            aria-label="关闭自定义服务商"
            onClick={close}
          >
            ×
          </button>
        </div>
        <p className="muted">填写兼容服务的 API 根地址，也支持本地模型服务。</p>
        <label htmlFor="custom-api-address">API 地址</label>
        <input
          id="custom-api-address"
          name="base_url"
          value={address}
          inputMode="url"
          placeholder="https://你的模型服务/v1"
          autoComplete="off"
          spellCheck={false}
          onChange={(event) => {
            setAddress(event.target.value);
            setError('');
          }}
        />
        {error && (
          <div className="error-inline" role="alert">
            {error}
          </div>
        )}
        <div className="dialog-actions">
          <button type="button" className="secondary" onClick={close}>
            取消
          </button>
          <button type="submit" className="primary">
            使用此地址
          </button>
        </div>
      </form>
    </div>
  );
}
