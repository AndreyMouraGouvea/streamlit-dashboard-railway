import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

# ── Railway Routes (from novo_mapa.html) ─────────────────────
ORIGINAL_ROUTE = [
    (-23.5553, -46.6121), (-23.8916, -46.424), (-23.9608, -46.3336),
    (-23.9631, -46.3919), (-24.0058, -46.4028), (-24.0948, -46.6208),
    (-24.1856, -46.7889), (-24.3129, -47.0012), (-24.2892, -47.1744),
    (-24.2747, -47.2328), (-24.2814, -47.4625), (-24.3208, -47.6347),
    (-24.4971, -47.8449), (-24.6925, -48.0022), (-24.7358, -48.1228),
    (-25.43055, -49.26646),
]

CONN_SP_JUNDIAI = [
    (-23.5553, -46.6121), (-23.1856528, -46.8892222),
]

STRATEGIC_ROUTE = [
    (-23.1856528, -46.8892222), (-23.0263471, -46.9818714),
    (-22.9691172, -46.9958185), (-22.9050824, -47.0613327),
    (-22.7410508, -47.1743005),
]

BRANCH_EAST = [
    (-23.5553, -46.6121), (-23.4596858, -46.5328559),
    (-23.2198396, -45.8915658),
]

BRANCH_INTERIOR = [
    (-22.7410508, -47.1743005), (-22.5838179, -47.4097569),
    (-22.0123291, -47.8908261), (-21.7742763, -48.1742397),
    (-21.1694018, -47.8110855),
]

BRANCH_MEDIAN = [
    ([(-23.4596858, -46.5328559), (-23.024996, -45.5638792)], 'Taubaté'),
    ([(-23.5553, -46.6121), (-23.6879922, -46.6251796)], 'Diadema'),
    ([(-22.7410508, -47.1743005), (-22.8573469, -47.2210564)], 'Hortolândia'),
    ([(-23.1856528, -46.8892222), (-23.470905, -47.4851488)], 'Sorocaba'),
    ([(-22.7410508, -47.1743005), (-21.8357036, -48.4930404)], 'Gavião Peixoto'),
]

MAIN_CITIES = [
    ('Curitiba',          -25.43055, -49.26646),
    ('Cajati',            -24.7358,  -48.1228),
    ('Jacupiranga',       -24.6925,  -48.0022),
    ('Registro',          -24.4971,  -47.8449),
    ('Juquiá',            -24.3208,  -47.6347),
    ('Miracatu',          -24.2814,  -47.4625),
    ('P. Toledo',         -24.2747,  -47.2328),
    ('Itariri',           -24.2892,  -47.1744),
    ('Peruíbe',           -24.3129,  -47.0012),
    ('Itanhaém',          -24.1856,  -46.7889),
    ('Mongaguá',          -24.0948,  -46.6208),
    ('Praia Grande',      -24.0058,  -46.4028),
    ('S. Vicente',        -23.9631,  -46.3919),
    ('Santos',            -23.9608,  -46.3336),
    ('Cubatao',           -23.8916,  -46.4240),
    ('Sao Paulo',         -23.5553,  -46.6121),
    ('Jundiai',           -23.1857,  -46.8892),
    ('Vinhedo',           -23.0263,  -46.9819),
    ('Valinhos',          -22.9691,  -46.9958),
    ('Campinas',          -22.9051,  -47.0613),
    ('Paulinia',          -22.7411,  -47.1743),
    ('Guarulhos',         -23.4597,  -46.5329),
    ('S.J.Campos',        -23.2198,  -45.8916),
    ('Limeira',           -22.5838,  -47.4098),
    ('Sao Carlos',        -22.0123,  -47.8908),
    ('Araraquara',        -21.7743,  -48.1742),
    ('R.Preto',           -21.1694,  -47.8111),
    ('Sorocaba',          -23.4709,  -47.4851),
    ('S.B.Campo',         -23.7018,  -46.5536),
    ('Piracicaba',        -22.7344,  -47.6480),
    ('Taubate',           -23.024996, -45.563879),
    ('Barueri',           -23.5035,  -46.8786),
    ('S.Sebastiao',       -23.801074, -45.402604),
    ('Gav.Peixoto',       -21.835704, -48.493040),
    ('Hortolandia',       -22.857347, -47.221056),
]


