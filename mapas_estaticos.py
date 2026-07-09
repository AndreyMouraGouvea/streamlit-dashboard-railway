import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import matplotlib.tri as tri
from matplotlib.lines import Line2D
from matplotlib.path import Path
from matplotlib.patches import PathPatch
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

# ── Railway routes ───────────────────────────────────────────
RAILWAY_ROUTE = [
    (-23.5553, -46.6121), (-23.8916, -46.4240), (-23.9608, -46.3336),
    (-23.9631, -46.3919), (-24.0058, -46.4028), (-24.0948, -46.6208),
    (-24.1856, -46.7889), (-24.3129, -47.0012), (-24.2892, -47.1744),
    (-24.2747, -47.2328), (-24.2814, -47.4625), (-24.3208, -47.6347),
    (-24.4971, -47.8449), (-24.6925, -48.0022), (-24.7358, -48.1228),
    (-25.43055, -49.26646),
]
STRATEGIC_ROUTE = [
    (-23.1856528, -46.8892222), (-23.0263471, -46.9818714),
    (-22.9691172, -46.9958185), (-22.9050824, -47.0613327),
    (-22.7410508, -47.1743005),
]
BRANCH_SJC = [
    (-23.5553, -46.6121), (-23.4596858, -46.5328559),
    (-23.2198396, -45.8915658),
]
BRANCH_INTERIOR = [
    (-22.7410508, -47.1743005), (-22.5838179, -47.4097569),
    (-22.0123291, -47.8908261), (-21.7742763, -48.1742397),
    (-21.1694018, -47.8110855),
]

ROUTE_DEFS = [
    {'name': 'Rota Original',      'color': '#FF8C00', 'coords': RAILWAY_ROUTE},
    {'name': 'Rota Estratégica',   'color': '#E63946', 'coords': STRATEGIC_ROUTE},
    {'name': 'Ramal Leste (SJC)',  'color': '#00B4D8', 'coords': BRANCH_SJC},
    {'name': 'Ramal Interior (RP)','color': '#06D6A0', 'coords': BRANCH_INTERIOR},
]


# ── Data Loading ──────────────────────────────────────────────
def load_data():
    df = pd.read_csv('dados_comex_stat.csv')
    num_cols = [
        'valor_movimentado_2025', 'valor_movimentado_2026',
        'valor_movimentado_total', 'empregos_agropecuaria',
        'empregos_industria', 'empregos_construção',
        'empregos_comercio', 'empregos_servicos', 'total_empregos',
    ]
    for col in num_cols:
        if col in df.columns:
            df[col] = (
                df[col].astype(str)
                .str.replace('.', '', regex=False)
                .str.replace(',', '.', regex=False)
            )
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    df['industria_share'] = np.where(
        df['total_empregos'] > 0,
        df['empregos_industria'] / df['total_empregos'],
        np.nan,
    )
    df['crescimento_valor'] = np.where(
        df['valor_movimentado_2025'] > 0,
        ((df['valor_movimentado_2026'] - df['valor_movimentado_2025'])
         / df['valor_movimentado_2025']) * 100,
        0,
    )
    return df


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


# ── Formatting Helpers ────────────────────────────────────────
def br_num(val):
    s = f'{val:,.0f}'
    return s.replace(',', '.')


def br_money(val):
    s = f'{val:,.2f}'
    partes = s.split('.')
    int_part = partes[0].replace(',', '.')
    return f'$ {int_part},{partes[1]}'


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


def add_railway_routes(ax):
    rr = np.array(RAILWAY_ROUTE)
    ax.plot(rr[:, 1], rr[:, 0], color='orange', linewidth=3,
            alpha=0.8, label='Ferrovia Santos-Cajati', zorder=3)
    sr = np.array(STRATEGIC_ROUTE)
    ax.plot(sr[:, 1], sr[:, 0], color='#E63946', linewidth=3,
            alpha=0.7, linestyle='--', label='Rota Estratégica', zorder=3)
    sjc = np.array(BRANCH_SJC)
    ax.plot(sjc[:, 1], sjc[:, 0], color='#FF6B6B', linewidth=2,
            alpha=0.6, linestyle=':', label='Ramais', zorder=3)
    intr = np.array(BRANCH_INTERIOR)
    ax.plot(intr[:, 1], intr[:, 0], color='#FF6B6B', linewidth=2,
            alpha=0.6, linestyle=':', zorder=3)


def add_sp_state(ax):
    sp = load_sp_state()
    if sp is not None:
        sp.boundary.plot(ax=ax, color='#555555', linewidth=1.2, alpha=0.6, zorder=1)
        return True
    return False


