import streamlit as st
import pandas as pd
from sqlalchemy import text
from tar_elec.calculos_tarifas import calcular_coste_electricidad
from tar_gas.tarifes_gas import calcular_coste_gas
import time
from streamlit_echarts import st_echarts
from datetime import datetime
from functools import lru_cache  # Para caché de funciones

# Conexión a la base de datos
conn = st.connection("energia_db")

@lru_cache(maxsize=8)
def obtener_companias_cache(tipo='electricidad'):
    """Obtiene la lista de compañías con caché para reducir consultas a la BD"""
    try:
        tabla = "tarifas_electricas" if tipo == 'electricidad' else "tarifas_gas"
        query = f"SELECT DISTINCT companyia FROM {tabla} ORDER BY companyia"
        with conn.session as s:
            result = s.execute(text(query)).fetchall()
            return [r[0] for r in result]
    except Exception as e:
        st.error(f"Error al obtenir companyes: {str(e)}")
        return []

def obtener_companias_electricidad():
    """Obtiene la lista de compañías que ofrecen electricidad"""
    return obtener_companias_cache('electricidad')

def obtener_companias_gas():
    """Obtiene la lista de compañías que ofrecen gas"""
    return obtener_companias_cache('gas')

@lru_cache(maxsize=16)
def obtener_tarifas_por_compania_cache(compania, tipo, discriminacion=None):
    """Caché para consultas de tarifas por compañía"""
    try:
        if tipo == 'electricidad':
            query = """
            SELECT id, companyia, tarifa, potencia_contratada, tipo_discriminacion 
            FROM tarifas_electricas 
            WHERE companyia = :compania
            """
            
            # Filtrar por tipo de discriminación si se especifica
            if discriminacion == "Amb discriminació":
                query += " AND tipo_discriminacion = 'con_discriminacion'"
            elif discriminacion == "Sense discriminació":
                query += " AND tipo_discriminacion = 'sin_discriminacion'"
                
            with conn.session as s:
                result = s.execute(text(query), {"compania": compania}).fetchall()
                tarifas = [{
                    'id': r[0], 'companyia': r[1], 'tarifa': r[2], 
                    'potencia_contratada': r[3], 'tipo_discriminacion': r[4]
                } for r in result]
        else:  # gas
            query = "SELECT id, companyia, tarifa FROM tarifas_gas WHERE companyia = :compania"
            with conn.session as s:
                result = s.execute(text(query), {"compania": compania}).fetchall()
                tarifas = [{
                    'id': r[0], 'companyia': r[1], 'tarifa': r[2]
                } for r in result]
        
        return tarifas
    except Exception as e:
        st.error(f"Error al obtenir tarifes: {str(e)}")
        return []

def obtener_tarifas_electricidad_por_compania(compania, tipo_discriminacion="Totes"):
    """Obtiene las tarifas de electricidad de una compañía específica"""
    return obtener_tarifas_por_compania_cache(compania, 'electricidad', tipo_discriminacion)

def obtener_tarifas_gas_por_compania(compania):
    """Obtiene las tarifas de gas de una compañía específica"""
    return obtener_tarifas_por_compania_cache(compania, 'gas')

def obtener_tarifa_completa(tipo, tarifa_id):
    """Obtiene los datos completos de una tarifa"""
    try:
        with conn.session as s:
            tabla = "tarifas_electricas" if tipo == 'electricidad' else "tarifas_gas"
            query = text(f"SELECT * FROM {tabla} WHERE id = :id")
            result = s.execute(query, {"id": tarifa_id}).fetchone()
            
            if result:
                # Método seguro de convertir a diccionario
                try:
                    if hasattr(result, '_mapping'):
                        return dict(result._mapping)
                    else:
                        return dict(result)
                except:
                    # Método fallback
                    columns = s.execute(text(f"PRAGMA table_info({tabla})")).fetchall()
                    column_names = [col[1] for col in columns]
                    return {column_names[i]: result[i] for i in range(len(column_names)) if i < len(result)}
            return None
    except Exception as e:
        st.error(f"Error al obtener tarifa: {str(e)}")
        return None

