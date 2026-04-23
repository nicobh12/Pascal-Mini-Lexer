{ factorial.pas — función recursiva, sin errores }
program Factorial;

var
  n : integer;

function Fact(n: integer): integer;
begin
  if n <= 1 then
    Fact := 1
  else
    Fact := n * Fact(n - 1)
end;

begin
  n := 7;
  writeln('7! = ', Fact(n))
end.
