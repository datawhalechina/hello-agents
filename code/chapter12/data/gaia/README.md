---
language:
- en
pretty_name: General AI Assistants Benchmark
extra_gated_prompt: "To avoid contamination and data leakage, you agree to not reshare this dataset outside of a gated or private repository on the HF hub."
extra_gated_fields:
  I agree to not reshare the GAIA submissions set according to the above conditions: checkbox
configs:
- config_name: 2023_all
  data_files:
  - split: test
    path: "2023/test/metadata.parquet"
  - split: validation
    path: "2023/validation/metadata.parquet"

- config_name: 2023_level1
  data_files:
  - split: test
    path: "2023/test/metadata.level1.parquet"
  - split: validation
    path: "2023/validation/metadata.level1.parquet"

- config_name: 2023_level2
  data_files:
  - split: test
    path: "2023/test/metadata.level2.parquet"
  - split: validation
    path: "2023/validation/metadata.level2.parquet"

- config_name: 2023_level3
  data_files:
  - split: test
    path: "2023/test/metadata.level3.parquet"
  - split: validation
    path: "2023/validation/metadata.level3.parquet"
---

# GAIA dataset

GAIA is a benchmark which aims at evaluating next-generation LLMs (LLMs with augmented capabilities due to added tooling, efficient prompting, access to search, etc).

We added gating to prevent bots from scraping the dataset. Please do not reshare the validation or test set in a crawlable format.

## Data and leaderboard
GAIA is made of more than 450 non-trivial question with an unambiguous answer, requiring different levels of tooling and autonomy to solve. It is therefore divided in 3 levels, where level 1 should be breakable by very good LLMs, and level 3 indicate a strong jump in model capabilities. Each level is divided into a fully public dev set for validation, and a test set with private answers and metadata.

GAIA leaderboard can be found in this space (https://huggingface.co/spaces/gaia-benchmark/leaderboard).

Questions are contained in metadata.jsonl. Some questions come with an additional file, that can be found in the same folder and whose id is given in the field file_name.

More details in [the paper](https://arxiv.org/abs/2311.12983) for now and soon here as well.

## Dataset Format update (October 2025)
To keep GAIA compatible with HF datasets 4.x where code-based dataset loaders are deprecated—we now ship Parquet-backed splits that mirror the former JSONL structure:
- `metadata.parquet` carries the full split, and companion files like `metadata.level1.parquet` retain the per-level views exposed in the configs.
- Columns remain `task_id`, `Question`, `Level`, `Final answer`, `file_name`, `file_path`, and the struct-valued `Annotator Metadata`, so existing processing pipelines can continue unchanged.
- `file_path` keeps pointing to attachments relative to the repository root (for example, `2023/test/<attachment-id>.pdf`), ensuring offline access to PDFs, media, and other auxiliary files.

### Load datasets 

```python
import os

from datasets import load_dataset
from huggingface_hub import snapshot_download

data_dir = snapshot_download(repo_id="gaia-benchmark/GAIA", repo_type="dataset")
dataset = load_dataset(data_dir, "2023_level1", split="test")
for example in dataset:
    question = example["Question"]
    file_path = os.path.join(data_dir, example["file_path"])
```