def crear_tarifa_referencia(tipo, potencia=None):
    """Crea una tarifa de referencia (electricidad o gas)"""
    try:
        with conn.session as s:
            if tipo == 'electricidad':
                # Buscar primero si existe una tarifa marcada como actual
                query = text("""
                    SELECT id FROM tarifas_electricas 
                    WHERE tarifa LIKE '%(actual)%' LIMIT 1
                """)
                result = s.execute(query).fetchone()
                
                if result:
                    # Si existe, actualizarla y devolverla
                    tarifa_id = result[0]
                    if potencia:
                        s.execute(
                            text("UPDATE tarifas_electricas SET potencia_contratada = :potencia WHERE id = :id"),
                            {"potencia": potencia, "id": tarifa_id}
                        )
                        s.commit()
                    return obtener_tarifa_completa('electricidad', tarifa_id)
                else:
                    # Si no existe, ver si hay una tarifa de referencia
                    query = text("SELECT id FROM tarifas_electricas WHERE companyia = 'Tarifa Referencia' AND tarifa = 'PVPC'")
                    result = s.execute(query).fetchone()
                    
                    if result:
                        # Actualizar y devolver
                        tarifa_id = result[0]
                        s.execute(text("""
                            UPDATE tarifas_electricas SET 
                            potencia_contratada = :potencia,
                            tipo_discriminacion = 'con_discriminacion',
                            termino_potencia_punta = 30.67,
                            termino_potencia_valle = 1.42,
                            termino_energia_punta = 0.16,
                            termino_energia_plana = 0.10,
                            termino_energia_valle = 0.08,
                            alquiler_contador = 0.026630,
                            financiacion_bono_social = 0.012742,
                            descuento = 0.0,
                            impuesto_electricidad = 5.1126963,
                            iva = 21.0
                            WHERE id = :id
                        """), {'potencia': potencia, 'id': tarifa_id})
                    else:
                        # Crear nueva tarifa de referencia
                        s.execute(text("""
                            INSERT INTO tarifas_electricas (
                                companyia, tarifa, potencia_contratada, tipo_discriminacion, 
                                termino_potencia_punta, termino_potencia_valle, 
                                termino_energia_punta, termino_energia_plana, termino_energia_valle,
                                alquiler_contador, financiacion_bono_social, descuento,
                                impuesto_electricidad, iva
                            ) VALUES (
                                'Tarifa Referencia', 'PVPC', :potencia, 'con_discriminacion',
                                30.67, 1.42, 0.16, 0.10, 0.08, 0.026630, 0.012742, 0.000000,
                                5.1126963, 21.0
                            )
                        """), {'potencia': potencia})
                        result = s.execute(text("SELECT last_insert_rowid()")).fetchone()
                        tarifa_id = result[0]
                    
                    s.commit()
                    return obtener_tarifa_completa('electricidad', tarifa_id)
            else:  # gas
                # Buscar si existe una tarifa marcada como actual
                query = text("""
                    SELECT id FROM tarifas_gas 
                    WHERE tarifa LIKE '%(actual)%' LIMIT 1
                """)
                result = s.execute(query).fetchone()
                
                if result:
                    # Si existe, devolverla
                    tarifa_id = result[0]
                    return obtener_tarifa_completa('gas', tarifa_id)
                else:
                    # Ver si hay una tarifa de referencia
                    query = text("SELECT id FROM tarifas_gas WHERE companyia = 'Tarifa Referencia' AND tarifa = 'TUR'")
                    result = s.execute(query).fetchone()
                    
                    if result:
                        # Actualizar valores standard
                        tarifa_id = result[0]
                        s.execute(text("""
                            UPDATE tarifas_gas SET 
                            termino_fijo = 0.16,
                            termino_energia = 0.05,
                            descuento = 0.0,
                            alquiler_contador = 0.02,
                            impuesto_ieh = 0.00234,
                            iva = 21.0
                            WHERE id = :id
                        """), {'id': tarifa_id})
                    else:
                        # Crear nueva tarifa de referencia
                        s.execute(text("""
                            INSERT INTO tarifas_gas (
                                companyia, tarifa, termino_fijo, termino_energia,
                                descuento, alquiler_contador, impuesto_ieh, iva
                            ) VALUES (
                                'Tarifa Referencia', 'TUR', 0.16, 0.05, 0.0, 
                                0.02, 0.00234, 21.0
                            )
                        """))
                        result = s.execute(text("SELECT last_insert_rowid()")).fetchone()
                        tarifa_id = result[0]
                    
                    s.commit()
                    return obtener_tarifa_completa('gas', tarifa_id)
    except Exception as e:
        st.error(f"Error al crear tarifa de referencia: {str(e)}")
        import traceback
        st.error(traceback.format_exc())
        return None

