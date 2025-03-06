import streamlit as st
from config import APP_NAME, APP_ICON

# Debe ser lo primero que se ejecuta
st.set_page_config(
    page_title=APP_NAME, 
    page_icon=APP_ICON, 
    layout="wide"
)

# Resto de imports después de set_page_config
from streamlit_option_menu import option_menu
from Tar_Graf.corba_carrega import mostrar_corba_carrega
from tar_elec.tarifes_electricas import mostrar_tarifes_electricas
from tar_gas.tarifes_gas import mostrar_tarifes_gas
from ranking_energetica import mostrar_ranking_energetico  # Nueva importación
from verificar_db import verificar_y_corregir_bd  # Aquí se importa verificar_db.py

# Ahora verificamos la base de datos después de set_page_config
verificar_y_corregir_bd()  # Y aquí se ejecuta la función

# Sidebar
with st.sidebar:
    st.image("assets/logo.png", width=100)
    st.title("Comparador Tarifes")
    
    selected = option_menu(
        menu_title=None,
        options=["Tarifes Elèctriques", "Corba de Càrrega", "Tarifes Gas", "Ranking Energètic"],  # Añadida nueva opción
        icons=["lightning-charge", "graph-up", "fire", "trophy"],  # Añadido icono de trofeo
        default_index=0,
    )

# Navegación principal
if selected == "Tarifes Elèctriques":
    mostrar_tarifes_electricas()
elif selected == "Corba de Càrrega":
    mostrar_corba_carrega()
elif selected == "Ranking Energètic":  # Nueva condición
    mostrar_ranking_energetico()
else:
    mostrar_tarifes_gas()
