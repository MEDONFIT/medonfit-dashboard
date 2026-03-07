import uuid
import io
from datetime import date, datetime

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
import gspread
from google.oauth2.service_account import Credentials

# =====================================================
# CONFIG
# =====================================================
st.set_page_config(
    page_title="Med On Fit | Dashboard",
    page_icon="🏆",
    layout="wide"
)

LOGO_PATH = "logo_medonfit.jpg"
NOMBRE_HOJA_REGISTRO = "Registro"
NOMBRE_HOJA_TIPOS = "Tipos"
NOMBRE_HOJA_ALUMNOS = "Alumnos"

COLUMNAS_REGISTRO = ["ID", "Fecha", "Alumno", "Tipo_Entrenamiento", "Puntaje"]
COLUMNAS_TIPOS = ["Tipo_Entrenamiento"]
COLUMNAS_ALUMNOS = ["Alumno"]

# =====================================================
# ESTILO DARK TIPO POWER BI
# =====================================================
st.markdown("""
<style>
    .stApp {
        background: linear-gradient(180deg, #0b1220 0%, #111827 100%);
        color: #e5e7eb;
    }

    .titulo-principal {
        font-size: 34px;
        font-weight: 800;
        color: #f9fafb;
        margin-bottom: 0px;
    }

    .subtitulo {
        font-size: 15px;
        color: #9ca3af;
        margin-top: 0px;
    }

    .mini-card {
        background: linear-gradient(145deg, #111827, #1f2937);
        border-radius: 16px;
        padding: 18px 16px;
        box-shadow: 0 4px 18px rgba(0, 0, 0, 0.35);
        border: 1px solid rgba(255,255,255,0.08);
        text-align: center;
        min-height: 120px;
    }

    .kpi-label {
        font-size: 13px;
        color: #9ca3af;
        margin-bottom: 6px;
    }

    .kpi-value {
        font-size: 28px;
        font-weight: 800;
        color: #ef4444;
        line-height: 1.1;
    }

    .leader-card {
        background: linear-gradient(135deg, #7f1d1d 0%, #991b1b 50%, #111827 100%);
        border-radius: 24px;
        padding: 26px;
        box-shadow: 0 10px 28px rgba(0, 0, 0, 0.35);
        border: 1px solid rgba(255,255,255,0.10);
        text-align: center;
        margin-bottom: 12px;
    }

    .leader-title {
        font-size: 18px;
        color: #fca5a5;
        font-weight: 700;
        margin-bottom: 10px;
        letter-spacing: 0.5px;
    }

    .leader-name {
        font-size: 38px;
        color: #ffffff;
        font-weight: 900;
        line-height: 1.05;
        margin-bottom: 10px;
    }

    .leader-score {
        font-size: 20px;
        color: #ffe4e6;
        font-weight: 700;
    }

    .section-title {
        font-size: 20px;
        font-weight: 800;
        color: #f9fafb;
        margin-bottom: 10px;
    }

    .stButton > button {
        border-radius: 12px !important;
        font-weight: 700 !important;
        background-color: #7f1d1d !important;
        color: white !important;
        border: 1px solid #991b1b !important;
    }

    .stDownloadButton > button {
        border-radius: 12px !important;
        font-weight: 700 !important;
    }

    div[data-testid="stDataFrame"] {
        border-radius: 14px;
        overflow: hidden;
    }

    .small-note {
        color: #9ca3af;
        font-size: 12px;
    }
</style>
""", unsafe_allow_html=True)

