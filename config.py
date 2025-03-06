import os
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

# Rutas
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'datos_energia.db')
ASSETS_PATH = os.path.join(BASE_DIR, 'assets')

# Configuración de la base de datos
DB_SCHEMA = """
CREATE TABLE IF NOT EXISTS consumos (
    Id INTEGER PRIMARY KEY,
    Fecha TEXT,
    Hora TEXT,
    AE_kWh REAL,
    AI_kVArh REAL
);

CREATE TABLE IF NOT EXISTS tarifas_electricas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    companyia TEXT NOT NULL,
    tarifa TEXT NOT NULL,
    potencia_contratada REAL DEFAULT 3.3,
    tipo_discriminacion TEXT DEFAULT 'sin_discriminacion',
    termino_potencia_punta REAL DEFAULT 0.0,
    termino_potencia_valle REAL DEFAULT 0.0,
    termino_energia REAL DEFAULT 0.0,
    termino_energia_punta REAL DEFAULT 0.0,
    termino_energia_plana REAL DEFAULT 0.0,
    termino_energia_valle REAL DEFAULT 0.0,
    alquiler_contador REAL DEFAULT 0.0,
    financiacion_bono_social REAL DEFAULT 0.0,
    descuento REAL DEFAULT 0.0,
    parametro_adicional TEXT DEFAULT '',
    permanencia INTEGER DEFAULT 0,
    duracion_anios INTEGER DEFAULT 1,
    impuesto_electricidad REAL DEFAULT 5.113,
    iva REAL DEFAULT 21.0,
    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    fecha_actualizacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS discriminacion_horaria (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    dia_tipo TEXT CHECK(dia_tipo IN ('laborable', 'fin_de_semana_festivo')),
    hora_inicio INTEGER CHECK(hora_inicio >= 0 AND hora_inicio < 24),
    hora_fin INTEGER CHECK(hora_fin > 0 AND hora_fin <= 24),
    periodo TEXT CHECK(periodo IN ('punta', 'llano', 'valle'))
);

-- Nueva tabla para días festivos
CREATE TABLE IF NOT EXISTS dias_festivos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fecha TEXT NOT NULL,  -- Formato DD/MM/YYYY
    descripcion TEXT,
    periodo_asignado TEXT DEFAULT 'llano' CHECK(periodo_asignado IN ('punta', 'llano', 'valle'))
);

CREATE TABLE IF NOT EXISTS tarifas_gas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    companyia TEXT NOT NULL,
    tarifa TEXT NOT NULL,
    termino_fijo REAL DEFAULT 0.0,
    termino_energia REAL DEFAULT 0.0,
    alquiler_contador REAL DEFAULT 0.0,
    descuento REAL DEFAULT 0.0,
    impuesto_ieh REAL DEFAULT 0.00234,
    iva REAL DEFAULT 21.0,
    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    fecha_actualizacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

# Configuración de la aplicación
APP_NAME = "Comparador Tarifes Elèctriques/Gas"
APP_ICON = "⚡"
TIMEZONE = "Europe/Madrid"

def obtener_cambios_horario(año):
    """Retorna las fechas de cambio de horario para el año especificado"""
    # Cambio a horario de verano (último domingo de marzo)
    cambio_verano = datetime(año, 3, 31, tzinfo=ZoneInfo(TIMEZONE))
    while cambio_verano.weekday() != 6:  # 6 = domingo
        cambio_verano = cambio_verano - timedelta(days=1)
    
    # Cambio a horario de invierno (último domingo de octubre)
    cambio_invierno = datetime(año, 10, 31, tzinfo=ZoneInfo(TIMEZONE))
    while cambio_invierno.weekday() != 6:
        cambio_invierno = cambio_invierno - timedelta(days=1)
    
    return {
        'verano': cambio_verano.date(),      # 23 horas
        'invierno': cambio_invierno.date(),  # 25 horas
        'fechas_especiales': {
            cambio_verano.date(): 23,   # día con 23 horas
            cambio_invierno.date(): 25  # día con 25 horas
        }
    }

def es_fecha_cambio_horario(fecha, año=None):
    """Verifica si una fecha corresponde a un cambio de horario"""
    if año is None:
        año = fecha.year
    cambios = obtener_cambios_horario(año)
    return fecha in cambios['fechas_especiales']

def get_horas_del_dia(fecha):
    """Retorna el número de horas que debe tener un día específico"""
    año = fecha.year
    cambios = obtener_cambios_horario(año)
    return cambios['fechas_especiales'].get(fecha, 24)
