import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import CoolProp.CoolProp as CP
import numpy as np
from prueba import simular_refrigerador

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Simulador Ciclo de Vapor", layout="wide", page_icon="❄️")


st.title("❄️ Simulador de Ciclo de Compresión de Vapor (R134a)")

# --- SIDEBAR: INPUTS ---
st.sidebar.header("⚙️ Parámetros de Entrada")

t_ambiente = st.sidebar.number_input(
    "Temperatura Ambiente (°C)", 
    min_value=-10.0, 
    max_value=50.0,
    value=25.0, 
    step=1.0,
    help="Temperatura del aire exterior donde se rechaza el calor."
)

t_interior = st.sidebar.number_input(
    "Temperatura Interior Objetivo (°C)", 
    min_value=-30.0, 
    max_value=10.0, 
    value=4.0, 
    step=1.0,
    help="Temperatura deseada dentro del refrigerador."
)

flujo_masico = st.sidebar.slider(
    "Flujo Másico (kg/s)", 
    min_value=0.001, 
    max_value=0.500, 
    value=0.100, 
    step=0.001,
    format="%.3f"
)

def create_cycle_schematic(states):
    """
    Crea un diagrama de bloques del ciclo con valores en tiempo real.
    """
    fig = go.Figure()
    
    # Coordenadas de componentes (Esquemático simple)
    # 1: Entrada Compresor (Abajo derecha)
    # 2: Salida Compresor / Entrada Condensador (Arriba derecha)
    # 3: Salida Condensador / Entrada Valvula (Arriba izquierda)
    # 4: Salida Valvula / Entrada Evaporador (Abajo izquierda)
    
    x = [0, 1, 1, 0, 0]
    y = [0, 0, 1, 1, 0]
    
    # Dibujar líneas de conexión (Tuberías)
    # Evaporador (0,0) -> Compresor (1,0) -> Condensador (1,1) -> Válvula (0,1) -> Evaporador (0,0)
    # Ajustamos visualmente para que parezca un ciclo
    
    # COMPRESOR (Lado Derecho, subiendo)
    fig.add_trace(go.Scatter(x=[1, 1], y=[0.2, 0.8], mode='lines', line=dict(color='black', width=2), showlegend=False))
    # CONDENSADOR (Arriba)
    fig.add_trace(go.Scatter(x=[0.8, 0.2], y=[1, 1], mode='lines', line=dict(color='red', width=4), name='Condensador'))
    # VALVULA (Lado Izquierdo, bajando)
    fig.add_trace(go.Scatter(x=[0, 0], y=[0.8, 0.2], mode='lines', line=dict(color='black', width=2), showlegend=False))
    # EVAPORADOR (Abajo)
    fig.add_trace(go.Scatter(x=[0.2, 0.8], y=[0, 0], mode='lines', line=dict(color='blue', width=4), name='Evaporador'))
    
    # Flechas/Conectores
    fig.add_annotation(x=1, y=0.5, text="Compresor", showarrow=False, xshift=40, font=dict(size=14, color="black"))
    fig.add_annotation(x=0, y=0.5, text="Válvula Exp.", showarrow=False, xshift=-40, font=dict(size=14, color="black"))
    fig.add_annotation(x=0.5, y=1, text="Condensador (Q out)", showarrow=False, yshift=20, font=dict(size=14, color="red"))
    fig.add_annotation(x=0.5, y=0, text="Evaporador (Q in)", showarrow=False, yshift=-20, font=dict(size=14, color="blue"))

    # Puntos de Estado y Valores
    # Estado 1: Entrada Compresor (1, 0)
    # Estado 2: Salida Compresor (1, 1)
    # Estado 3: Salida Condensador (0, 1)
    # Estado 4: Entrada Evaporador (0, 0)
    
    # Formatear textos
    s1 = states[1]; s2 = states[2]; s3 = states[3]; s4 = states[4]
    
    def get_text(s):
        return f"<b>{s['P']/100000:.1f} bar</b><br>{s['T']-273.15:.1f} °C"

    # Annotations para los estados en las esquinas
    # Estado 1 (Abajo Derecha)
    fig.add_annotation(x=1, y=0, text=f"Estado 1<br>{get_text(s1)}", showarrow=True, arrowhead=1, ax=30, ay=30, bgcolor="white", bordercolor="black")
    # Estado 2 (Arriba Derecha)
    fig.add_annotation(x=1, y=1, text=f"Estado 2<br>{get_text(s2)}", showarrow=True, arrowhead=1, ax=30, ay=-30, bgcolor="white", bordercolor="red")
    # Estado 3 (Arriba Izquierda)
    fig.add_annotation(x=0, y=1, text=f"Estado 3<br>{get_text(s3)}", showarrow=True, arrowhead=1, ax=-30, ay=-30, bgcolor="white", bordercolor="red")
    # Estado 4 (Abajo Izquierda)
    fig.add_annotation(x=0, y=0, text=f"Estado 4<br>{get_text(s4)}", showarrow=True, arrowhead=1, ax=-30, ay=30, bgcolor="white", bordercolor="blue")

    fig.update_xaxes(showgrid=False, zeroline=False, visible=False, range=[-0.3, 1.3])
    fig.update_yaxes(showgrid=False, zeroline=False, visible=False, range=[-0.2, 1.2])
    fig.update_layout(
        title="Esquema del Ciclo (Valores Reales)",
        height=400,
        margin=dict(l=10, r=10, t=40, b=10),
        template="plotly_white"
    )
    return fig

