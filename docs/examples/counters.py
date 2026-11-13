"""Bounded counter lifecycle: create, increment, decrement, reset, and boundary handling.

This example demonstrates rate-limiting style counters that stay within declared
limits. Phantom applies all instructions before the host starts, then prints
any diagnostics that were recorded.
"""


def handle_request(request_id: int) -> None:
    print(f"Handling request {request_id}")


if __name__ == "__main__":
    handle_request(1)
    handle_request(2)

#: phantom:0.1.0 counter.create("api_calls", 3)
#: phantom:0.1.0 counter.increment("api_calls")
#: phantom:0.1.0 counter.increment("api_calls")
#: phantom:0.1.0 diagnostic.note("api_calls at 2/3")
#: phantom:0.1.0 counter.decrement("api_calls")
#: phantom:0.1.0 diagnostic.note("after decrement: 1/3")
#: phantom:0.1.0 counter.reset("api_calls")
#: phantom:0.1.0 diagnostic.note("counter reset to 0/3")
#: phantom:0.1.0 counter.increment("api_calls")
#: phantom:0.1.0 counter.increment("api_calls")
#: phantom:0.1.0 counter.increment("api_calls")
#: phantom:0.1.0 counter.increment("api_calls")
#: phantom:0.1.0 counter.decrement("api_calls")
#: phantom:0.1.0 counter.decrement("api_calls")
#: phantom:0.1.0 counter.decrement("api_calls")
#: phantom:0.1.0 counter.decrement("api_calls")
#: phantom:0.1.0 diagnostic.note("boundary handling complete")
