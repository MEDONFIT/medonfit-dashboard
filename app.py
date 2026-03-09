import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import date
from pathlib import Path

# =========================
# CONFIGURACIÓN GENERAL
# =========================
st.set_page_config(
    page_title="Med On Fit | Dashboard de Ranking",
    page_icon="🏋️",
    layout="wide"
)

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

HOJA_REGISTRO = "Registro"
HOJA_TIPOS = "Tipos"

COLUMNAS_REGISTRO = ["ID", "Fecha", "Alumno", "Tipo_Entrenamiento", "Puntaje"]
COLUMNAS_TIPOS = ["Tipo_Entrenamiento", "Puntaje"]


# =========================
# CONEXIÓN GOOGLE SHEETS
# =========================
@st.cache_resource
def conectar_gsheet():
    creds_dict = dict(st.secrets["gcp_service_account"])
    creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
    client = gspread.authorize(creds)

    # IMPORTANTE: usar SHEET_ID en Secrets
    sh = client.open_by_key(st.secrets["SHEET_ID"])
    return sh


def get_or_create_worksheet(nombre_hoja, columnas, rows=200, cols=10):
    sh = conectar_gsheet()

    try:
        ws = sh.worksheet(nombre_hoja)
    except gspread.WorksheetNotFound:
        ws = sh.add_worksheet(title=nombre_hoja, rows=rows, cols=cols)
        ws.append_row(columnas)

    # validar encabezados
    try:
        headers = ws.row_values(1)
    except Exception:
        headers = []

    if not headers:
        ws.clear()
        ws.append_row(columnas)
    elif headers != columnas:
        ws.clear()
        ws.append_row(columnas)

    return ws


# =========================
# CARGA DE DATOS
# =========================
def cargar_tipos():
    ws = get_or_create_worksheet(HOJA_TIPOS, COLUMNAS_TIPOS, rows=100, cols=5)

    try:
        values = ws.get_all_values()
    except Exception as e:
        st.error(f"Error al leer la hoja '{HOJA_TIPOS}': {e}")
        return pd.DataFrame(columns=COLUMNAS_TIPOS)

    if not values or len(values) <= 1:
        return pd.DataFrame(columns=COLUMNAS_TIPOS)

    headers = values[0]
    data = values[1:]
    df = pd.DataFrame(data, columns=headers)

    for col in COLUMNAS_TIPOS:
        if col not in df.columns:
            df[col] = ""

    df = df[COLUMNAS_TIPOS].copy()
    df["Tipo_Entrenamiento"] = df["Tipo_Entrenamiento"].astype(str).str.strip()
    df["Puntaje"] = pd.to_numeric(df["Puntaje"], errors="coerce").fillna(0).astype(int)
    df = df[df["Tipo_Entrenamiento"] != ""].reset_index(drop=True)

    return df


def cargar_registro():
    ws = get_or_create_worksheet(HOJA_REGISTRO, COLUMNAS_REGISTRO, rows=2000, cols=10)

    try:
        values = ws.get_all_values()
    except Exception as e:
        st.error(f"Error al leer la hoja '{HOJA_REGISTRO}': {e}")
        return pd.DataFrame(columns=COLUMNAS_REGISTRO)

    if not values or len(values) <= 1:
        return pd.DataFrame(columns=COLUMNAS_REGISTRO)

    headers = values[0]
    data = values[1:]
    df = pd.DataFrame(data, columns=headers)

    for col in COLUMNAS_REGISTRO:
        if col not in df.columns:
            df[col] = ""

    df = df[COLUMNAS_REGISTRO].copy()
    df["ID"] = pd.to_numeric(df["ID"], errors="coerce").fillna(0).astype(int)
    df["Fecha"] = pd.to_datetime(df["Fecha"], errors="coerce")
    df["Alumno"] = df["Alumno"].astype(str).str.strip()
    df["Tipo_Entrenamiento"] = df["Tipo_Entrenamiento"].astype(str).str.strip()
    df["Puntaje"] = pd.to_numeric(df["Puntaje"], errors="coerce").fillna(0).astype(int)

    df = df[df["Alumno"] != ""].reset_index(drop=True)
    return df


def guardar_registro(fecha, alumno, tipo_entrenamiento, puntaje):
    ws = get_or_create_worksheet(HOJA_REGISTRO, COLUMNAS_REGISTRO, rows=2000, cols=10)
    df_actual = cargar_registro()

    nuevo_id = 1 if df_actual.empty else int(df_actual["ID"].max()) + 1

    nueva_fila = [
        nuevo_id,
        str(fecha),
        alumno,
        tipo_entrenamiento,
        int(puntaje)
    ]

    ws.append_row(nueva_fila, value_input_option="USER_ENTERED")


# =========================
# UTILIDADES
# =========================
def obtener_puntaje_por_tipo(df_tipos, tipo):
    fila = df_tipos[df_tipos["Tipo_Entrenamiento"] == tipo]
    if fila.empty:
        return 0
    return int(fila.iloc[0]["Puntaje"])


def mostrar_logo():
    posibles_rutas = [
        "logo_medonfit.png",
        "logo.png",
        "Logo.png"
    ]
    for ruta in posibles_rutas:
        if Path(ruta).exists():
            st.image(ruta, width=180)
            return