# =====================================================
# GOOGLE SHEETS
# =====================================================
@st.cache_resource
def get_gsheet_client():
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]

    creds_dict = {
        "type": st.secrets["gcp_service_account"]["type"],
        "project_id": st.secrets["gcp_service_account"]["project_id"],
        "private_key_id": st.secrets["gcp_service_account"]["private_key_id"],
        "private_key": st.secrets["gcp_service_account"]["private_key"],
        "client_email": st.secrets["gcp_service_account"]["client_email"],
        "client_id": st.secrets["gcp_service_account"]["client_id"],
        "auth_uri": st.secrets["gcp_service_account"]["auth_uri"],
        "token_uri": st.secrets["gcp_service_account"]["token_uri"],
        "auth_provider_x509_cert_url": st.secrets["gcp_service_account"]["auth_provider_x509_cert_url"],
        "client_x509_cert_url": st.secrets["gcp_service_account"]["client_x509_cert_url"],
        "universe_domain": st.secrets["gcp_service_account"].get("universe_domain", "googleapis.com"),
    }

    credentials = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    return gspread.authorize(credentials)


@st.cache_resource
def get_spreadsheet():
    client = get_gsheet_client()
    spreadsheet_name = st.secrets["google_sheets"]["spreadsheet_name"]
    return client.open(spreadsheet_name)


def get_or_create_worksheet(sheet_name, headers):
    sh = get_spreadsheet()

    try:
        ws = sh.worksheet(sheet_name)
    except gspread.WorksheetNotFound:
        ws = sh.add_worksheet(title=sheet_name, rows=2000, cols=max(len(headers), 10))
        ws.append_row(headers)

    current_headers = ws.row_values(1)
    if not current_headers:
        ws.append_row(headers)
    elif current_headers != headers:
        ws.clear()
        ws.append_row(headers)

    return ws

# =====================================================
# DATOS DESDE GOOGLE SHEETS
# =====================================================
def cargar_tipos():
    ws = get_or_create_worksheet(NOMBRE_HOJA_TIPOS, COLUMNAS_TIPOS)
    records = ws.get_all_records()

    if not records:
        return []

    df = pd.DataFrame(records)
    if "Tipo_Entrenamiento" not in df.columns:
        return []

    tipos = (
        df["Tipo_Entrenamiento"]
        .fillna("")
        .astype(str)
        .str.strip()
        .tolist()
    )
    return sorted(list({t for t in tipos if t != ""}))


def guardar_tipo(tipo):
    tipo = str(tipo).strip()
    if tipo == "":
        return

    tipos_actuales = cargar_tipos()
    if tipo.lower() in [t.lower() for t in tipos_actuales]:
        return

    ws = get_or_create_worksheet(NOMBRE_HOJA_TIPOS, COLUMNAS_TIPOS)
    ws.append_row([tipo])


def cargar_alumnos():
    ws = get_or_create_worksheet(NOMBRE_HOJA_ALUMNOS, COLUMNAS_ALUMNOS)
    records = ws.get_all_records()

    if not records:
        return []

    df = pd.DataFrame(records)
    if "Alumno" not in df.columns:
        return []

    alumnos = (
        df["Alumno"]
        .fillna("")
        .astype(str)
        .str.strip()
        .tolist()
    )
    return sorted(list({a for a in alumnos if a != ""}))


def guardar_alumno(alumno):
    alumno = str(alumno).strip()
    if alumno == "":
        return

    alumnos_actuales = cargar_alumnos()
    if alumno.lower() in [a.lower() for a in alumnos_actuales]:
        return

    ws = get_or_create_worksheet(NOMBRE_HOJA_ALUMNOS, COLUMNAS_ALUMNOS)
    ws.append_row([alumno])


def cargar_datos():
    ws = get_or_create_worksheet(NOMBRE_HOJA_REGISTRO, COLUMNAS_REGISTRO)
    records = ws.get_all_records()

    if not records:
        return pd.DataFrame(columns=COLUMNAS_REGISTRO)

    df = pd.DataFrame(records)

    for col in COLUMNAS_REGISTRO:
        if col not in df.columns:
            df[col] = pd.NA

    df = df[COLUMNAS_REGISTRO].copy()
    df["ID"] = df["ID"].fillna("").astype(str).str.strip()
    df["Fecha"] = pd.to_datetime(df["Fecha"], errors="coerce")
    df["Alumno"] = df["Alumno"].fillna("").astype(str).str.strip()
    df["Tipo_Entrenamiento"] = df["Tipo_Entrenamiento"].fillna("").astype(str).str.strip()
    df["Puntaje"] = pd.to_numeric(df["Puntaje"], errors="coerce").fillna(0)

    df = df.dropna(subset=["Fecha"])
    df = df[df["Alumno"] != ""].reset_index(drop=True)

    return df


