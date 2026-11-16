"""Hot-reloadable model settings with write-only, locally encrypted credentials."""
from __future__ import annotations

import hashlib
import ipaddress
import json
import os
from pathlib import Path
from urllib.parse import urlsplit

from cryptography.fernet import Fernet, InvalidToken

from ..config import Settings
from ..schemas import ModelConnectionRequest, ModelConnectionResult, ModelSettingsUpdate, ModelSettingsView, utcnow
from ..storage import ConflictError, Repository


def validate_endpoint(value: str) -> str:
    value = value.strip().rstrip("/")
    if any(c in value for c in "\r\n\t"):
        raise ValueError("服务地址格式无效")
    try:
        parts = urlsplit(value)
        port = parts.port
    except ValueError as error:
        raise ValueError("服务地址格式无效") from error
    if parts.scheme not in {"http", "https"} or not parts.hostname or parts.username or parts.password or parts.query or parts.fragment:
        raise ValueError("请填写HTTP(S)接口根地址，不要包含用户名、密码、查询参数或片段")
    if port is not None and not 1 <= port <= 65535:
        raise ValueError("服务端口无效")
    try:
        address = ipaddress.ip_address(parts.hostname)
    except ValueError:
        address = None
    if address and (address.is_link_local or address.is_multicast or address.is_unspecified):
        raise ValueError("该服务地址不可用")
    if parts.path.rstrip("/").endswith(("/chat/completions", "/responses")):
        raise ValueError("请填写接口根地址，例如服务商提供的/v1地址，不要填写完整聊天路径")
    return value


class LocalSecretStore:
    def __init__(self, database_path: str):
        self.path = None if database_path == ":memory:" else Path(database_path).resolve().parent / ".workflow-model.key"
        self.memory_key: bytes | None = None

    def _key(self, create: bool) -> bytes:
        if self.path is None:
            if self.memory_key is None:
                if not create:
                    raise ValueError("保存的密钥不可读取，请重新填写API Key")
                self.memory_key = Fernet.generate_key()
            return self.memory_key
        if create and not self.path.exists():
            self.path.parent.mkdir(parents=True, exist_ok=True)
            try:
                descriptor = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            except FileExistsError:
                pass
            else:
                with os.fdopen(descriptor, "wb") as stream:
                    stream.write(Fernet.generate_key())
        try:
            return self.path.read_bytes()
        except OSError as error:
            raise ValueError("保存的密钥不可读取，请重新填写API Key") from error

    def encrypt(self, value: str) -> str:
        try:
            return Fernet(self._key(True)).encrypt(value.encode()).decode()
        except (OSError, ValueError) as error:
            raise ValueError("无法保存本机密钥，请检查数据目录权限") from error

    def decrypt(self, value: str) -> str:
        try:
            return Fernet(self._key(False)).decrypt(value.encode()).decode()
        except (InvalidToken, ValueError, UnicodeError) as error:
            raise ValueError("保存的密钥不可读取，请重新填写API Key") from error


def _fingerprint(model: str, base_url: str, key: str) -> str:
    return hashlib.sha256(json.dumps([model, base_url, key], ensure_ascii=False).encode()).hexdigest()


class ModelSettingsService:
    def __init__(self, repository: Repository, settings: Settings):
        self.repository = repository
        self.settings = settings
        self.secrets = LocalSecretStore(settings.database_path)

    def _saved(self) -> dict | None:
        return self.repository.read_state("model_settings")

    def _key(self) -> str:
        saved = self._saved()
        if saved is None:
            return self.settings.llm_api_key
        ciphertext = saved.get("encrypted_api_key", "")
        return self.secrets.decrypt(ciphertext) if ciphertext else ""

    def view(self) -> ModelSettingsView:
        saved = self._saved()
        values = saved or {"provider": self.settings.provider, "model": self.settings.llm_model,
                           "base_url": self.settings.llm_base_url, "external_data_authorized": self.settings.external_data_authorized,
                           "batch_size": self.settings.llm_batch_size}
        storage_error = None
        try:
            key = self._key()
        except ValueError as error:
            key = ""
            storage_error = str(error)
        tested = self.repository.read_state("model_connection_test") or {}
        signature = _fingerprint(values["model"], values["base_url"], key) if key else ""
        return ModelSettingsView(provider=values["provider"], model=values["model"], base_url=values["base_url"],
                                 api_key_configured=bool(key or storage_error), external_data_authorized=bool(values["external_data_authorized"]),
                                 batch_size=values["batch_size"], saved=saved is not None,
                                 test_status="passed" if signature and tested.get("fingerprint") == signature else "not_tested", storage_error=storage_error,
                                 thinking=values.get('thinking', self.settings.llm_thinking if saved is None else False))

    def effective(self) -> Settings:
        saved = self._saved()
        if saved is None:
            return self.settings
        return self.settings.model_copy(update={"provider": saved["provider"], "llm_model": saved["model"],
                                               "llm_base_url": saved["base_url"], "llm_api_key": self._key(),
                                               "external_llm_enabled": saved["provider"] == "helloagents-llm",
                                               "external_data_authorized": saved["external_data_authorized"], "llm_batch_size": saved["batch_size"],
                                               "llm_thinking": saved.get('thinking', False)})

    def test(self, request: ModelConnectionRequest) -> ModelConnectionResult:
        from ..extraction.remote import test_model_connection
        model = request.model.strip()
        if not model:
            raise ValueError("请填写模型ID")
        endpoint = validate_endpoint(request.base_url)
        supplied = request.api_key.get_secret_value().strip() if request.api_key else ""
        key = supplied or self._key()
        if not key:
            raise ValueError("请填写API Key")
        result = ModelConnectionResult.model_validate(test_model_connection(model, key, endpoint))
        if result.ok:
            self.repository.write_state("model_connection_test", {"fingerprint": _fingerprint(model, endpoint, key), "tested_at": utcnow().isoformat()})
        return result

    def update(self, request: ModelSettingsUpdate) -> ModelSettingsView:
        with self.repository.lock:
            if any(job.status in {"queued", "running"} for job in self.repository.jobs()):
                raise ConflictError("分析任务仍在运行，请先停止任务或等待完成后修改模型设置")
            supplied = request.api_key.get_secret_value().strip() if request.api_key else ""
            key = "" if request.clear_api_key else supplied or self._key()
            model = request.model.strip()
            endpoint = validate_endpoint(request.base_url) if request.base_url.strip() else ""
            authorized = request.provider == "helloagents-llm" and request.external_data_authorized
            if request.provider == "helloagents-llm":
                if not model or not endpoint or not key:
                    raise ValueError("启用模型需要填写模型ID、服务地址和API Key")
                if not authorized:
                    raise ValueError("请明确授权将当前所选来源消息发送到该模型服务")
                tested = self.repository.read_state("model_connection_test") or {}
                if tested.get("fingerprint") != _fingerprint(model, endpoint, key):
                    raise ConflictError("请先测试当前地址、模型与API Key的连接")
            self.repository.write_state("model_settings", {"provider": request.provider, "model": model, "base_url": endpoint,
                                                            "external_data_authorized": bool(authorized), "batch_size": request.batch_size,
                                                            "encrypted_api_key": self.secrets.encrypt(key) if key else "", 'thinking': request.thinking})
            return self.view()
