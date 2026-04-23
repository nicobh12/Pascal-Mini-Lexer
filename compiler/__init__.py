"""
compiler — Mini-Pascal compiler package.

Three-layer pipeline
--------------------
  Layer 1  compiler.lexer     — PLY lexical analysis
  Layer 2  compiler.parser    — PLY LALR(1) parser, AST construction
  Layer 3  compiler.semantic  — Visitor-based semantic analysis

Quick start
-----------
  from compiler import compile_source

  result = compile_source(open('program.pas').read())
  if result.ok:
      print("Compilation successful")
  else:
      for err in result.all_errors():
          print(err)

Partial runs
------------
  from compiler import compile_source

  result = compile_source(source, phase='lex')     # lexer only
  result = compile_source(source, phase='parse')   # lex + parse
  result = compile_source(source, phase='all')     # all three layers
"""

# ---- Layer 1: lexer ----------------------------------------
from compiler.lexer import make_lexer, LexError

# ---- Layer 2: parser / AST ---------------------------------
from compiler.parser import parse
from compiler.ast import (
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

# ---- Layer 3: semantic analysis ----------------------------
from compiler.semantic import analyze, SemanticResult, SemanticError

# ---- Pipeline ----------------------------------------------
from compiler.pipeline import compile_source, CompileResult, PHASES

# ---- Visitor utilities ------------------------------------
from compiler.visitors import ASTVisitor, ASTPrinter

__all__ = [
    # Lexer
    'make_lexer', 'LexError',
    # Parser / AST
    'parse', 'ParseResult', 'ParseError',
    'Program', 'Block',
    'ConstDef', 'TypeDef', 'VarDecl', 'ProcDecl', 'FuncDecl', 'Param',
    'SimpleType', 'SubrangeType', 'ArrayType', 'RecordType', 'SetType',
    'FileType', 'PointerType',
    'CompoundStmt', 'AssignStmt', 'IfStmt', 'WhileStmt', 'ForStmt',
    'RepeatStmt', 'CaseStmt', 'GotoStmt', 'WritelnStmt', 'ProcCallStmt',
    'WithStmt',
    'IntLit', 'RealLit', 'StrLit', 'NilLit', 'BoolLit', 'BinOp', 'UnaryOp', 'FuncCall',
    'Var', 'IndexVar', 'FieldVar', 'DerefVar',
    # Semantic
    'analyze', 'SemanticResult', 'SemanticError',
    # Pipeline
    'compile_source', 'CompileResult', 'PHASES',
    # Visitors
    'ASTVisitor', 'ASTPrinter',
]
