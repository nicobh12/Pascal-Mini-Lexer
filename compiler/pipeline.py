"""
compiler/pipeline.py
Top-level compilation pipeline — orchestrates the three layers.

Public API
----------
  compile_source(source, phase='all') -> CompileResult
  CompileResult
    .ast              — Program node or None
    .lex_errors       — list of LexError
    .parse_errors     — list of ParseError
    .semantic_errors  — list of SemanticError (empty when phase < 'semantic')
    .ok               — True when all active phases succeeded
    .all_errors()     — flat list of every error across all phases
"""
from __future__ import annotations

from typing import Any, List, Optional

from compiler.lexer import make_lexer, LexError
from compiler.parser import parse, ParseResult
from compiler.semantic import analyze, SemanticResult, SemanticError
from compiler.ast import Program

# Valid phase names, in pipeline order
PHASES = ('lex', 'parse', 'semantic', 'all')


class CompileResult:
    """
    Aggregated result for one compilation run.

    Attributes are populated according to the requested *phase*:

    =========  =============================================
    phase      populated attributes
    =========  =============================================
    ``lex``    lex_errors only (no AST, no parse/semantic)
    ``parse``  ast, lex_errors, parse_errors
    ``all``    all fields
    =========  =============================================
    """

    def __init__(self) -> None:
        self.parse_result: Optional[ParseResult] = None
        self.semantic_result: Optional[SemanticResult] = None
        # Lex-only results (when phase == 'lex')
        self._lex_only_errors: List[LexError] = []

    # ------------------------------------------------------------------
    # Convenience properties
    # ------------------------------------------------------------------

    @property
    def ast(self) -> Optional[Program]:
        if self.parse_result is None:
            return None
        return self.parse_result.program

    @property
    def lex_errors(self) -> List[LexError]:
        if self.parse_result is not None:
            return self.parse_result.lex_errors
        return self._lex_only_errors

    @property
    def parse_errors(self) -> List:
        if self.parse_result is None:
            return []
        return self.parse_result.parse_errors

    @property
    def semantic_errors(self) -> List[SemanticError]:
        if self.semantic_result is None:
            return []
        return self.semantic_result.errors

    @property
    def ok(self) -> bool:
        return (
            not self.lex_errors
            and not self.parse_errors
            and not self.semantic_errors
        )

    def __bool__(self) -> bool:
        return self.ok

    def all_errors(self) -> List[Any]:
        """Flat list of every error, ordered lex → parse → semantic."""
        return self.lex_errors + self.parse_errors + self.semantic_errors


# ============================================================
# Pipeline entry points
# ============================================================

def lex_source(source: str) -> CompileResult:
    """Run the lexer only. Returns a CompileResult with .lex_errors."""
    result = CompileResult()
    lx = make_lexer()
    lx.input(source)
    # Consume all tokens to trigger error callbacks
    for _ in lx:
        pass
    result._lex_only_errors = list(lx.errors)
    return result


def compile_source(source: str, phase: str = 'all') -> CompileResult:
    """
    Run the Mini-Pascal compiler up to *phase*.

    Parameters
    ----------
    source : str
        Pascal source code.
    phase : {'lex', 'parse', 'semantic', 'all'}
        Which phase to run through.  ``'all'`` and ``'semantic'`` are
        equivalent — both run all three layers.

    Returns
    -------
    CompileResult
    """
    if phase not in PHASES:
        raise ValueError(f"phase must be one of {PHASES!r}, got {phase!r}")

    if phase == 'lex':
        return lex_source(source)

    # Phase 1 + 2: lex & parse
    result = CompileResult()
    pr = parse(source)
    result.parse_result = pr

    if phase == 'parse':
        return result

    # Phase 3: semantic analysis (only when parse produced a tree)
    if pr.program is not None and not pr.parse_errors:
        result.semantic_result = analyze(pr.program)

    return result
