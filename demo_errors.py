"""
demo_errors.py — compile test_errors.pas and display all errors per phase.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from mini_pascal_compiler import compile_source

with open('test_errors.pas') as fh:
    source = fh.read()

print("=" * 70)
print("SOURCE WITH INTENTIONAL ERRORS".center(70))
print("=" * 70)
for n, line in enumerate(source.splitlines(), 1):
    print(f"{n:>3} | {line}")
print()

result = compile_source(source, semantic=False)

# ---- Lexical errors ----
if result.lex_errors:
    print(f"LEXICAL ERRORS ({len(result.lex_errors)})")
    print("-" * 70)
    for err in result.lex_errors:
        print(f"  Line {err.line:>3}: [{err.kind}] {err.value!r}")
    print()

# ---- Syntax errors ----
if result.parse_errors:
    print(f"SYNTAX ERRORS ({len(result.parse_errors)})")
    print("-" * 70)
    for err in result.parse_errors:
        print(f"  Line {err.line:>3}: {err.message}")
    print()

if not result.lex_errors and not result.parse_errors:
    print("No errors detected (source is valid).")

print("=" * 70)
status = "FAILED" if not result.ok else "OK"
print(f"Compilation status: {status}")
print("=" * 70)