def calcular_ranking_combinado(companias, consumo_elec, consumo_gas, potencia, tipo_discriminacion="Totes"):
    """Calcula el ranking combinado de electricidad y gas para las compañías seleccionadas"""
    # Inicializar lista de resultados
    resultados = []
    
    # Crear tarifas de referencia si es necesario
    tarifa_ref_elec = None
    tarifa_ref_gas = None
    if "Tarifa Referencia" in companias:
        tarifa_ref_elec = crear_tarifa_referencia('electricidad', potencia)
        tarifa_ref_gas = crear_tarifa_referencia('gas')
    
    # Procesar cada compañía
    for compania in companias:
        if compania == "Tarifa Referencia":
            if tarifa_ref_elec and tarifa_ref_gas:
                # Calcular coste eléctrico
                resultado_elec_ref = calcular_coste_electricidad(conn, [tarifa_ref_elec['id']])
                coste_elec = resultado_elec_ref[0]['total'] if resultado_elec_ref else 0
                
                # Calcular coste de gas
                resultado_gas_ref = calcular_coste_gas(tarifa_ref_gas, consumo_gas)
                
                # Procesar el resultado del gas (puede ser lista o diccionario)
                if isinstance(resultado_gas_ref, list) and len(resultado_gas_ref) > 0:
                    coste_gas = resultado_gas_ref[0]['total']
                else:
                    coste_gas = resultado_gas_ref['total'] if resultado_gas_ref else 0
                
                # Añadir resultado
                resultados.append({
                    'companyia': "Tarifa Actual",
                    'tarifa_elec': tarifa_ref_elec['tarifa'],
                    'coste_elec': coste_elec,
                    'tarifa_gas': tarifa_ref_gas['tarifa'],
                    'coste_gas': coste_gas,
                    'coste_total': coste_elec + coste_gas,
                    'es_referencia': True
                })
            continue
        
        # Procesar compañías regulares
        tarifas_elec = obtener_tarifas_electricidad_por_compania(compania, tipo_discriminacion)
        tarifas_gas = obtener_tarifas_gas_por_compania(compania)
        
        if not tarifas_elec or not tarifas_gas:
            continue
        
        # Encontrar mejor tarifa eléctrica
        mejor_tarifa_elec = procesar_mejor_tarifa_electrica(tarifas_elec, potencia)
        if not mejor_tarifa_elec:
            continue
            
        # Encontrar mejor tarifa gas
        mejor_tarifa_gas = procesar_mejor_tarifa_gas(tarifas_gas, consumo_gas)
        if not mejor_tarifa_gas:
            continue
        
        # Guardar resultado
        resultados.append({
            'companyia': compania,
            'tarifa_elec': mejor_tarifa_elec['tarifa'],
            'coste_elec': mejor_tarifa_elec['total'],
            'descuento_kwh_elec': mejor_tarifa_elec.get('descuento_kwh', 0),
            'tarifa_gas': mejor_tarifa_gas['tarifa'],
            'coste_gas': mejor_tarifa_gas['total'],
            'coste_total': mejor_tarifa_elec['total'] + mejor_tarifa_gas['total'],
            'es_referencia': False,
            'tipo_discriminacion': mejor_tarifa_elec.get('tipo_discriminacion', 'sin_discriminacion')
        })
    
    # Ordenar resultados por coste total
    return sorted(resultados, key=lambda x: x['coste_total'])