# ── Data Loading ──────────────────────────────────────────────
def load_data():
    df = pd.read_csv('dados_comex_stat.csv')
    num_cols = [
        'valor_movimentado_2025', 'valor_movimentado_2026',
        'valor_movimentado_total', 'empregos_agropecuaria',
        'empregos_industria', 'empregos_construcao',
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
    return df


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


# ── Helpers ────────────────────────────────────────────────────
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


def plot_route(ax, coords, color, lw, alpha, dashed=False, zorder=4):
    lons = [c[1] for c in coords]
    lats = [c[0] for c in coords]
    ls = '--' if dashed else '-'
    ax.plot(lons, lats, color=color, linewidth=lw, alpha=alpha,
            linestyle=ls, zorder=zorder)


# ── Map Generation ────────────────────────────────────────────
def gerar_mapa_tramos(output='mapa_ferrovia_tramos.png'):
    print('Carregando dados...')
    df = load_data()
    print(f'  {len(df)} cidades carregadas')

    has_trade = df['valor_movimentado_2025'] > 0
    cities = df[has_trade].copy()

    fig, ax = plt.subplots(figsize=(26, 16))
    fig.patch.set_facecolor('#0E1117')
    setup_dark_ax(ax, 'MALHA FERROVIARIA ESTRATEGICA - ROTAS E TRAMOS (COMEX)',
                  'Longitude', 'Latitude')

    sp = load_sp_state()
    if sp is not None:
        sp.boundary.plot(ax=ax, color='#555555', linewidth=1.2, alpha=0.4, zorder=1)

    # Routes
    plot_route(ax, ORIGINAL_ROUTE, '#FF8C00', 3.5, 0.9, dashed=False, zorder=4)
    plot_route(ax, CONN_SP_JUNDIAI, '#E63946', 2.5, 0.8, dashed=True, zorder=4)
    plot_route(ax, STRATEGIC_ROUTE, '#E63946', 3.0, 0.9, dashed=False, zorder=4)
    plot_route(ax, BRANCH_EAST, '#FF6B6B', 2.5, 0.7, dashed=True, zorder=4)
    plot_route(ax, BRANCH_INTERIOR, '#FF6B6B', 2.5, 0.7, dashed=True, zorder=4)
    for branch_coords, name in BRANCH_MEDIAN:
        plot_route(ax, branch_coords, '#FFB3B3', 1.5, 0.5, dashed=True, zorder=3)

    # COMEX cities
    min_val = max(cities['valor_movimentado_2025'].max() / 5000, 1)
    max_val = cities['valor_movimentado_2025'].max()
    sizes = 20 + 180 * (
        np.log10(np.maximum(cities['valor_movimentado_2025'], min_val))
        - np.log10(min_val)
    ) / (np.log10(max_val) - np.log10(min_val))
    ax.scatter(cities['longitude'], cities['latitude'], s=sizes,
               c='#3186cc', edgecolors='white', linewidths=0.5,
               alpha=0.85, zorder=5)

    # Porto de Santos highlight
    santos_row = df[df['Cidade'].str.contains('Santos', case=False, na=False)]
    if not santos_row.empty:
        r = santos_row.iloc[0]
        ax.scatter(r['longitude'], r['latitude'], s=400, c='#E63946',
                   edgecolors='white', linewidths=2, marker='*', zorder=6)

    # Curitiba — start of route (large orange square)
    cur_lat, cur_lon = -25.43055, -49.26646
    ax.scatter(cur_lon, cur_lat, s=500, c='#FF8C00',
               edgecolors='white', linewidths=2.5, marker='s', zorder=6)
    ax.annotate('Curitiba\n(inicio da rota)', (cur_lon, cur_lat),
                xytext=(12, -35), textcoords='offset points',
                fontsize=12, color='white', fontweight='bold', zorder=7)

    # São Paulo — terminal (large orange square)
    sp_lat, sp_lon = -23.5553, -46.6121
    ax.scatter(sp_lon, sp_lat, s=500, c='#FF8C00',
               edgecolors='white', linewidths=2.5, marker='s', zorder=6)
    ax.annotate('Sao Paulo\n(terminal)', (sp_lon, sp_lat),
                xytext=(12, 12), textcoords='offset points',
                fontsize=12, color='white', fontweight='bold', zorder=7)

    # Main city labels
    large = {'Campinas', 'Santos', 'R.Preto', 'S.J.Campos',
             'Sorocaba', 'S.B.Campo', 'Piracicaba', 'Jundiai'}

    for name, lat, lon in MAIN_CITIES:
        if name in ('Sao Paulo', 'Curitiba'):
            continue  # handled with special annotations above
        if name == 'Santos':
            ax.annotate('Porto de Santos', (lon, lat), xytext=(12, -25),
                        textcoords='offset points', fontsize=11,
                        color='white', fontweight='bold', zorder=7)
        elif name in large:
            ax.annotate(name, (lon, lat), xytext=(8, 8),
                        textcoords='offset points', fontsize=11,
                        color='white', fontweight='bold', alpha=0.95, zorder=7)
        else:
            offset = -14 if lat > -23 else 8
            ax.annotate(name, (lon, lat), xytext=(6, offset),
                        textcoords='offset points', fontsize=8,
                        color='#dddddd', alpha=0.85, zorder=7)

    # Legend
    legend_elements = [
        Line2D([0], [0], color='#FF8C00', lw=4, label='Rota Original (Santos-Cajati)'),
        Line2D([0], [0], color='#E63946', lw=4, label='Rota Estrategica (Jundiai-Paulinia)'),
        Line2D([0], [0], color='#E63946', lw=2.5, linestyle='--', label='Conexao SP-Jundiai'),
        Line2D([0], [0], color='#FF6B6B', lw=2.5, linestyle='--', label='Ramais (Leste / Interior)'),
        Line2D([0], [0], color='#FFB3B3', lw=1.5, linestyle='--', label='Ramais P-Median'),
        Line2D([0], [0], marker='o', color='w', markerfacecolor='#3186cc',
               markersize=10, label='Cidades COMEX'),
        Line2D([0], [0], marker='*', color='w', markerfacecolor='#E63946',
               markersize=12, label='Sao Paulo / Porto de Santos'),
    ]
    ax.legend(handles=legend_elements, loc='lower right',
              facecolor='#1a1a2e', edgecolor='#444444',
              labelcolor='white', fontsize=11)

    # Bounds (include route endpoints so Curitiba/terminals are visible)
    all_lons = cities['longitude'].tolist() + [c[2] for c in MAIN_CITIES]
    all_lats = cities['latitude'].tolist() + [c[1] for c in MAIN_CITIES]
    pad_lon = (max(all_lons) - min(all_lons)) * 0.10
    pad_lat = (max(all_lats) - min(all_lats)) * 0.10
    ax.set_xlim(min(all_lons) - pad_lon, max(all_lons) + pad_lon)
    ax.set_ylim(min(all_lats) - pad_lat, max(all_lats) + pad_lat)
    ax.set_aspect(1.3)

    plt.tight_layout()
    fig.savefig(output, dpi=180, bbox_inches='tight', facecolor=fig.get_facecolor())
    plt.close(fig)
    print(f'  [OK] {output} gerado')


if __name__ == '__main__':
    gerar_mapa_tramos()
