program TestProgram;

const
  maxn = 10;
  pi = 3.14159;

type
  MyArray = array[1..10] of integer;

var
  i, j : integer;
  sum : real;
  data : MyArray;

procedure PrintValue(x: integer);
begin
  writeln('Value: ', x)
end;

function AddTwo(a: integer; b: integer): integer;
var
  result : integer;
begin
  result := a + b;
  AddTwo := result
end;

begin
  sum := 0;
  for i := 1 to maxn do
    data[i] := i * i;
  
  for i := 1 to maxn do
    sum := sum + data[i];
  
  if sum > 0 then
    PrintValue(maxn)
  else
    writeln('Sum is zero');
    
  while i > 0 do
    i := i - 1
end.
