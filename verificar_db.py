import streamlit as st
import os
import sqlite3
from sqlalchemy import text, create_engine
from datetime import datetime
import pandas as pd

# Variable global para seguir el estado de verificación
_DB_VERIFICADA = False

def get_festivos_nacionales(año):
    """Obtiene los festivos nacionales para un año específico"""
    festivos = {
        datetime(año, 1, 1).date(): "Año Nuevo",
        datetime(año, 1, 6).date(): "Epifanía del Señor",
        datetime(año, 5, 1).date(): "Fiesta del Trabajo",
        datetime(año, 8, 15).date(): "Asunción de la Virgen",
        datetime(año, 10, 12).date(): "Fiesta Nacional",
        datetime(año, 11, 1).date(): "Todos los Santos",
        datetime(año, 12, 6).date(): "Día de la Constitución",
        datetime(año, 12, 8).date(): "Inmaculada Concepción",
        datetime(año, 12, 25).date(): "Navidad"
    }
    
    return festivos

def inicializar_festivos(session):
    """Inicializa los días festivos nacionales para el año actual"""
    try:
        # Verificar si ya hay festivos para el año actual
        año_actual = datetime.now().year
        
        # Consulta adaptada a la nueva estructura de tabla
        query = text("""
            SELECT COUNT(*) FROM dias_festivos 
            WHERE fecha LIKE :patron
        """)
        
        result = session.execute(query, {"patron": f"%/{año_actual}"}).fetchone()
        
        if not result or result[0] == 0:
            # No hay festivos para el año actual, añadirlos
            festivos = [
                (f"01/01/{año_actual}", "Año Nuevo"),
                (f"06/01/{año_actual}", "Epifanía del Señor"),
                (f"19/03/{año_actual}", "San José"),
                (f"29/03/{año_actual}", "Viernes Santo"),  # Fecha variable, aproximada
                (f"01/05/{año_actual}", "Día del Trabajo"),
                (f"15/08/{año_actual}", "Asunción de la Virgen"),
                (f"12/10/{año_actual}", "Fiesta Nacional de España"),
                (f"01/11/{año_actual}", "Todos los Santos"),
                (f"06/12/{año_actual}", "Día de la Constitución"),
                (f"08/12/{año_actual}", "Inmaculada Concepción"),
                (f"25/12/{año_actual}", "Navidad")
            ]
            
            for fecha, descripcion in festivos:
                session.execute(text("""
                INSERT INTO dias_festivos (fecha, descripcion, periodo_asignado)
                VALUES (:fecha, :descripcion, 'valle')
                """), {"fecha": fecha, "descripcion": descripcion})
                
            print(f"Festivos de {año_actual} inicializados correctamente.")
        
        session.commit()
    except Exception as e:
        print(f"Error al inicializar festivos: {e}")
        import traceback
        traceback.print_exc()

def verificar_tablas_necesarias(conn):
    """Verifica que existan las tablas necesarias para la aplicación"""
    tablas_requeridas = [
        'consumos', 
        'tarifas_electricas', 
        'discriminacion_horaria',
        'tarifas_gas'
    ]
    
    with conn.session as s:
        tablas_existentes = s.execute(text("SELECT name FROM sqlite_master WHERE type='table'")).fetchall()
        tablas_existentes = [t[0] for t in tablas_existentes]
        
        for tabla in tablas_requeridas:
            if tabla not in tablas_existentes:
                return False
    
    return True

def verificar_y_corregir_bd():
    """
    Verifica que la base de datos tiene todas las tablas y columnas necesarias,
    las crea si no existen y migra datos si es necesario.
    """
    global _DB_VERIFICADA
    
    # Si ya verificamos la BD en esta ejecución, no repetir
    if _DB_VERIFICADA:
        return
    
    # Indicar que ya hemos verificado la BD
    _DB_VERIFICADA = True
    
    # Conectar con la BD a través de Streamlit
    conn = st.connection("energia_db", type="sql")
    
    with conn.session as s:
        # 1. Verificar tabla días festivos
        verificar_tabla_dias_festivos(s)
        
        # 2. Migrar datos de termino_energia si es necesario
        migrar_datos_termino_energia(s)
    
    # Opcional: Registrar verificación completa (solo una vez)
    print("Verificación inicial de la base de datos completada.")

