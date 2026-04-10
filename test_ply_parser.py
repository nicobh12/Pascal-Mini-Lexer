"""
test_ply_parser.py
Test script for the PLY-based Mini-Pascal parser.

Note: Test structure, assertions, and formatting were designed with assistance
from Anthropic Claude (AI) and GitHub Copilot. The test cases and validation logic
were completed and reviewed by the author.
"""
import sys
from mini_pascal_parser_ply import parse

# Read the test program
with open('test_errors.pas', 'r') as f:
    source = f.read()

print(" TESTING PLY-BASED MINI-PASCAL PARSER ".center(70, "-"))
print()

print("SOURCE CODE:")
print("-" * 70)
for n, line in enumerate(source.splitlines(), 1):
    print(f"{n:>3} │ {line}")
print()

print(" PARSING RESULT ".center(70, "-"))

result = parse(source)

if result.lex_errors:
    print(f"Lexical errors ({len(result.lex_errors)}):")
    for err in result.lex_errors:
        if isinstance(err, str):
            print(f"  {err}")
        else:
            print(f"  Line {err.line}: {err.kind} — {err.value!r}")
    print()

if result.parse_errors:
    print(f"Parse errors ({len(result.parse_errors)}):")
    for err in result.parse_errors:
        if isinstance(err, str):
            print(f"  {err}")
        else:
            print(f"  Line {err.line}: {err.message}")
    print()
else:
    print("No syntax errors detected!")
    print()

print(f"The result of your parsing has been {('successful! Congratulations!', 'unsuccessful! Please check the errors above and try again after fixing them')[not result.ok]}")
print("-" * 70)