def guardar_registro(fecha, alumno, tipo, puntaje):
    ws = get_or_create_worksheet(NOMBRE_HOJA_REGISTRO, COLUMNAS_REGISTRO)
    ws.append_row([
        str(uuid.uuid4())[:8],
        pd.to_datetime(fecha).strftime("%Y-%m-%d"),
        str(alumno).strip(),
        str(tipo).strip(),
        float(puntaje)
    ])


def eliminar_registros(ids):
    if not ids:
        return

    ws = get_or_create_worksheet(NOMBRE_HOJA_REGISTRO, COLUMNAS_REGISTRO)
    all_values = ws.get_all_values()

    if not all_values:
        return

    headers = all_values[0]
    data_rows = all_values[1:]

    if "ID" not in headers:
        return

    id_idx = headers.index("ID")
    rows_to_delete = []

    for i, row in enumerate(data_rows, start=2):
        row_id = row[id_idx] if id_idx < len(row) else ""
        if row_id in ids:
            rows_to_delete.append(i)

    for row_number in sorted(rows_to_delete, reverse=True):
        ws.delete_rows(row_number)

# =====================================================
# FUNCIONES AUXILIARES
# =====================================================
def preparar_periodos(df):
    out = df.copy()

    if out.empty:
        out["Mes"] = pd.Series(dtype="object")
        out["Mes_Label"] = pd.Series(dtype="object")
        out["Semana"] = pd.Series(dtype="object")
        return out

    out["Mes"] = out["Fecha"].dt.to_period("M").astype(str)
    out["Mes_Label"] = out["Fecha"].dt.strftime("%Y-%m")
    iso = out["Fecha"].dt.isocalendar()
    out["Semana"] = iso["year"].astype(str) + "-W" + iso["week"].astype(str).str.zfill(2)
    return out


def ranking_dinamico(df):
    if df.empty:
        return pd.DataFrame(columns=["Posición", "Alumno", "Puntaje Total"])

    ranking = (
        df.groupby("Alumno", as_index=False)["Puntaje"]
        .sum()
        .rename(columns={"Puntaje": "Puntaje Total"})
        .sort_values(by=["Puntaje Total", "Alumno"], ascending=[False, True])
        .reset_index(drop=True)
    )

    ranking["Posición"] = ranking["Puntaje Total"].rank(method="dense", ascending=False).astype(int)
    return ranking[["Posición", "Alumno", "Puntaje Total"]]


def ranking_mensual(df):
    if df.empty:
        return pd.DataFrame(columns=["Mes", "Alumno", "Puntaje Total", "Posición"])

    agg = (
        df.groupby(["Mes", "Alumno"], as_index=False)["Puntaje"]
        .sum()
        .rename(columns={"Puntaje": "Puntaje Total"})
    )

    agg = agg.sort_values(by=["Mes", "Puntaje Total", "Alumno"], ascending=[True, False, True])
    agg["Posición"] = agg.groupby("Mes")["Puntaje Total"].rank(method="dense", ascending=False).astype(int)
    return agg


def obtener_medalla(pos):
    if pos == 1:
        return "🥇"
    if pos == 2:
        return "🥈"
    if pos == 3:
        return "🥉"
    return ""


def convertir_excel_bytes(df):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Export")
    return output.getvalue()

# =====================================================
# CARGA BASE
# =====================================================
tipos = cargar_tipos()
alumnos = cargar_alumnos()
df_base = preparar_periodos(cargar_datos())

