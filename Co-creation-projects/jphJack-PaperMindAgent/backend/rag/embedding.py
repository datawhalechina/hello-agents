"""本地 Embedding：直接用 transformers 加载 BGE 模型（绕开 sentence-transformers 与 pyarrow）。

为什么不用 sentence-transformers：
  你的环境里 pyarrow 在 import datasets 时触发 0xC0000005 访问冲突，
  而 sentence-transformers 强依赖 datasets → pyarrow，整条链路崩溃。
  这里直接用 transformers 加载 BERT backbone + CLS Pooling，向量结果与 sentence-transformers 等价。
"""
from __future__ import annotations

import os
import threading
import logging
from typing import List, Optional

# tokenizers 并行告警抑制；CUDA 由 torch 自行检测（GPU 优先，CPU 兜底）
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
# 强制 transformers / huggingface_hub 走离线模式，不再请求 Hub
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
os.environ.setdefault("HF_HUB_OFFLINE", "1")

from backend.config import settings

logger = logging.getLogger(__name__)

# mini-batch 大小：GPU 16，CPU 8（避免内存爆 + 减少 padding 浪费）
EMBED_BATCH_SIZE = 16


class Embedder:
    """本地 Embedder，懒加载 BGE 系列模型。

    支持任意 HuggingFace 上有 BertModel + AutoTokenizer 结构的嵌入模型
    （bge-large-zh-v1.5 / bge-base-zh / bge-small-zh / bge-m3 等）。
    """

    def __init__(self, model_name: Optional[str] = None):
        self.model_name = model_name or settings.EMBEDDING_MODEL
        self._model = None
        self._tokenizer = None
        self._lock = threading.Lock()
        # 自动检测：GPU 可用则用 GPU，否则回退 CPU
        self._device = self._detect_device()
        self._batch_size = EMBED_BATCH_SIZE if self._device != "cpu" else 8

    @staticmethod
    def _detect_device() -> str:
        """检测可用设备：CUDA 优先，CPU 兜底。"""
        try:
            import torch

            if torch.cuda.is_available():
                return "cuda"
        except Exception:
            pass
        return "cpu"

    def _resolve_local_snapshot(self, model_name: str) -> Optional[str]:
        """如果 HF 本地缓存已有该模型的 snapshot，直接返回快照路径。"""
        try:
            from pathlib import Path as _P
            from huggingface_hub.constants import HF_HUB_CACHE

            repo_dir_name = "models--" + model_name.replace("/", "--")
            snapshots_dir = _P(HF_HUB_CACHE) / repo_dir_name / "snapshots"
            if snapshots_dir.is_dir():
                snapshots = sorted(
                    [p for p in snapshots_dir.iterdir() if p.is_dir()],
                    key=lambda p: p.stat().st_mtime,
                    reverse=True,
                )
                if snapshots:
                    snap = snapshots[0]
                    if (snap / "config.json").exists():
                        return str(snap)
        except Exception:
            pass
        return None

    def _load(self):
        """懒加载模型：首次调用时加载，双重检查锁保证线程安全。"""
        import time as _time_load
        _t_entry = _time_load.perf_counter()
        logger.info("[_load] 进入 _load: model_is_none=%s", self._model is None)
        if self._model is None:
            _t_lock0 = _time_load.perf_counter()
            logger.info("[_load] 等待 self._lock...")
            with self._lock:
                _t_lock1 = _time_load.perf_counter()
                logger.info("[_load] 获得 self._lock: 等待 %.3fs", _t_lock1 - _t_lock0)
                if self._model is None:
                    import time as _time
                    _t_imp_t = _time.perf_counter()
                    import torch
                    _t_imp_torch = _time.perf_counter()
                    from transformers import AutoModel, AutoTokenizer
                    _t_imp_tf = _time.perf_counter()
                    logger.info(
                        "[_load] imports 完成: 总耗时 %.3fs (torch=%.3fs transformers=%.3fs, 从获得锁算起)",
                        _t_imp_tf - _t_lock1,
                        _t_imp_torch - _t_imp_t,
                        _t_imp_tf - _t_imp_torch,
                    )

                    _t0 = _time.perf_counter()
                    local_snapshot = self._resolve_local_snapshot(self.model_name)
                    if local_snapshot:
                        load_path = local_snapshot
                    else:
                        load_path = self.model_name
                    _t_resolve = _time.perf_counter()

                    # 注意：bge 官方建议 query 加指令前缀 "为这个句子生成表示以用于检索中文文档："
                    self._tokenizer = AutoTokenizer.from_pretrained(
                        load_path, local_files_only=bool(local_snapshot)
                    )
                    _t_tok = _time.perf_counter()

                    self._model = AutoModel.from_pretrained(
                        load_path, local_files_only=bool(local_snapshot)
                    )
                    _t_model_load = _time.perf_counter()

                    # 关键：将模型迁移到 device，并验证实际驻留设备
                    self._model = self._model.to(self._device)
                    _t_to_device = _time.perf_counter()

                    # 探测模型参数实际所在设备（防止 .to("cuda") 静默失败）
                    try:
                        param = next(self._model.parameters())
                        actual_device = str(param.device)
                    except Exception:
                        actual_device = "unknown"

                    self._model.eval()
                    _t_eval = _time.perf_counter()

                    # 注意：不做 CUDA warmup。
                    # 实测在 uvicorn 长驻进程里，dummy forward 反而要 24s（首次 CUDA 上下文初始化）。
                    # 让第一次真实 forward 自然完成初始化即可，避免额外开销。
                    _t_warmup = _t_eval

                    logger.info(
                        "Embedder 模型加载完成: model=%s, device=%s, actual_param_device=%s, batch_size=%d | "
                        "resolve=%.2fs tokenizer=%.2fs model_load=%.2fs to_device=%.2fs eval=%.2fs cuda_warmup=%.2fs total=%.2fs",
                        self.model_name, self._device, actual_device, self._batch_size,
                        _t_resolve - _t0, _t_tok - _t_resolve, _t_model_load - _t_tok,
                        _t_to_device - _t_model_load, _t_eval - _t_to_device,
                        _t_warmup - _t_eval, _t_warmup - _t0,
                    )

    @staticmethod
    def _last_token_pool(last_hidden_states, attention_mask):
        """BGE 系列使用的 last-token pooling（等价于 sentence-transformers 的 cls + 末尾 token）。"""
        left_padding = attention_mask[:, -1].sum() == attention_mask.shape[0]
        if left_padding:
            return last_hidden_states[:, -1]
        sequence_lengths = attention_mask.sum(dim=1) - 1
        batch_size = last_hidden_states.shape[0]
        return last_hidden_states[
            torch.arange(batch_size, device=last_hidden_states.device),
            sequence_lengths,
        ]

    def _encode(self, texts: List[str]):
        import time as _time
        import torch

        # BGE 官方推荐：query 加指令前缀，passage 不加
        is_query = getattr(self, "_is_query", True)
        if is_query and "bge" in self.model_name.lower() and "zh" in self.model_name.lower():
            prefix = "为这个句子生成表示以用于检索中文文档："
            texts = [prefix + t for t in texts]

        # 探测模型实际驻留设备（防止 .to("cuda") 静默失败导致实际跑 CPU）
        try:
            _actual_dev = str(next(self._model.parameters()).device)
        except Exception:
            _actual_dev = "unknown"

        # mini-batching：避免一次性把全部 chunk 喂入模型（CPU/显存压力 + padding 浪费）
        all_embeddings: List[List[float]] = []
        bs = max(1, self._batch_size)
        n_batches = (len(texts) + bs - 1) // bs
        _t_enc_start = _time.perf_counter()
        logger.info(
            "[_encode] 开始编码: %d texts, batch_size=%d, %d batches, model_device=%s, declared=%s",
            len(texts), bs, n_batches, _actual_dev, self._device,
        )
        for i in range(0, len(texts), bs):
            bi = i // bs
            batch = texts[i : i + bs]
            _t_b0 = _time.perf_counter()
            inputs = self._tokenizer(
                batch,
                padding=True,
                truncation=True,
                max_length=512,
                return_tensors="pt",
            ).to(self._device)
            _t_tok = _time.perf_counter()

            with torch.no_grad():
                outputs = self._model(**inputs)
                # bge 用 last_token_pool；其它 BERT 类模型退化为 [CLS] pooling
                try:
                    embeddings = self._last_token_pool(
                        outputs.last_hidden_state, inputs["attention_mask"]
                    )
                except Exception:
                    embeddings = outputs.last_hidden_state[:, 0]
                embeddings = torch.nn.functional.normalize(embeddings, p=2, dim=1)
            # GPU 同步，确保 forward 真正完成后再计时
            if "cuda" in _actual_dev:
                torch.cuda.synchronize()
            _t_fwd = _time.perf_counter()
            all_embeddings.extend(embeddings.cpu().numpy().tolist())
            _t_cpu = _time.perf_counter()

            # 每个批次都打印（首次诊断用；定位后可改为每 10 批打印一次）
            if bi < 3 or bi % 10 == 0 or bi == n_batches - 1:
                logger.info(
                    "[_encode] batch %d/%d: size=%d, tok=%.3fs fwd=%.3fs to_cpu=%.3fs (elapsed %.2fs)",
                    bi + 1, n_batches, len(batch),
                    _t_tok - _t_b0, _t_fwd - _t_tok, _t_cpu - _t_fwd, _t_cpu - _t_enc_start,
                )
        logger.info(
            "[_encode] 完成: %d texts, total=%.2fs, avg=%.3fs/text",
            len(texts), _time.perf_counter() - _t_enc_start,
            (_time.perf_counter() - _t_enc_start) / max(1, len(texts)),
        )
        return all_embeddings

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """批量向量化（passage/documents）：不加 query 前缀。"""
        import time as _time_et
        logger.info("[embed_texts] 入口: %d texts, model_loaded=%s", len(texts), self._model is not None)
        if not texts:
            return []
        _t_et0 = _time_et.perf_counter()
        self._load()
        logger.info("[embed_texts] _load 返回: %.3fs", _time_et.perf_counter() - _t_et0)
        old = getattr(self, "_is_query", True)
        self._is_query = False
        try:
            return self._encode(texts)
        finally:
            self._is_query = old

    def embed_query(self, text: str) -> List[float]:
        """单条查询向量化：加 query 前缀。"""
        self._load()
        self._is_query = True
        return self._encode([text])[0]


# ---------- 模块级单例 ----------
_default_embedder: Optional["Embedder"] = None
_embedder_lock = threading.Lock()


def get_default_embedder() -> "Embedder":
    """获取模块级单例 Embedder，复用已加载的模型与 CUDA 上下文。

    业务流程应优先调用此函数，而非直接 Embedder()，避免重复加载模型（每次 12s）
    和重复触发 CUDA 上下文初始化（首次 forward 42s）。
    """
    global _default_embedder
    if _default_embedder is None:
        with _embedder_lock:
            if _default_embedder is None:
                _default_embedder = Embedder()
    return _default_embedder
