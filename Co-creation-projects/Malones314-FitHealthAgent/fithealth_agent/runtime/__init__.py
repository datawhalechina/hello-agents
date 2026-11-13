"""运行时装配层：共享单例、可替换的外部依赖引用、通用 HTTP 工具。

**不要在这里 eager import `deps`。** store 的路径解析读 `FITHEALTH_DATA_DIR`，而
`tests/__init__.py` 是在导入任何东西之前才设这个环境变量；一旦 `import
fithealth_agent` 就顺带把 `deps` 拉起来，整套测试会在真实 `data/` 目录上建 store
实例，直接污染用户的健康数据。`tests/test_package_lazy_import.py` 守着这条。
"""
