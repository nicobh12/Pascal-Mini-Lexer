"""
mini_pascal_compiler.py
Top-level compilation pipeline for Mini-Pascal.

Pipeline layers
---------------
  Layer 1 – Lexical analysis   : mini_pascal_lex.py
  Layer 2 – Syntactic analysis : mini_pascal_parser.py   (PLY yacc, builds AST)
  Layer 3 – Semantic analysis  : mini_pascal_semantic.py (symbol table, type checks)

Usage
-----
  from mini_pascal_compiler import compile_source, CompileResult

  result = compile_source(source_code)
  if result.ok:
      print("Compilation successful")
      print(result.ast)
  else:
      for err in result.all_errors():
          print(err)
"""
from dataclasses import dataclass, field
from typing import List, Any, Optional

from mini_pascal_parser import parse, ParseResult, Program
from mini_pascal_semantic import analyze, SemanticResult, SemanticError


@dataclass
class CompileResult:
    parse_result: ParseResult
    semantic_result: Optional[SemanticResult] = None

    @property
    def ast(self) -> Optional[Program]:
        return self.parse_result.program

    @property
    def lex_errors(self) -> List:
        return self.parse_result.lex_errors

    @property
    def parse_errors(self) -> List:
        return self.parse_result.parse_errors

    @property
    def semantic_errors(self) -> List[SemanticError]:
        if self.semantic_result is None:
            return []
        return self.semantic_result.errors

    @property
    def ok(self) -> bool:
        return (self.parse_result.ok and
                (self.semantic_result is None or self.semantic_result.ok))

    def __bool__(self) -> bool:
        return self.ok

    def all_errors(self) -> List:
        """Return all errors from every phase in order."""
        return self.lex_errors + self.parse_errors + self.semantic_errors


def compile_source(source: str, semantic: bool = True) -> CompileResult:
    """
    Run the full compilation pipeline.

    Parameters
    ----------
    source   : Pascal source code string.
    semantic : If True (default) run semantic analysis after successful parse.

    Returns
    -------
    CompileResult with populated fields for each phase.
    """
    # ---- Phase 1 & 2: lex + parse ----
    pr = parse(source)
    cr = CompileResult(parse_result=pr)

    # ---- Phase 3: semantic analysis (only when parse produced a tree) ----
    if semantic and pr.program is not None and not pr.parse_errors:
        cr.semantic_result = analyze(pr.program)

    return cr