def procesar_mejor_tarifa_electrica(tarifas, potencia):
    """Procesa las tarifas eléctricas para encontrar la mejor"""
    mejor_tarifa = None
    menor_coste = float('inf')
    
    for tarifa in tarifas:
        # Ajustar la potencia contratada
        with conn.session as s:
            s.execute(
                text("UPDATE tarifas_electricas SET potencia_contratada = :potencia WHERE id = :id"),
                {"potencia": potencia, "id": tarifa['id']}
            )
            s.commit()
        
        # Calcular coste
        resultados = calcular_coste_electricidad(conn, [tarifa['id']])
        if resultados and len(resultados) > 0:
            coste = resultados[0]['total']
            if coste < menor_coste:
                menor_coste = coste
                mejor_tarifa = {
                    'id': tarifa['id'],
                    'tarifa': tarifa['tarifa'],
                    'total': coste,
                    'descuento_kwh': resultados[0].get('descuento_kwh', 0),
                    'tipo_discriminacion': tarifa.get('tipo_discriminacion', 'sin_discriminacion')
                }
    
    return mejor_tarifa

def procesar_mejor_tarifa_gas(tarifas, consumo):
    """Procesa las tarifas de gas para encontrar la mejor"""
    mejor_tarifa = None
    menor_coste = float('inf')
    
    for tarifa in tarifas:
        tarifa_completa = obtener_tarifa_completa('gas', tarifa['id'])
        if tarifa_completa:
            # Calcular coste
            resultado = calcular_coste_gas(tarifa_completa, consumo)
            
            if resultado:
                # Procesar el resultado (puede ser lista o diccionario)
                if isinstance(resultado, list) and len(resultado) > 0:
                    coste = resultado[0]['total']
                else:
                    coste = resultado['total']
                
                if coste < menor_coste:
                    menor_coste = coste
                    mejor_tarifa = {
                        'id': tarifa['id'],
                        'tarifa': tarifa['tarifa'],
                        'total': coste
                    }
    
    return mejor_tarifa

def preparar_datos_grafico(resultados):
    """Prepara los datos para el gráfico"""
    return {
        'companias': [r['companyia'] for r in resultados],
        'costes_elec': [r['coste_elec'] for r in resultados],
        'costes_gas': [r['coste_gas'] for r in resultados],
        'costes_total': [r['coste_total'] for r in resultados]
    }

def crear_configuracion_grafico(datos):
    """Crea la configuración para el gráfico"""
    # Preparar etiquetas destacando al ganador
    rich_labels = []
    for i, compania in enumerate(datos['companias']):
        if i == 0:  # La primera compañía (ya ordenada) es la mejor
            rich_labels.append({
                "value": compania,
                "textStyle": {
                    "fontWeight": "bold",
                    "backgroundColor": "#91cc75",
                    "padding": [3, 6],
                    "borderRadius": 3,
                    "color": "#fff"
                }
            })
        else:
            rich_labels.append(compania)
    
    # Configuración del gráfico
    return {
        "tooltip": {
            "trigger": "axis",
            "axisPointer": {"type": "shadow"}
        },
        "legend": {
            "data": ["Cost Electricitat", "Cost Gas"]
        },
        "grid": {
            "left": "22%",
            "right": "4%",
            "bottom": "3%",
            "containLabel": False
        },
        "xAxis": {
            "type": "value",
            "name": "Import (€)",
            "axisLabel": {"formatter": "{value} €"}
        },
        "yAxis": {
            "type": "category",
            "data": rich_labels,
            "axisLabel": {
                "width": 180,
                "overflow": "break",
                "interval": 0,
                "lineHeight": 15
            }
        },
        "series": [
            {
                "name": "Cost Electricitat",
                "type": "bar",
                "stack": "total",
                "label": {"show": True, "position": "inside", "formatter": "{c} €"},
                "data": [round(c, 2) for c in datos['costes_elec']]
            },
            {
                "name": "Cost Gas",
                "type": "bar",
                "stack": "total",
                "label": {"show": True, "position": "inside", "formatter": "{c} €"},
                "data": [round(c, 2) for c in datos['costes_gas']]
            }
        ],
        # Elemento gráfico para marcar la mejor oferta
        "graphic": [
            {
                "type": "group",
                "left": "5%",
                "top": "10%",
                "z": 100,
                "children": [
                    {
                        "type": "text",
                        "style": {
                            "text": "🏆 Millor oferta combinada",
                            "fontSize": 14,
                            "fontWeight": "bold",
                            "textFill": "#3a7d44"
                        }
                    }
                ]
            }
        ]
    }

