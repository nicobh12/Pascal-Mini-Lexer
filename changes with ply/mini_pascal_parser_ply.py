#Parser for a mini-Pascal language, implemented using PLY (Python Lex-Yacc).
# Note: Some design decisions, documentation, and error management strategies were developed
# with assistance from Anthropic Claude (AI) and GitHub Copilot. The final implementation and
# integration were completed and reviewed by the author.

import ply.yacc as yacc
from mini_pascal_lex import tokens, make_lexer

# ---------------------------------------------------------------------------
# parse result
# ---------------------------------------------------------------------------
class ParseResult:
    def __init__(self):
        self.lex_errors = []
        self.parse_errors = []
        self.ok = True

parse_errors_global = []

# ---------------------------------------------------------------------------
# precedence
# ---------------------------------------------------------------------------
precedence = (
    ('right', 'ASSIGN'),
    ('left', 'OR'),
    ('left', 'AND'),
    ('left', 'EQUALS','NEQ','LT','GT','LEQ','GEQ','IN'),
    ('left', 'PLUS','MINUS'),
    ('left', 'TIMES','DIVIDE','DIV','MOD'),
    ('right', 'NOT'),
)

# ---------------------------------------------------------------------------
# program
# ---------------------------------------------------------------------------
def p_program(p):
    '''program : PROGRAM ID opt_prog_params SEMICOLON block DOT'''
    pass

def p_opt_prog_params(p):
    '''opt_prog_params : LPAREN id_list RPAREN
                       | empty'''
    pass

# ---------------------------------------------------------------------------
# block
# ---------------------------------------------------------------------------
def p_block(p):
    '''block : label_part const_part type_part var_part subprogram_part compound_stmt'''
    pass

# ---------------------------------------------------------------------------
# label
# ---------------------------------------------------------------------------
def p_label_part(p):
    '''label_part : LABEL label_list SEMICOLON
                  | empty'''
    pass

def p_label_list(p):
    '''label_list : label_list COMMA label_id
                  | label_id'''
    pass

def p_label_id(p):
    '''label_id : INTEGER
                | ID'''
    pass

# ---------------------------------------------------------------------------
# const
# ---------------------------------------------------------------------------
def p_const_part(p):
    '''const_part : CONST const_defs
                  | empty'''
    pass

def p_const_defs(p):
    '''const_defs : const_defs const_def
                  | const_def'''
    pass

def p_const_def(p):
    '''const_def : ID EQUALS constant SEMICOLON'''
    pass

def p_constant(p):
    '''constant : PLUS unsigned_constant
                | MINUS unsigned_constant
                | unsigned_constant'''
    pass

def p_unsigned_constant(p):
    '''unsigned_constant : INTEGER
                         | REAL
                         | STRING
                         | NIL
                         | ID'''
    pass

# ---------------------------------------------------------------------------
# types
# ---------------------------------------------------------------------------
def p_type_part(p):
    '''type_part : TYPE type_defs
                 | empty'''
    pass

def p_type_defs(p):
    '''type_defs : type_defs type_def
                 | type_def'''
    pass

def p_type_def(p):
    '''type_def : ID EQUALS type_denoter SEMICOLON'''
    pass

def p_type_denoter(p):
    '''type_denoter : simple_type
                     | array_type
                     | record_type
                     | set_type
                     | file_type
                     | pointer_type
                     | packed_struct'''
    pass

def p_pointer_type(p):
    '''pointer_type : CARET ID'''
    pass

def p_packed_struct(p):
    '''packed_struct : PACKED array_type
                     | PACKED record_type
                     | PACKED set_type
                     | PACKED file_type'''
    pass

def p_simple_type(p):
    '''simple_type : ID
                   | INTEGER DOTDOT constant
                   | constant DOTDOT constant'''
    pass

def p_array_type(p):
    '''array_type : ARRAY LBRACKET simple_type_list RBRACKET OF type_denoter'''
    pass

