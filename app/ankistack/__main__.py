import sys

if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "worker":
        from .worker import main
    elif cmd == "mcp":
        from .mcp_server import main
    else:
        sys.exit("usage: python -m ankistack worker|mcp")
    main()