def verificar_tabla_dias_festivos(session):
    """
    Verifica que existe la tabla de días festivos y la crea si no existe
    """
    # Verificar si existe la tabla
    try:
        result = session.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='dias_festivos'")).fetchone()
        
        if not result:
            # Si no existe, crear la tabla
            session.execute(text("""
                CREATE TABLE dias_festivos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    fecha TEXT NOT NULL,  -- Formato DD/MM/YYYY
                    descripcion TEXT,
                    periodo_asignado TEXT DEFAULT 'valle' CHECK(periodo_asignado IN ('punta', 'llano', 'valle'))
                )
            """))
            session.commit()
            
            # Insertar algunos festivos nacionales para el año actual
            anyo_actual = st.session_state.get('anyo_actual', 2024)
            festivos = [
                (f"01/01/{anyo_actual}", "Año Nuevo", "valle"),
                (f"06/01/{anyo_actual}", "Reyes Magos", "valle"),
                (f"01/05/{anyo_actual}", "Día del Trabajo", "valle"),
                (f"15/08/{anyo_actual}", "Asunción de la Virgen", "valle"),
                (f"12/10/{anyo_actual}", "Fiesta Nacional", "valle"),
                (f"01/11/{anyo_actual}", "Todos los Santos", "valle"),
                (f"06/12/{anyo_actual}", "Día de la Constitución", "valle"),
                (f"25/12/{anyo_actual}", "Navidad", "valle")
            ]
            
            for festivo in festivos:
                session.execute(
                    text("INSERT INTO dias_festivos (fecha, descripcion, periodo_asignado) VALUES (?, ?, ?)"),
                    festivo
                )
            session.commit()
    except Exception as e:
        print(f"Error en verificar_tabla_dias_festivos: {e}")
        import traceback
        traceback.print_exc()

def migrar_datos_termino_energia(session):
    """
    Migra datos de termino_energia a los nuevos campos específicos para discriminación horaria
    """
    try:
        # Verificar si hay tarifas que necesitan migración (término energía > 0 pero términos específicos son 0)
        result = session.execute(text("""
            SELECT COUNT(*) FROM tarifas_electricas 
            WHERE termino_energia > 0 
            AND (termino_energia_punta = 0 OR termino_energia_plana = 0 OR termino_energia_valle = 0)
        """)).fetchone()
        
        if result and result[0] > 0:
            # Migrar datos
            session.execute(text("""
                UPDATE tarifas_electricas 
                SET termino_energia_punta = termino_energia,
                    termino_energia_plana = termino_energia,
                    termino_energia_valle = termino_energia
                WHERE termino_energia > 0 
                AND (termino_energia_punta = 0 OR termino_energia_plana = 0 OR termino_energia_valle = 0)
            """))
            session.commit()
    except Exception as e:
        print(f"Error en migrar_datos_termino_energia: {e}")
        import traceback
        traceback.print_exc()

