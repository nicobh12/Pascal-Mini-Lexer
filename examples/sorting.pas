{ sorting.pas — burbuja, forward declaration, sin errores }
program Sorting;

const
  N = 5;

type
  Lista = array[1..N] of integer;

var
  datos : Lista;
  i     : integer;

procedure Swap(var a: integer; var b: integer);
var
  tmp : integer;
begin
  tmp := a;
  a   := b;
  b   := tmp
end;

procedure BubbleSort(var arr: Lista; n: integer);
var
  i, j : integer;
begin
  for i := 1 to n - 1 do
    for j := 1 to n - i do
      if arr[j] > arr[j + 1] then
        Swap(arr[j], arr[j + 1])
end;

begin
  datos[1] := 42;
  datos[2] := 7;
  datos[3] := 19;
  datos[4] := 3;
  datos[5] := 55;

  BubbleSort(datos, N);

  for i := 1 to N do
    writeln(datos[i])
end.
