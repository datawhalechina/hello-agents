# test_minimax_llm.py
"""
MiniMax Provider 单元测试

测试 MyLLM 中新增的 MiniMax provider 配置逻辑。
MiniMax 提供 OpenAI 兼容接口，支持以下模型：
  - MiniMax-M2.7          旗舰版
  - MiniMax-M2.7-highspeed  高速版

运行方式：
    python test_minimax_llm.py
"""
import os
import sys
import unittest
from unittest.mock import patch, MagicMock


class TestMiniMaxProvider(unittest.TestCase):
    """测试 MiniMax provider 的配置解析逻辑（不调用真实 API）"""

    def _make_llm(self, **kwargs):
        """辅助方法：创建 MyLLM 实例（mock OpenAI 客户端）"""
        with patch("my_llm.OpenAI") as mock_openai_cls:
            mock_openai_cls.return_value = MagicMock()
            from my_llm import MyLLM
            llm = MyLLM(provider="minimax", **kwargs)
            return llm, mock_openai_cls

    def setUp(self):
        # 重置模块缓存，避免测试间互相影响
        if "my_llm" in sys.modules:
            del sys.modules["my_llm"]

    def test_raises_when_api_key_missing(self):
        """未设置 API Key 时应抛出 ValueError"""
        with patch.dict(os.environ, {}, clear=True):
            # 清除可能存在的 MINIMAX_API_KEY
            os.environ.pop("MINIMAX_API_KEY", None)
            with patch("my_llm.OpenAI"):
                from my_llm import MyLLM
                with self.assertRaises(ValueError) as ctx:
                    MyLLM(provider="minimax")
                self.assertIn("MINIMAX_API_KEY", str(ctx.exception))

    def test_default_model_is_minimax_m27(self):
        """未指定模型时，默认应为 MiniMax-M2.7"""
        with patch.dict(os.environ, {"MINIMAX_API_KEY": "test-key"}, clear=False):
            llm, _ = self._make_llm()
            self.assertEqual(llm.model, "MiniMax-M2.7")

    def test_custom_model_is_respected(self):
        """显式传入模型名称时，应使用传入的值"""
        with patch.dict(os.environ, {"MINIMAX_API_KEY": "test-key"}, clear=False):
            llm, _ = self._make_llm(model="MiniMax-M2.7-highspeed")
            self.assertEqual(llm.model, "MiniMax-M2.7-highspeed")

    def test_default_base_url(self):
        """默认 base URL 应指向海外版 api.minimax.io"""
        with patch.dict(os.environ, {"MINIMAX_API_KEY": "test-key"}, clear=False):
            os.environ.pop("MINIMAX_BASE_URL", None)
            llm, mock_openai_cls = self._make_llm()
            called_url = mock_openai_cls.call_args.kwargs.get("base_url") or \
                         mock_openai_cls.call_args[1].get("base_url")
            self.assertIn("api.minimax.io", called_url)

    def test_custom_base_url(self):
        """显式传入 base_url 时，应使用传入的值"""
        custom_url = "https://custom.minimax.io/v1"
        with patch.dict(os.environ, {"MINIMAX_API_KEY": "test-key"}, clear=False):
            llm, mock_openai_cls = self._make_llm(base_url=custom_url)
            called_url = mock_openai_cls.call_args.kwargs.get("base_url") or \
                         mock_openai_cls.call_args[1].get("base_url")
            self.assertEqual(called_url, custom_url)

    def test_default_temperature_is_1(self):
        """MiniMax temperature 默认值应为 1.0（不支持 0）"""
        with patch.dict(os.environ, {"MINIMAX_API_KEY": "test-key"}, clear=False):
            llm, _ = self._make_llm()
            self.assertEqual(llm.temperature, 1.0)

    def test_api_key_from_env(self):
        """未传入 api_key 时，应从 MINIMAX_API_KEY 环境变量读取"""
        with patch.dict(os.environ, {"MINIMAX_API_KEY": "env-test-key"}, clear=False):
            llm, mock_openai_cls = self._make_llm()
            called_api_key = mock_openai_cls.call_args.kwargs.get("api_key") or \
                             mock_openai_cls.call_args[1].get("api_key")
            self.assertEqual(called_api_key, "env-test-key")

    def test_api_key_from_argument_overrides_env(self):
        """传入 api_key 参数时，应优先于环境变量"""
        with patch.dict(os.environ, {"MINIMAX_API_KEY": "env-key"}, clear=False):
            llm, mock_openai_cls = self._make_llm(api_key="arg-key")
            called_api_key = mock_openai_cls.call_args.kwargs.get("api_key") or \
                             mock_openai_cls.call_args[1].get("api_key")
            self.assertEqual(called_api_key, "arg-key")


class TestMiniMaxProviderSelection(unittest.TestCase):
    """测试 provider 路由逻辑"""

    def setUp(self):
        if "my_llm" in sys.modules:
            del sys.modules["my_llm"]

    def test_minimax_provider_selected(self):
        """provider='minimax' 应触发 MiniMax 分支，打印对应提示"""
        with patch.dict(os.environ, {"MINIMAX_API_KEY": "test-key"}, clear=False):
            with patch("my_llm.OpenAI"):
                from my_llm import MyLLM
                import io
                from contextlib import redirect_stdout
                f = io.StringIO()
                with redirect_stdout(f):
                    llm = MyLLM(provider="minimax")
                output = f.getvalue()
                self.assertIn("MiniMax", output)
                self.assertEqual(llm.provider, "minimax")


if __name__ == "__main__":
    print("=" * 60)
    print("MiniMax Provider 单元测试")
    print("=" * 60)
    unittest.main(verbosity=2)