# =====================================================
# HEADER
# =====================================================
c1, c2 = st.columns([1, 4])

with c1:
    try:
        st.image(LOGO_PATH, width=170)
    except Exception:
        st.warning("No se encontró el logo. Guarda la imagen como 'logo_medonfit.jpg'.")

with c2:
    st.markdown('<p class="titulo-principal">Dashboard Med On Fit</p>', unsafe_allow_html=True)
    st.markdown(
        '<p class="subtitulo">Clínica Deportiva | Ranking dinámico, leaderboard, ranking mensual y análisis interactivo</p>',
        unsafe_allow_html=True
    )

st.divider()

# =====================================================
# SIDEBAR
# =====================================================
with st.sidebar:
    st.subheader("Filtros interactivos")

    if df_base.empty or df_base["Fecha"].dropna().empty:
        fecha_min = date.today()
        fecha_max = date.today()
    else:
        fecha_min = df_base["Fecha"].min().date()
        fecha_max = df_base["Fecha"].max().date()

    rango_fechas = st.date_input("Rango de fechas", value=(fecha_min, fecha_max))
    if isinstance(rango_fechas, tuple) and len(rango_fechas) == 2:
        fecha_ini, fecha_fin = rango_fechas
    else:
        fecha_ini, fecha_fin = fecha_min, fecha_max

    meses_disponibles = sorted(df_base["Mes"].dropna().unique().tolist()) if not df_base.empty else []
    mes_filtro = st.selectbox("Mes específico", ["Todos"] + meses_disponibles)

    alumnos_disponibles = sorted(df_base["Alumno"].dropna().unique().tolist()) if not df_base.empty else []
    filtro_alumnos = st.multiselect("Alumno", alumnos_disponibles)

    tipos_disponibles = sorted(df_base["Tipo_Entrenamiento"].dropna().unique().tolist()) if not df_base.empty else []
    filtro_tipos = st.multiselect("Tipo de entrenamiento", tipos_disponibles)

    top_n = st.slider("Top del ranking", min_value=3, max_value=20, value=10, step=1)

    if st.button("🔄 Actualizar datos", use_container_width=True):
        st.rerun()

    st.markdown("---")
    st.subheader("Nuevo registro")

    fecha = st.date_input("Fecha", value=datetime.today(), key="fecha_nueva")

    alumno_pick = st.selectbox(
        "Alumno",
        options=(alumnos + ["(Nuevo alumno)"]) if alumnos else ["(Nuevo alumno)"]
    )

    if alumno_pick == "(Nuevo alumno)":
        alumno = st.text_input("Nuevo alumno", placeholder="Ej: Juan Pérez")
    else:
        alumno = alumno_pick

    tipo_pick = st.selectbox(
        "Tipo de entrenamiento",
        options=(tipos + ["(Nuevo tipo de entrenamiento)"]) if tipos else ["(Nuevo tipo de entrenamiento)"]
    )

    if tipo_pick == "(Nuevo tipo de entrenamiento)":
        tipo = st.text_input("Nuevo tipo de entrenamiento", placeholder="Ej: Pilates Clínico")
    else:
        tipo = tipo_pick

    puntaje = st.number_input("Puntaje", min_value=0.0, step=1.0, value=0.0)

    if st.button("Guardar registro", use_container_width=True):
        if str(alumno).strip() == "":
            st.error("Debes ingresar un alumno.")
        elif str(tipo).strip() == "":
            st.error("Debes ingresar un tipo de entrenamiento.")
        else:
            guardar_alumno(str(alumno).strip())
            guardar_tipo(str(tipo).strip())
            guardar_registro(fecha, str(alumno).strip(), str(tipo).strip(), puntaje)
            st.success("Registro guardado correctamente.")
            st.rerun()

# =====================================================
# FILTROS
# =====================================================
df = df_base.copy()

if not df.empty:
    df = df[(df["Fecha"].dt.date >= fecha_ini) & (df["Fecha"].dt.date <= fecha_fin)]

