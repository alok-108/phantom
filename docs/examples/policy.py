"""Example program demonstrating counter capabilities and event handlers."""

def main() -> None:
    print("Running host program under policy rules.")


if __name__ == "__main__":
    main()

#: phantom:0.1.0 counter.create("cap.counters", 10)
#: phantom:0.1.0 counter.increment("cap.counters")
#: phantom:0.1.0 event.on("phantom.pre_execute", "hooks.on_start")