# ── Geometry helpers for route matching ──────────────────────
def haversine_km(lat1, lon1, lat2, lon2):
    R = 6371.0
    dlat = np.radians(lat2 - lat1)
    dlon = np.radians(lon2 - lon1)
    a = (np.sin(dlat / 2) ** 2
         + np.cos(np.radians(lat1)) * np.cos(np.radians(lat2))
         * np.sin(dlon / 2) ** 2)
    return R * 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))


def project_point_to_segment(px, py, ax, ay, bx, by):
    abx, aby = bx - ax, by - ay
    apx, apy = px - ax, py - ay
    t = (apx * abx + apy * aby) / (abx * abx + aby * aby + 1e-12)
    t = np.clip(t, 0, 1)
    cx = ax + t * abx
    cy = ay + t * aby
    dist = haversine_km(cy, cx, py, px)
    return (cx, cy), dist


def find_nearest_route(lon, lat, route_defs):
    best_dist = float('inf')
    best_point = None
    best_route = None
    for rd in route_defs:
        coords = rd['coords']
        for i in range(len(coords) - 1):
            a_lat, a_lon = coords[i]
            b_lat, b_lon = coords[i + 1]
            pt, d = project_point_to_segment(lon, lat, a_lon, a_lat, b_lon, b_lat)
            if d < best_dist:
                best_dist = d
                best_point = pt
                best_route = rd
    return best_route, best_point, best_dist


# ── Map 1: Flow Map ───────────────────────────────────────────
def gerar_mapa_fluxo(df, output='mapa_fluxo_comercial.png'):
    santos = df[df['Cidade'].str.contains('Santos', case=False, na=False)]
    if santos.empty:
        print('ERRO: Santos não encontrada na base')
        return
    santos_row = santos.iloc[0]

    min_val = max(df['valor_movimentado_2025'].max() / 5000, 1)
    max_val = df['valor_movimentado_2025'].max()
    cities = df[df['valor_movimentado_2025'] > 0].copy()

    fig, ax = plt.subplots(figsize=(22, 13))
    fig.patch.set_facecolor('#0E1117')
    setup_dark_ax(ax, 'FLUXO COMERCIAL — CONEXÕES COM A FERROVIA (2025)',
                  'Longitude', 'Latitude')

    add_sp_state(ax)
    add_railway_routes(ax)

    # Draw flow lines: each city connects to its nearest route segment
    route_counts = {rd['name']: 0 for rd in ROUTE_DEFS}
    flow_handles = {}

    for _, row in cities.iterrows():
        v = row['valor_movimentado_2025']
        if v <= 0:
            continue
        cx, cy = row['longitude'], row['latitude']

        nearest_route, nearest_pt, _ = find_nearest_route(cx, cy, ROUTE_DEFS)
        if nearest_pt is None:
            continue
        tx, ty = nearest_pt

        route_counts[nearest_route['name']] += 1
        route_color = nearest_route['color']

        lw = 0.3 + 4.5 * (np.log10(max(v, min_val)) - np.log10(min_val)) / (
            np.log10(max_val) - np.log10(min_val)
        )
        log_v = np.log10(v)
        frac = (log_v - np.log10(min_val)) / (
            np.log10(max_val) - np.log10(min_val)
        )
        frac = np.clip(frac, 0, 1)
        alpha = 0.12 + 0.50 * frac

        t = np.linspace(0, 1, 50)
        mx, my = (cx + tx) / 2, (cy + ty) / 2
        dx, dy = tx - cx, ty - cy
        dist = np.hypot(dx, dy)
        curvature = 0.0005 * dist
        cpx = mx - dy * curvature
        cpy = my + dx * curvature
        bx = (1 - t) ** 2 * cx + 2 * (1 - t) * t * cpx + t ** 2 * tx
        by = (1 - t) ** 2 * cy + 2 * (1 - t) * t * cpy + t ** 2 * ty
        ax.plot(bx, by, color=route_color, linewidth=lw,
                alpha=alpha, zorder=2)

    top10 = cities.nlargest(10, 'valor_movimentado_2025')
    scatter_v = df['valor_movimentado_2025'].values
    sizes = 20 + 180 * (
        np.log10(np.maximum(scatter_v, min_val)) - np.log10(min_val)
    ) / (np.log10(max_val) - np.log10(min_val))
    ax.scatter(df['longitude'], df['latitude'], s=sizes,
               c='#3186cc', edgecolors='white', linewidths=0.5,
               alpha=0.85, zorder=5)

    sx, sy = santos_row['longitude'], santos_row['latitude']
    ax.scatter(sx, sy, s=350, c='#E63946', edgecolors='white',
               linewidths=2, marker='*', zorder=6)

    for _, row in top10.iterrows():
        lbl = row['Cidade'].split('/')[0].split(',')[0][:14]
        ax.annotate(
            lbl,
            (row['longitude'], row['latitude']),
            xytext=(7, 7), textcoords='offset points',
            fontsize=12, color='white', fontweight='bold',
            alpha=0.9, zorder=7,
        )

    legend_elements = []
    for rd in ROUTE_DEFS:
        cnt = route_counts[rd['name']]
        legend_elements.append(
            Line2D([0], [0], color=rd['color'], lw=4,
                   label=f"{rd['name']} ({cnt} cidades)")
        )
    legend_elements.append(
        Line2D([0], [0], marker='o', color='w', markerfacecolor='#3186cc',
               markersize=10, label='Cidades COMEX')
    )
    legend_elements.append(
        Line2D([0], [0], marker='*', color='w', markerfacecolor='#E63946',
               markersize=12, label='Porto de Santos')
    )

    ax.legend(handles=legend_elements, loc='lower left',
              facecolor='#1a1a2e', edgecolor='#444444',
              labelcolor='white', fontsize=12)

    ax.set_xlim(df['longitude'].min() - 0.3, df['longitude'].max() + 0.3)
    ax.set_ylim(df['latitude'].min() - 0.2, df['latitude'].max() + 0.2)
    ax.set_aspect(1.3)

    plt.tight_layout()
    fig.savefig(output, dpi=180, bbox_inches='tight', facecolor=fig.get_facecolor())
    plt.close(fig)
    print(f'  [OK] {output} gerado')


