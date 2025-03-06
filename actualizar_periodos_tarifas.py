import streamlit as st
from sqlalchemy import text
import pandas as pd
from datetime import datetime

def actualizar_periodos_discriminacion():
    """
    Actualiza los periodos de discriminación horaria en la base de datos
    para que coincidan con la configuración estándar:
    
    - Horas valle: 00:00-08:00 en días laborables, 24h en fines de semana y festivos
    - Horas llano: 08:00-10:00, 14:00-18:00, 22:00-00:00 en días laborables
    - Horas punta: 10:00-14:00, 18:00-22:00 en días laborables
    """
    st.title("Actualización de Periodos de Discriminación Horaria")
    
    # Conectar a la base de datos
    conn = st.connection("energia_db", type="sql")
    
    # Mostrar la configuración actual
    st.subheader("Configuración Actual")
    with conn.session as s:
        df_actual = pd.read_sql_query(
            "SELECT dia_tipo, hora_inicio, hora_fin, periodo FROM discriminacion_horaria ORDER BY dia_tipo, hora_inicio",
            s.connection()
        )
    
    # Mostrar tabla actual
    if not df_actual.empty:
        # Formatear para mostrar
        df_display = df_actual.copy()
        df_display['Horario'] = df_display.apply(
            lambda x: f"{int(x['hora_inicio']):02d}:00 - {int(x['hora_fin']):02d}:00",
            axis=1
        )
        df_display['Tipo Día'] = df_display['dia_tipo'].map({
            'laborable': 'Laborable (L-V)',
            'fin_de_semana_festivo': 'Fin de semana y festivos'
        })
        df_display['Periodo'] = df_display['periodo'].map({
            'punta': '⚡ Punta',
            'llano': '🔋 Llano',
            'valle': '🌙 Valle'
        })
        
        st.dataframe(
            df_display[['Tipo Día', 'Horario', 'Periodo']],
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info("No hay configuración de discriminación horaria en la base de datos")
    
    # Definir la nueva configuración estándar CORREGIDA (0-23h) correcta (0-23h)
    config_laborables = [
        ('laborable', 0, 8, 'valle'),   # 00:00-07:59 Valle
        ('laborable', 8, 10, 'llano'),  # 08:00-09:59 Llano
        ('laborable', 10, 14, 'punta'), # 10:00-13:59 Punta
        ('laborable', 14, 18, 'llano'), # 14:00-17:59 Llano
        ('laborable', 18, 22, 'punta'), # 18:00-21:59 Punta
        ('laborable', 22, 24, 'llano'),  # 22:00-23:59 Llano (el sistema debe interpretar 24 como final de día) (corregido de 24 a 0)
    ]
    
    config_festivos = [
        ('fin_de_semana_festivo', 0, 24, 'valle')  # Todo el día Valle (el sistema debe interpretar 24 como final de día) (corregido de 24 a 23)
    ]
    
    # Ofrecer botón para actualizar
    if st.button("Actualizar a Configuración Estándar"):
        try:
            with conn.session as s:
                # Eliminar configuración actual
                s.execute(text("DELETE FROM discriminacion_horaria"))
                
                # Insertar nueva configuración - laborables
                for config in config_laborables:
                    s.execute(
                        text("""
                            INSERT INTO discriminacion_horaria (dia_tipo, hora_inicio, hora_fin, periodo)
                            VALUES (:dia_tipo, :hora_inicio, :hora_fin, :periodo)
                        """),
                        {
                            'dia_tipo': config[0],
                            'hora_inicio': config[1],
                            'hora_fin': config[2],
                            'periodo': config[3]
                        }
                    )
                
                # Insertar nueva configuración - festivos
                for config in config_festivos:
                    s.execute(
                        text("""
                            INSERT INTO discriminacion_horaria (dia_tipo, hora_inicio, hora_fin, periodo)
                            VALUES (:dia_tipo, :hora_inicio, :hora_fin, :periodo)
                        """),
                        {
                            'dia_tipo': config[0],
                            'hora_inicio': config[1],
                            'hora_fin': config[2],
                            'periodo': config[3]
                        }
                    )
                
                s.commit()
                st.success("✅ Configuración actualizada correctamente")
                
                # Mostrar nueva configuración
                df_nueva = pd.read_sql_query(
                    "SELECT dia_tipo, hora_inicio, hora_fin, periodo FROM discriminacion_horaria ORDER BY dia_tipo, hora_inicio",
                    s.connection()
                )
                
                # Formatear para mostrar
                df_display = df_nueva.copy()
                df_display['Horario'] = df_display.apply(
                    lambda x: f"{int(x['hora_inicio']):02d}:00 - {int(x['hora_fin']):02d}:00",
                    axis=1
                )
                df_display['Tipo Día'] = df_display['dia_tipo'].map({
                    'laborable': 'Laborable (L-V)',
                    'fin_de_semana_festivo': 'Fin de semana y festivos'
                })
                df_display['Periodo'] = df_display['periodo'].map({
                    'punta': '⚡ Punta',
                    'llano': '🔋 Llano',
                    'valle': '🌙 Valle'
                })
                
                st.subheader("Nueva Configuración")
                st.dataframe(
                    df_display[['Tipo Día', 'Horario', 'Periodo']],
                    use_container_width=True,
                    hide_index=True
                )
                
        except Exception as e:
            st.error(f"Error al actualizar la configuración: {str(e)}")
            import traceback
            st.error(traceback.format_exc())
    
    # Explicación de la configuración estándar
    with st.expander("ℹ️ Información sobre los periodos horarios"):
        st.markdown("""
        ### Periodos de Discriminación Horaria Estándar
        
        La configuración estándar define los siguientes periodos:
        
        #### 🌙 **Horas Valle** (las más económicas):
        - **Días laborables (L-V):** De 00:00 a 08:00
        - **Fines de semana y festivos nacionales:** Las 24 horas del día
        
        #### 🔋 **Horas Llano** (precio moderado):
        - **Días laborables (L-V): 
          * De 08:00 a 10:00
          * De 14:00 a 18:00 
          * De 22:00 a 00:00
        
        #### ⚡ **Horas Punta** (las menos económicas):
        - **Días laborables (L-V):**
          * De 10:00 a 14:00
          * De 18:00 a 22:00
        - **Fines de semana y festivos:** No hay horas punta
        """)
        
        st.info("Esta configuración corresponde a la tarifa 2.0TD estándar regulada por el mercado eléctrico español.")

# Ejecutar la aplicación cuando se ejecute este script
if __name__ == "__main__":
    actualizar_periodos_discriminacion()
