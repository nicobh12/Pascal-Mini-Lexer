"""
demo_errors.py — Mini-Pascal Analyzer: program with intentional errors
Run: python3 demo_errors.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from demo import run

SOURCE = """\
program Buggy;

const
  limit = 100;
  rate  = 2wex;

var
  x, y : integer;
  msg  : string;

begin
  x := limit # 10;
  msg := 'hello;
  if x > 0
    y := x * rate;
  for i := 1 to limit
    writeln(i)
end.
"""

ANNOTATIONS = {
    5:  'invalid token  — digits followed by letters (2wex)',
    12: 'illegal character  — # is not valid Pascal',
    13: 'unterminated string  — missing closing quote',
    14: 'missing THEN  — parser expects THEN after condition',
    16: 'missing DO  — parser expects DO after loop range',
}

if __name__ == '__main__':
    print()
    print('  ERRORS INJECTED IN THIS PROGRAM:')
    print('  ' + '-' * 56)
    for line, msg in ANNOTATIONS.items():
        print(f"  Line {line:<4} {msg}")
    print()

    run(SOURCE, 'MINI-PASCAL ANALYZER — PROGRAM WITH ERRORS')
