"""
mini_pascal_compiler.py
Backward-compatibility wrapper — re-exports everything from compiler.pipeline
so that existing imports continue to work unchanged.

Prefer importing from the ``compiler`` package directly:
  from compiler import compile_source, CompileResult
"""
from compiler.pipeline import compile_source, CompileResult  # noqa: F401
from compiler.semantic import SemanticError                  # noqa: F401
