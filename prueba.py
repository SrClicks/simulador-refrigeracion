import CoolProp.CoolProp as CP
import pint

u = pint.UnitRegistry()
Q_ = u.Quantity # type: ignore

def simular_refrigerador(T_ambiente_C, T_interior_C, Flujo_masico_kg_s):

    refrigerante = 'R134a'

    # --- INPUTS ---
    T_ambiente = Q_(T_ambiente_C, "degC").to("kelvin")
    T_interior = Q_(T_interior_C, "degC").to("kelvin")
    Flujo_masico = Q_(Flujo_masico_kg_s, "kg/s")

    # Definimos Deltas térmicos (Diferencia de temperatura necesaria para transferir calor)
    Delta_T_cond = Q_(15, "delta_degC") # El condensador debe estar más caliente que el aire

    # --- ESTADO 1: Entrada Compresor (Vapor Saturado) ---
    # T_interior define la evaporación
    h1 = Q_(CP.PropsSI("H", "T", T_interior.magnitude, "Q", 1, refrigerante), "J/kg")
    s1 = Q_(CP.PropsSI("S", "T", T_interior.magnitude, "Q", 1, refrigerante), "J/kg/K")

    # --- ESTADO 2: Entrada Condensador (Vapor Sobrecalentado) ---
    T_condensacion = T_ambiente + Delta_T_cond
    P_condensacion = Q_(CP.PropsSI("P", "T", T_condensacion.magnitude, "Q", 0, refrigerante), "Pa")

    s2 = s1
    P2 = P_condensacion
    h2 = Q_(CP.PropsSI("H", "P", P2.to("Pa").magnitude, "S", s2.to("J/kg/K").magnitude, refrigerante), "J/kg")
    Trabajo_necesario = Flujo_masico * (h2 - h1)

    # --- ESTADO 3: Salida Condensador (Líquido Saturado) ---
    P3 = P2
    h3 = Q_(CP.PropsSI("H", "P", P3.to("Pa").magnitude, "Q", 0, refrigerante), "J/kg")
    T3 = Q_(CP.PropsSI("T", "P", P3.to("Pa").magnitude, "Q", 0, refrigerante), "kelvin")

    # --- ESTADO 4: Entrada Evaporador (Mezcla) ---
    h4 = h3
    P4 = Q_(CP.PropsSI("P", "T", T_interior.magnitude, "Q", 1, refrigerante), "Pa")
    x4 = CP.PropsSI("Q", "P", P4.to("Pa").magnitude, "H", h4.to("J/kg").magnitude, refrigerante)     # Para saber cuánto gas flash hay

    # --- CÁLCULOS FINALES ---
    Q_evap = Flujo_masico * (h1 - h4)
    
    # COP (Coeficiente de desempeño)
    COP = Q_evap / Trabajo_necesario

    # --- RESULTADOS ---
    # Empaquetamos los resultados en un diccionario
    resultados = {
        "scalar": {
            "Trabajo_Compresor_kW": Trabajo_necesario.to('kW').magnitude,
            "Calor_Extraido_kW": Q_evap.to('kW').magnitude,
            "COP": COP.magnitude,
            "Calidad_Evap": x4,
            "Temp_Descarga_C": CP.PropsSI('T','H',h2.magnitude,'P',P2.magnitude,refrigerante)-273.15,
            "Flujo_Masico_kg_s": Flujo_masico.magnitude
        },
        "states": {
            1: {"P": P4.to("Pa").magnitude, "T": T_interior.to("kelvin").magnitude, "h": h1.to("J/kg").magnitude, "s": s1.to("J/kg/K").magnitude, "desc": "Entrada Compresor"},
            2: {"P": P2.to("Pa").magnitude, "T": (T_ambiente + Delta_T_cond).to("kelvin").magnitude, "h": h2.to("J/kg").magnitude, "s": s2.to("J/kg/K").magnitude, "desc": "Entrada Condensador"}, # Nota: T calculada aprox en ciclo
            3: {"P": P3.to("Pa").magnitude, "T": T3.to("kelvin").magnitude, "h": h3.to("J/kg").magnitude, "s": CP.PropsSI("S", "P", P3.magnitude, "Q", 0, refrigerante), "desc": "Salida Condensador"},
            4: {"P": P4.to("Pa").magnitude, "T": T_interior.to("kelvin").magnitude, "h": h4.to("J/kg").magnitude, "s": CP.PropsSI("S", "P", P4.magnitude, "H", h4.magnitude, refrigerante), "desc": "Entrada Evaporador"},
        } 
    }
    
    # Recalculamos T real de descarga para el estado 2 (el modelo asume sobrecalentamiento isentrópico)
    T2_real = CP.PropsSI('T','H',h2.magnitude,'P',P2.magnitude,refrigerante)
    resultados["states"][2]["T"] = T2_real
    
    return resultados

def imprimir_resultados(res, t_amb_c):
    print(f"--- RESULTADOS (Ambiente: {t_amb_c} C) ---")
    print(f"- Trabajo Compresor: {res['scalar']['Trabajo_Compresor_kW']:.2f} kW")
    print(f"- Calor Extraido:    {res['scalar']['Calor_Extraido_kW']:.2f} kW")
    print(f"- COP del ciclo:     {res['scalar']['COP']:.2f}")
    print(f"- Calidad en Evap:   {res['scalar']['Calidad_Evap']:.2f} ({(res['scalar']['Calidad_Evap']*100):.1f}% es gas flash)")
    print(f"- Temp. Descarga:    {res['scalar']['Temp_Descarga_C']:.1f} C")


# --- BLOQUE INTERACTIVO ---
if __name__ == "__main__":
    print("\n--- CONFIGURACION DE LA SIMULACION ---")
    try:
        # Pedimos los datos al usuario
        t_amb_input = float(input("1. Ingrese Temperatura Ambiente (C): "))
        t_int_input = float(input("2. Ingrese Temperatura Interior Objetivo (C): "))
        flujo_input = float(input("3. Ingrese Flujo Masico (kg/s): "))
        
        print("\nCalculando...")
        
        # Llamamos a tu función con los datos ingresados
        resultados = simular_refrigerador(t_amb_input, t_int_input, flujo_input)
        imprimir_resultados(resultados, t_amb_input)
        
    except ValueError:
        print("Error: Por favor ingrese solo números (use punto para decimales).")