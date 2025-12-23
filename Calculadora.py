def calculadora():
    a = float(input("Ingrese el primer número: "))
    op = input("Ingrese la operación (+, -, *, /): ")
    b = float(input("Ingrese el segundo número: "))

    res = None
    if op == "+":
        res = a + b
    elif op == "-":
        res = a - b
    elif op == "*":
        res = a * b
    elif op == "/":
        if b != 0:
            res = a / b
        else:
            print("Error: división por cero")
            return
    else:
        print("Operación no válida")
        return

    # Mostrar resultado y, si es entero, indicar par o impar
    if isinstance(res, float) and res.is_integer():
        entero = int(res)
        paridad = "par" if entero % 2 == 0 else "impar"
        print(f"Resultado: {res} -> {paridad}")
    elif isinstance(res, int):
        paridad = "par" if res % 2 == 0 else "impar"
        print(f"Resultado: {res} -> {paridad}")
    else:
        print(f"Resultado: {res} (no es entero — par/impar no aplica)")

calculadora()

print("Fin del programa")
