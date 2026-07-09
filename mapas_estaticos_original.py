import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
from matplotlib.lines import Line2D
from matplotlib.collections import LineCollection
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

# ── Route coordinates (from coordenadas.csv) ────────────────
ROUTE_CITIES = [
    ('SAO PAULO/SP', -23.5553, -46.6121),
    ('CUBATAO/SP', -23.8916, -46.4240),
    ('SANTOS/SP', -23.9608, -46.3336),
    ('SAO VICENTE/SP', -23.9631, -46.3919),
    ('PRAIA GRANDE/SP', -24.0058, -46.4028),
    ('MONGAGUA/SP', -24.0948, -46.6208),
    ('ITANHAEM/SP', -24.1856, -46.7889),
    ('PERUIBE/SP', -24.3129, -47.0012),
    ('ITARIRI/SP', -24.2892, -47.1744),
    ('PEDRO DE TOLEDO/SP', -24.2747, -47.2328),
    ('MIRACATU/SP', -24.2814, -47.4625),
    ('JUQUIA/SP', -24.3208, -47.6347),
    ('REGISTRO/SP', -24.4971, -47.8449),
    ('JACUPIRANGA/SP', -24.6925, -48.0022),
    ('CAJATI/SP', -24.7358, -48.1228),
    ('CURITIBA/PR', -25.43055, -49.26646),
]
ROUTE_CITY_NAMES = set(c[0] for c in ROUTE_CITIES)
ROUTE_COORDS = [(c[1], c[2]) for c in ROUTE_CITIES]  # (lat, lon)

# Reference-only stations (coordinates exist, no railway data)
REFERENCE_NAMES = {'MONGAGUA/SP', 'ITARIRI/SP', 'PEDRO DE TOLEDO/SP', 'JUQUIA/SP'}


# ── SP State Boundary (shared helper) ────────────────────────
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


# ── Data Loading ──────────────────────────────────────────────
def load_data():
    rail = pd.read_excel('dataRailway.xlsx')
    for col in ['ponto_origem_viagem', 'ponto_destino_viagem',
                 'tipo_servico', 'tipo_gratuidade']:
        rail[col] = rail[col].str.strip().str.upper()
    return rail


def build_route_index():
    df = pd.DataFrame(ROUTE_CITIES, columns=['cidade', 'latitude', 'longitude'])
    df['norm'] = df['cidade'].str.strip().str.upper()
    return df


# ── Plotting Helpers ─────────────────────────────────────────
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


def add_sp_state(ax):
    sp = load_sp_state()
    if sp is not None:
        sp.boundary.plot(ax=ax, color='#555555', linewidth=1.2, alpha=0.6, zorder=1)
        return True
    return False


def add_route_line(ax, color='#FF8C00', lw=3, alpha=0.7, label=None):
    lons = [c[2] for c in ROUTE_CITIES]
    lats = [c[1] for c in ROUTE_CITIES]
    ax.plot(lons, lats, color=color, linewidth=lw, alpha=alpha,
            label=label, zorder=3)


def haversine_km(lat1, lon1, lat2, lon2):
    R = 6371.0
    dlat = np.radians(lat2 - lat1)
    dlon = np.radians(lon2 - lon1)
    a = (np.sin(dlat / 2) ** 2
         + np.cos(np.radians(lat1)) * np.cos(np.radians(lat2))
         * np.sin(dlon / 2) ** 2)
    return R * 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))


