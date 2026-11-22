#!/usr/bin/env python3
import sys
import os

DIR = os.path.dirname(os.path.abspath(__file__))
if DIR not in sys.path:
    sys.path.insert(0, DIR)

from crosscoop.main import main

if __name__ == "__main__":
    main()
