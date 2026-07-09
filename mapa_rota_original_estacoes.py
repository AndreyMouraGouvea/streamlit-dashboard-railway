import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

# ── Route cities (south → north) ──────────────────────────────
ROUTE_CITIES = [
    ('Cajati',           -24.7358, -48.1228),
    ('Registro',         -24.4971, -47.8449),
    ('Juquiá',           -24.3208, -47.6347),
    ('Miracatu',         -24.2814, -47.4625),
    ('Pedro de Toledo',  -24.2747, -47.2328),
    ('Itariri',          -24.2892, -47.1744),
    ('Peruíbe',          -24.3129, -47.0012),
    ('Itanhaém',         -24.1856, -46.7889),
    ('Praia Grande',     -24.0058, -46.4028),
    ('Santos (Porto)',   -23.9608, -46.3336),
    ('Cubatão',          -23.8916, -46.4240),
    ('São Paulo',        -23.5553, -46.6121),
    ('Barra Funda',      -23.5245, -46.6650),
]


# ── SP State Boundary ─────────────────────────────────────────
def load_sp_state():
    cache_path = Path('sp_boundary.geojson')
    if cache_path.exists():
        try:
            import geopandas as gpd
            return gpd.read_file(cache_path)
        except Exception:
            pass
    try:
        import geopandas as gpd
        import shutil
        from io import BytesIO
        from zipfile import ZipFile
        import requests
        url = (
            'https://geoftp.ibge.gov.br/'
            'organizacao_do_territorio/malhas_territoriais/'
            'malhas_municipais/municipio_2022/'
            'Brasil/BR/BR_UF_2022.zip'
        )
        r = requests.get(url, timeout=30)
        r.raise_for_status()
        tmp = Path('_tmp_sp_shp')
        tmp.mkdir(exist_ok=True)
        with BytesIO(r.content) as buf:
            with ZipFile(buf) as zf:
                zf.extractall(tmp)
        uf = gpd.read_file(tmp / 'BR_UF_2022.shp')
        col = 'SIGLA_UF' if 'SIGLA_UF' in uf.columns else 'SIGLA'
        sp = uf[uf[col] == 'SP'].to_crs(epsg=4326)
        sp.to_file(cache_path, driver='GeoJSON')
        shutil.rmtree(tmp)
        return sp
    except Exception:
        return None


# ── Dark-theme axis setup ─────────────────────────────────────
def setup_dark_ax(ax, title, xlabel='', ylabel=''):
    ax.set_facecolor('#0E1117')
    ax.tick_params(axis='both', colors='white', labelsize=14)
    ax.set_xlabel(xlabel, color='white', fontsize=16)
    ax.set_ylabel(ylabel, color='white', fontsize=16)
    ax.set_title(title, color='white', fontsize=22, fontweight='bold', pad=20)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['bottom'].set_color('#444444')
    ax.spines['left'].set_color('#444444')
    ax.grid(True, alpha=0.15, color='white', linestyle='--')


# ── Map Generation ────────────────────────────────────────────
def gerar_mapa_rota_estacoes(output='mapa_rota_original_estacoes.png'):
    lons = [c[2] for c in ROUTE_CITIES]
    lats = [c[1] for c in ROUTE_CITIES]

    fig, ax = plt.subplots(figsize=(20, 14))
    fig.patch.set_facecolor('#0E1117')
    setup_dark_ax(ax, 'ROTA ORIGINAL SANTOS–CAJATI — ESTAÇÕES',
                  'Longitude', 'Latitude')

    # SP state boundary
    sp = load_sp_state()
    if sp is not None:
        sp.boundary.plot(ax=ax, color='#555555', linewidth=1.2, alpha=0.5, zorder=1)

    # Route line
    ax.plot(lons, lats, color='#FF8C00', linewidth=3.5,
            alpha=0.85, zorder=3)

    # All stations
    ax.scatter(lons, lats, s=160, c='#3186cc',
               edgecolors='white', linewidths=1, alpha=0.9, zorder=5)

    # Porto de Santos highlight
    santos_idx = 9  # 'Santos (Porto)'
    ax.scatter(lons[santos_idx], lats[santos_idx], s=450, c='#E63946',
               edgecolors='white', linewidths=2, marker='*', zorder=6)

    # Barra Funda highlight (final station)
    bf_idx = len(ROUTE_CITIES) - 1
    ax.scatter(lons[bf_idx], lats[bf_idx], s=300, c='#9B59B6',
               edgecolors='white', linewidths=2, marker='D', zorder=6)

    # Annotations
    for i, (name, lat, lon) in enumerate(ROUTE_CITIES):
        if name == 'Santos (Porto)':
            lbl = 'Porto de Santos'
        elif name == 'Barra Funda':
            lbl = 'Barra Funda'
        else:
            lbl = name
        ax.annotate(lbl, (lon, lat), xytext=(7, 7),
                    textcoords='offset points', fontsize=11,
                    color='white', fontweight='bold', alpha=0.95, zorder=7)

    # Distances between stations
    for i in range(len(ROUTE_CITIES) - 1):
        lat1, lon1 = ROUTE_CITIES[i][1], ROUTE_CITIES[i][2]
        lat2, lon2 = ROUTE_CITIES[i + 1][1], ROUTE_CITIES[i + 1][2]
        R = 6371.0
        dlat = np.radians(lat2 - lat1)
        dlon = np.radians(lon2 - lon1)
        a = (np.sin(dlat / 2) ** 2
             + np.cos(np.radians(lat1)) * np.cos(np.radians(lat2))
             * np.sin(dlon / 2) ** 2)
        dist_km = R * 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))
        mid_lat = (lat1 + lat2) / 2
        mid_lon = (lon1 + lon2) / 2
        ax.annotate(f'{dist_km:.0f} km', (mid_lon, mid_lat),
                    xytext=(0, -18), textcoords='offset points',
                    fontsize=8, color='#aaaaaa',
                    ha='center', alpha=0.7, zorder=4)

    # Legend
    legend_elements = [
        Line2D([0], [0], color='#FF8C00', lw=4, label='Rota Santos–Cajati'),
        Line2D([0], [0], marker='o', color='w', markerfacecolor='#3186cc',
               markersize=10, label='Estação'),
        Line2D([0], [0], marker='*', color='w', markerfacecolor='#E63946',
               markersize=12, label='Porto de Santos'),
        Line2D([0], [0], marker='D', color='w', markerfacecolor='#9B59B6',
               markersize=10, label='Barra Funda (final)'),
    ]
    ax.legend(handles=legend_elements, loc='lower left',
              facecolor='#1a1a2e', edgecolor='#444444',
              labelcolor='white', fontsize=12)

    # Map bounds
    pad_lon = (max(lons) - min(lons)) * 0.10
    pad_lat = (max(lats) - min(lats)) * 0.10
    ax.set_xlim(min(lons) - pad_lon, max(lons) + pad_lon)
    ax.set_ylim(min(lats) - pad_lat, max(lats) + pad_lat)
    ax.set_aspect(1.3)

    plt.tight_layout()
    fig.savefig(output, dpi=180, bbox_inches='tight', facecolor=fig.get_facecolor())
    plt.close(fig)
    print(f'  [OK] {output} gerado')


if __name__ == '__main__':
    gerar_mapa_rota_estacoes()