def p_simple_type_list(p):
    '''simple_type_list : simple_type_list COMMA simple_type
                        | simple_type'''
    pass

def p_record_type(p):
    '''record_type : RECORD field_list END'''
    pass

def p_field_list(p):
    '''field_list : field_list SEMICOLON record_section
                  | record_section
                  | empty'''
    pass

def p_record_section(p):
    '''record_section : id_list COLON type_denoter'''
    pass

def p_set_type(p):
    '''set_type : SET OF simple_type'''
    pass

def p_file_type(p):
    '''file_type : FILE OF type_denoter'''
    pass

# ---------------------------------------------------------------------------
# var
# ---------------------------------------------------------------------------
def p_var_part(p):
    '''var_part : VAR var_decl_list
                | empty'''
    pass

def p_var_decl_list(p):
    '''var_decl_list : var_decl_list var_decl
                     | var_decl'''
    pass

def p_var_decl(p):
    '''var_decl : id_list COLON type_denoter SEMICOLON'''
    pass

def p_id_list(p):
    '''id_list : id_list COMMA ID
               | ID'''
    pass

# ---------------------------------------------------------------------------
# subprograms
# ---------------------------------------------------------------------------
def p_subprogram_part(p):
    '''subprogram_part : subprogram_part subprogram
                       | empty'''
    pass

def p_subprogram(p):
    '''subprogram : procedure_decl
                  | function_decl'''
    pass

def p_procedure_decl(p):
    '''procedure_decl : PROCEDURE ID formal_params SEMICOLON proc_tail'''
    pass

def p_proc_tail(p):
    '''proc_tail : FORWARD SEMICOLON
                 | block SEMICOLON'''
    pass

def p_function_decl(p):
    '''function_decl : FUNCTION ID formal_params COLON ID SEMICOLON func_tail'''
    pass

def p_func_tail(p):
    '''func_tail : FORWARD SEMICOLON
                 | block SEMICOLON'''
    pass

def p_formal_params(p):
    '''formal_params : LPAREN param_sections RPAREN
                     | empty'''
    pass

def p_param_sections(p):
    '''param_sections : param_sections SEMICOLON param_section
                      | param_section'''
    pass

def p_param_section(p):
    '''param_section : VAR id_list COLON ID
                     | id_list COLON ID'''
    pass

# ---------------------------------------------------------------------------
# statements
# ---------------------------------------------------------------------------
def p_compound_stmt(p):
    '''compound_stmt : BEGIN stmt_seq END'''
    pass

def p_stmt_seq(p):
    '''stmt_seq : stmt_seq SEMICOLON statement
                | statement
                | empty'''
    pass

def p_statement(p):
    '''statement : assign_stmt
                 | if_stmt
                 | while_stmt
                 | for_stmt
                 | repeat_stmt
                 | case_stmt
                 | goto_stmt
                 | writeln_stmt
                 | with_stmt
                 | proc_call_stmt
                 | compound_stmt
                 | empty'''
    pass

def p_assign_stmt(p):
    '''assign_stmt : var ASSIGN expression'''
    pass

def p_if_stmt(p):
    '''if_stmt : IF expression THEN statement
               | IF expression THEN statement ELSE statement'''
    pass

def p_while_stmt(p):
    '''while_stmt : WHILE expression DO statement'''
    pass

def p_for_stmt(p):
    '''for_stmt : FOR ID ASSIGN expression TO expression DO statement
                | FOR ID ASSIGN expression DOWNTO expression DO statement'''
    pass

def p_repeat_stmt(p):
    '''repeat_stmt : REPEAT stmt_seq UNTIL expression'''
    pass

def p_case_stmt(p):
    '''case_stmt : CASE expression OF case_elements END'''
    pass

def p_case_elements(p):
    '''case_elements : case_elements SEMICOLON case_element
                     | case_element'''
    pass