# ── Map 2: Employment Composition Heatmap ─────────────────────
def gerar_mapa_calor_emprego(df, output='mapa_composicao_emprego.png'):
    plot_df = df[df['total_empregos'] > 0].copy()
    plot_df = plot_df[plot_df['industria_share'].notna()].copy()

    niveis = 25
    triang = tri.Triangulation(plot_df['longitude'], plot_df['latitude'])
    x_min, x_max = plot_df['longitude'].min() - 0.2, plot_df['longitude'].max() + 0.2
    y_min, y_max = plot_df['latitude'].min() - 0.15, plot_df['latitude'].max() + 0.15

    fig, ax = plt.subplots(figsize=(22, 13))
    fig.patch.set_facecolor('#0E1117')
    setup_dark_ax(ax, 'COMPOSIÇÃO SETORIAL DO EMPREGO — PARTICIPAÇÃO DA INDÚSTRIA',
                  'Longitude', 'Latitude')

    has_state = add_sp_state(ax)
    add_railway_routes(ax)

    cf = ax.tricontourf(
        triang, plot_df['industria_share'].values,
        levels=niveis, cmap='plasma', alpha=0.75, zorder=2,
    )
    cbar = fig.colorbar(cf, ax=ax, shrink=0.6, pad=0.02)
    cbar.set_label('Participação da Indústria (%)', color='white', fontsize=15)
    cbar.ax.yaxis.set_major_formatter(
        ticker.FuncFormatter(lambda x, _: f'{x*100:.0f}%')
    )
    cbar.ax.tick_params(colors='white', labelsize=12)

    top_ind = plot_df.nlargest(10, 'industria_share')
    ax.scatter(
        plot_df['longitude'], plot_df['latitude'],
        c=plot_df['industria_share'], cmap='plasma',
        s=120, edgecolors='white', linewidths=0.6,
        alpha=0.9, zorder=5, vmin=plot_df['industria_share'].min(),
        vmax=plot_df['industria_share'].max(),
    )

    ax.scatter(
        top_ind['longitude'], top_ind['latitude'],
        s=260, facecolors='none', edgecolors='white',
        linewidths=1.8, zorder=6,
    )

    for _, row in top_ind.iterrows():
        lbl = row['Cidade'].split('/')[0].split(',')[0][:14]
        pct = row['industria_share'] * 100
        ax.annotate(
            f'{lbl} ({pct:.0f}%)',
            (row['longitude'], row['latitude']),
            xytext=(9, 9), textcoords='offset points',
            fontsize=12, color='white', fontweight='bold',
            alpha=0.9, zorder=7,
        )

    ax.set_xlim(x_min, x_max)
    ax.set_ylim(y_min, y_max)
    ax.set_aspect(1.3)

    plt.tight_layout()
    fig.savefig(output, dpi=180, bbox_inches='tight', facecolor=fig.get_facecolor())
    plt.close(fig)
    print(f'  [OK] {output} gerado')


# ── Main ──────────────────────────────────────────────────────
if __name__ == '__main__':
    DATA_PATH = Path('dados_comex_stat.csv')
    if not DATA_PATH.exists():
        print(f'ERRO: {DATA_PATH} não encontrado')
        exit(1)

    print('Carregando dados...')
    df = load_data()
    print(f'  {len(df)} municípios carregados')

    print('\nGerando mapa de fluxo comercial...')
    gerar_mapa_fluxo(df)

    print('\nGerando mapa de composição setorial do emprego...')
    gerar_mapa_calor_emprego(df)

    print('\n[OK] Mapas gerados com sucesso!')