if mes_filtro != "Todos" and not df.empty:
    df = df[df["Mes"] == mes_filtro]

if filtro_alumnos:
    df = df[df["Alumno"].isin(filtro_alumnos)]

if filtro_tipos:
    df = df[df["Tipo_Entrenamiento"].isin(filtro_tipos)]

ranking_full = ranking_dinamico(df)

if not ranking_full.empty:
    ranking_full = ranking_full.copy()
    ranking_full["Posición"] = ranking_full["Puntaje Total"].rank(method="dense", ascending=False).astype(int)

ranking = ranking_full[ranking_full["Posición"] <= top_n].copy() if not ranking_full.empty else ranking_full

ranking_mes = ranking_mensual(df_base)
if mes_filtro != "Todos" and not ranking_mes.empty:
    ranking_mes = ranking_mes[ranking_mes["Mes"] == mes_filtro]

# =====================================================
# KPIs
# =====================================================
if ranking_full.empty:
    top1_alumno = "-"
    top1_puntaje = 0
else:
    top1_alumno = ranking_full.iloc[0]["Alumno"]
    top1_puntaje = int(ranking_full.iloc[0]["Puntaje Total"])

total_registros = len(df)
total_alumnos = df["Alumno"].nunique() if not df.empty else 0
puntaje_total = int(df["Puntaje"].sum()) if not df.empty else 0
tipos_unicos = df["Tipo_Entrenamiento"].nunique() if not df.empty else 0

k1, k2, k3, k4 = st.columns(4)

with k1:
    st.markdown(f"""
    <div class="mini-card">
        <div class="kpi-label">🎯 PUNTAJE TOTAL</div>
        <div class="kpi-value">{puntaje_total}</div>
    </div>
    """, unsafe_allow_html=True)

with k2:
    st.markdown(f"""
    <div class="mini-card">
        <div class="kpi-label">📋 TOTAL REGISTROS</div>
        <div class="kpi-value">{total_registros}</div>
    </div>
    """, unsafe_allow_html=True)

with k3:
    st.markdown(f"""
    <div class="mini-card">
        <div class="kpi-label">👥 ALUMNOS ÚNICOS</div>
        <div class="kpi-value">{total_alumnos}</div>
    </div>
    """, unsafe_allow_html=True)

with k4:
    st.markdown(f"""
    <div class="mini-card">
        <div class="kpi-label">🏋️ TIPOS DE ENTRENAMIENTO</div>
        <div class="kpi-value">{tipos_unicos}</div>
    </div>
    """, unsafe_allow_html=True)

st.write("")

# =====================================================
# LEADERBOARD TOP 1
# =====================================================
st.markdown(f"""
<div class="leader-card">
    <div class="leader-title">🏆 TOP 1 GENERAL</div>
    <div class="leader-name">{top1_alumno}</div>
    <div class="leader-score">Puntaje acumulado: {top1_puntaje}</div>
</div>
""", unsafe_allow_html=True)

# =====================================================
# TABS
# =====================================================
tab1, tab2, tab3, tab4 = st.tabs([
    "📊 Dashboard Ejecutivo",
    "📅 Ranking Mensual",
    "🧾 Registros y eliminación",
    "⬇️ Exportación"
])

