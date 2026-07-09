import geopandas as gpd
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

# ── Constants ─────────────────────────────────────────────────
RAILWAY_ROUTE = [
    (-23.5553, -46.6121), (-23.8916, -46.4240), (-23.9608, -46.3336),
    (-23.9631, -46.3919), (-24.0058, -46.4028), (-24.0948, -46.6208),
    (-24.1856, -46.7889), (-24.3129, -47.0012), (-24.2892, -47.1744),
    (-24.2747, -47.2328), (-24.2814, -47.4625), (-24.3208, -47.6347),
    (-24.4971, -47.8449), (-24.6925, -48.0022), (-24.7358, -48.1228),
    (-25.43055, -49.26646),
]

# COMEX strategic cities (from dashboard)
STRATEGIC_CITIES = {
    'Sao Paulo':        (-23.5558, -46.6396),
    'Santos':           (-23.9592, -46.3318),
    'Cubatao':          (-23.8918, -46.4248),
    'Jundiai':          (-23.1857, -46.8892),
    'Vinhedo':          (-23.0263, -46.9819),
    'Valinhos':         (-22.9691, -46.9958),
    'Campinas':         (-22.9051, -47.0613),
    'Paulinia':         (-22.7411, -47.1743),
    'Guarulhos':        (-23.4597, -46.5329),
    'Sao Jose Campos':  (-23.2198, -45.8916),
    'Limeira':          (-22.5838, -47.4098),
    'Sao Carlos':       (-22.0123, -47.8908),
    'Araraquara':       (-21.7743, -48.1742),
    'Ribeirao Preto':   (-21.1694, -47.8111),
    'Registro':         (-24.4971, -47.8449),
    'Cajati':           (-24.7358, -48.1228),
    'Curitiba':         (-25.4305, -49.2665),
}

# Road groups matching the railway strategic routes
ROAD_GROUPS = [
    {
        'name': 'BR-116 (Regis Bittencourt) — Rota Original',
        'color': '#FF8C00',
        'roads': [],
        'source': 'federal',
        'codes': [116],
        'code_col': 'Codigo_BR',
    },
    {
        'name': 'SP-330 (Anhanguera) — Rota Estrategica',
        'color': '#E63946',
        'roads': ['330'],
        'source': 'estadual',
        'codes': ['330'],
    },
    {
        'name': 'SP-060 (Via Dutra) — Ramal Leste',
        'color': '#00B4D8',
        'roads': ['060'],
        'source': 'estadual',
        'codes': ['060'],
    },
    {
        'name': 'SP-310 + SP-326 — Ramal Interior',
        'color': '#06D6A0',
        'roads': ['310', '326'],
        'source': 'estadual',
        'codes': ['310', '326'],
    },
    {
        'name': 'SP-150 + SP-160 — Acesso ao Porto',
        'color': '#9B59B6',
        'roads': ['150', '160'],
        'source': 'estadual',
        'codes': ['150', '160'],
    },
    {
        'name': 'SP-055 (Padre Nobrega) — Litoral Sul',
        'color': '#FF6B6B',
        'roads': ['055'],
        'source': 'estadual',
        'codes': ['055'],
    },
]


# ── SP State Boundary ─────────────────────────────────────────
def load_sp_state():
    import geopandas as gpd
    cache_path = Path('sp_boundary.geojson')
    if cache_path.exists():
        try:
            return gpd.read_file(cache_path)
        except Exception:
            pass
    try:
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


# ── Road Data Loading ─────────────────────────────────────────
def load_roads():
    root = Path('.')
    est_shp = root / 'rodovias estaduais' / 'vw_cide_rod_2021.shp'
    fed_shp = root / 'rodovias federais' / 'vw_snv_rod.shp'

    if not est_shp.exists() or not fed_shp.exists():
        print('ERRO: Shapefiles nao encontrados nas pastas rodovias_*')
        return None, None

    est = gpd.read_file(est_shp)
    fed = gpd.read_file(fed_shp)

    # Filter to SP state segments
    est_sp = est[est['Codigo_SNV'].str.contains('ESP', na=False)].copy()
    fed_sp = fed[fed['Codigo_SNV'].str.contains('SP', na=False)].copy()

    return est_sp, fed_sp


def get_road_group_geoms(est_sp, fed_sp):
    """Extract and dissolve geometries for each road group."""
    groups = []
    for grp in ROAD_GROUPS:
        if grp['source'] == 'estadual':
            df = est_sp
            col = 'Codigo_Rod'
        else:
            df = fed_sp
            col = 'Codigo_BR'

        segs = []
        for code in grp['codes']:
            subset = df[df[col].astype(str) == str(code)].copy()
            if len(subset) > 0:
                segs.append(subset)
        if segs:
            combined = pd.concat(segs, ignore_index=True)
            groups.append({
                'name': grp['name'],
                'color': grp['color'],
                'geom': combined.geometry.unary_union,
                'km': combined['Extensao'].sum(),
                'segs': len(combined),
            })
        else:
            print(f'  AVISO: {grp["name"]} sem segmentos encontrados')

    return groups


