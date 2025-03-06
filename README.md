# Comparador de Tarifes

Aplicación web desarrollada con Streamlit para la comparación de tarifas energéticas (electricidad y gas) y análisis de consumo.

## 📋 Descripción

Esta aplicación permite a los usuarios:
- Comparar diferentes tarifas eléctricas
- Visualizar curvas de carga de consumo eléctrico
- Comparar tarifas de gas
- Ver un ranking energético de proveedores

## 🔧 Requisitos e instalación

```bash
# Clonar el repositorio
git clone https://github.com/tu-usuario/Comp_Tarifes.git
cd Comp_Tarifes

# Crear entorno virtual (opcional pero recomendado)
python -m venv env
source env/bin/activate  # En Windows: env\Scripts\activate

# Instalar dependencias
pip install -r requirements.txt

# Ejecutar la aplicación
streamlit run app.py
```

## 📁 Estructura del proyecto

```
Comp_Tarifes/
│
├── app.py                  # Punto de entrada principal
├── config.py               # Configuración de la aplicación
├── verificar_db.py         # Verificación de base de datos
├── ranking_energetica.py   # Módulo de ranking energético
├── actualizar_periodos_tarifas.py # Actualización de periodos de tarifas
│
├── tar_elec/               # Módulo de tarifas eléctricas
│   ├── tarifes_electricas.py  # Interfaz de tarifas eléctricas
│   ├── tarifas_db.py       # Acceso a DB para tarifas eléctricas
│   ├── calculos_tarifas.py # Cálculos de costes eléctricos
│   └── inicializar_discriminacion_horaria.py # Gestión de discriminación horaria
│
├── tar_gas/                # Módulo de tarifas de gas
│   └── tarifes_gas.py      # Gestión de tarifas de gas
│
├── Tar_Graf/               # Módulo de gráficos y visualizaciones
│   ├── corba_carrega.py    # Visualización de curva de carga
│   └── utils.py            # Utilidades para gráficos
│
└── assets/                 # Recursos estáticos (imágenes, etc.)
    └── logo.png
```

## 🚀 Funcionalidades

### Tarifas Eléctricas
Comparación y análisis de diferentes tarifas eléctricas disponibles en el mercado.

### Curva de Carga
Visualización y análisis de los patrones de consumo eléctrico.

### Tarifas de Gas
Comparación de diferentes ofertas y tarifas de gas natural.

### Ranking Energético
Clasificación de proveedores energéticos según diversos criterios de calidad y precio.

## 💡 Uso

1. Inicie la aplicación con `streamlit run app.py`
2. Utilice el menú lateral para navegar entre las diferentes secciones
3. En cada sección, complete los formularios según sus necesidades específicas
4. Analice los resultados mostrados en tablas y gráficos

## 📫 Contacto y Contribución

Para contribuir al proyecto:
1. Haga fork del repositorio
2. Cree una rama para su característica (`git checkout -b feature/nueva-caracteristica`)
3. Haga commit de sus cambios (`git commit -am 'Añadir nueva característica'`)
4. Haga push a la rama (`git push origin feature/nueva-caracteristica`)
5. Abra un Pull Request

## 📄 Licencia

Este proyecto está bajo la licencia MIT - vea el archivo [LICENSE.md](LICENSE.md) para más detalles.
