"""Lifecycle events: handlers are plain functions found by dotted path.

Run with `phantom run docs/examples/events.py`. Phantom resolves the handler
paths below relative to this file's directory, so no import is needed here.
"""

import os


def announce_start(host_file, args):
    print(f"[hook] about to run {os.path.basename(host_file)}")


def announce_done(host_file, result):
    print(f"[hook] finished with exit code {result.exit_code}")


def main() -> None:
    print("Doing the work.")


if __name__ == "__main__":
    main()

#: phantom:0.1.0 event.on("phantom.pre_execute", "events.announce_start")
#: phantom:0.1.0 event.on("phantom.post_execute", "events.announce_done")