# =====================================================
# TAB 1 - DASHBOARD
# =====================================================
with tab1:
    c1, c2 = st.columns([1.25, 1.75])

    with c1:
        st.markdown('<div class="section-title">Ranking dinámico</div>', unsafe_allow_html=True)

        if ranking.empty:
            st.info("No hay datos para mostrar.")
        else:
            max_puntaje = ranking["Puntaje Total"].max() if ranking["Puntaje Total"].max() > 0 else 1

            ranking_show = ranking.copy()
            ranking_show["Medalla"] = ranking_show["Posición"].apply(obtener_medalla)
            ranking_show = ranking_show[["Medalla", "Posición", "Alumno", "Puntaje Total"]]

            st.dataframe(ranking_show, use_container_width=True, hide_index=True)

            st.markdown('<p class="small-note">Progreso por alumno</p>', unsafe_allow_html=True)
            for _, row in ranking.iterrows():
                pct = int((row["Puntaje Total"] / max_puntaje) * 100) if max_puntaje > 0 else 0
                medalla = obtener_medalla(int(row["Posición"]))
                st.write(f"{medalla} {int(row['Posición'])} | {row['Alumno']} — {int(row['Puntaje Total'])} pts")
                st.progress(max(0, min(pct, 100)))

    with c2:
        st.markdown('<div class="section-title">Puntaje total por alumno</div>', unsafe_allow_html=True)

        if ranking.empty:
            st.info("No hay datos para graficar.")
        else:
            fig_bar = px.bar(
                ranking.sort_values("Puntaje Total"),
                x="Puntaje Total",
                y="Alumno",
                orientation="h",
                text="Puntaje Total"
            )
            fig_bar.update_layout(
                height=520,
                xaxis_title="Puntaje acumulado",
                yaxis_title="Alumno",
                plot_bgcolor="#111827",
                paper_bgcolor="#111827",
                font=dict(color="#e5e7eb"),
                margin=dict(l=10, r=10, t=10, b=10),
                coloraxis_showscale=False
            )
            fig_bar.update_traces(textposition="outside")
            st.plotly_chart(fig_bar, use_container_width=True)

    c3, c4 = st.columns(2)

    with c3:
        st.markdown('<div class="section-title">Distribución por tipo de entrenamiento</div>', unsafe_allow_html=True)

        if df.empty:
            st.info("No hay datos para mostrar.")
        else:
            by_tipo = (
                df.groupby("Tipo_Entrenamiento", as_index=False)["Puntaje"]
                .sum()
                .sort_values("Puntaje", ascending=False)
            )

            fig_donut = px.pie(
                by_tipo,
                values="Puntaje",
                names="Tipo_Entrenamiento",
                hole=0.55
            )
            fig_donut.update_layout(
                height=420,
                plot_bgcolor="#111827",
                paper_bgcolor="#111827",
                font=dict(color="#e5e7eb"),
                margin=dict(l=10, r=10, t=10, b=10)
            )
            st.plotly_chart(fig_donut, use_container_width=True)

    with c4:
        st.markdown('<div class="section-title">Tendencia mensual de puntajes</div>', unsafe_allow_html=True)

        if df.empty:
            st.info("No hay datos para mostrar.")
        else:
            serie_mes = (
                df.groupby("Mes", as_index=False)["Puntaje"]
                .sum()
                .sort_values("Mes")
            )

            fig_line = go.Figure()
            fig_line.add_trace(go.Scatter(
                x=serie_mes["Mes"],
                y=serie_mes["Puntaje"],
                mode="lines+markers+text",
                text=serie_mes["Puntaje"],
                textposition="top center"
            ))
            fig_line.update_layout(
                height=420,
                xaxis_title="Mes",
                yaxis_title="Puntaje total",
                plot_bgcolor="#111827",
                paper_bgcolor="#111827",
                font=dict(color="#e5e7eb"),
                margin=dict(l=10, r=10, t=10, b=10)
            )
            st.plotly_chart(fig_line, use_container_width=True)