# ── Map 1: Passenger Flow Map ────────────────────────────────
def gerar_mapa_fluxo_passageiros(rail, output='mapa_fluxo_passageiros.png'):
    route_idx = build_route_index()
    city_coords = dict(zip(route_idx['cidade'],
                           zip(route_idx['longitude'], route_idx['latitude'])))

    intra = rail[
        rail['ponto_origem_viagem'].isin(ROUTE_CITY_NAMES) &
        rail['ponto_destino_viagem'].isin(ROUTE_CITY_NAMES)
    ].copy()
    intra = intra[intra['ponto_origem_viagem'] != intra['ponto_destino_viagem']]

    agg = intra.groupby(['ponto_origem_viagem', 'ponto_destino_viagem']).agg(
        bilhetes=('quantidade_bilhetes', 'sum'),
    ).reset_index()

    for col in ['ponto_origem_viagem', 'ponto_destino_viagem']:
        agg[col] = agg[col].str.strip().str.upper()

    min_tix = agg['bilhetes'].max() / 5000
    max_tix = agg['bilhetes'].max()

    fig, ax = plt.subplots(figsize=(20, 14))
    fig.patch.set_facecolor('#0E1117')
    setup_dark_ax(ax, 'FLUXO DE PASSAGEIROS — ROTA ORIGINAL SANTOS–CAJATI',
                  'Longitude', 'Latitude')

    add_sp_state(ax)
    add_route_line(ax, color='#555555', lw=2, alpha=0.3)

    north_count = 0
    south_count = 0
    for _, row in agg.iterrows():
        orig = row['ponto_origem_viagem']
        dest = row['ponto_destino_viagem']
        if orig not in city_coords or dest not in city_coords:
            continue
        ox, oy = city_coords[orig]
        dx, dy = city_coords[dest]
        tickets = row['bilhetes']
        if tickets <= 0:
            continue

        is_north = dy > oy
        route_color = '#00B4D8' if is_north else '#FF8C00'
        if is_north:
            north_count += tickets
        else:
            south_count += tickets

        lw = 0.3 + 5.0 * (np.log10(max(tickets, min_tix)) - np.log10(min_tix)) / (
            np.log10(max_tix) - np.log10(min_tix)
        )
        frac = (np.log10(max(tickets, min_tix)) - np.log10(min_tix)) / (
            np.log10(max_tix) - np.log10(min_tix)
        )
        frac = np.clip(frac, 0, 1)
        alpha = 0.10 + 0.50 * frac

        t = np.linspace(0, 1, 50)
        mx, my = (ox + dx) / 2, (oy + dy) / 2
        dix, diy = dx - ox, dy - oy
        dist = np.hypot(dix, diy)
        curvature = 0.0005 * dist
        cpx = mx - diy * curvature
        cpy = my + dix * curvature
        bx = (1 - t) ** 2 * ox + 2 * (1 - t) * t * cpx + t ** 2 * dx
        by = (1 - t) ** 2 * oy + 2 * (1 - t) * t * cpy + t ** 2 * dy
        ax.plot(bx, by, color=route_color, linewidth=lw,
                alpha=alpha, zorder=2)

    # Station volume
    station_vol = intra.groupby('ponto_origem_viagem')['quantidade_bilhetes'].sum()
    station_data = []
    for cname, clat, clon in ROUTE_CITIES:
        vol = station_vol.get(cname, 0)
        station_data.append((cname, clon, clat, vol))

    sd = pd.DataFrame(station_data, columns=['cidade', 'lon', 'lat', 'vol'])
    vol_min = sd['vol'].max() / 200
    vol_max = sd['vol'].max()
    sizes = 30 + 200 * (
        np.log10(np.maximum(sd['vol'], vol_min)) - np.log10(vol_min)
    ) / (np.log10(vol_max) - np.log10(vol_min))

    has_data = sd['cidade'].isin(ROUTE_CITY_NAMES - REFERENCE_NAMES)
    ax.scatter(sd.loc[has_data, 'lon'], sd.loc[has_data, 'lat'],
               s=sizes[has_data], c='#3186cc', edgecolors='white',
               linewidths=0.6, alpha=0.85, zorder=5, label='Estação com dados')

    ref = sd[~has_data]
    if not ref.empty:
        ax.scatter(ref['lon'], ref['lat'], s=30, c='#555555',
                   edgecolors='#888888', linewidths=0.5,
                   alpha=0.6, zorder=4, marker='s', label='Estação (ref.)')

    # Label top 5 stations
    top5 = sd.nlargest(5, 'vol')
    for _, row in top5.iterrows():
        lbl = row['cidade'].split('/')[0][:14]
        ax.annotate(lbl, (row['lon'], row['lat']),
                    xytext=(7, 7), textcoords='offset points',
                    fontsize=12, color='white', fontweight='bold',
                    alpha=0.9, zorder=7)

    from matplotlib.patches import Patch
    legend_elements = [
        Line2D([0], [0], color='#00B4D8', lw=4,
               label=f'Sentido Norte (SP) — {north_count:,} passagens'),
        Line2D([0], [0], color='#FF8C00', lw=4,
               label=f'Sentido Sul (Curitiba) — {south_count:,} passagens'),
        Line2D([0], [0], marker='o', color='w', markerfacecolor='#3186cc',
               markersize=10, label='Estação com dados'),
        Patch(facecolor='#555555', edgecolor='#888888', label='Estação (referência)'),
    ]
    ax.legend(handles=legend_elements, loc='lower left',
              facecolor='#1a1a2e', edgecolor='#444444',
              labelcolor='white', fontsize=12)

    lons = [c[2] for c in ROUTE_CITIES]
    lats = [c[1] for c in ROUTE_CITIES]
    pad_lon = (max(lons) - min(lons)) * 0.12
    pad_lat = (max(lats) - min(lats)) * 0.08
    ax.set_xlim(min(lons) - pad_lon, max(lons) + pad_lon)
    ax.set_ylim(min(lats) - pad_lat, max(lats) + pad_lat)
    ax.set_aspect(1.2)

    plt.tight_layout()
    fig.savefig(output, dpi=180, bbox_inches='tight', facecolor=fig.get_facecolor())
    plt.close(fig)
    print(f'  [OK] {output} gerado')


