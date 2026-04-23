"""
mini_pascal_parser.py
Backward-compatibility wrapper — re-exports everything from compiler.parser
and compiler.ast so that existing imports continue to work unchanged.

Prefer importing from the ``compiler`` package directly:
  from compiler import parse, Program, ParseResult, …
"""
# Re-export the public parse API
from compiler.parser import parse          # noqa: F401
from compiler.ast import (                  # noqa: F401
    ParseResult, ParseError,
    Program, Block,
    ConstDef, TypeDef, VarDecl, ProcDecl, FuncDecl, Param,
    SimpleType, SubrangeType, ArrayType, RecordType, SetType, FileType,
    PointerType,
    CompoundStmt, AssignStmt, IfStmt, WhileStmt, ForStmt, RepeatStmt,
    CaseStmt, GotoStmt, WritelnStmt, ProcCallStmt, WithStmt,
    IntLit, RealLit, StrLit, NilLit, BoolLit, BinOp, UnaryOp, FuncCall,
    Var, IndexVar, FieldVar, DerefVar,
)