# ── Plotting ──────────────────────────────────────────────────
def setup_dark_ax(ax, title):
    ax.set_facecolor('#0E1117')
    ax.tick_params(axis='both', colors='white', labelsize=14)
    ax.set_xlabel('Longitude', color='white', fontsize=16)
    ax.set_ylabel('Latitude', color='white', fontsize=16)
    ax.set_title(title, color='white', fontsize=22, fontweight='bold', pad=20)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['bottom'].set_color('#444444')
    ax.spines['left'].set_color('#444444')
    ax.grid(True, alpha=0.15, color='white', linestyle='--')


def gerar_mapa_rodoviario(output='mapa_rodoviario.png'):
    print('Carregando shapefiles...')
    est_sp, fed_sp = load_roads()
    if est_sp is None:
        return

    print('  Extraindo geometrias das rodovias...')
    groups = get_road_group_geoms(est_sp, fed_sp)
    for g in groups:
        print(f'    {g["name"]:40s} {g["segs"]:3d} segmentos, {g["km"]:.0f} km')

    fig, ax = plt.subplots(figsize=(22, 14))
    fig.patch.set_facecolor('#0E1117')
    setup_dark_ax(ax, 'MALHA RODOVIÁRIA ESTRATÉGICA — CONEXÕES AO PORTO DE SANTOS')

    # SP state
    sp = load_sp_state()
    if sp is not None:
        sp.boundary.plot(ax=ax, color='#555555', linewidth=1.2, alpha=0.5, zorder=1)

    # Railway route (reference, dashed)
    rr = np.array(RAILWAY_ROUTE)
    ax.plot(rr[:, 1], rr[:, 0], color='#888888', linewidth=1.5,
            alpha=0.4, linestyle='--', zorder=2)

    # Road groups
    road_kms = {}
    for grp in groups:
        geom = grp['geom']
        if geom is None or geom.is_empty:
            continue
        road_kms[grp['name']] = grp['km']
        if geom.geom_type == 'MultiLineString':
            for line in geom.geoms:
                xs, ys = line.xy
                ax.plot(xs, ys, color=grp['color'], linewidth=3.0,
                        alpha=0.85, zorder=4)
        elif geom.geom_type == 'LineString':
            xs, ys = geom.xy
            ax.plot(xs, ys, color=grp['color'], linewidth=3.0,
                    alpha=0.85, zorder=4)

    # Strategic cities
    city_names = list(STRATEGIC_CITIES.keys())
    city_lons = [c[1] for c in STRATEGIC_CITIES.values()]
    city_lats = [c[0] for c in STRATEGIC_CITIES.values()]

    ax.scatter(city_lons, city_lats, s=140, c='#3186cc',
               edgecolors='white', linewidths=0.8, alpha=0.9, zorder=6)

    # Port of Santos highlight
    santos_lon, santos_lat = STRATEGIC_CITIES['Santos'][1], STRATEGIC_CITIES['Santos'][0]
    ax.scatter(santos_lon, santos_lat, s=400, c='#E63946',
               edgecolors='white', linewidths=2, marker='*', zorder=7)

    # City labels
    for name, (lat, lon) in STRATEGIC_CITIES.items():
        if name == 'Curitiba':
            continue  # label outside map or smaller
        lbl = name[:14]
        ax.annotate(lbl, (lon, lat), xytext=(6, 6),
                    textcoords='offset points', fontsize=9,
                    color='white', fontweight='bold', alpha=0.85, zorder=7)

    # Curitiba label south
    clat, clon = STRATEGIC_CITIES['Curitiba']
    ax.annotate('Curitiba', (clon, clat), xytext=(6, 6),
                textcoords='offset points', fontsize=9,
                color='white', fontweight='bold', alpha=0.7, zorder=7)

    # Legend
    legend_elements = []
    for grp in groups:
        km = road_kms.get(grp['name'], 0)
        label = f"{grp['name']} ({km:.0f} km)"
        legend_elements.append(
            Line2D([0], [0], color=grp['color'], lw=4, label=label)
        )
    legend_elements.append(
        Line2D([0], [0], color='#888888', lw=2, linestyle='--',
               label='Ferrovia Santos-Cajati (ref.)')
    )
    legend_elements.append(
        Line2D([0], [0], marker='*', color='w', markerfacecolor='#E63946',
               markersize=12, label='Porto de Santos')
    )

    ax.legend(handles=legend_elements, loc='lower left',
              facecolor='#1a1a2e', edgecolor='#444444',
              labelcolor='white', fontsize=11)

    # Map bounds: focus on SP + neighboring areas
    all_lons = [c[1] for c in STRATEGIC_CITIES.values()]
    all_lats = [c[0] for c in STRATEGIC_CITIES.values()]
    pad_lon = (max(all_lons) - min(all_lons)) * 0.10
    pad_lat = (max(all_lats) - min(all_lats)) * 0.10
    ax.set_xlim(min(all_lons) - pad_lon, max(all_lons) + pad_lon)
    ax.set_ylim(min(all_lats) - pad_lat, max(all_lats) + pad_lat)
    ax.set_aspect(1.3)

    plt.tight_layout()
    fig.savefig(output, dpi=180, bbox_inches='tight', facecolor=fig.get_facecolor())
    plt.close(fig)
    print(f'  [OK] {output} gerado')


# ── Main ──────────────────────────────────────────────────────
if __name__ == '__main__':
    gerar_mapa_rodoviario()