# =====================================================
# TAB 2 - RANKING MENSUAL
# =====================================================
with tab2:
    st.markdown('<div class="section-title">Ranking mensual automático</div>', unsafe_allow_html=True)

    if ranking_mes.empty:
        st.info("No hay datos para mostrar.")
    else:
        meses_rank = sorted(ranking_mes["Mes"].dropna().unique().tolist())
        mes_rank_sel = st.selectbox("Selecciona el mes para ver el ranking", meses_rank)

        rank_mes_view = ranking_mes[ranking_mes["Mes"] == mes_rank_sel].copy()
        rank_mes_view = rank_mes_view[rank_mes_view["Posición"] <= top_n].copy()
        rank_mes_view["Medalla"] = rank_mes_view["Posición"].apply(obtener_medalla)
        rank_mes_view = rank_mes_view[["Medalla", "Posición", "Alumno", "Puntaje Total"]]

        c1, c2 = st.columns([1.2, 1.8])

        with c1:
            st.dataframe(rank_mes_view, use_container_width=True, hide_index=True)

        with c2:
            fig_mes = px.bar(
                rank_mes_view.sort_values("Puntaje Total"),
                x="Puntaje Total",
                y="Alumno",
                orientation="h",
                text="Puntaje Total"
            )
            fig_mes.update_layout(
                height=480,
                xaxis_title="Puntaje mensual",
                yaxis_title="Alumno",
                plot_bgcolor="#111827",
                paper_bgcolor="#111827",
                font=dict(color="#e5e7eb"),
                margin=dict(l=10, r=10, t=10, b=10)
            )
            fig_mes.update_traces(textposition="outside")
            st.plotly_chart(fig_mes, use_container_width=True)

# =====================================================
# TAB 3 - REGISTROS Y ELIMINACIÓN
# =====================================================
with tab3:
    st.markdown('<div class="section-title">Detalle de registros</div>', unsafe_allow_html=True)

    if df_base.empty:
        st.info("No existen registros.")
    else:
        tabla = df_base.copy()
        tabla["Fecha"] = pd.to_datetime(tabla["Fecha"]).dt.strftime("%d-%m-%Y")
        tabla = tabla[["ID", "Fecha", "Alumno", "Tipo_Entrenamiento", "Puntaje"]].copy()
        tabla.insert(0, "Eliminar", False)

        edited = st.data_editor(
            tabla,
            use_container_width=True,
            hide_index=True,
            disabled=["ID", "Fecha", "Alumno", "Tipo_Entrenamiento", "Puntaje"],
            column_config={
                "Eliminar": st.column_config.CheckboxColumn("Eliminar"),
                "ID": st.column_config.TextColumn("ID"),
                "Fecha": st.column_config.TextColumn("Fecha"),
                "Alumno": st.column_config.TextColumn("Alumno"),
                "Tipo_Entrenamiento": st.column_config.TextColumn("Tipo"),
                "Puntaje": st.column_config.NumberColumn("Puntaje")
            },
            height=460
        )

        ids = edited.loc[edited["Eliminar"] == True, "ID"].tolist()

        c1, c2 = st.columns([1, 1])
        with c1:
            st.write(f"Registros seleccionados: **{len(ids)}**")
        with c2:
            confirmar = st.checkbox("Confirmo eliminación", value=False)

        if st.button("🗑️ Eliminar seleccionados", use_container_width=True, disabled=(not confirmar or len(ids) == 0)):
            eliminar_registros(ids)
            st.success("Registros eliminados correctamente.")
            st.rerun()

# =====================================================
# TAB 4 - EXPORTACIÓN
# =====================================================
with tab4:
    st.markdown('<div class="section-title">Exportación</div>', unsafe_allow_html=True)

    if df.empty:
        st.info("No hay datos para exportar.")
    else:
        c1, c2, c3 = st.columns(3)

        with c1:
            st.download_button(
                "⬇️ Descargar detalle filtrado",
                data=convertir_excel_bytes(df[["Fecha", "Alumno", "Tipo_Entrenamiento", "Puntaje"]].copy()),
                file_name="detalle_medonfit.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )

        with c2:
            st.download_button(
                "⬇️ Descargar ranking actual",
                data=convertir_excel_bytes(ranking.copy()),
                file_name="ranking_medonfit.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )

        with c3:
            st.download_button(
                "⬇️ Descargar ranking mensual",
                data=convertir_excel_bytes(ranking_mes.copy()),
                file_name="ranking_mensual_medonfit.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )