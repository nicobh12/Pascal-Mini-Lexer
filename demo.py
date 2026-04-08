"""
demo.py — Mini-Pascal Analyzer: valid program
Run: python3 demo.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from mini_pascal_lex import make_lexer
from mini_pascal_parser import (
    parse,
    Program, Block,
    ConstDef, TypeDef, VarDecl, ProcDecl, FuncDecl,
    SimpleType, SubrangeType, ArrayType, RecordType, SetType, FileType, PointerType,
    CompoundStmt, AssignStmt, IfStmt, WhileStmt, ForStmt, RepeatStmt,
    CaseStmt, GotoStmt, WritelnStmt, ProcCallStmt, WithStmt,
    IntLit, RealLit, StrLit, NilLit, BinOp, UnaryOp, FuncCall,
    Var, IndexVar, FieldVar, DerefVar,
)

SOURCE = """\
program Demo;

const
  maxn = 5;
  pi   = 3.14159;

type
  arr = array[1..5] of integer;

var
  i, n : integer;
  sum  : real;
  data : arr;

function sumArray(var a: arr; n: integer): integer;
var
  i, s: integer;
begin
  s := 0;
  for i := 1 to n do
    s := s + a[i];
  sumArray := s
end;

procedure printResult(val: integer);
begin
  writeln('Sum =', val)
end;

begin
  n := maxn;
  for i := 1 to n do
    data[i] := i * i;
  sum := sumArray(data, n);
  if sum > 0 then
    printResult(sum)
  else
    writeln('No data')
