"""Comment-encoded Phantom instructions (the recommended encoding)."""


def greet(name: str) -> str:
    message = f"Hello, {name}!"
    print(message)
    return message


if __name__ == "__main__":
    greet("World")

# An ordinary comment that merely mentions phantom:0.1.0 is not an instruction.
#: phantom:0.1.0 meta.author("Ada Lovelace")
#: phantom:0.1.0 meta.version("1.0.0")
#: phantom:0.1.0 counter.create("greetings", 100)
#: phantom:0.1.0 counter.increment("greetings")
#: phantom:0.1.0 diagnostic.note("Greeting counter initialised")
