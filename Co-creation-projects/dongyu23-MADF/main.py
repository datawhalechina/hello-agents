"""Hello-Agents co-creation entry point for the MADF demo."""

from demo_helloagents import run_demo


def main():
    transcript = run_demo()
    for key in ("opening", "speech", "summary", "closing"):
        print(f"\n[{key}]\n{transcript[key]}")


if __name__ == "__main__":
    main()