# =========================
# ESTILO
# =========================
st.markdown("""
    <style>
    .main-title {
        font-size: 34px;
        font-weight: 800;
        margin-bottom: 5px;
    }
    .sub-title {
        color: #666;
        margin-bottom: 20px;
    }
    .kpi-card {
        padding: 18px;
        border-radius: 16px;
        background: #f7f9fc;
        border: 1px solid #e5e7eb;
        text-align: center;
    }
    .kpi-title {
        font-size: 15px;
        color: #6b7280;
        margin-bottom: 6px;
    }
    .kpi-value {
        font-size: 28px;
        font-weight: 800;
    }
    </style>
""", unsafe_allow_html=True)


# =========================
# CABECERA
# =========================
col_logo, col_titulo = st.columns([1, 4])

with col_logo:
    mostrar_logo()

with col_titulo:
    st.markdown('<div class="main-title">Dashboard Med On Fit</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-title">Registro de entrenamientos y ranking de alumnos</div>', unsafe_allow_html=True)


# =========================
# CARGA DE DATOS
# =========================
try:
    tipos = cargar_tipos()
    registro = cargar_registro()
except Exception as e:
    st.error("No se pudo conectar correctamente a Google Sheets.")
    st.exception(e)
    st.stop()


# =========================
# SIDEBAR - REGISTRO
# =========================
st.sidebar.header("Nuevo Registro")

if tipos.empty:
    st.sidebar.warning("La hoja 'Tipos' está vacía. Debes cargar tipos y puntajes en Google Sheets.")
else:
    fecha = st.sidebar.date_input("Fecha", value=date.today())

    alumnos_existentes = []
    if not registro.empty:
        alumnos_existentes = sorted(registro["Alumno"].dropna().astype(str).str.strip().unique().tolist())

    opcion_alumno = st.sidebar.radio(
        "Selecciona cómo ingresar el alumno",
        ["Elegir de la lista", "Escribir nuevo alumno"]
    )

    if opcion_alumno == "Elegir de la lista" and alumnos_existentes:
        alumno = st.sidebar.selectbox("Alumno", alumnos_existentes)
    else:
        alumno = st.sidebar.text_input("Nombre del alumno").strip()

    lista_tipos = tipos["Tipo_Entrenamiento"].tolist()
    tipo_entrenamiento = st.sidebar.selectbox("Tipo de entrenamiento", lista_tipos)

    puntaje = obtener_puntaje_por_tipo(tipos, tipo_entrenamiento)
    st.sidebar.metric("Puntaje asignado", puntaje)

    if st.sidebar.button("Guardar registro", use_container_width=True):
        if not alumno:
            st.sidebar.error("Debes ingresar el nombre del alumno.")
        else:
            try:
                guardar_registro(fecha, alumno, tipo_entrenamiento, puntaje)
                st.sidebar.success("Registro guardado correctamente.")
                st.rerun()
            except Exception as e:
                st.sidebar.error("No se pudo guardar el registro.")
                st.sidebar.exception(e)


# =========================
# RESUMEN Y RANKING
# =========================
if registro.empty:
    st.info("Aún no hay registros cargados.")
else:
    ranking = (
        registro.groupby("Alumno", as_index=False)["Puntaje"]
        .sum()
        .sort_values("Puntaje", ascending=False)
        .reset_index(drop=True)
    )
    ranking["Posición"] = ranking.index + 1
    ranking = ranking[["Posición", "Alumno", "Puntaje"]]

    top_10 = ranking.head(10)

    mejor_alumno = top_10.iloc[0]["Alumno"] if not top_10.empty else "-"
    mejor_puntaje = int(top_10.iloc[0]["Puntaje"]) if not top_10.empty else 0
    total_registros = len(registro)
    total_alumnos = registro["Alumno"].nunique()

    c1, c2, c3, c4 = st.columns(4)

    with c1:
        st.markdown(
            f'<div class="kpi-card"><div class="kpi-title">🏆 Mejor Alumno</div><div class="kpi-value">{mejor_alumno}</div></div>',
            unsafe_allow_html=True
        )
    with c2:
        st.markdown(
            f'<div class="kpi-card"><div class="kpi-title">⭐ Puntaje Nº1</div><div class="kpi-value">{mejor_puntaje}</div></div>',
            unsafe_allow_html=True
        )
    with c3:
        st.markdown(
            f'<div class="kpi-card"><div class="kpi-title">📝 Total Registros</div><div class="kpi-value">{total_registros}</div></div>',
            unsafe_allow_html=True
        )
    with c4:
        st.markdown(
            f'<div class="kpi-card"><div class="kpi-title">👥 Total Alumnos</div><div class="kpi-value">{total_alumnos}</div></div>',
            unsafe_allow_html=True
        )

    st.markdown("### Top 10 alumnos")
    st.dataframe(top_10, use_container_width=True, hide_index=True)

    st.markdown("### Puntaje acumulado por alumno")
    chart_df = ranking.set_index("Alumno")["Puntaje"]
    st.bar_chart(chart_df)

    st.markdown("### Registro completo")
    vista_registro = registro.copy()
    vista_registro["Fecha"] = vista_registro["Fecha"].dt.strftime("%Y-%m-%d")
    st.dataframe(vista_registro, use_container_width=True, hide_index=True)