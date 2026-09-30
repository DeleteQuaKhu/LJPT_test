#!/usr/bin/env python3
"""
test.py - Sample/test script inside the N2 folder of the LJPT_test project.

Usage:
    python test.py
    python test.py --name World
    python test.py --test

Run the built-in tests with:
    python test.py --test
    # or, if pytest is installed:
    pytest test.py
"""

import argparse
import sys


def greet(name: str = "World") -> str:
    """Return a friendly greeting for the given name."""
    if not name or not name.strip():
        raise ValueError("name must be a non-empty string")
    return f"Hello, {name.strip()}!"


def multiply(a: int, b: int) -> int:
    """Return the product of two numbers."""
    return a * b


def run_tests() -> int:
    """A tiny self-contained test suite. Returns the number of failures."""
    failures = 0

    cases = [
        (greet, (), "Hello, World!"),
        (greet, ("Alice",), "Hello, Alice!"),
        (greet, ("  Bob  ",), "Hello, Bob!"),
        (multiply, (2, 3), 6),
        (multiply, (0, 100), 0),
    ]

    for func, args, expected in cases:
        result = func(*args)
        if result == expected:
            print(f"PASS: {func.__name__}{args} -> {result!r}")
        else:
            failures += 1
            print(f"FAIL: {func.__name__}{args} -> {result!r}, expected {expected!r}")

    # Also verify that an empty name raises ValueError.
    try:
        greet("")
    except ValueError:
        print("PASS: greet('') raised ValueError")
    else:
        failures += 1
        print("FAIL: greet('') did not raise ValueError")

    print(f"\n{len(cases) + 1 - failures}/{len(cases) + 1} checks passed.")
    return failures


def main(argv=None) -> int:
    """Entry point for the command-line interface."""
    parser = argparse.ArgumentParser(description="A simple sample test script (N2).")
    parser.add_argument("--name", default="World", help="Name to greet (default: World)")
    parser.add_argument("--test", action="store_true", help="Run the built-in test suite")
    args = parser.parse_args(argv)

    if args.test:
        return 1 if run_tests() else 0

    print(greet(args.name))
    return 0


if __name__ == "__main__":
    sys.exit(main())