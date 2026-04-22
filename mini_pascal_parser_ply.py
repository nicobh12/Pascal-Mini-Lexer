"""
mini_pascal_parser_ply.py
Backward-compatible wrapper – re-exports everything from mini_pascal_parser.py.
The full PLY-based parser (grammar + AST construction + error recovery) lives
in mini_pascal_parser.py.  This module keeps the original import path working.
"""
from mini_pascal_parser import (           # noqa: F401
    parse,
    ParseResult, ParseError,
    Program, Block,
    ConstDef, TypeDef, VarDecl, ProcDecl, FuncDecl, Param,
    SimpleType, SubrangeType, ArrayType, RecordType, SetType, FileType,
    PointerType,
    CompoundStmt, AssignStmt, IfStmt, WhileStmt, ForStmt, RepeatStmt,
    CaseStmt, GotoStmt, WritelnStmt, ProcCallStmt, WithStmt,
    IntLit, RealLit, StrLit, NilLit, BinOp, UnaryOp, FuncCall,
    Var, IndexVar, FieldVar, DerefVar,
)
