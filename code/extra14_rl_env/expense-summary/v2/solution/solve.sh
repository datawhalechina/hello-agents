#!/bin/sh
set -eu
script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
cp "$script_dir/summarize.py" /app/summarize.py
python /app/summarize.py /app/input.csv /app/summary.csv /app/over_500.csv
