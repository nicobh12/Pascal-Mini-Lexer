# Mini-Pascal Lexer + Parser

A **lexical analyser** and **recursive-descent syntactic parser** for the
Mini-Pascal language, built with **Python 3.9+** and the **PLY** library.

---

## Table of contents

1. [Project structure](#project-structure)
2. [Architecture overview](#architecture-overview)
3. [Token reference](#token-reference)
4. [PLY internals — how the lexer works](#ply-internals--how-the-lexer-works)
5. [Parser — how it works](#parser--how-it-works)
6. [Docker (no local install required)](#docker-no-local-install-required)
7. [Setup and usage](#setup-and-usage)
8. [Running tests](#running-tests)
9. [Development workflow](#development-workflow)
10. [Agent-assisted development](#agent-assisted-development)

---

## Project structure

```
Pascal-Mini-Lexer/
├── mini_pascal_lex.py          # PLY lexer — single source of truth
├── mini_pascal_parser.py       # Recursive-descent parser + AST nodes
├── demo.py                     # Demo: valid program (tokens + AST)
├── demo_errors.py              # Demo: program with intentional errors
├── tests/
│   ├── test_lexer.py           # pytest suite — lexer happy-path (30 tests)
│   ├── test_lexer_errors.py    # pytest suite — lexer error detection (47 tests)
│   └── test_parser.py          # pytest suite — parser (155 tests)
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
  ┌───────────────────────┐
  │  Recursive-descent    │  mini_pascal_parser.py
  │  parser               │
  │                       │
  │  1. program           │  PROGRAM id ; block .
  │  2. block             │  label? const? type? var? proc/func* compound
  │  3. statements        │  if / while / for / repeat / case / assign / call
  │  4. expressions       │  precedence: NOT > */div/mod/and > +/-/or > relational
  │  5. types             │  simple / subrange / array / record / set / file / pointer
  └───────────────────────┘
        |
        v
  ParseResult(program: Program, parse_errors, lex_errors)
  Typed AST — dataclass nodes for every construct
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

## Parser — how it works

`mini_pascal_parser.py` contains a hand-written LL(1)-style **recursive-descent
parser** that consumes the token stream produced by the lexer and builds a typed
Abstract Syntax Tree (AST).

### Using the parser as a library

```python
from mini_pascal_parser import parse

result = parse("""\
program HelloWorld;
begin
  writeln('Hello, World!')
end.
""")

if result.ok:
    prog = result.program
    print(prog.name)           # 'HelloWorld'
    print(prog.block.body)     # CompoundStmt(stmts=[WritelnStmt(...)])
else:
    for err in result.parse_errors:
        print(err)             # [ParseError] syntax_error at line N: ...
    for err in result.lex_errors:
        print(err)             # [LexError] ...
```

### ParseResult

| Field | Type | Description |
|---|---|---|
| `program` | `Program \| None` | Root AST node (None only on catastrophic failure) |
| `parse_errors` | `list[ParseError]` | Syntax errors collected during parsing |
| `lex_errors` | `list[LexError]` | Lexical errors from the scanner |
| `.ok` | `bool` | `True` when both error lists are empty |

### ParseError

```python
@dataclass
class ParseError:
    kind: str       # always 'syntax_error'
    line: int       # 1-based line number where the error was detected
    message: str    # human-readable description, e.g. "Expected 'THEN', got 'ID'"
```

### AST node reference

Every node is a Python `dataclass` with a `line` field (1-based source line).

| Category | Nodes |
|---|---|
| **Program** | `Program(name, params, block)` · `Block(labels, consts, types, vars, subprograms, body)` |
| **Declarations** | `ConstDef` · `TypeDef` · `VarDecl` · `Param` · `ProcDecl` · `FuncDecl` |
| **Types** | `SimpleType` · `SubrangeType` · `ArrayType` · `RecordType` · `SetType` · `FileType` · `PointerType` |
| **Statements** | `CompoundStmt` · `AssignStmt` · `IfStmt` · `WhileStmt` · `ForStmt` · `RepeatStmt` · `CaseStmt` · `GotoStmt` · `WritelnStmt` · `ProcCallStmt` · `WithStmt` |
| **Expressions** | `BinOp(op, left, right)` · `UnaryOp(op, operand)` · `FuncCall(name, args)` |
| **Literals** | `IntLit` · `RealLit` · `StrLit` · `NilLit` |
| **Variables** | `Var(name)` · `IndexVar(base, indices)` · `FieldVar(base, field_name)` · `DerefVar(base)` |

### Operator precedence (lowest → highest)

| Level | Operators |
|---|---|
| 1 (lowest) | `=` `<>` `<` `>` `<=` `>=` `in` |
| 2 | `+` `-` `or` |
| 3 | `*` `/` `div` `mod` `and` |
| 4 (highest) | `not` (unary) · `-` (unary) |

### Grammar summary

```
program         → PROGRAM id [( id-list )] ; block .
block           → [LABEL labels ;] [CONST const-defs] [TYPE type-defs]
                  [VAR var-decls] subprogram* compound
subprogram      → PROCEDURE id params ; (FORWARD ; | block ;)
                | FUNCTION  id params : id ; (FORWARD ; | block ;)
params          → ( param-section { ; param-section } ) | ε
param-section   → [VAR] id-list : id
compound        → BEGIN stmt { ; stmt } END
stmt            → assign | compound | if | while | for | repeat | case
                | goto | writeln | with | proc-call | ε
assign          → variable := expr
expr            → simple-expr [ rel-op simple-expr ]
simple-expr     → [sign] term { add-op term }
term            → factor { mul-op factor }
factor          → integer | real | string | nil | ( expr ) | NOT factor
                | id [ ( args ) | suffixes ]
variable        → id { [ indices ] | . id | ^ }
type-denoter    → simple-type | ARRAY[…] OF type | RECORD fields END
                | SET OF simple-type | FILE OF type | ^id | PACKED …
```

---

## Docker (no local install required)

The only prerequisite is [Docker Desktop](https://www.docker.com/products/docker-desktop/).
No Python, no PLY, no pytest needed on your machine.

```
Pascal-Mini-Lexer/
├── Dockerfile          # python:3.11-slim + pip install
├── docker-compose.yml  # three services: analyzer / analyzer-errors / test
├── requirements.txt    # ply + pytest pinned versions
└── .dockerignore       # keeps the image small
```

### Build the image

```bash
docker compose build
```

### Run the valid program demo

```bash
docker compose run --rm analyzer
```

### Run the error program demo

```bash
docker compose run --rm analyzer-errors
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

### Run only the parser tests

```bash
docker compose run --rm test pytest tests/test_parser.py -v
```

Both commands automatically rebuild the image if any file has changed.

---

## Setup and usage

```bash
# Install dependencies
pip install ply pytest

# Valid program — tokens + AST
python3 demo.py

# Program with errors — lexical and syntactic error report
python3 demo_errors.py

# Lexer-only demo (raw token table with intentional lex errors)
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
# All tests (232 total)
pytest tests/ -v

# Lexer only
pytest tests/test_lexer.py tests/test_lexer_errors.py -v

# Parser only
pytest tests/test_parser.py -v

# Parser — error cases only
pytest tests/test_parser.py::TestParseErrors -v
```

```
232 passed in 0.18s
```

### With Docker

```bash
# All tests
docker compose run --rm test

# Parser tests only
docker compose run --rm test pytest tests/test_parser.py -v

# Error-detection tests only
docker compose run --rm test pytest tests/test_lexer_errors.py tests/test_parser.py::TestParseErrors -v
```

### Test classes

**`tests/test_lexer.py`** — lexer happy-path (30 tests)

| Class | Coverage |
|---|---|
| `TestLiterals` | INTEGER, REAL (dot and exp), STRING, empty string, escaped quote |
| `TestIdentifiers` | plain ID, reserved words, case-insensitive keywords, underscore |
| `TestOperators` | prefix conflicts (`:=`/`:`, `..`/`.`, `<=`/`<`, `>=`/`>`, `<>`) |
| `TestComments` | brace, paren-star, inline, multiline line-number tracking |
| `TestLineNumbers` | lineno increments across newlines |
| `TestIntegration` | assignment, if-then-else, for-loop, array range |

**`tests/test_lexer_errors.py`** — lexer error detection (47 tests)

| Class | Coverage |
|---|---|
| `TestIllegalCharacters` | `#` `$` `%` `!` `~` `` ` ``; error value, line number, recovery after bad char |
| `TestUnterminatedString` | Missing closing `'`, at EOL, mid-file, after escaped-quote `''` edge case |
| `TestUnterminatedBraceComment` | `{ ...` never closed; value, recovery, multiline valid case |
| `TestUnterminatedParenComment` | `(* ...` never closed; value, recovery, multiline valid/invalid |
| `TestLexErrorAttributes` | `kind`, `line`, `value` fields; `__str__` output; dataclass shape |
| `TestErrorRecovery` | Mixed error types, valid tokens after errors, clean input = empty list |

**`tests/test_parser.py`** — parser (155 tests)

| Class | Tests | Coverage |
|---|---|---|
| `TestProgramStructure` | 5 | minimal program, params, block, body |
| `TestLabelDeclaration` | 3 | integer label, id label, multiple labels |
| `TestConstDeclarations` | 6 | int, real, string, negative, named, multiple |
| `TestTypeDeclarations` | 13 | alias, subrange, signed subrange, array, packed array, multidim array, record, record multifield, record trailing `;`, pointer, set, file, multiple |
| `TestVarDeclarations` | 5 | single, multi-name, multiple decls, array type, record type |
| `TestSubprogramDeclarations` | 8 | proc no params, with params, var param, multi-section params, function, forward proc, forward func, multiple subprograms |
| `TestCompoundStatement` | 5 | empty, single, multiple, trailing `;`, nested |
| `TestAssignmentStatement` | 8 | simple, expression, array element, multidim array, field, deref, chained field, string |
| `TestIfStatement` | 5 | if-then, if-then-else, nested if, compound branch, boolean condition |
| `TestWhileStatement` | 3 | basic, compound body, NOT condition |
| `TestForStatement` | 4 | to, downto, expr bounds, compound body |
| `TestRepeatStatement` | 2 | basic, multiple stmts |
| `TestCaseStatement` | 5 | single element, multiple elements, multiple labels, trailing `;`, expression |
| `TestGotoStatement` | 2 | integer label, id label |
| `TestWritelnStatement` | 4 | no args, one arg, multiple args, expression arg |
| `TestProcedureCallStatement` | 3 | no args, with args, expression arg |
| `TestWithStatement` | 3 | basic, multiple vars, compound body |
| `TestExpressions` | 19 | all literals, arithmetic precedence, parens, unary −/NOT, all relational ops, AND/OR, DIV/MOD, function calls, IN, nested calls, complex, array/field/deref access |
| `TestComplexPrograms` | 5 | factorial (recursive fn), bubble sort, hello world, record program, GCD with repeat |
| `TestParseErrors` | 46 | every missing keyword/token across program, const, type, var, subprogram, and statement levels; error metadata (line, message, str format); `ParseResult.ok` and `bool()` |

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
