# Mini-Pascal Compiler

A three-layer **Mini-Pascal compiler front-end** built with **Python 3.9+** and the **PLY** library.
Covers lexical analysis, LALR(1) parsing with full AST construction, and semantic analysis.

---

## Table of contents

1. [Project structure](#project-structure)
2. [Architecture overview](#architecture-overview)
3. [Setup](#setup)
4. [CLI usage](#cli-usage)
5. [Python API](#python-api)
6. [Token reference](#token-reference)
7. [AST node reference](#ast-node-reference)
8. [Running tests](#running-tests)
9. [Docker](#docker)
10. [Development workflow](#development-workflow)

---

## Project structure

```
Pascal-Mini-Lexer/
├── compiler/                   # Main compiler package
│   ├── __init__.py             # Public API re-exports
│   ├── __main__.py             # CLI entry point (python -m compiler)
│   ├── lexer.py                # PLY lexer — Layer 1
│   ├── parser.py               # PLY LALR(1) parser + AST builder — Layer 2
│   ├── ast.py                  # AST dataclass nodes
│   ├── semantic.py             # Visitor-based semantic analyser — Layer 3
│   ├── visitors.py             # ASTVisitor base + ASTPrinter
│   └── pipeline.py             # compile_source() pipeline helper
├── examples/
│   ├── hello.pas               # Programa mínimo (sin errores)
│   ├── factorial.pas           # Función recursiva (sin errores)
│   ├── sorting.pas             # Burbuja + forward declaration (sin errores)
│   ├── records.pas             # Registros y WITH (sin errores)
│   └── errors/
│       ├── lex_errors.pas      # Errores léxicos deliberados
│       ├── syntax_errors.pas   # Errores sintácticos deliberados
│       └── semantic_errors.pas # Errores semánticos deliberados
├── mini_pascal_lex.py          # Backward-compat wrapper → compiler.lexer
├── mini_pascal_parser.py       # Backward-compat wrapper → compiler.parser / ast
├── mini_pascal_semantic.py     # Backward-compat wrapper → compiler.semantic
├── mini_pascal_compiler.py     # Backward-compat wrapper → compiler.pipeline
├── tests/
│   ├── test_lexer.py           # Lexer happy-path (30 tests)
│   ├── test_lexer_errors.py    # Lexer error detection (47 tests)
│   ├── test_parser.py          # Parser tests (172 tests)
│   └── test_semantic.py        # Semantic analysis tests (83 tests)
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── README.md
```

---

## Architecture overview

```
Source code (string)
        │
        ▼
┌─────────────────┐
│  compiler.lexer │  Layer 1 — PLY lexer
│                 │  • Ignores whitespace and comments
│                 │  • Produces INTEGER / REAL / STRING / ID / keyword tokens
└─────────────────┘
        │  Stream of LexToken objects
        ▼
┌──────────────────────┐
│  compiler.parser     │  Layer 2 — PLY LALR(1) parser
│                      │  • Builds a typed AST from the token stream
│                      │  • Collects syntax errors without crashing
│                      │  • Returns ParseResult(program, parse_errors, lex_errors)
└──────────────────────┘
        │  ParseResult
        ▼
┌──────────────────────┐
│  compiler.semantic   │  Layer 3 — Visitor-based semantic analyser
│                      │  • Type checking and inference
│                      │  • Symbol table with nested scopes
│                      │  • Forward declaration resolution
│                      │  • Arity validation for calls
│                      │  • Returns SemanticResult(errors)
└──────────────────────┘
```

---

## Setup

```bash
# Install dependencies
pip install -r requirements.txt
# or manually
pip install ply pytest
```

---

## CLI usage

```bash
python -m compiler [options] <file.pas>
```

### Options

| Flag | Description |
|---|---|
| `--phase lex` | Run only the lexer, print the token table |
| `--phase parse` | Run lexer + parser, report syntax errors |
| `--phase semantic` | Run all three layers, report all errors |
| `--phase all` | Same as `semantic` (default) |
| `--tokens` | Print the token stream (layer 1) |
| `--ast` | Print the AST after parsing (layer 2) |
| `--symbols` | Print the symbol table after semantic analysis (layer 3) |
| `--no-color` | Disable ANSI color output |

### Programas válidos

```bash
# Compilación completa — sin errores esperados
python3 -m compiler examples/hello.pas
python3 -m compiler examples/factorial.pas
python3 -m compiler examples/sorting.pas
python3 -m compiler examples/records.pas
```

Salida típica:

```
Mini-Pascal Compiler  —  examples/hello.pas  [phase: all]

┌───────────────────────┐
│  Compilation Summary  │
└───────────────────────┘
  ✓  Lexical analysis           0 error(s)
  ✓  Syntactic analysis         0 error(s)
  ✓  Semantic analysis          0 error(s)

  Compilation successful.
```

### Programas con errores

```bash
# Errores léxicos (carácter ilegal, string sin cerrar, comentario sin cerrar)
python3 -m compiler examples/errors/lex_errors.pas

# Errores sintácticos (falta THEN, falta DO, falta punto final)
python3 -m compiler examples/errors/syntax_errors.pas

# Errores semánticos (type_mismatch, undeclared, arity_mismatch)
python3 -m compiler examples/errors/semantic_errors.pas
```

Salida de `semantic_errors.pas`:

```
Mini-Pascal Compiler  —  examples/errors/semantic_errors.pas  [phase: all]

┌────────────────────────┐
│  Semantic Errors  [4]  │
└────────────────────────┘
  ✗  [SemanticError] type_mismatch at line 20: cannot assign string to integer
  ✗  [SemanticError] type_mismatch at line 21: cannot assign real to boolean
  ✗  [SemanticError] undeclared_identifier at line 23: identifier 'z' is not declared
  ✗  [SemanticError] arity_mismatch at line 25: 'Suma' expects 2 argument(s), got 3

┌───────────────────────┐
│  Compilation Summary  │
└───────────────────────┘
  ✓  Lexical analysis           0 error(s)
  ✓  Syntactic analysis         0 error(s)
  ✗  Semantic analysis          4 error(s)

  4 error(s) found — compilation failed.
```

### Inspeccionar cada capa

```bash
# Capa 1 — ver tokens
python3 -m compiler --phase lex examples/factorial.pas

# Capa 2 — ver el AST
python3 -m compiler --phase parse --ast examples/records.pas

# Capa 3 — ver la tabla de símbolos (scopes + tipos)
python3 -m compiler --symbols examples/sorting.pas

# Todo junto
python3 -m compiler --tokens --ast --symbols examples/factorial.pas

# Sin colores (útil para CI o pipes)
python3 -m compiler --no-color examples/hello.pas
```

Ejemplo de salida de `--symbols examples/sorting.pas`:

```
┌────────────────┐
│  Symbol Table  │
└────────────────┘

  [Sorting]
    N             integer
    Lista         array of integer
    datos         array of integer
    i             integer
    Swap          procedure
    BubbleSort    procedure

  [Swap]
    a      integer
    b      integer
    tmp    integer

  [BubbleSort]
    arr    array of integer
    n      integer
    i      integer
    j      integer
```

---

## Python API

### Full pipeline

```python
from compiler import compile_source

result = compile_source(open('program.pas').read())
if result.ok:
    print("Compilation successful")
else:
    for err in result.all_errors():
        print(err)
```

### Partial runs

```python
from compiler import compile_source

result = compile_source(source, phase='lex')       # lexer only
result = compile_source(source, phase='parse')     # lex + parse
result = compile_source(source, phase='semantic')  # all three layers
result = compile_source(source, phase='all')       # same as 'semantic'
```

### Parser only

```python
from compiler import parse

result = parse("""\
program Hello;
begin
  writeln('Hello, World!')
end.
""")

if result.ok:
    prog = result.program
    print(prog.name)           # 'Hello'
    print(prog.block.body)     # CompoundStmt(...)
else:
    for err in result.parse_errors:
        print(err)             # [ParseError] syntax_error at line N: ...
    for err in result.lex_errors:
        print(err)             # [LexError] ...
```

### Semantic analysis only

```python
from compiler import parse, analyze

parse_result = parse(source)
sem_result = analyze(parse_result.program)

if sem_result.ok:
    print("No semantic errors")
else:
    for err in sem_result.errors:
        print(err)             # [SemanticError] type_mismatch at line N: ...
```

### Lexer only

```python
from compiler import make_lexer

lx = make_lexer()
lx.input("x := 42;")

for tok in lx:
    print(tok.type, tok.value, tok.lineno)
# ID        x   1
# ASSIGN    :=  1
# INTEGER   42  1
# SEMICOLON ;   1

if lx.errors:
    for err in lx.errors:
        print(err)
```

### AST visitor

```python
from compiler import parse
from compiler.visitors import ASTVisitor

class MyVisitor(ASTVisitor):
    def visit_AssignStmt(self, node):
        print(f"Assignment at line {node.line}: {node.target} := ...")

result = parse(source)
v = MyVisitor()
v.visit(result.program)
```

### Print the AST

```python
from compiler import parse
from compiler.visitors import ASTPrinter

result = parse(source)
ASTPrinter().visit(result.program)
```

---

## Token reference

### Literals

| Token | Pattern | Python value | Example |
|---|---|---|---|
| `INTEGER` | `\d+` | `int` | `42` |
| `REAL` | `\d+\.\d+` or `\d+[eE]…` | `float` | `3.14`, `9E8` |
| `STRING` | `'…'` (with `''` escape) | `str` (unescaped) | `'hello'`, `'it''s'` |
| `ID` | `[a-zA-Z_][a-zA-Z0-9_]*` | `str` (original case) | `myVar`, `_foo` |

### Operators

| Token | Symbol | Token | Symbol |
|---|---|---|---|
| `PLUS` | `+` | `MINUS` | `-` |
| `TIMES` | `*` | `DIVIDE` | `/` |
| `EQUALS` | `=` | `NEQ` | `<>` |
| `LT` | `<` | `GT` | `>` |
| `LEQ` | `<=` | `GEQ` | `>=` |

### Delimiters

| Token | Symbol | Token | Symbol |
|---|---|---|---|
| `LPAREN` | `(` | `RPAREN` | `)` |
| `LBRACKET` | `[` | `RBRACKET` | `]` |
| `ASSIGN` | `:=` | `COLON` | `:` |
| `DOTDOT` | `..` | `DOT` | `.` |
| `COMMA` | `,` | `SEMICOLON` | `;` |
| `CARET` | `^` | `AT` | `@` |

### Reserved words (36 keywords)

```
AND      ARRAY    BEGIN    CASE     CONST    DIV      DO
DOWNTO   ELSE     END      FILE     FOR      FORWARD  FUNCTION
GOTO     IF       IN       LABEL    MOD      NIL      NOT
OF       OR       PACKED   PROCEDURE PROGRAM RECORD   REPEAT
SET      THEN     TO       TYPE     UNTIL    VAR      WHILE
WITH
```

Keywords are **case-insensitive**: `BEGIN`, `begin`, and `Begin` all produce
the same `BEGIN` token.

> `true` and `false` are **not** reserved words — they are predefined identifiers
> that the parser and semantic analyser recognise as boolean literals.
> `integer`, `real`, `boolean`, and `char` are also not reserved; they tokenise as `ID`.

### Comments (discarded)

```pascal
{ This is a brace comment }
(* This is a paren-star comment
   spanning multiple lines *)
```

---

## AST node reference

Every node is a Python `dataclass` with a `line` field (1-based source line).

| Category | Nodes |
|---|---|
| **Program** | `Program(name, params, block)` · `Block(labels, consts, types, vars, subprograms, body)` |
| **Declarations** | `ConstDef` · `TypeDef` · `VarDecl` · `Param` · `ProcDecl` · `FuncDecl` |
| **Types** | `SimpleType` · `SubrangeType` · `ArrayType` · `RecordType` · `SetType` · `FileType` · `PointerType` |
| **Statements** | `CompoundStmt` · `AssignStmt` · `IfStmt` · `WhileStmt` · `ForStmt` · `RepeatStmt` · `CaseStmt` · `GotoStmt` · `WritelnStmt` · `ProcCallStmt` · `WithStmt` |
| **Expressions** | `BinOp(op, left, right)` · `UnaryOp(op, operand)` · `FuncCall(name, args)` |
| **Literals** | `IntLit` · `RealLit` · `StrLit` · `NilLit` · `BoolLit(value: bool)` |
| **Variables** | `Var(name)` · `IndexVar(base, indices)` · `FieldVar(base, field_name)` · `DerefVar(base)` |

### Operator precedence (lowest → highest)

| Level | Operators |
|---|---|
| 1 (lowest) | `=` `<>` `<` `>` `<=` `>=` `in` |
| 2 | `+` `-` `or` |
| 3 | `*` `/` `div` `mod` `and` |
| 4 (highest) | `not` (unary) · unary `-` |

---

## Running tests

### Locally

```bash
# All tests (332 total)
pytest tests/ -v

# Individual suites
pytest tests/test_lexer.py -v
pytest tests/test_lexer_errors.py -v
pytest tests/test_parser.py -v
pytest tests/test_semantic.py -v

# Specific class
pytest tests/test_semantic.py::TestArityChecking -v
pytest tests/test_parser.py::TestParseErrors -v
```

```
332 passed in 0.XX s
```

### Test suites

**`tests/test_lexer.py`** — 30 tests

| Class | Coverage |
|---|---|
| `TestLiterals` | INTEGER, REAL, STRING, empty string, escaped quote |
| `TestIdentifiers` | plain ID, reserved words, case-insensitive keywords |
| `TestOperators` | prefix conflicts (`:=`/`:`, `..`/`.`, `<=`/`<`, `>=`/`>`, `<>`) |
| `TestComments` | brace, paren-star, inline, multiline, line-number tracking |
| `TestLineNumbers` | lineno increments across newlines |
| `TestIntegration` | assignment, if-then-else, for-loop, array range |

**`tests/test_lexer_errors.py`** — 47 tests

| Class | Coverage |
|---|---|
| `TestIllegalCharacters` | `#` `$` `%` `!` `~`; error value, line, recovery |
| `TestUnterminatedString` | Missing `'`, at EOL, mid-file, after `''` edge case |
| `TestUnterminatedBraceComment` | `{ ...` never closed |
| `TestUnterminatedParenComment` | `(* ...` never closed |
| `TestLexErrorAttributes` | `kind`, `line`, `value` fields; `__str__` format |
| `TestErrorRecovery` | Mixed error types, valid tokens after errors |

**`tests/test_parser.py`** — 172 tests

| Class | Tests | Coverage |
|---|---|---|
| `TestProgramStructure` | 5 | minimal program, params, block, body |
| `TestLabelDeclaration` | 3 | integer label, id label, multiple labels |
| `TestConstDeclarations` | 6 | int, real, string, negative, named, multiple |
| `TestTypeDeclarations` | 13 | alias, subrange, array, record, pointer, set, file |
| `TestVarDeclarations` | 5 | single, multi-name, multiple decls |
| `TestSubprogramDeclarations` | 8 | proc, function, forward, params, var-params |
| `TestCompoundStatement` | 5 | empty, single, multiple, nested |
| `TestAssignmentStatement` | 8 | simple, array, field, deref, chained |
| `TestIfStatement` | 5 | if-then, if-then-else, nested |
| `TestWhileStatement` | 3 | basic, NOT condition |
| `TestForStatement` | 4 | to, downto, expr bounds |
| `TestRepeatStatement` | 2 | basic, multiple stmts |
| `TestCaseStatement` | 5 | single/multiple elements, multiple labels |
| `TestGotoStatement` | 2 | integer label, id label |
| `TestWritelnStatement` | 4 | no args, one arg, multiple args |
| `TestProcedureCallStatement` | 3 | no args, with args |
| `TestWithStatement` | 3 | basic, multiple vars, compound body |
| `TestExpressions` | 19 | all literals, precedence, unary, relational, calls |
| `TestComplexPrograms` | 5 | factorial, bubble sort, GCD, records |
| `TestParseErrors` | 46 | every missing keyword/token; error metadata |
| `TestBoolLiteral` | 5 | true/false as BoolLit nodes |
| `TestLabeledStatements` | 3 | `10: stmt`, `myLabel: stmt` |
| `TestLvalueAsStatementError` | 2 | complex lvalue as statement → parse error |
| `TestMainNotKeyword` | 3 | `main` is a valid identifier |

**`tests/test_semantic.py`** — 83 tests

| Class | Tests | Coverage |
|---|---|---|
| `TestBasicDeclarations` | 8 | var, const, type declarations |
| `TestTypeChecking` | 12 | assignments, int→real widening, type mismatch |
| `TestExpressionTypes` | 10 | literals, arithmetic, boolean, comparison |
| `TestControlFlow` | 8 | if, while, for, repeat condition type checking |
| `TestProceduresAndFunctions` | 8 | decl, call, return type |
| `TestUndeclaredIdentifiers` | 6 | undeclared vars, funcs |
| `TestArityChecking` | 7 | too few / too many args, exact match, builtins skip arity |
| `TestTypeCompatibilityExtended` | 3 | `char := 'A'`, `string → char`, nil → pointer |
| `TestWithScope` | 3 | field access inside WITH, nested records, unknown field |
| `TestForwardDeclarations` | 3 | forward proc, forward func, no duplicate error |
| `TestBoolLit` | 3 | true/false are T_BOOL, bool in condition |
| `TestMainNotReserved` | 2 | `main` as var/proc name |
| `TestSemanticErrors` | ~12 | complete error message/kind/line coverage |

---

## Docker

No local Python install required — only [Docker Desktop](https://www.docker.com/products/docker-desktop/).

```bash
# Build the image
docker compose build

# Run the valid program demo
docker compose run --rm analyzer

# Run the error program demo
docker compose run --rm analyzer-errors

# Run all 332 tests
docker compose run --rm test

# Run a specific test suite
docker compose run --rm test pytest tests/test_semantic.py -v
docker compose run --rm test pytest tests/test_parser.py::TestParseErrors -v
```

---

## Development workflow

```bash
# 1. Branch
git checkout -b feat/<description>

# 2. Implement + test
pytest tests/ -v

# 3. Commit
git add compiler/ tests/
git commit -m "feat: <description>"

# 4. PR
git push -u origin feat/<description>
gh pr create --title "..." --body "..."
```

Branch naming: `feat/`, `fix/`, `test/`, `docs/`.

See [CONTRIBUTING.md](CONTRIBUTING.md) for the full guide.