# ── Map 2: Price Heatmap (along route) ──────────────────────
def gerar_mapa_calor_precos(rail, output='mapa_precos_trechos.png'):
    route_idx = build_route_index()

    intra = rail[
        rail['ponto_origem_viagem'].isin(ROUTE_CITY_NAMES) &
        rail['ponto_destino_viagem'].isin(ROUTE_CITY_NAMES)
    ].copy()

    # Average total fare per origin city (simple mean of media_valor_total)
    def city_avg_price(g):
        return g['media_valor_total'].mean()

    city_price = intra.groupby('ponto_origem_viagem').apply(city_avg_price).to_dict()

    # Build segment data: for each consecutive station pair, average their prices
    segments = []
    segment_prices = []
    for i in range(len(ROUTE_CITIES) - 1):
        c1, lat1, lon1 = ROUTE_CITIES[i]
        c2, lat2, lon2 = ROUTE_CITIES[i + 1]
        p1 = city_price.get(c1, np.nan)
        p2 = city_price.get(c2, np.nan)
        seg_price = np.nanmean([p1, p2])
        segments.append([(lon1, lat1), (lon2, lat2)])
        segment_prices.append(seg_price)

    # Station-level price for markers
    station_prices = []
    station_coords = []
    station_labels = []
    for cname, clat, clon in ROUTE_CITIES:
        p = city_price.get(cname, np.nan)
        station_prices.append(p)
        station_coords.append((clon, clat))
        lbl = cname.split('/')[0][:12]
        station_labels.append(lbl)

    fig, ax = plt.subplots(figsize=(20, 14))
    fig.patch.set_facecolor('#0E1117')
    setup_dark_ax(ax, 'PREÇO MÉDIO DAS PASSAGENS — ROTA ORIGINAL',
                  'Longitude', 'Latitude')

    add_sp_state(ax)
    add_route_line(ax, color='#555555', lw=2, alpha=0.3)

    # Colored segments
    seg_arr = np.array(segment_prices)
    valid_mask = ~np.isnan(seg_arr)
    if valid_mask.any():
        segs_valid = [segments[i] for i in range(len(segments)) if valid_mask[i]]
        prices_valid = seg_arr[valid_mask]
        lc = LineCollection(segs_valid, cmap='plasma', linewidth=10,
                            alpha=0.9, zorder=3)
        lc.set_array(prices_valid)
        lc.set_clim(prices_valid.min(), prices_valid.max())
        ax.add_collection(lc)
        cbar = fig.colorbar(lc, ax=ax, shrink=0.55, pad=0.02)
        cbar.set_label('Preço Médio (R$)', color='white', fontsize=15)
        cbar.ax.yaxis.set_major_formatter(ticker.FuncFormatter(lambda x, _: f'R$ {x:.2f}'))
        cbar.ax.tick_params(colors='white', labelsize=12)

    # Station markers colored by price
    sp_arr = np.array(station_prices)
    sp_valid = ~np.isnan(sp_arr)
    if sp_valid.any():
        sc = ax.scatter(
            [c[0] for c, v in zip(station_coords, sp_valid) if v],
            [c[1] for c, v in zip(station_coords, sp_valid) if v],
            c=sp_arr[sp_valid], cmap='plasma', s=220,
            edgecolors='white', linewidths=1.5,
            alpha=0.95, zorder=6, vmin=prices_valid.min(),
            vmax=prices_valid.max(),
        )

    # Reference stations (no data)
    ref_idx = [i for i, c in enumerate(ROUTE_CITIES)
               if c[0] in REFERENCE_NAMES]
    if ref_idx:
        ref_coords = [(ROUTE_CITIES[i][2], ROUTE_CITIES[i][1]) for i in ref_idx]
        ax.scatter([c[0] for c in ref_coords], [c[1] for c in ref_coords],
                   s=60, c='#555555', edgecolors='#888888',
                   linewidths=0.8, alpha=0.6, marker='s', zorder=4)

    # Label stations with prices
    for i in range(len(ROUTE_CITIES)):
        if sp_valid[i]:
            lbl = station_labels[i]
            p = station_prices[i]
            ax.annotate(f'{lbl}\nR$ {p:.0f}',
                        station_coords[i],
                        xytext=(10, 10), textcoords='offset points',
                        fontsize=11, color='white', fontweight='bold',
                        alpha=0.85, zorder=7)

    from matplotlib.patches import Patch
    legend_elements = [
        Patch(facecolor='#555555', edgecolor='#888888',
              label='Estação (referência)'),
    ]
    ax.legend(handles=legend_elements, loc='lower left',
              facecolor='#1a1a2e', edgecolor='#444444',
              labelcolor='white', fontsize=12)

    lons = [c[2] for c in ROUTE_CITIES]
    lats = [c[1] for c in ROUTE_CITIES]
    pad_lon = (max(lons) - min(lons)) * 0.12
    pad_lat = (max(lats) - min(lats)) * 0.08
    ax.set_xlim(min(lons) - pad_lon, max(lons) + pad_lon)
    ax.set_ylim(min(lats) - pad_lat, max(lats) + pad_lat)
    ax.set_aspect(1.2)

    plt.tight_layout()
    fig.savefig(output, dpi=180, bbox_inches='tight', facecolor=fig.get_facecolor())
    plt.close(fig)
    print(f'  [OK] {output} gerado')


# ── Main ──────────────────────────────────────────────────────
if __name__ == '__main__':
    for f in ['dataRailway.xlsx', 'coordenadas.csv']:
        if not Path(f).exists():
            print(f'ERRO: {f} não encontrado')
            exit(1)

    print('Carregando dados...')
    rail = load_data()
    print(f'  {len(rail)} registros de passagens')

    print('\nGerando mapa de fluxo de passageiros...')
    gerar_mapa_fluxo_passageiros(rail)

    print('\nGerando mapa de preços por trecho...')
    gerar_mapa_calor_precos(rail)

    print('\n[OK] Mapas gerados com sucesso!')
