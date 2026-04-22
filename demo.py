"""
demo.py — compile test_program.pas and display the AST + compilation report.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from mini_pascal_compiler import compile_source

with open('test_program.pas') as fh:
    source = fh.read()


def _indent(level: int) -> str:
    return '  ' * level


def _print_ast(node, level: int = 0) -> None:
    """Recursively pretty-print an AST node."""
    from mini_pascal_parser import (
        Program, Block, ConstDef, TypeDef, VarDecl, ProcDecl, FuncDecl,
        CompoundStmt, AssignStmt, IfStmt, WhileStmt, ForStmt, RepeatStmt,
        CaseStmt, WritelnStmt, ProcCallStmt, WithStmt, GotoStmt,
        BinOp, UnaryOp, FuncCall, Var, IndexVar, FieldVar, DerefVar,
        IntLit, RealLit, StrLit, NilLit,
    )
    pad = _indent(level)
    if node is None:
        print(f"{pad}(empty)")
        return
    if isinstance(node, Program):
        print(f"{pad}Program '{node.name}' params={node.params}")
        _print_ast(node.block, level + 1)
    elif isinstance(node, Block):
        if node.labels:
            print(f"{pad}Labels: {node.labels}")
        for c in node.consts:
            _print_ast(c, level)
        for t in node.types:
            _print_ast(t, level)
        for v in node.vars:
            _print_ast(v, level)
        for s in node.subprograms:
            _print_ast(s, level)
        _print_ast(node.body, level)
    elif isinstance(node, ConstDef):
        print(f"{pad}Const {node.name} = {node.value}")
    elif isinstance(node, TypeDef):
        print(f"{pad}Type {node.name} = {node.type_node}")
    elif isinstance(node, VarDecl):
        print(f"{pad}Var {node.names} : {node.type_node}")
    elif isinstance(node, ProcDecl):
        print(f"{pad}Procedure {node.name}({'forward' if node.forward else 'body'})")
    elif isinstance(node, FuncDecl):
        print(f"{pad}Function {node.name}: {node.return_type}({'forward' if node.forward else 'body'})")
    elif isinstance(node, CompoundStmt):
        print(f"{pad}Begin")
        for s in node.stmts:
            _print_ast(s, level + 1)
        print(f"{pad}End")
    elif isinstance(node, AssignStmt):
        print(f"{pad}Assign {node.target} := {node.value}")
    elif isinstance(node, IfStmt):
        print(f"{pad}If {node.condition}")
        print(f"{pad}  Then:")
        _print_ast(node.then_branch, level + 2)
        if node.else_branch:
            print(f"{pad}  Else:")
            _print_ast(node.else_branch, level + 2)
    elif isinstance(node, WhileStmt):
        print(f"{pad}While {node.condition} Do:")
        _print_ast(node.body, level + 1)
    elif isinstance(node, ForStmt):
        print(f"{pad}For {node.var} := {node.start} {node.direction} {node.end} Do:")
        _print_ast(node.body, level + 1)
    elif isinstance(node, RepeatStmt):
        print(f"{pad}Repeat:")
        for s in node.body:
            _print_ast(s, level + 1)
        print(f"{pad}Until {node.condition}")
    elif isinstance(node, CaseStmt):
        print(f"{pad}Case {node.expression} Of")
        for labels, stmt in node.elements:
            print(f"{pad}  {labels}:")
            _print_ast(stmt, level + 2)
    elif isinstance(node, WritelnStmt):
        print(f"{pad}Writeln({', '.join(str(a) for a in node.args)})")
    elif isinstance(node, ProcCallStmt):
        print(f"{pad}Call {node.name}({', '.join(str(a) for a in node.args)})")
    elif isinstance(node, GotoStmt):
        print(f"{pad}Goto {node.label}")
    else:
        print(f"{pad}{node}")


# ---- Run ----
print("=" * 70)
print("SOURCE".center(70))
print("=" * 70)
for n, line in enumerate(source.splitlines(), 1):
    print(f"{n:>3} | {line}")
print()

result = compile_source(source)

print("=" * 70)
print("ABSTRACT SYNTAX TREE".center(70))
print("=" * 70)
if result.ast:
    _print_ast(result.ast)
else:
    print("(no AST — parse failed)")
print()

print("=" * 70)
print("COMPILATION REPORT".center(70))
print("=" * 70)
if result.ok:
    print("Compilation SUCCESSFUL — no errors detected.")
else:
    all_errs = result.all_errors()
    print(f"Compilation FAILED — {len(all_errs)} error(s):")
    for err in all_errs:
        print(f"  {err}")
print("=" * 70)
