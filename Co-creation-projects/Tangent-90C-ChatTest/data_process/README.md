# Data Process - 考试试卷数据集收集

本文件夹的功能是收集和管理各类考试试卷的数据集。主要通过维护一份数据源清单，并利用脚本自动从 GitHub 等平台下载相关仓库。

## 文件组成

- **`data_sources.xlsx`**: 数据源配置文件（Excel）。
- **`download_repos.py`**: 数据下载脚本。
- **`datas/`**: 下载的数据存放目录。

## 如何使用

### 1. 配置数据源 (`data_sources.xlsx`)

请打开 `data_sources.xlsx` 文件，在文件中填写需要下载的仓库链接。
- **注意**：该 Excel 文件必须包含一个名为 **`数据源`** 的列，脚本将读取该列下的所有 URL 地址。

### 2. 运行下载脚本 (`download_repos.py`)

在终端中切换到本目录（`data_process`）或项目根目录，运行以下命令启动下载：

#### 方法一：使用 uv (推荐)

```bash
# 本项目使用 uv 管理依赖，直接使用 uv 运行脚本即可
# (uv 会自动配置环境并安装 pandas, openpyxl 等依赖)
uv run data_process/download_repos.py
```

#### 方法二：不使用 uv (传统方式)

如果你没有安装 `uv`，也可以使用标准的 pip 和 python 命令：

```bash
# 1. 安装依赖
pip install pandas openpyxl

# 2. 运行脚本
# (如果在 data_process 目录下)
python download_repos.py
# (如果在项目根目录下)
python data_process/download_repos.py
```

脚本运行过程说明：
1. 自动并在当前目录下检查或创建 `datas` 文件夹。
2. 读取 `data_sources.xlsx` 中的 `数据源` 列。
3. 遍历每个链接，将其对应的仓库 clone 到 `datas` 目录下。
   - 如果目标目录已存在，脚本可能会跳过下载（具体视代码实现而定）。

## 依赖说明

- Python 3.x
- Git (需要确保命令行可以使用 `git` 命令)
- Python 库: `pandas`, `openpyxl`
