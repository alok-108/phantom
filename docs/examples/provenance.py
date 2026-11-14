"""Provenance metadata: author, version, license, tags, and a reviewer note.

The meta.* instructions record metadata only and never change the host. Phantom
applies them before the host starts, then prints the recorded diagnostic after
the host output.
"""


def main() -> None:
    print("Running the provenance example.")


if __name__ == "__main__":
    main()

#: phantom:0.1.0 meta.author("Ada Lovelace")
#: phantom:0.1.0 meta.version("1.0.0")
#: phantom:0.1.0 meta.license("MIT")
#: phantom:0.1.0 meta.tags("example,metadata,provenance")
#: phantom:0.1.0 diagnostic.note("Provenance metadata declared")