def corregir_tabla_festivos(session):
    """Corrige la estructura de la tabla de días festivos"""
    try:
        # Verificar si existe la tabla
        result = session.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='dias_festivos'")).fetchone()
        
        if result:
            # La tabla existe, verificar su estructura
            columns = session.execute(text("PRAGMA table_info(dias_festivos)")).fetchall()
            column_names = [col[1] for col in columns]
            
            # Si la tabla tiene una estructura incorrecta, recrearla
            if 'año' in column_names and 'fecha' not in column_names:
                print("Corrigiendo estructura de tabla dias_festivos...")
                
                # Guardar datos existentes si es posible
                try:
                    datos_festivos = session.execute(text("SELECT * FROM dias_festivos")).fetchall()
                except:
                    datos_festivos = []
                
                # Eliminar tabla existente
                session.execute(text("DROP TABLE dias_festivos"))
                
                # Crear tabla con estructura correcta
                session.execute(text("""
                CREATE TABLE dias_festivos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    fecha TEXT NOT NULL,  -- Formato DD/MM/YYYY
                    descripcion TEXT,
                    periodo_asignado TEXT DEFAULT 'valle' CHECK(periodo_asignado IN ('punta', 'llano', 'valle'))
                )
                """))
                
                # Si había datos, intentar migrarlos
                if datos_festivos:
                    for festivo in datos_festivos:
                        try:
                            # Convertir año a fecha completa (asumiendo 1 de enero)
                            año = festivo[1]  # posición de la columna año
                            fecha = f"01/01/{año}"  # formato DD/MM/YYYY
                            descripcion = festivo[2] if len(festivo) > 2 else f"Festivo {año}"
                            
                            session.execute(text("""
                            INSERT INTO dias_festivos (fecha, descripcion, periodo_asignado)
                            VALUES (:fecha, :descripcion, 'valle')
                            """), {"fecha": fecha, "descripcion": descripcion})
                        except:
                            pass
            
            # Si la tabla no tiene la columna periodo_asignado, añadirla
            elif 'periodo_asignado' not in column_names and 'fecha' in column_names:
                session.execute(text("""
                ALTER TABLE dias_festivos
                ADD COLUMN periodo_asignado TEXT DEFAULT 'valle' CHECK(periodo_asignado IN ('punta', 'llano', 'valle'))
                """))
        else:
            # La tabla no existe, crearla
            session.execute(text("""
            CREATE TABLE IF NOT EXISTS dias_festivos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fecha TEXT NOT NULL,  -- Formato DD/MM/YYYY
                descripcion TEXT,
                periodo_asignado TEXT DEFAULT 'valle' CHECK(periodo_asignado IN ('punta', 'llano', 'valle'))
            )
            """))
        
        session.commit()
        print("Verificación de tabla dias_festivos completada.")
    except Exception as e:
        print(f"Error al corregir tabla de festivos: {e}")
        import traceback
        traceback.print_exc()

def verificar_campos_tarifas(session):
    """Verifica y añade campos faltantes en la tabla de tarifas eléctricas"""
    try:
        # Verificar campos en tarifas_electricas
        columnas_info = session.execute(text("PRAGMA table_info(tarifas_electricas)")).fetchall()
        columnas = [col[1] for col in columnas_info]
        
        # Campos que deberían existir
        campos_requeridos = {
            'termino_energia_punta': 'REAL DEFAULT 0.0',
            'termino_energia_plana': 'REAL DEFAULT 0.0',
            'termino_energia_valle': 'REAL DEFAULT 0.0',
            'impuesto_electricidad': 'REAL DEFAULT 5.1126963',
            'parametro_adicional': 'TEXT DEFAULT ""'
        }
        
        # Añadir campos faltantes
        for campo, tipo in campos_requeridos.items():
            if campo not in columnas:
                query = f"ALTER TABLE tarifas_electricas ADD COLUMN {campo} {tipo}"
                session.execute(text(query))
                print(f"Campo añadido a tarifas_electricas: {campo}")
        
        # Migrar datos si es necesario
        if 'termino_energia' in columnas and 'termino_energia_punta' in columnas:
            # Copiar termino_energia a los campos específicos de período
            session.execute(text("""
            UPDATE tarifas_electricas 
            SET termino_energia_punta = termino_energia,
                termino_energia_plana = termino_energia,
                termino_energia_valle = termino_energia
            WHERE (termino_energia_punta = 0 OR termino_energia_punta IS NULL)
              AND termino_energia > 0
            """))
            print("Migración de datos de termino_energia completada.")
        
        session.commit()
    except Exception as e:
        print(f"Error al verificar campos de tarifas: {e}")
        import traceback
        traceback.print_exc()

# Si se ejecuta este script directamente
if __name__ == "__main__":
    verificar_y_corregir_bd()
