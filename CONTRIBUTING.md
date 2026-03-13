# Contributing — Mini-Pascal Lexer

## Architecture

```
Pascal-Mini-Lexer/
├── mini_pascal_lex.py      # PLY lexer — single source of truth
├── tests/
│   └── test_lexer.py       # pytest suite
├── .claude/
│   ├── CLAUDE.md           # Claude Code project instructions
│   └── agents.md           # Multi-agent workflow definitions
└── CONTRIBUTING.md         # This file
```

### Lexer design decisions

| Decision | Reason |
|---|---|
| All rules in one file | PLY requires tokens/rules in the same module |
| String rules for operators | PLY auto-sorts by decreasing pattern length, preventing prefix conflicts |
| Function rules for literals | Functions run before string rules — needed for REAL vs INTEGER disambiguation |
| No negative literal | Unary minus belongs to the parser, not the lexer |
| Case-insensitive keywords | Pascal spec; implemented via `t.value.lower()` in `t_ID` |
| Comment rules return nothing | PLY discards the token — correct behaviour |

---

## Git workflow

### Branch naming

```
feat/<short-description>     # new token or feature
fix/<short-description>      # bug in existing rule
test/<short-description>     # test-only change
docs/<short-description>     # documentation only
```

### Step-by-step flow

```
1. git checkout main && git pull
2. git checkout -b feat/<description>
3. # implement changes following .claude/CLAUDE.md conventions
4. pytest tests/ -v                      # must pass before commit
5. git add mini_pascal_lex.py tests/     # never add parser/output files
6. git commit -m "<type>: <description>"
7. git push -u origin feat/<description>
8. gh pr create --title "..." --body "..."
```

### Commit message format

```
<type>: <imperative description>

# types: feat | fix | test | docs | refactor
# examples:
feat: add DOTDOT token for array range syntax
fix: ensure REAL rule matches before INTEGER
test: cover case-insensitive reserved word lookup
```

---

## PR checklist

Before opening a PR, verify every item:

- [ ] `pytest tests/ -v` passes with no warnings
- [ ] Every new token has at least one test
- [ ] `tokens` tuple and `reserved` dict are in sync
- [ ] No debug prints left in lexer code
- [ ] Branch is up to date with `main` (`git rebase main`)

PR description must include:
1. **What** — which tokens/rules changed and why.
2. **Test evidence** — paste `pytest` output.
3. **Edge cases** — list any tricky inputs considered.

---

## Running locally

```bash
# install dependencies
pip install ply pytest

# run demo
python mini_pascal_lex.py

# run tests
pytest tests/ -v

# run tests with coverage (optional)
pip install pytest-cov
pytest tests/ -v --cov=mini_pascal_lex --cov-report=term-missing
```

---

## Agent-assisted development

This project uses Claude Code sub-agents defined in `.claude/agents.md`.

Quick reference:

| Goal | Agent |
|---|---|
| Add / fix a token | `implementer` |
| Write tests | `tester` |
| Review a PR | `reviewer` |
| Update docs | `docs` |

See `.claude/agents.md` for full trigger conditions and output contracts.
