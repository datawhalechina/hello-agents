from dotenv import load_dotenv
load_dotenv()
import os

from datasets import load_dataset
from huggingface_hub import snapshot_download

data_dir = snapshot_download(repo_id="gaia-benchmark/GAIA", repo_type="dataset")
dataset = load_dataset(data_dir, "2023_level1", split="test")
for example in dataset:
    question = example["Question"]
    file_path = os.path.join(data_dir, example["file_path"])
