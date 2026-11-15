"""Handler module referenced by policy.py."""

def on_start(host_file, args):
    print(f"[hook] starting {host_file}")