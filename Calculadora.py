def calculadora():
    while True:
        print("\n--- CALCULADORA ---")
        print("1. Sumar")
        print("2. Restar")
        print("3. Multiplicar")
        print("4. Dividir")
        print("5. Potencia")
        print("6. Salir")

        opcion = input("Elige una opción: ")

        if opcion == "6":
            print("Calculadora cerrada")
            break

        a = float(input("Ingrese el primer número: "))
        b = float(input("Ingrese el segundo número: "))

        if opcion == "1":
            print("Resultado:", a + b)
        elif opcion == "2":
            print("Resultado:", a - b)
        elif opcion == "3":
            print("Resultado:", a * b)
        elif opcion == "4":
            print("Resultado:", "Error: división por cero" if b == 0 else a / b)
        elif opcion == "5":
            print("Resultado:", a ** b)
        else:
            print("Opción no válida")

calculadora()
