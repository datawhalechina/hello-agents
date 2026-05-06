import pathlib
from setuptools import setup, find_packages

version = {}
with open(pathlib.Path(__file__).parent / "version.py", encoding="utf-8") as f:
    exec(f.read(), version)

setup(
    name="hello-agents",
    version=version["__version__"],
    packages=find_packages(),
    python_requires=">=3.10",
)
