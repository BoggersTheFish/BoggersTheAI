from __future__ import annotations

from BoggersTheAI import BoggersRuntime


def main() -> None:
    runtime = BoggersRuntime()
    response = runtime.ask("What is the TS-OS architecture in this project?")
    print("Answer:")
    print(response.answer)
    print("\nHypotheses:")
    for item in response.hypotheses:
        print(f"- {item}")


if __name__ == "__main__":
    main()
