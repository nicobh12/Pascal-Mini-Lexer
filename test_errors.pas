{ test_errors.pas
  A deliberately broken Mini-Pascal program used to exercise
  every layer of the compiler's error detection.

  Expected errors
  ---------------
  L04  [LexError]    unterminated_comment   — missing closing brace
  L08  [ParseError]  missing semicolon after constant 'limit = 100'
  L09  [ParseError]  missing semicolon after constant 'rate = 2.5'
  L12  [ParseError]  missing semicolon after variable declaration
  L14  [ParseError]  unexpected token in expression (missing operator)
  L15  [LexError]    unterminated_string    — 'hello has no closing quote
  L17  [ParseError]  missing THEN in if-statement
  L19  [ParseError]  missing DO in for-statement
  L21  [ParseError]  missing final dot after END
}

program BuggyProgram;

{ This constant section is missing semicolons after each definition }
const
  limit = 100          { <-- missing semicolon here }
  rate = 2.5           { <-- missing semicolon here }

{ Variable section: missing semicolon after first declaration }
var
  x, y : integer       { <-- missing semicolon here }
  msg : string;

begin
  { Missing operator between 'limit' and '10' }
  x := limit 10;

  { Unterminated string literal — closing quote is missing }
  msg := 'hello;

  { Missing THEN keyword in if-statement }
  if x > 0
    y := x;

  { Missing DO keyword in for-loop }
  for i := 1 to limit
    writeln(i)

  { Intentional: no final dot after END }
end
