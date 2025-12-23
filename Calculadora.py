def calculadora():
    a = float(input("Ingrese el primer número: "))
    op = input("Ingrese la operación (+, -, *, /): ")
    b = float(input("Ingrese el segundo número: "))

    if op == "+":
        print("Resultado:", a + b)
    elif op == "-":
        print("Resultado:", a - b)
    elif op == "*":
        print("Resultado:", a * b)
    elif op == "/":
        if b != 0:
            print("Resultado:", a / b)
        else:
            print("Error: división por cero")
    else:
        print("Operación no válida")

calculadora()