@st.cache_data
def calcular_campana_saturacion():
    """Calcula la campana de saturación (cacheada porque nunca cambia)."""
    refrigerante = 'R134a'
    T_crit = CP.PropsSI("Tcrit", refrigerante)
    T_range = np.linspace(-60 + 273.15, T_crit - 0.1, 100)
    h_liq = [CP.PropsSI("H", "T", t, "Q", 0, refrigerante)/1000 for t in T_range]
    p_liq = [CP.PropsSI("P", "T", t, "Q", 0, refrigerante)/100000 for t in T_range]
    h_vap = [CP.PropsSI("H", "T", t, "Q", 1, refrigerante)/1000 for t in T_range]
    p_vap = [CP.PropsSI("P", "T", t, "Q", 1, refrigerante)/100000 for t in T_range]
    return h_liq, p_liq, h_vap, p_vap

# --- CÁLCULO ---
try:
    resultados = simular_refrigerador(t_ambiente, t_interior, flujo_masico)
    scalar = resultados["scalar"]
    states = resultados["states"]

    # --- METRICAS CLAVE ---
    st.markdown("### 📊 Métricas Clave")
    col1, col2, col3, col4 = st.columns(4)
    
    col1.metric("COP del Ciclo", f"{scalar['COP']:.2f}")
    col2.metric("Trabajo Compresor", f"{scalar['Trabajo_Compresor_kW']:.2f} kW")
    col3.metric("Calor Extraído", f"{scalar['Calor_Extraido_kW']:.2f} kW")
    col4.metric("Temp. Descarga", f"{scalar['Temp_Descarga_C']:.1f} °C")

    st.markdown("---")
    
    # --- LAYOUT DE 2 COLUMNAS ---
    col_left, col_right = st.columns([1, 1])
    
    with col_left:
        # --- GRÁFICO P-h ---
        st.markdown("### 📈 Diagrama P-h")
        
        # Obtener datos de la campana (cacheados - no recalcula cada vez)
        h_liq, p_liq, h_vap, p_vap = calcular_campana_saturacion()

        fig_ph = go.Figure()
        fig_ph.add_trace(go.Scatter(x=h_liq, y=p_liq, mode='lines', name='Líquido Sat', line=dict(color='blue', width=1)))
        fig_ph.add_trace(go.Scatter(x=h_vap, y=p_vap, mode='lines', name='Vapor Sat', line=dict(color='red', width=1)))

        cycle_points = [1, 2, 3, 4, 1]
        h_cycle = [states[p]["h"]/1000 for p in cycle_points]
        p_cycle = [states[p]["P"]/100000 for p in cycle_points]
        txt_cycle = [f"E{p}" for p in cycle_points]
        
        fig_ph.add_trace(go.Scatter(x=h_cycle, y=p_cycle, mode='lines+markers+text', name='Ciclo', 
                                 text=txt_cycle, textposition="top center",
                                 line=dict(color='black', width=3, dash='solid'),
                                 marker=dict(size=8, color='black')))
        

        fig_ph.update_layout(
            xaxis_title="Entalpía (kJ/kg)",
            yaxis_title="Presión (bar)",
            yaxis_type="log",
            height=450,
            template="plotly_white",
            paper_bgcolor="white", # Fondo blanco forzado
            plot_bgcolor="white",  # Fondo del gráfico blanco forzado
            font=dict(color="black"), # Texto negro forzado
            xaxis=dict(gridcolor="lightgrey", linecolor="black"),
            yaxis=dict(gridcolor="lightgrey", linecolor="black"),
            margin=dict(l=20, r=20, t=30, b=20),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        
        # Agregamos borde negro al gráfico usando shapes
        fig_ph.add_shape(
            type="rect",
            xref="paper", yref="paper",
            x0=0, y0=0, x1=1, y1=1,
            line=dict(color="black", width=2),
        )

        st.plotly_chart(fig_ph, use_container_width=True)

    with col_right:
        # --- ESQUEMA DINÁMICO ---
        st.markdown("### 🔄 Esquema del Ciclo")
        fig_schematic = create_cycle_schematic(states)
        
        # Ajustes estéticos para asegurar fondo blanco y borde en cualquier modo
        fig_schematic.update_layout(
             paper_bgcolor="white",
             plot_bgcolor="white",
             font=dict(color="black")
        )
        # Borde
        fig_schematic.add_shape(
            type="rect",
            xref="paper", yref="paper",
            x0=0, y0=0, x1=1, y1=1,
            line=dict(color="black", width=2),
        )

        st.plotly_chart(fig_schematic, use_container_width=True)

    # --- TABLA DE DETALLES ---
    st.markdown("---")
    with st.expander("📋 Detalles Termodinámicos (Expandir)", expanded=False):
        data = []
        for s_id in [1, 2, 3, 4]:
            s = states[s_id]
            data.append({
                "Estado": s_id,
                "Descripción": s["desc"],
                "Presión (bar)": f"{s['P']/100000:.3f}",
                "Temperatura (°C)": f"{s['T']-273.15:.2f}",
                "Entalpía (kJ/kg)": f"{s['h']/1000:.2f}",
                "Entropía (kJ/kg·K)": f"{s['s']/1000:.3f}"
            })
        st.table(pd.DataFrame(data))

except Exception as e:
    st.error(f"Ocurrió un error en el cálculo: {e}")
    st.warning("Verifica que los inputs sean consistentes.")
