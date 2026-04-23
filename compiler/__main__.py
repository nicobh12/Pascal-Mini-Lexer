"""
compiler/__main__.py
Command-line interface for the Mini-Pascal compiler.

Usage
-----
  python -m compiler [options] <file.pas>
  python -m compiler [options] -          # read from stdin

Options
-------
  --phase {lex,parse,semantic,all}
      Which compiler phase(s) to run (default: all).

  --ast
      Print the AST after parsing (requires phase >= parse).

  --tokens
      Print the token stream (phase = lex or above).

  --symbols
      Print the symbol table (scopes + types) after semantic analysis.

  --no-color
      Disable ANSI colour in output.

Examples
--------
  # Full compilation
  python -m compiler program.pas

  # Lexer only
  python -m compiler --phase lex program.pas

  # Parser only, show AST
  python -m compiler --phase parse --ast program.pas

  # All layers with token dump
  python -m compiler --tokens program.pas
"""
from __future__ import annotations

import argparse
import sys
from typing import List

from compiler.lexer import make_lexer
from compiler.pipeline import compile_source, PHASES
from compiler.visitors import ASTPrinter


# ============================================================
# ANSI helpers
# ============================================================

_USE_COLOR = True


def _color(text: str, code: str) -> str:
    if not _USE_COLOR:
        return text
    return f'\033[{code}m{text}\033[0m'


def _red(t: str)    -> str: return _color(t, '31')
def _yellow(t: str) -> str: return _color(t, '33')
def _green(t: str)  -> str: return _color(t, '32')
def _cyan(t: str)   -> str: return _color(t, '36')
def _bold(t: str)   -> str: return _color(t, '1')


# ============================================================
# Output helpers
# ============================================================

def _section(title: str) -> None:
    bar = '─' * (len(title) + 4)
    print(f'\n{_bold(_cyan(f"┌{bar}┐"))}')
    print(f'{_bold(_cyan("│"))}  {_bold(title)}  {_bold(_cyan("│"))}')
    print(f'{_bold(_cyan(f"└{bar}┘"))}')


def _print_errors(errors: list, label: str) -> None:
    if not errors:
        return
    _section(f'{label} Errors  [{len(errors)}]')
    for e in errors:
        print(f'  {_red("✗")}  {e}')


def _print_tokens(source: str) -> None:
    _section('Token Stream')
    lx = make_lexer()
    lx.input(source)
    for tok in lx:
        print(f'  {_cyan(f"L{tok.lineno:>3}")}  '
              f'{_yellow(f"{tok.type:<12}")}  '
              f'{tok.value!r}')
    if lx.errors:
        print()
        for e in lx.errors:
            print(f'  {_red("✗")}  {e}')


def _print_ast(program) -> None:
    _section('Abstract Syntax Tree')
    printer = ASTPrinter()
    printer.visit(program)
    for line in printer.result().splitlines():
        print(f'  {line}')


def _print_symbols(symbol_log: list) -> None:
    _section('Symbol Table')
    if not symbol_log:
        print('  (no symbols)')
        return

    # Group entries by scope, preserving definition order
    from collections import OrderedDict
    scopes: dict = OrderedDict()
    for scope_name, ident, type_repr in symbol_log:
        scopes.setdefault(scope_name, []).append((ident, type_repr))

    for scope_name, entries in scopes.items():
        print(f'\n  {_bold(_yellow(f"[{scope_name}]"))}')
        name_w = max(len(e[0]) for e in entries) + 2
        for ident, type_repr in entries:
            print(f'    {_cyan(ident.ljust(name_w))}  {type_repr}')


def _print_summary(result, phase: str) -> None:
    _section('Compilation Summary')
    lex_n    = len(result.lex_errors)
    parse_n  = len(result.parse_errors)
    sem_n    = len(result.semantic_errors)
    total    = lex_n + parse_n + sem_n

    def _row(label: str, count: int) -> None:
        marker = _red('✗') if count else _green('✓')
        print(f'  {marker}  {label:<25}  {count} error(s)')

    _row('Lexical analysis', lex_n)
    if phase not in ('lex',):
        _row('Syntactic analysis', parse_n)
    if phase in ('semantic', 'all'):
        _row('Semantic analysis', sem_n)

    print()
    if total == 0:
        print(f'  {_green(_bold("Compilation successful."))}')
    else:
        print(f'  {_red(_bold(f"{total} error(s) found — compilation failed."))}')


# ============================================================
# CLI entry point
# ============================================================

def main(argv: List[str] | None = None) -> int:
    global _USE_COLOR

    ap = argparse.ArgumentParser(
        prog='python -m compiler',
        description='Mini-Pascal compiler — run individual phases or the full pipeline.',
    )
    ap.add_argument('file', metavar='FILE',
                    help='Pascal source file (use - for stdin)')
    ap.add_argument('--phase', choices=list(PHASES), default='all',
                    help='Which phase(s) to run  [default: all]')
    ap.add_argument('--ast', action='store_true',
                    help='Print the AST after parsing')
    ap.add_argument('--tokens', action='store_true',
                    help='Print the token stream')
    ap.add_argument('--symbols', action='store_true',
                    help='Print the symbol table after semantic analysis')
    ap.add_argument('--no-color', dest='color', action='store_false',
                    default=True, help='Disable ANSI colour output')

    args = ap.parse_args(argv)
    _USE_COLOR = args.color and sys.stdout.isatty()

    # ---- Read source ------------------------------------------
    if args.file == '-':
        source = sys.stdin.read()
        filename = '<stdin>'
    else:
        try:
            with open(args.file, encoding='utf-8') as fh:
                source = fh.read()
        except OSError as exc:
            print(f'{_red("Error")}: {exc}', file=sys.stderr)
            return 2
        filename = args.file

    print(f'\n{_bold("Mini-Pascal Compiler")}  —  {_cyan(filename)}  '
          f'[phase: {_yellow(args.phase)}]')

    # ---- Token stream (independent of phase) ------------------
    if args.tokens:
        _print_tokens(source)

    # ---- Run pipeline -----------------------------------------
    result = compile_source(source, phase=args.phase)

    # ---- AST --------------------------------------------------
    if args.ast and result.ast is not None:
        _print_ast(result.ast)

    # ---- Symbol table -----------------------------------------
    if args.symbols and args.phase in ('semantic', 'all'):
        _print_symbols(result.semantic_result.symbol_log
                       if result.semantic_result is not None else [])

    # ---- Errors -----------------------------------------------
    _print_errors(result.lex_errors, 'Lexical')
    if args.phase not in ('lex',):
        _print_errors(result.parse_errors, 'Syntactic')
    if args.phase in ('semantic', 'all'):
        _print_errors(result.semantic_errors, 'Semantic')

    # ---- Summary ----------------------------------------------
    _print_summary(result, args.phase)

    return 0 if result.ok else 1


if __name__ == '__main__':
    sys.exit(main())