def mostrar_tabla_resumen(resultados):
    """Muestra una tabla de resumen de los resultados"""
    st.subheader("Resum de costos anuals per companyia")
    
    df_resumen = pd.DataFrame({
        "Companyia": [r['companyia'] for r in resultados],
        "Tarifa Electricitat": [r['tarifa_elec'] for r in resultados],
        "Cost Electricitat": [r['coste_elec'] for r in resultados],
        "Tarifa Gas": [r['tarifa_gas'] for r in resultados],
        "Cost Gas": [r['coste_gas'] for r in resultados],
        "Cost Total": [r['coste_total'] for r in resultados],
        "Discriminació": [r.get('tipo_discriminacion', 'sin_discriminacion') == 'con_discriminacion' 
                         for r in resultados]
    })
    
    st.dataframe(
        df_resumen,
        hide_index=True,
        column_config={
            "Companyia": st.column_config.TextColumn("Companyia"),
            "Tarifa Electricitat": st.column_config.TextColumn("Tarifa Electricitat"),
            "Cost Electricitat": st.column_config.NumberColumn("Cost Electricitat", format="%.2f €"),
            "Tarifa Gas": st.column_config.TextColumn("Tarifa Gas"),
            "Cost Gas": st.column_config.NumberColumn("Cost Gas", format="%.2f €"),
            "Cost Total": st.column_config.NumberColumn("Cost Total", format="%.2f €"),
            "Discriminació": st.column_config.CheckboxColumn("Discriminació Horària")
        },
        use_container_width=True
    )

def mostrar_comparacion_referencia(resultados, ganador):
    """Muestra una comparación con la tarifa de referencia si existe"""
    tarifas_referencia = [r for r in resultados if r.get('es_referencia', False)]
    if tarifas_referencia and ganador['companyia'] != "Tarifa Actual":
        tarifa_ref = tarifas_referencia[0]
        ahorro = tarifa_ref['coste_total'] - ganador['coste_total']
        porcentaje = (ahorro / tarifa_ref['coste_total']) * 100
        
        st.info(f"""
        ### 💰 Comparació amb la teva tarifa actual
        
        - **Estalvi anual amb la millor oferta:** {ahorro:.2f}€ ({porcentaje:.2f}%)
        - **Cost anual tarifa actual:** {tarifa_ref['coste_total']:.2f}€
        - **Cost anual millor oferta:** {ganador['coste_total']:.2f}€
        """)

def mostrar_resultados_ranking(resultados, tipo_discriminacion="Totes"):
    """Muestra los resultados del ranking en forma de gráfico y tabla"""
    if not resultados:
        st.warning("No hi ha resultats per mostrar")
        return
    
    # Destacar el ganador
    ganador = resultados[0]
    
    # Mostrar subtítulo con tipo de discriminación si aplica
    subtitulo = f" ({tipo_discriminacion})" if tipo_discriminacion != "Totes" else ""
    
    # Mostrar mensaje de éxito con el ganador
    st.success(f"🏆 **Millor oferta combinada{subtitulo}:** {ganador['companyia']}\n\n" +
               f"Tarifa elèctrica: {ganador['tarifa_elec']} - {ganador['coste_elec']:.2f}€\n\n" + 
               f"Tarifa gas: {ganador['tarifa_gas']} - {ganador['coste_gas']:.2f}€\n\n" +
               f"**Cost total anual: {ganador['coste_total']:.2f}€**")
    
    # Preparar datos para gráfico
    datos_grafico = preparar_datos_grafico(resultados)
    
    # Crear y mostrar gráfico
    option = crear_configuracion_grafico(datos_grafico)
    st_echarts(options=option, height="500px")
    
    # Mostrar tabla de resumen
    mostrar_tabla_resumen(resultados)
    
    # Mostrar comparación con tarifa de referencia si existe
    mostrar_comparacion_referencia(resultados, ganador)

