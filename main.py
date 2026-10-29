import sys

# Source launches must not create bytecode files before the first folder setup.
sys.dont_write_bytecode = True

from fileflow.app import main

if __name__ == "__main__":
    raise SystemExit(main())
