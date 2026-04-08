"""
mini_pascal_parser.py
Recursive-descent syntactic analyser for Mini-Pascal.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Optional

from mini_pascal_lex import make_lexer


# ============================================================
# AST Nodes
# ============================================================

@dataclass
class Node:
    line: int = 0


# -- Literals --

@dataclass
class IntLit(Node):
    value: int = 0


@dataclass
class RealLit(Node):
    value: float = 0.0


@dataclass
class StrLit(Node):
    value: str = ''


@dataclass
class NilLit(Node):
    pass


# -- Variables (l-values / r-values) --

@dataclass
class Var(Node):
    name: str = ''


@dataclass
class IndexVar(Node):
    base: Any = None
    indices: list = field(default_factory=list)


@dataclass
class FieldVar(Node):
    base: Any = None
    field_name: str = ''


@dataclass
class DerefVar(Node):
    base: Any = None


# -- Expressions --

@dataclass
class BinOp(Node):
    op: str = ''
    left: Any = None
    right: Any = None


@dataclass
class UnaryOp(Node):
    op: str = ''
    operand: Any = None


@dataclass
class FuncCall(Node):
    name: str = ''
    args: list = field(default_factory=list)


# -- Types --

@dataclass
class SimpleType(Node):
    name: str = ''


@dataclass
class SubrangeType(Node):
    low: Any = None
    high: Any = None


@dataclass
class ArrayType(Node):
    packed: bool = False
    indices: list = field(default_factory=list)
    element_type: Any = None


@dataclass
class RecordType(Node):
    packed: bool = False
    fields: list = field(default_factory=list)   # [(names, type_node), ...]


@dataclass
class SetType(Node):
    packed: bool = False
    base: Any = None


@dataclass
class FileType(Node):
    packed: bool = False
    element_type: Any = None


@dataclass
class PointerType(Node):
    target: str = ''


# -- Declarations --

@dataclass
class ConstDef(Node):
    name: str = ''
    value: Any = None


@dataclass
class TypeDef(Node):
    name: str = ''
    type_node: Any = None


@dataclass
class VarDecl(Node):
    names: list = field(default_factory=list)
    type_node: Any = None


@dataclass
class Param(Node):
    names: list = field(default_factory=list)
    type_name: str = ''
    by_ref: bool = False


@dataclass
class ProcDecl(Node):
    name: str = ''
    params: list = field(default_factory=list)
    body: Any = None
    forward: bool = False


@dataclass
class FuncDecl(Node):
    name: str = ''
    params: list = field(default_factory=list)
    return_type: str = ''
    body: Any = None
    forward: bool = False


@dataclass
class Block(Node):
    labels: list = field(default_factory=list)
    consts: list = field(default_factory=list)
    types: list = field(default_factory=list)
    vars: list = field(default_factory=list)
    subprograms: list = field(default_factory=list)
    body: Any = None   # CompoundStmt


@dataclass
class Program(Node):
    name: str = ''
    params: list = field(default_factory=list)
    block: Any = None


# -- Statements --

@dataclass
class CompoundStmt(Node):
    stmts: list = field(default_factory=list)


@dataclass
class AssignStmt(Node):
    target: Any = None
    value: Any = None


@dataclass
class IfStmt(Node):
    condition: Any = None
    then_branch: Any = None
    else_branch: Any = None


@dataclass
class WhileStmt(Node):
    condition: Any = None
    body: Any = None


@dataclass
class ForStmt(Node):
    var: str = ''
    start: Any = None
    direction: str = 'to'
    end: Any = None
    body: Any = None


@dataclass
class RepeatStmt(Node):
    body: list = field(default_factory=list)
    condition: Any = None


@dataclass
class CaseStmt(Node):
    expression: Any = None
    elements: list = field(default_factory=list)   # [(labels, stmt), ...]
    else_branch: Any = None


@dataclass
class GotoStmt(Node):
    label: Any = None


@dataclass
class WritelnStmt(Node):
    args: list = field(default_factory=list)


@dataclass
class ProcCallStmt(Node):
    name: str = ''
    args: list = field(default_factory=list)


@dataclass
class WithStmt(Node):
    vars: list = field(default_factory=list)
    body: Any = None


# ============================================================
# Parse Error & Result
# ============================================================

@dataclass
class ParseError:
    kind: str
    line: int
    message: str

    def __str__(self) -> str:
        return f"[ParseError] {self.kind} at line {self.line}: {self.message}"


@dataclass
class ParseResult:
    program: Optional[Program]
    parse_errors: list
    lex_errors: list

    @property
    def ok(self) -> bool:
        return not self.parse_errors and not self.lex_errors

    def __bool__(self) -> bool:
        return self.ok


# ============================================================
# Parser
# ============================================================

class Parser:
    def __init__(self, lexer):
        self.errors: list[ParseError] = []
        self._tokens: list = [tok for tok in lexer]
        self._pos: int = 0

    # ---- Token primitives ----

    def _cur(self):
        return self._tokens[self._pos] if self._pos < len(self._tokens) else None

    def _peek(self, offset: int = 1):
        i = self._pos + offset
        return self._tokens[i] if i < len(self._tokens) else None

    def _cur_type(self) -> str:
        tok = self._cur()
        return tok.type if tok else 'EOF'

    def _cur_line(self) -> int:
        tok = self._cur()
        return tok.lineno if tok else 0

    def _advance(self):
        tok = self._cur()
        if self._pos < len(self._tokens):
            self._pos += 1
        return tok

    def _check(self, *types) -> bool:
        return self._cur_type() in types

    def _match(self, *types):
        if self._check(*types):
            return self._advance()
        return None

    def _expect(self, token_type: str):
        if self._cur_type() == token_type:
            return self._advance()
        self._err(f"Expected '{token_type}', got '{self._cur_type()}'")
        return None

    def _err(self, message: str) -> None:
        self.errors.append(ParseError(
            kind='syntax_error',
            line=self._cur_line(),
            message=message,
        ))

    # ============================================================
    # Program
    # ============================================================

    def parse_program(self) -> Program:
        line = self._cur_line()
        self._expect('PROGRAM')
        name_tok = self._expect('ID')
        name = name_tok.value if name_tok else ''

        params: list = []
        if self._match('LPAREN'):
            params = self._parse_id_list()
            self._expect('RPAREN')

        self._expect('SEMICOLON')
        block = self._parse_block()
        self._expect('DOT')
        return Program(line=line, name=name, params=params, block=block)

    # ============================================================
    # Block
    # ============================================================

    def _parse_block(self) -> Block:
        line = self._cur_line()
        labels      = self._parse_label_part()
        consts      = self._parse_const_part()
        types       = self._parse_type_part()
        vars_       = self._parse_var_part()
        subprograms = self._parse_subprogram_part()
        body        = self._parse_compound_statement()
        return Block(line=line, labels=labels, consts=consts,
                     types=types, vars=vars_, subprograms=subprograms, body=body)

    # ---- Label part ----

    def _parse_label_part(self) -> list:
        if not self._match('LABEL'):
            return []
        labels = [self._parse_label_id()]
        while self._match('COMMA'):
            labels.append(self._parse_label_id())
        self._expect('SEMICOLON')
        return labels

    def _parse_label_id(self):
        if self._check('INTEGER'):
            return self._advance().value
        tok = self._expect('ID')
        return tok.value if tok else None

    # ---- Const part ----

    def _parse_const_part(self) -> list:
        if not self._match('CONST'):
            return []
        defs = []
        while self._check('ID'):
            defs.append(self._parse_const_def())
        return defs

    def _parse_const_def(self) -> ConstDef:
        line = self._cur_line()
        name_tok = self._expect('ID')
        name = name_tok.value if name_tok else ''
        self._expect('EQUALS')
        value = self._parse_constant()
        self._expect('SEMICOLON')
        return ConstDef(line=line, name=name, value=value)

    def _parse_constant(self):
        line = self._cur_line()
        if self._check('PLUS', 'MINUS'):
            sign = self._advance().type
            lit = self._parse_unsigned_constant()
            return UnaryOp(line=line, op=sign, operand=lit)
        return self._parse_unsigned_constant()

    def _parse_unsigned_constant(self):
        line = self._cur_line()
        if self._check('INTEGER'):
            return IntLit(line=line, value=self._advance().value)
        if self._check('REAL'):
            return RealLit(line=line, value=self._advance().value)
        if self._check('STRING'):
            return StrLit(line=line, value=self._advance().value)
        if self._check('NIL'):
            self._advance()
            return NilLit(line=line)
        if self._check('ID'):
            return Var(line=line, name=self._advance().value)
        self._err(f"Expected constant, got '{self._cur_type()}'")
        return None

    # ---- Type part ----

    def _parse_type_part(self) -> list:
        if not self._match('TYPE'):
            return []
        defs = []
        while self._check('ID'):
            defs.append(self._parse_type_def())
        return defs

    def _parse_type_def(self) -> TypeDef:
        line = self._cur_line()
        name_tok = self._expect('ID')
        name = name_tok.value if name_tok else ''
        self._expect('EQUALS')
        type_node = self._parse_type_denoter()
        self._expect('SEMICOLON')
        return TypeDef(line=line, name=name, type_node=type_node)

    def _parse_type_denoter(self):
        line = self._cur_line()
        if self._check('ARRAY'):
            return self._parse_array_type(packed=False)
        if self._check('RECORD'):
            return self._parse_record_type(packed=False)
        if self._check('SET'):
            return self._parse_set_type(packed=False)
        if self._check('FILE'):
            return self._parse_file_type(packed=False)
        if self._check('CARET'):
            self._advance()
            target_tok = self._expect('ID')
            return PointerType(line=line, target=target_tok.value if target_tok else '')
        if self._check('PACKED'):
            self._advance()
            if self._check('ARRAY'):
                return self._parse_array_type(packed=True)
            if self._check('RECORD'):
                return self._parse_record_type(packed=True)
            if self._check('SET'):
                return self._parse_set_type(packed=True)
            if self._check('FILE'):
                return self._parse_file_type(packed=True)
            self._err("Expected structured type after PACKED")
            return None
        return self._parse_simple_type()

    def _parse_simple_type(self):
        """type-ID  |  const..const  (subrange)"""
        line = self._cur_line()
        # Signed subrange: +N..M or -N..M
        if self._check('PLUS', 'MINUS'):
            low = self._parse_constant()
            self._expect('DOTDOT')
            high = self._parse_constant()
            return SubrangeType(line=line, low=low, high=high)
        # Integer subrange: N..M
        if self._check('INTEGER'):
            low = IntLit(line=line, value=self._advance().value)
            self._expect('DOTDOT')
            high = self._parse_constant()
            return SubrangeType(line=line, low=low, high=high)
        # ID — type alias OR enumerated-constant subrange (ID..ID)
        if self._check('ID'):
            peek = self._peek()
            if peek and peek.type == 'DOTDOT':
                low = Var(line=line, name=self._advance().value)
                self._advance()   # consume DOTDOT
                high = self._parse_constant()
                return SubrangeType(line=line, low=low, high=high)
            return SimpleType(line=line, name=self._advance().value)
        self._err(f"Expected type, got '{self._cur_type()}'")
        return None

    def _parse_array_type(self, packed: bool) -> ArrayType:
        line = self._cur_line()
        self._expect('ARRAY')
        self._expect('LBRACKET')
        indices = [self._parse_simple_type()]
        while self._match('COMMA'):
            indices.append(self._parse_simple_type())
        self._expect('RBRACKET')
        self._expect('OF')
        element_type = self._parse_type_denoter()
        return ArrayType(line=line, packed=packed, indices=indices, element_type=element_type)

    def _parse_record_type(self, packed: bool) -> RecordType:
        line = self._cur_line()
        self._expect('RECORD')
        fields = self._parse_field_list()
        self._expect('END')
        return RecordType(line=line, packed=packed, fields=fields)

    def _parse_field_list(self) -> list:
        fields = []
        if not self._check('ID'):
            return fields
        fields.append(self._parse_record_section())
        while self._check('SEMICOLON'):
            nxt = self._peek()
            if nxt and nxt.type == 'ID':
                self._advance()   # consume ';'
                fields.append(self._parse_record_section())
            else:
                self._advance()   # trailing ';' before END
                break
        return fields

    def _parse_record_section(self) -> tuple:
        names = self._parse_id_list()
        self._expect('COLON')
        type_node = self._parse_type_denoter()
        return (names, type_node)

    def _parse_set_type(self, packed: bool) -> SetType:
        line = self._cur_line()
        self._expect('SET')
        self._expect('OF')
        base = self._parse_simple_type()
        return SetType(line=line, packed=packed, base=base)

    def _parse_file_type(self, packed: bool) -> FileType:
        line = self._cur_line()
        self._expect('FILE')
        self._expect('OF')
        element_type = self._parse_type_denoter()
        return FileType(line=line, packed=packed, element_type=element_type)

    # ---- Var part ----

    def _parse_var_part(self) -> list:
        if not self._match('VAR'):
            return []
        decls = []
        while self._check('ID'):
            decls.append(self._parse_var_decl())
        return decls

    def _parse_var_decl(self) -> VarDecl:
        line = self._cur_line()
        names = self._parse_id_list()
        self._expect('COLON')
        type_node = self._parse_type_denoter()
        self._expect('SEMICOLON')
        return VarDecl(line=line, names=names, type_node=type_node)

    # ---- Shared helper ----

    def _parse_id_list(self) -> list:
        names = []
        tok = self._expect('ID')
        if tok:
            names.append(tok.value)
        while self._match('COMMA'):
            tok = self._expect('ID')
            if tok:
                names.append(tok.value)
        return names

    # ---- Subprogram part ----

    def _parse_subprogram_part(self) -> list:
        subprograms = []
        while self._check('PROCEDURE', 'FUNCTION'):
            if self._check('PROCEDURE'):
                subprograms.append(self._parse_procedure_decl())
            else:
                subprograms.append(self._parse_function_decl())
        return subprograms

    def _parse_procedure_decl(self) -> ProcDecl:
        line = self._cur_line()
        self._expect('PROCEDURE')
        name_tok = self._expect('ID')
        name = name_tok.value if name_tok else ''
        params = self._parse_formal_params()
        self._expect('SEMICOLON')
        if self._match('FORWARD'):
            self._expect('SEMICOLON')
            return ProcDecl(line=line, name=name, params=params, body=None, forward=True)
        body = self._parse_block()
        self._expect('SEMICOLON')
        return ProcDecl(line=line, name=name, params=params, body=body, forward=False)

    def _parse_function_decl(self) -> FuncDecl:
        line = self._cur_line()
        self._expect('FUNCTION')
        name_tok = self._expect('ID')
        name = name_tok.value if name_tok else ''
        params = self._parse_formal_params()
        self._expect('COLON')
        ret_tok = self._expect('ID')
        return_type = ret_tok.value if ret_tok else ''
        self._expect('SEMICOLON')
        if self._match('FORWARD'):
            self._expect('SEMICOLON')
            return FuncDecl(line=line, name=name, params=params,
                            return_type=return_type, body=None, forward=True)
        body = self._parse_block()
        self._expect('SEMICOLON')
        return FuncDecl(line=line, name=name, params=params,
                        return_type=return_type, body=body, forward=False)

    def _parse_formal_params(self) -> list:
        if not self._check('LPAREN'):
            return []
        self._advance()
        params = [self._parse_param_section()]
        while self._match('SEMICOLON'):
            params.append(self._parse_param_section())
        self._expect('RPAREN')
        return params

    def _parse_param_section(self) -> Param:
        line = self._cur_line()
        by_ref = bool(self._match('VAR'))
        names = self._parse_id_list()
        self._expect('COLON')
        type_tok = self._expect('ID')
        type_name = type_tok.value if type_tok else ''
        return Param(line=line, names=names, type_name=type_name, by_ref=by_ref)

    # ============================================================
    # Statements
    # ============================================================

    def _parse_compound_statement(self) -> CompoundStmt:
        line = self._cur_line()
        self._expect('BEGIN')
        stmts = self._parse_stmt_seq({'END'})
        self._expect('END')
        return CompoundStmt(line=line, stmts=stmts)

    def _parse_stmt_seq(self, terminators: set) -> list:
        """Parse semicolon-separated statements; stop at any token in terminators."""
        stmts = []
        if not self._check(*terminators) and not self._check('EOF'):
            stmts.append(self._parse_statement())
        while self._match('SEMICOLON'):
            if self._check(*terminators) or self._check('EOF'):
                break
            stmts.append(self._parse_statement())
        return [s for s in stmts if s is not None]

    def _parse_statement(self):
        t = self._cur_type()
        if t == 'BEGIN':
            return self._parse_compound_statement()
        if t == 'IF':
            return self._parse_if()
        if t == 'WHILE':
            return self._parse_while()
        if t == 'FOR':
            return self._parse_for()
        if t == 'REPEAT':
            return self._parse_repeat()
        if t == 'CASE':
            return self._parse_case()
        if t == 'GOTO':
            return self._parse_goto()
        if t == 'WRITELN':
            return self._parse_writeln()
        if t == 'WITH':
            return self._parse_with()
        if t == 'ID':
            return self._parse_id_stmt()
        return None   # empty statement

    def _parse_id_stmt(self):
        """Assignment (var := expr) or procedure call."""
        line = self._cur_line()
        name_tok = self._advance()
        name = name_tok.value

        # Parse optional variable suffixes
        var = Var(line=line, name=name)
        var = self._parse_var_suffix(var)

        if self._match('ASSIGN'):
            value = self._parse_expression()
            return AssignStmt(line=line, target=var, value=value)

        # No ':=' → must be procedure call; suffix must be empty
        if not isinstance(var, Var):
            self._err(f"Expected ':=' after variable access")
            return None

        args = []
        if self._match('LPAREN'):
            args = self._parse_arg_list()
            self._expect('RPAREN')
        return ProcCallStmt(line=line, name=name, args=args)

    def _parse_var_suffix(self, base):
        """Consume any number of [indices], .field, ^ suffixes."""
        while True:
            line = self._cur_line()
            if self._match('LBRACKET'):
                indices = [self._parse_expression()]
                while self._match('COMMA'):
                    indices.append(self._parse_expression())
                self._expect('RBRACKET')
                base = IndexVar(line=line, base=base, indices=indices)
            elif self._match('DOT'):
                field_tok = self._expect('ID')
                base = FieldVar(line=line, base=base,
                                field_name=field_tok.value if field_tok else '')
            elif self._match('CARET'):
                base = DerefVar(line=line, base=base)
            else:
                break
        return base

    def _parse_if(self) -> IfStmt:
        line = self._cur_line()
        self._expect('IF')
        cond = self._parse_expression()
        self._expect('THEN')
        then_br = self._parse_statement()
        else_br = None
        if self._match('ELSE'):
            else_br = self._parse_statement()
        return IfStmt(line=line, condition=cond,
                      then_branch=then_br, else_branch=else_br)

    def _parse_while(self) -> WhileStmt:
        line = self._cur_line()
        self._expect('WHILE')
        cond = self._parse_expression()
        self._expect('DO')
        body = self._parse_statement()
        return WhileStmt(line=line, condition=cond, body=body)

    def _parse_for(self) -> ForStmt:
        line = self._cur_line()
        self._expect('FOR')
        var_tok = self._expect('ID')
        var = var_tok.value if var_tok else ''
        self._expect('ASSIGN')
        start = self._parse_expression()
        if self._match('TO'):
            direction = 'to'
        elif self._match('DOWNTO'):
            direction = 'downto'
        else:
            self._err("Expected TO or DOWNTO in FOR statement")
            direction = 'to'
        end = self._parse_expression()
        self._expect('DO')
        body = self._parse_statement()
        return ForStmt(line=line, var=var, start=start,
                       direction=direction, end=end, body=body)

    def _parse_repeat(self) -> RepeatStmt:
        line = self._cur_line()
        self._expect('REPEAT')
        stmts = self._parse_stmt_seq({'UNTIL'})
        self._expect('UNTIL')
        cond = self._parse_expression()
        return RepeatStmt(line=line, body=stmts, condition=cond)

    def _parse_case(self) -> CaseStmt:
        line = self._cur_line()
        self._expect('CASE')
        expr = self._parse_expression()
        self._expect('OF')
        elements = []
        while not self._check('END', 'EOF'):
            labels = [self._parse_constant()]
            while self._match('COMMA'):
                labels.append(self._parse_constant())
            self._expect('COLON')
            stmt = self._parse_statement()
            elements.append((labels, stmt))
            if not self._match('SEMICOLON'):
                break
        self._expect('END')
        return CaseStmt(line=line, expression=expr,
                        elements=elements, else_branch=None)

    def _parse_goto(self) -> GotoStmt:
        line = self._cur_line()
        self._expect('GOTO')
        if self._check('INTEGER'):
            label = self._advance().value
        else:
            tok = self._expect('ID')
            label = tok.value if tok else ''
        return GotoStmt(line=line, label=label)

    def _parse_writeln(self) -> WritelnStmt:
        line = self._cur_line()
        self._expect('WRITELN')
        args = []
        if self._match('LPAREN'):
            args = self._parse_arg_list()
            self._expect('RPAREN')
        return WritelnStmt(line=line, args=args)

    def _parse_with(self) -> WithStmt:
        line = self._cur_line()
        self._expect('WITH')
        tok = self._expect('ID')
        v = Var(line=line, name=tok.value if tok else '')
        vars_ = [self._parse_var_suffix(v)]
        while self._match('COMMA'):
            inner = self._cur_line()
            tok2 = self._expect('ID')
            v2 = Var(line=inner, name=tok2.value if tok2 else '')
            vars_.append(self._parse_var_suffix(v2))
        self._expect('DO')
        body = self._parse_statement()
        return WithStmt(line=line, vars=vars_, body=body)

    # ============================================================
    # Expressions
    # ============================================================

    def _parse_arg_list(self) -> list:
        args = [self._parse_expression()]
        while self._match('COMMA'):
            args.append(self._parse_expression())
        return args

    def _parse_expression(self):
        """expression = simple_expr [ rel_op simple_expr ]"""
        line = self._cur_line()
        left = self._parse_simple_expr()
        if self._check('EQUALS', 'NEQ', 'LT', 'GT', 'LEQ', 'GEQ', 'IN'):
            op = self._advance().type
            right = self._parse_simple_expr()
            return BinOp(line=line, op=op, left=left, right=right)
        return left

    def _parse_simple_expr(self):
        """simple_expr = [sign] term { add_op term }"""
        line = self._cur_line()
        if self._check('PLUS', 'MINUS'):
            sign = self._advance().type
            left = UnaryOp(line=line, op=sign, operand=self._parse_term())
        else:
            left = self._parse_term()
        while self._check('PLUS', 'MINUS', 'OR'):
            op = self._advance().type
            right = self._parse_term()
            left = BinOp(line=line, op=op, left=left, right=right)
        return left

    def _parse_term(self):
        """term = factor { mul_op factor }"""
        line = self._cur_line()
        left = self._parse_factor()
        while self._check('TIMES', 'DIVIDE', 'DIV', 'MOD', 'AND'):
            op = self._advance().type
            right = self._parse_factor()
            left = BinOp(line=line, op=op, left=left, right=right)
        return left

    def _parse_factor(self):
        """factor = literal | nil | (expr) | NOT factor | ID [suffix | call]"""
        line = self._cur_line()
        if self._check('INTEGER'):
            return IntLit(line=line, value=self._advance().value)
        if self._check('REAL'):
            return RealLit(line=line, value=self._advance().value)
        if self._check('STRING'):
            return StrLit(line=line, value=self._advance().value)
        if self._check('NIL'):
            self._advance()
            return NilLit(line=line)
        if self._check('LPAREN'):
            self._advance()
            expr = self._parse_expression()
            self._expect('RPAREN')
            return expr
        if self._check('NOT'):
            self._advance()
            return UnaryOp(line=line, op='NOT', operand=self._parse_factor())
        if self._check('ID'):
            name = self._advance().value
            if self._match('LPAREN'):
                args = self._parse_arg_list()
                self._expect('RPAREN')
                return FuncCall(line=line, name=name, args=args)
            return self._parse_var_suffix(Var(line=line, name=name))
        self._err(f"Expected expression, got '{self._cur_type()}'")
        return None


# ============================================================
# Public API
# ============================================================

def parse(source: str) -> ParseResult:
    """Parse a Mini-Pascal source string. Returns ParseResult with AST + errors."""
    lx = make_lexer()
    lx.input(source)
    parser = Parser(lx)
    try:
        program = parser.parse_program()
    except Exception as exc:
        parser.errors.append(ParseError(
            kind='internal_error',
            line=0,
            message=str(exc),
        ))
        program = None
    return ParseResult(
        program=program,
        parse_errors=parser.errors,
        lex_errors=lx.errors,
    )
