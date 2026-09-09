"""Frozen desktop entry point; bridge mode remains explicitly opt-in."""

import sys

if __name__ == "__main__":
    if "--diagnostics" in sys.argv:
        from kotoba.diagnostics import main
    elif "--bridge" in sys.argv:
        from kotoba.bridge import main
    else:
        from kotoba.workspace import main
    main()
