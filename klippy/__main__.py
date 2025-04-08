import sys
import os

# Ensure the package's root directory is on sys.path for proper module resolution
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from .klippy import main

if __name__ == "__main__":
    main()
