import csv
import json
import sys


def main(path):
    totals = {}
    with open(path, newline="") as f:
        for row in csv.DictReader(f):
            amount = float(row["amount"])
            totals[row["user"]] = totals.get(row["user"], 0) + amount
    print(json.dumps(totals, sort_keys=True))


if __name__ == "__main__":
    main(sys.argv[1])