def p_case_element(p):
    '''case_element : const_list COLON statement'''
    pass

def p_const_list(p):
    '''const_list : const_list COMMA constant
                  | constant'''
    pass

def p_goto_stmt(p):
    '''goto_stmt : GOTO INTEGER
                 | GOTO ID'''
    pass

def p_writeln_stmt(p):
    '''writeln_stmt : WRITELN
                    | WRITELN LPAREN arg_list RPAREN'''
    pass

def p_proc_call_stmt(p):
    '''proc_call_stmt : ID LPAREN arg_list RPAREN
                      | ID'''
    pass

def p_with_stmt(p):
    '''with_stmt : WITH var_list DO statement'''
    pass

def p_var_list(p):
    '''var_list : var_list COMMA var
                | var'''
    pass

# ---------------------------------------------------------------------------
# var usage
# ---------------------------------------------------------------------------
def p_var(p):
    '''var : ID var_suffix'''
    pass

def p_var_suffix(p):
    '''var_suffix : var_suffix suffix
                  | empty'''
    pass

def p_suffix(p):
    '''suffix : LBRACKET expr_list RBRACKET
              | DOT ID
              | CARET'''
    pass

# ---------------------------------------------------------------------------
# expressions
# ---------------------------------------------------------------------------
def p_expression(p):
    '''expression : simple_expr relop simple_expr
                  | simple_expr'''
    pass

def p_relop(p):
    '''relop : EQUALS
             | NEQ
             | LT
             | GT
             | LEQ
             | GEQ
             | IN'''
    pass

def p_simple_expr(p):
    '''simple_expr : sign term
                   | term
                   | simple_expr addop term'''
    pass

def p_sign(p):
    '''sign : PLUS
            | MINUS'''
    pass

def p_addop(p):
    '''addop : PLUS
             | MINUS
             | OR'''
    pass

def p_term(p):
    '''term : term mulop factor
            | factor'''
    pass

def p_mulop(p):
    '''mulop : TIMES
             | DIVIDE
             | DIV
             | MOD
             | AND'''
    pass

def p_factor(p):
    '''factor : INTEGER
              | REAL
              | STRING
              | NIL
              | LPAREN expression RPAREN
              | NOT factor
              | ID LPAREN arg_list RPAREN
              | var'''
    pass

def p_arg_list(p):
    '''arg_list : arg_list COMMA expression
                | expression
                | empty'''
    pass

def p_expr_list(p):
    '''expr_list : expr_list COMMA expression
                 | expression'''
    pass

# ---------------------------------------------------------------------------
# empty + error
# ---------------------------------------------------------------------------
def p_empty(p):
    'empty :'
    pass

# ---------------------------------------------------------------------------
# error reporting
# Note: Error management implementation and recovery strategies were developed
# with assistance from GitHub Copilot.
# ---------------------------------------------------------------------------
def p_error(p):
    if not p:
        parse_errors_global.append("Syntax error at end of file")
        return

    # evitar spam de errores en la misma línea
    if len(parse_errors_global) > 0:
        last = parse_errors_global[-1]
        if f"line {p.lineno}" in last:
            return

    parse_errors_global.append(
        f"Syntax error '{p.value}' line {p.lineno}"
    )

    # sincronización: saltar hasta algo útil
    while True:
        tok = parser.token()
        if not tok or tok.type in ('SEMICOLON', 'END'):
            break

    parser.errok()

# ---------------------------------------------------------------------------
# build
# ---------------------------------------------------------------------------
parser = yacc.yacc()

def parse(source):
    global parse_errors_global
    parse_errors_global = []

    result = ParseResult()

    lexer = make_lexer()
    lexer.input(source)

    parser.parse(source, lexer=lexer)

    result.lex_errors = lexer.errors
    result.parse_errors = parse_errors_global
    result.ok = (len(result.lex_errors) == 0 and len(result.parse_errors) == 0)

    return result