end.
"""

# ---------------------------------------------------------------------------
# AST pretty-printer (shared — imported by demo_errors.py)
# ---------------------------------------------------------------------------

W = 66


def _expr_str(node) -> str:
    if node is None:                  return '?'
    if isinstance(node, IntLit):      return str(node.value)
    if isinstance(node, RealLit):     return str(node.value)
    if isinstance(node, StrLit):      return f"'{node.value}'"
    if isinstance(node, NilLit):      return 'nil'
    if isinstance(node, Var):         return node.name
    if isinstance(node, IndexVar):
        idx = ', '.join(_expr_str(i) for i in node.indices)
        return f"{_expr_str(node.base)}[{idx}]"
    if isinstance(node, FieldVar):
        return f"{_expr_str(node.base)}.{node.field_name}"
    if isinstance(node, DerefVar):
        return f"{_expr_str(node.base)}^"
    if isinstance(node, BinOp):
        return f"({_expr_str(node.left)} {node.op.lower()} {_expr_str(node.right)})"
    if isinstance(node, UnaryOp):
        return f"({node.op.lower()} {_expr_str(node.operand)})"
    if isinstance(node, FuncCall):
        args = ', '.join(_expr_str(a) for a in node.args)
        return f"{node.name}({args})"
    return repr(node)


def _type_str(node) -> str:
    if node is None:                    return '?'
    if isinstance(node, SimpleType):    return node.name
    if isinstance(node, SubrangeType):
        return f"{_expr_str(node.low)}..{_expr_str(node.high)}"
    if isinstance(node, ArrayType):
        packed = 'packed ' if node.packed else ''
        idx = ', '.join(_type_str(i) for i in node.indices)
        return f"{packed}array[{idx}] of {_type_str(node.element_type)}"
    if isinstance(node, RecordType):
        packed = 'packed ' if node.packed else ''
        fields = '; '.join(f"{', '.join(ns)}: {_type_str(t)}" for ns, t in node.fields)
        return f"{packed}record {fields} end"
    if isinstance(node, SetType):       return f"set of {_type_str(node.base)}"
    if isinstance(node, FileType):      return f"file of {_type_str(node.element_type)}"
    if isinstance(node, PointerType):   return f"^{node.target}"
    return repr(node)


def _print_stmt(node, prefix: str, last: bool) -> None:
    c  = '└── ' if last else '├── '
    cp = prefix + ('    ' if last else '│   ')

    if node is None:
        print(f"{prefix}{c}<empty>")
        return
    if isinstance(node, AssignStmt):
        print(f"{prefix}{c}{_expr_str(node.target)} := {_expr_str(node.value)}")
    elif isinstance(node, ProcCallStmt):
        args = ', '.join(_expr_str(a) for a in node.args)
        print(f"{prefix}{c}CALL {node.name}({args})" if node.args else f"{prefix}{c}CALL {node.name}")
    elif isinstance(node, WritelnStmt):
        args = ', '.join(_expr_str(a) for a in node.args)
        print(f"{prefix}{c}WRITELN({args})" if node.args else f"{prefix}{c}WRITELN")
    elif isinstance(node, CompoundStmt):
        print(f"{prefix}{c}BEGIN")
        for i, s in enumerate(node.stmts):
            _print_stmt(s, cp, i == len(node.stmts) - 1)
    elif isinstance(node, IfStmt):
        print(f"{prefix}{c}IF {_expr_str(node.condition)}")
        print(f"{cp}├── THEN")
        _print_stmt(node.then_branch, cp + '│   ', node.else_branch is None)
        if node.else_branch is not None:
            print(f"{cp}└── ELSE")
            _print_stmt(node.else_branch, cp + '    ', True)
    elif isinstance(node, WhileStmt):
        print(f"{prefix}{c}WHILE {_expr_str(node.condition)} DO")
        _print_stmt(node.body, cp, True)
    elif isinstance(node, ForStmt):
        d = 'TO' if node.direction == 'to' else 'DOWNTO'
        print(f"{prefix}{c}FOR {node.var} := {_expr_str(node.start)} {d} {_expr_str(node.end)} DO")
        _print_stmt(node.body, cp, True)
    elif isinstance(node, RepeatStmt):
        print(f"{prefix}{c}REPEAT..UNTIL {_expr_str(node.condition)}")
        for i, s in enumerate(node.body):
            _print_stmt(s, cp, i == len(node.body) - 1)
    elif isinstance(node, CaseStmt):
        print(f"{prefix}{c}CASE {_expr_str(node.expression)} OF")
        for i, (labels, stmt) in enumerate(node.elements):
            lbl = ', '.join(_expr_str(l) for l in labels)
            lc  = '└── ' if i == len(node.elements) - 1 else '├── '
            lcp = cp + ('    ' if i == len(node.elements) - 1 else '│   ')
            print(f"{cp}{lc}{lbl}:")
            _print_stmt(stmt, lcp, True)
    elif isinstance(node, GotoStmt):
        print(f"{prefix}{c}GOTO {node.label}")
    elif isinstance(node, WithStmt):
        vs = ', '.join(_expr_str(v) for v in node.vars)
        print(f"{prefix}{c}WITH {vs} DO")
        _print_stmt(node.body, cp, True)
    else:
        print(f"{prefix}{c}{node!r}")


def _print_block(block: Block, indent: str = '') -> None:
    sub = indent + '│   '
    if block.labels:
        print(f"{indent}├── LABEL {', '.join(str(l) for l in block.labels)}")
    if block.consts:
        print(f"{indent}├── CONST")
        for i, c in enumerate(block.consts):
            con = '└── ' if i == len(block.consts) - 1 else '├── '
            print(f"{sub}{con}{c.name} = {_expr_str(c.value)}")
    if block.types:
        print(f"{indent}├── TYPE")
        for i, t in enumerate(block.types):
            con = '└── ' if i == len(block.types) - 1 else '├── '
            print(f"{sub}{con}{t.name} = {_type_str(t.type_node)}")
    if block.vars:
        print(f"{indent}├── VAR")
        for i, v in enumerate(block.vars):
            con = '└── ' if i == len(block.vars) - 1 else '├── '
            print(f"{sub}{con}{', '.join(v.names)} : {_type_str(v.type_node)}")
    for sp in block.subprograms:
        _print_subprogram(sp, indent)
    stmts = block.body.stmts if block.body else []
    label = '└── BEGIN' if stmts else '└── BEGIN (empty)'
    print(f"{indent}{label}")
    for i, s in enumerate(stmts):
        _print_stmt(s, indent + '    ', i == len(stmts) - 1)


def _print_subprogram(node, indent: str) -> None:
    sub = indent + '│   '
    if isinstance(node, ProcDecl):
        fwd = '  [forward]' if node.forward else ''
        print(f"{indent}├── PROCEDURE {node.name}({_params_str(node.params)}){fwd}")
        if node.body:
            _print_block(node.body, sub)
    elif isinstance(node, FuncDecl):
        fwd = '  [forward]' if node.forward else ''
        print(f"{indent}├── FUNCTION {node.name}({_params_str(node.params)}): {node.return_type}{fwd}")
        if node.body:
            _print_block(node.body, sub)


def _params_str(params: list) -> str:
    return '; '.join(
        f"{'var ' if p.by_ref else ''}{', '.join(p.names)}: {p.type_name}"
        for p in params
    )


def print_ast(program: Program) -> None:
    print(f"PROGRAM {program.name}" +
          (f"({', '.join(program.params)})" if program.params else ''))
    _print_block(program.block)


def run(source: str, title: str) -> None:
    print('=' * W)
    print(f' {title} '.center(W, '='))
    print('=' * W)
    print()
    print('SOURCE CODE')
    print('-' * W)
    for n, line in enumerate(source.splitlines(), 1):
        print(f"{n:>3} │ {line}")
    print()

    # ── Phase 1: Lexical analysis ────────────────────────────────────────────
    print('─' * W)
    print(' PHASE 1 — LEXICAL ANALYSIS '.center(W))
    print('─' * W)
    print(f"{'Line':<6} {'Token Type':<18} Value")
    print('-' * W)
    lx = make_lexer()
    lx.input(source)
    for tok in lx:
        print(f"{tok.lineno:<6} {tok.type:<18} {tok.value!r}")
    print('-' * W)
    print()
    if lx.errors:
        print(f"  ✗  LEXICAL ERRORS ({len(lx.errors)})")
        print(f"  {'Line':<6} {'Kind':<28} Value")
        print(f"  {'-'*56}")
        for err in lx.errors:
            print(f"  {err.line:<6} {err.kind:<28} {err.value!r}")
    else:
        print('  ✓  No lexical errors.')
    print()

    # ── Phase 2: Syntactic analysis ─────────────────────────────────────────
    print('─' * W)
    print(' PHASE 2 — SYNTACTIC ANALYSIS '.center(W))
    print('─' * W)
    print()
    result = parse(source)
    if result.parse_errors:
        print(f"  ✗  PARSE ERRORS ({len(result.parse_errors)})")
        print(f"  {'Line':<6} Message")
        print(f"  {'-'*56}")
        for err in result.parse_errors:
            print(f"  {err.line:<6} {err.message}")
    else:
        print('  ✓  No parse errors.')
        print()
        print('  ABSTRACT SYNTAX TREE')
        print('  ' + '-' * (W - 2))
        print_ast(result.program)
    print()
    print('=' * W)


# ---------------------------------------------------------------------------

if __name__ == '__main__':
    run(SOURCE, 'MINI-PASCAL ANALYZER — VALID PROGRAM')
