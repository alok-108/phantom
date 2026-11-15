#: phantom:0.1.0 meta.author("Test Author")
#: phantom:0.1.0 meta.version("1.0.0")
#: phantom:0.1.0 event.declare("on_start")
#: phantom:0.1.0 event.declare("on_finish")
#: phantom:0.1.0 event.on("on_start", "myapp.handlers.start")
#: phantom:0.1.0 diagnostic.note("Entry point")
#: phantom:0.1.0 counter.create("requests", 1000)

def main():
    print("Hello from Phantom!")

if __name__ == "__main__":
    main()
