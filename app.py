import folium
from folium.plugins import LocateControl
import streamlit as st
import pandas as pd
from streamlit_folium import st_folium

import numpy as np
from scipy.interpolate import griddata
import matplotlib.pyplot as plt
import base64
from io import BytesIO

# Configuración de la página
st.set_page_config(page_title="Mapa Climatología", layout="wide")
st.title("🌍 Mapa interactivo de Climatología")

# Botón para cargar archivo CSV
uploaded_file = st.file_uploader("📂 Cargar archivo CSV con columnas: lat, lon, value, date", type="csv")

# Crear mapa base con capa satelital de vegetación
m = folium.Map(location=[3.45, -76.53], zoom_start=8, tiles="Esri.WorldImagery")

# Control de localización estilo Google Maps
LocateControl(auto_start=False, flyTo=True, keepCurrentZoomLevel=False).add_to(m)

# Si se carga un archivo CSV
if uploaded_file is not None:
    df = pd.read_csv(uploaded_file)

    # Validación de columnas
    required_cols = {"lat", "lon", "value", "date"}
    if required_cols.issubset(df.columns):
        # 1) dibujar puntos originales
        for _, row in df.iterrows():
            folium.CircleMarker(
                location=[row["lat"], row["lon"]],
                radius=6,
                color="black",
                fill=True,
                fill_color="white",
                fill_opacity=0.9,
                popup=f"📍 Valor: {row['value']}<br>📅 Fecha: {row['date']}"
            ).add_to(m)

        # 2) interpolación (griddata)
        points = df[['lon', 'lat']].values
        values = df['value'].values

        # rejilla del mapa (ajusta 200 -> más resolución / más tiempo)
        grid_lon = np.linspace(df['lon'].min(), df['lon'].max(), 200)
        grid_lat = np.linspace(df['lat'].min(), df['lat'].max(), 200)
        grid_x, grid_y = np.meshgrid(grid_lon, grid_lat)

        grid_z = griddata(points, values, (grid_x, grid_y), method='linear')

        # 3) imagen con colormap azul->verde->amarillo->rojo
        fig, ax = plt.subplots(figsize=(6, 6), dpi=100)
        # 'RdYlBu_r' invertido hace azul=bajo, rojo=alto; otra opción: 'jet' o 'plasma'
        img = ax.imshow(
            grid_z,
            extent=(df['lon'].min(), df['lon'].max(), df['lat'].min(), df['lat'].max()),
            origin='lower',
            cmap="RdYlBu_r",
            alpha=0.6
        )
        ax.axis('off')

        # guardar PNG en memoria
        buf = BytesIO()
        plt.savefig(buf, format="png", bbox_inches="tight", pad_inches=0, transparent=True)
        plt.close(fig)
        b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
        img_url = f"data:image/png;base64,{b64}"

        bounds = [[df['lat'].min(), df['lon'].min()], [df['lat'].max(), df['lon'].max()]]
        folium.raster_layers.ImageOverlay(image=img_url, bounds=bounds, opacity=0.6, name="Interpolación").add_to(m)

        # añadir leyenda (simple)
        folium.LayerControl().add_to(m)

        # 4) botón para descargar la rejilla interpolada como CSV
        interp_df = pd.DataFrame({
            "lon": grid_x.ravel(),
            "lat": grid_y.ravel(),
            "value_interp": grid_z.ravel()
        })
        # eliminar NaNs
        interp_df = interp_df[~np.isnan(interp_df["value_interp"])]
        csv_bytes = interp_df.to_csv(index=False).encode("utf-8")
        st.download_button("⬇️ Descargar CSV interpolado", data=csv_bytes, file_name="interpolacion.csv", mime="text/csv")

    else:
        st.error("⚠️ El CSV debe contener las columnas: lat, lon, value, date")

# Mostrar mapa en Streamlit
st_data = st_folium(m, width=1200, height=700)
