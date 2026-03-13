# Mini-Pascal Lexer

A lexical analyser for the Mini-Pascal language, built with **Python 3.9+** and
the **PLY** (Python Lex-Yacc) library.

---

## Table of contents

1. [Project structure](#project-structure)
2. [Architecture overview](#architecture-overview)
3. [Token reference](#token-reference)
4. [PLY internals — how the lexer works](#ply-internals--how-the-lexer-works)
5. [Docker (no local install required)](#docker-no-local-install-required)
6. [Setup and usage](#setup-and-usage)
7. [Running tests](#running-tests)
8. [Development workflow](#development-workflow)
9. [Agent-assisted development](#agent-assisted-development)

---

## Project structure

```
Pascal-Mini-Lexer/
├── mini_pascal_lex.py          # PLY lexer — single source of truth
├── tests/
│   ├── test_lexer.py           # pytest suite — happy-path tests (30 tests)
│   └── test_lexer_errors.py    # pytest suite — error detection tests (47 tests)
├── .claude/
│   ├── CLAUDE.md               # Claude Code project instructions
│   └── agents.md               # Multi-agent workflow definitions
├── CONTRIBUTING.md             # PR process and git workflow
└── README.md                   # This file
```

---

## Architecture overview

```
Source code (string)
        |
        v
  ┌─────────────┐
  │  PLY  lexer │  mini_pascal_lex.py
  │             │
  │  1. ignore  │  spaces, tabs, carriage returns
  │  2. discard │  { comments }  (* and these *)
  │  3. match   │  literals → INTEGER / REAL / STRING
  │  4. match   │  identifiers → ID or reserved keyword token
  │  5. match   │  operators & delimiters
  └─────────────┘
        |
        v
  Stream of LexToken objects
  (type, value, lineno, lexpos)
        |
        v
  [future] Parser / AST
```

### Rule priority in PLY

PLY applies rules in this fixed order:

| Priority | Rule type | Examples |
|---|---|---|
| 1 (highest) | Function rules, top-to-bottom | `t_REAL`, `t_INTEGER`, `t_STRING`, `t_ID` |
| 2 | String rules, sorted by **decreasing pattern length** | `t_ASSIGN` (`:=`) before `t_COLON` (`:`) |
| 3 (lowest) | `t_error` fallback | illegal characters |

This ordering is why `REAL` is defined before `INTEGER` (so `3.14` is never
split into `3`, `.`, `14`) and why `:=` is never mis-tokenised as `:` + `=`.

---

## Token reference

### Literals

| Token | Pattern | Python value | Example |
|---|---|---|---|
| `INTEGER` | `\d+` | `int` | `42` |
| `REAL` | `\d+\.\d+…` or `\d+[eE]…` | `float` | `3.14`, `9E8` |
| `STRING` | `'…'` (with `''` escape) | `str` (unescaped) | `'hello'`, `'it''s'` |
| `ID` | `[a-zA-Z_][a-zA-Z0-9_]*` | `str` (original case) | `myVar`, `_foo` |

### Arithmetic operators

| Token | Symbol |
|---|---|
| `PLUS` | `+` |
| `MINUS` | `-` |
| `TIMES` | `*` |
| `DIVIDE` | `/` |

### Relational operators

| Token | Symbol |
|---|---|
| `EQUALS` | `=` |
| `NEQ` | `<>` |
| `LT` | `<` |
| `GT` | `>` |
| `LEQ` | `<=` |
| `GEQ` | `>=` |

### Delimiters

| Token | Symbol | Token | Symbol |
|---|---|---|---|
| `LPAREN` | `(` | `RPAREN` | `)` |
| `LBRACKET` | `[` | `RBRACKET` | `]` |
| `ASSIGN` | `:=` | `COLON` | `:` |
| `DOTDOT` | `..` | `DOT` | `.` |
| `COMMA` | `,` | `SEMICOLON` | `;` |
| `CARET` | `^` | `AT` | `@` |

### Reserved words (37 keywords)

```
AND      ARRAY    BEGIN    CASE     CONST    DIV      DO
DOWNTO   ELSE     END      FILE     FOR      FORWARD  FUNCTION
GOTO     IF       IN       LABEL    MAIN     MOD      NIL
NOT      OF       OR       PACKED   PROCEDURE PROGRAM RECORD
REPEAT   SET      THEN     TO       TYPE     UNTIL    VAR
WHILE    WITH
```

Keywords are **case-insensitive**: `BEGIN`, `begin`, and `Begin` all produce
the same `BEGIN` token.

> Note: predefined type names such as `integer`, `real`, and `boolean` are
> **not** reserved words in Pascal. They tokenise as `ID`.

### Comments (discarded)

Both comment styles are silently dropped; newlines inside them are counted for
accurate line-number tracking.

```pascal
{ This is a brace comment }
(* This is a parenthesis-star comment
   spanning multiple lines *)
```

---

## PLY internals — how the lexer works

### 1. Module-level `reserved` dict

Maps lowercase keyword strings to their uppercase token names. Used inside
`t_ID` to distinguish identifiers from keywords without adding 37 separate
regex rules.

```python
reserved = { 'begin': 'BEGIN', 'end': 'END', ... }
```

### 2. `tokens` tuple

PLY requires every token name to appear in `tokens`. The tuple is built by
combining the explicit token names with `tuple(reserved.values())`, keeping a
single source of truth.

### 3. String rules vs function rules

**String rules** (simple assignments) are used for operators and delimiters
because PLY automatically sorts them by decreasing pattern length — no manual
ordering needed for prefix conflicts like `:=` vs `:`.

**Function rules** are used for literals because they need value conversion
(`int()`, `float()`, quote-stripping) and because function order matters for
disambiguation (`t_REAL` before `t_INTEGER`).

### 4. `t_ID` — keyword detection

```python
def t_ID(t):
    r'[a-zA-Z_][a-zA-Z0-9_]*'
    t.type = reserved.get(t.value.lower(), 'ID')
    return t
```

The lowercase normalisation makes keyword matching case-insensitive while
preserving the original casing in `t.value`.

### 5. Comment rules

Comment functions do **not** `return t`, so PLY discards the token entirely.
They still update `t.lexer.lineno` so subsequent tokens report correct line
numbers.

### 6. No negative literal rule

Negative numbers (`-42`, `-3.14`) are **not** handled by the lexer. The minus
sign is always a `MINUS` token; the parser is responsible for interpreting
unary minus. Handling negation in the lexer would cause ambiguity with
subtraction expressions like `x - 1`.

---

## Docker (no local install required)

The only prerequisite is [Docker Desktop](https://www.docker.com/products/docker-desktop/).
No Python, no PLY, no pytest needed on your machine.

```
Pascal-Mini-Lexer/
├── Dockerfile          # python:3.11-slim + pip install
├── docker-compose.yml  # two services: lexer / test
├── requirements.txt    # ply + pytest pinned versions
└── .dockerignore       # keeps the image small
```

### Build the image

```bash
docker compose build
```

### Run the demo

```bash
docker compose run --rm lexer
```

### Run all tests

```bash
docker compose run --rm test
```

### Run only the error-detection tests

```bash
docker compose run --rm test pytest tests/test_lexer_errors.py -v
```

### Run only the happy-path tests

```bash
docker compose run --rm test pytest tests/test_lexer.py -v
```

Both commands automatically rebuild the image if any file has changed.

---

## Setup and usage

```bash
# Install dependencies
pip install ply pytest

# Run the built-in demo (tokenises a small Pascal program)
python3 mini_pascal_lex.py
```

Expected output (truncated):

```
Line   Token Type     Value
------------------------------------------------------------
1      PROGRAM        'program'
1      ID             'HelloWorld'
1      SEMICOLON      ';'
...
```

### Using the lexer as a library

```python
from mini_pascal_lex import make_lexer

lx = make_lexer()
lx.input("x := 42;")

for tok in lx:
    print(tok.type, tok.value, tok.lineno)
# ID        x   1
# ASSIGN    :=  1
# INTEGER   42  1
# SEMICOLON ;   1

# Check for lexical errors after scanning
if lx.errors:
    for err in lx.errors:
        print(err)
```

---

## Running tests

### Locally

```bash
# All tests (77 total)
pytest tests/ -v

# Happy-path only
pytest tests/test_lexer.py -v

# Error-detection only
pytest tests/test_lexer_errors.py -v
```

```
77 passed in 0.06s
```

### With Docker

```bash
# All tests
docker compose run --rm test

# Error-detection tests only
docker compose run --rm test pytest tests/test_lexer_errors.py -v

# Happy-path tests only
docker compose run --rm test pytest tests/test_lexer.py -v
```

### Test classes

**`tests/test_lexer.py`** — happy-path (30 tests)

| Class | Coverage |
|---|---|
| `TestLiterals` | INTEGER, REAL (dot and exp), STRING, empty string, escaped quote |
| `TestIdentifiers` | plain ID, reserved words, case-insensitive keywords, underscore |
| `TestOperators` | prefix conflicts (`:=`/`:`, `..`/`.`, `<=`/`<`, `>=`/`>`, `<>`) |
| `TestComments` | brace, paren-star, inline, multiline line-number tracking |
| `TestLineNumbers` | lineno increments across newlines |
| `TestIntegration` | assignment, if-then-else, for-loop, array range |

**`tests/test_lexer_errors.py`** — error detection (47 tests)

| Class | Coverage |
|---|---|
| `TestIllegalCharacters` | `#` `$` `%` `!` `~` `` ` ``; error value, line number, recovery after bad char |
| `TestUnterminatedString` | Missing closing `'`, at EOL, mid-file, after escaped-quote `''` edge case |
| `TestUnterminatedBraceComment` | `{ ...` never closed; value, recovery, multiline valid case |
| `TestUnterminatedParenComment` | `(* ...` never closed; value, recovery, multiline valid/invalid |
| `TestLexErrorAttributes` | `kind`, `line`, `value` fields; `__str__` output; dataclass shape |
| `TestErrorRecovery` | Mixed error types, valid tokens after errors, clean input = empty list |

### `LexError` reference

Every error is stored as a `LexError(kind, line, value)` dataclass on `lx.errors`:

```python
from mini_pascal_lex import make_lexer

lx = make_lexer()
lx.input("x := #42; 'unterminated")
tokens = list(lx)

for err in lx.errors:
    print(err)
# [LexError] illegal_character at line 1: '#'
# [LexError] unterminated_string at line 1: "'unterminated"
```

| `kind` value | Trigger |
|---|---|
| `illegal_character` | Any character not matched by any rule (e.g. `#`, `$`, `%`) |
| `unterminated_string` | A string literal opened with `'` but not closed before end of line |
| `unterminated_comment` | A `{ }` or `(* *)` comment opened but never closed |

---

## Development workflow

See [CONTRIBUTING.md](CONTRIBUTING.md) for the full guide. Quick reference:

```bash
# 1. Branch
git checkout -b feat/<description>

# 2. Implement + test
pytest tests/ -v

# 3. Commit
git add mini_pascal_lex.py tests/
git commit -m "feat: <description>"

# 4. PR
git push -u origin feat/<description>
gh pr create --title "..." --body "..."
```

Branch naming: `feat/`, `fix/`, `test/`, `docs/`.

---

## Agent-assisted development

This project uses Claude Code sub-agents defined in [`.claude/agents.md`](.claude/agents.md).

| Goal | Agent |
|---|---|
| Add or fix a token | `implementer` |
| Write tests | `tester` |
| Review a PR | `reviewer` |
| Update docs | `docs` |

Agent order: `implementer` → `tester` → `reviewer` → merge.