def mostrar_ranking_energetico():
    """Función principal que muestra la interfaz de usuario"""
    st.title("🏆 Ranking Energètic")
    st.write("Compara tarifes combinades d'electricitat i gas per trobar la millor oferta.")
    
    # Sidebar para filtros y opciones
    st.header("⚙️ Opcions")
    
    # Selector de compañías
    todas_electricidad = obtener_companias_electricidad()
    todas_gas = obtener_companias_gas()
    
    # Encontrar compañías que ofrecen ambos servicios
    companias_comunes = [c for c in todas_electricidad if c in todas_gas]
    companias_comunes.append("Tarifa Referencia")  # Añadir tarifa de referencia
    
    companias_seleccionadas = st.multiselect(
        "Selecciona companyies a comparar:", 
        options=companias_comunes,
        default=["Tarifa Referencia"] + companias_comunes[:3] if len(companias_comunes) > 3 else companias_comunes
    )
    
    # Parámetros de consumo
    st.subheader("Paràmetres de consum")
    
    # Potencia contratada
    potencia = st.slider(
        "Potència contractada (kW):", 
        min_value=1.0, max_value=10.0, value=5.75, step=0.05,
        help="Potència contractada en kiloWatts (kW)"
    )
    
    # Tipo de discriminación
    tipo_discriminacion = st.radio(
        "Tipus de discriminació horària:",
        options=["Totes", "Amb discriminació", "Sense discriminació"],
        help="Filtra per tarifes amb o sense discriminació horària"
    )
    
    # Consumo eléctrico anual
    consumo_electricidad = st.number_input(
        "Consum anual d'electricitat (kWh):", 
        min_value=500, max_value=10000, value=4232,
        help="Consum anual d'electricitat en kiloWatts hora (kWh)"
    )
    
    # Consumo gas anual
    consumo_gas = st.number_input(
        "Consum anual de gas (kWh):", 
        min_value=3000, max_value=15000, value=9273,
        help="Consum anual de gas en kiloWatts hora (kWh)"
    )
    
    # Botón para calcular
    if st.button("📊 Calcular Ranking"):
        if not companias_seleccionadas:
            st.warning("Si us plau, selecciona almenys una companyia per comparar.")
        else:
            with st.spinner("Calculant el ranking energètic..."):
                # Mostrar mensaje de procesamiento
                calculos_placeholder = st.empty()
                calculos_placeholder.info("Processant tarifes i calculant costos...")
                
                # Calcular ranking
                resultados = calcular_ranking_combinado(
                    companias_seleccionadas, 
                    consumo_electricidad, 
                    consumo_gas, 
                    potencia,
                    tipo_discriminacion
                )
                
                # Eliminar mensaje de procesamiento
                calculos_placeholder.empty()
                
                # Mostrar resultados
                if resultados:
                    mostrar_resultados_ranking(resultados, tipo_discriminacion)
                else:
                    st.error("No s'han pogut calcular resultats amb les dades proporcionades.")
    else:
        # Mensaje inicial
        st.info("""
        ### 📋 Instruccions
        1. Selecciona les companyies que vols comparar.
        2. Ajusta els paràmetres de consum (potència, kWh d'electricitat i gas).
        3. Fes clic a "Calcular Ranking" per veure els resultats.
        
        El sistema calcularà la millor combinació de tarifes per cada companyia.
        """)

# Ejecutar cuando se llama directamente a este script
if __name__ == "__main__":
    # Configuración de la página
    st.set_page_config(
        page_title="Ranking Energètic",
        page_icon="🏆",
        layout="wide"
    )
    
    mostrar_ranking_energetico()