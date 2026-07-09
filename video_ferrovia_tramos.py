import os, io, shutil, tempfile
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from pathlib import Path
from moviepy import ImageSequenceClip
import warnings
warnings.filterwarnings('ignore')

# ── Constants ─────────────────────────────────────────────────
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
    [(-23.4596858, -46.5328559), (-23.024996, -45.5638792)],
    [(-23.5553, -46.6121), (-23.6879922, -46.6251796)],
    [(-22.7410508, -47.1743005), (-22.8573469, -47.2210564)],
    [(-23.1856528, -46.8892222), (-23.470905, -47.4851488)],
    [(-22.7410508, -47.1743005), (-21.8357036, -48.4930404)],
]

MAIN_CITIES = [
    ('Curitiba',          -25.43055, -49.26646),
    ('Cajati',            -24.7358,  -48.1228),
    ('Jacupiranga',       -24.6925,  -48.0022),
    ('Registro',          -24.4971,  -47.8449),
    ('Juquiá',            -24.3208,  -47.6347),
    ('Miracatu',          -24.2814,  -47.4625),
    ('P.Toledo',          -24.2747,  -47.2328),
    ('Itariri',           -24.2892,  -47.1744),
    ('Peruíbe',           -24.3129,  -47.0012),
    ('Itanhaém',          -24.1856,  -46.7889),
    ('Mongaguá',          -24.0948,  -46.6208),
    ('Praia Grande',      -24.0058,  -46.4028),
    ('S.Vicente',         -23.9631,  -46.3919),
    ('Santos',            -23.9608,  -46.3336),
    ('Cubatão',           -23.8916,  -46.4240),
    ('São Paulo',         -23.5553,  -46.6121),
    ('Jundiaí',           -23.1857,  -46.8892),
    ('Vinhedo',           -23.0263,  -46.9819),
    ('Valinhos',          -22.9691,  -46.9958),
    ('Campinas',          -22.9051,  -47.0613),
    ('Paulínia',          -22.7411,  -47.1743),
    ('Guarulhos',         -23.4597,  -46.5329),
    ('S.J.Campos',        -23.2198,  -45.8916),
    ('Limeira',           -22.5838,  -47.4098),
    ('São Carlos',        -22.0123,  -47.8908),
    ('Araraquara',        -21.7743,  -48.1742),
    ('R.Preto',           -21.1694,  -47.8111),
    ('Sorocaba',          -23.4709,  -47.4851),
    ('S.B.Campo',         -23.7018,  -46.5536),
    ('Piracicaba',        -22.7344,  -47.6480),
    ('Taubaté',           -23.024996, -45.563879),
    ('Barueri',           -23.5035,  -46.8786),
    ('S.Sebastião',       -23.801074, -45.402604),
    ('Gav.Peixoto',       -21.835704, -48.493040),
    ('Hortolândia',       -22.857347, -47.221056),
]

LARGE_CITIES = {'São Paulo', 'Curitiba', 'Campinas', 'Santos',
                'R.Preto', 'S.J.Campos', 'Sorocaba', 'S.B.Campo',
                'Piracicaba', 'Jundiaí'}

# ── Map bounds ────────────────────────────────────────────────
ALL_LONS = [c[2] for c in MAIN_CITIES]
ALL_LATS = [c[1] for c in MAIN_CITIES]
PAD_LON = (max(ALL_LONS) - min(ALL_LONS)) * 0.10
PAD_LAT = (max(ALL_LATS) - min(ALL_LATS)) * 0.10
XLIM = (min(ALL_LONS) - PAD_LON, max(ALL_LONS) + PAD_LON)
YLIM = (min(ALL_LATS) - PAD_LAT, max(ALL_LATS) + PAD_LAT)


# ── Data ──────────────────────────────────────────────────────
def load_data():
    df = pd.read_csv('dados_comex_stat.csv')
    num_cols = ['valor_movimentado_2025', 'valor_movimentado_2026',
                'valor_movimentado_total', 'empregos_agropecuaria',
                'empregos_industria', 'empregos_construção',
                'empregos_comercio', 'empregos_servicos', 'total_empregos']
    for col in num_cols:
        if col in df.columns:
            df[col] = (df[col].astype(str).str.replace('.', '', regex=False)
                       .str.replace(',', '.', regex=False))
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    return df


def load_sp_state():
    cache_path = Path('sp_boundary.geojson')
    if cache_path.exists():
        try:
            import geopandas as gpd
            return gpd.read_file(cache_path)
        except Exception:
            pass
    try:
        import geopandas as gpd, shutil
        from io import BytesIO
        from zipfile import ZipFile
        import requests
        url = ('https://geoftp.ibge.gov.br/'
               'organizacao_do_territorio/malhas_territoriais/'
               'malhas_municipais/municipio_2022/'
               'Brasil/BR/BR_UF_2022.zip')
        r = requests.get(url, timeout=30)
        r.raise_for_status()
        tmp = Path('_tmp_sp_shp')
        tmp.mkdir(exist_ok=True)
        with BytesIO(r.content) as buf, ZipFile(buf) as zf:
            zf.extractall(tmp)
        uf = gpd.read_file(tmp / 'BR_UF_2022.shp')
        col = 'SIGLA_UF' if 'SIGLA_UF' in uf.columns else 'SIGLA'
        sp = uf[uf[col] == 'SP'].to_crs(epsg=4326)
        sp.to_file(cache_path, driver='GeoJSON')
        shutil.rmtree(tmp)
        return sp
    except Exception:
        return None


# ── Progress-based route drawing ──────────────────────────────
def route_at_progress(coords, progress):
    """Return (lons, lats) for the route up to the given progress 0..1."""
    n_seg = len(coords) - 1
    total = progress * n_seg
    full = int(total)
    rem = total - full
    pts = list(coords[:full + 1])
    if rem > 0 and full < n_seg:
        lat = coords[full][0] + (coords[full + 1][0] - coords[full][0]) * rem
        lon = coords[full][1] + (coords[full + 1][1] - coords[full][1]) * rem
        pts[-1] = (lat, lon)
    if len(pts) < 2:
        return [], []
    return [p[1] for p in pts], [p[0] for p in pts]


# ── Frame rendering ───────────────────────────────────────────
def render_frame(progress, df, cities_data, sp_boundary):
    """
    progress: 0.0 to 1.0
    Returns a numpy RGB array of the frame.
    """
    fig, ax = plt.subplots(figsize=(16, 10))
    fig.patch.set_facecolor('#0E1117')

    ax.set_facecolor('#0E1117')
    ax.tick_params(axis='both', colors='white', labelsize=10)
    ax.set_xlabel('Longitude', color='white', fontsize=12)
    ax.set_ylabel('Latitude', color='white', fontsize=12)
    ax.set_title('MALHA FERROVIARIA ESTRATEGICA - ROTAS E TRAMOS (COMEX)',
                 color='white', fontsize=16, fontweight='bold', pad=15)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['bottom'].set_color('#444444')
    ax.spines['left'].set_color('#444444')
    ax.grid(True, alpha=0.15, color='white', linestyle='--')
    ax.set_xlim(XLIM)
    ax.set_ylim(YLIM)
    ax.set_aspect(1.3)

    t = progress  # shortcut

    # ── SP boundary (visible from start) ──
    if sp_boundary is not None:
        alpha_b = min(t / 0.05, 1.0) * 0.4
        sp_boundary.boundary.plot(ax=ax, color='#555555',
                                  linewidth=1.0, alpha=alpha_b, zorder=1)

    # ── Route drawing phases ──
    # Phase 1: Rota Original  (t: 0.05 – 0.25)
    t1 = np.clip((t - 0.05) / 0.20, 0, 1)
    if t1 > 0:
        lons, lats = route_at_progress(ORIGINAL_ROUTE, t1)
        if lons:
            ax.plot(lons, lats, color='#FF8C00', linewidth=3.0,
                    alpha=0.9, zorder=4)

    # Phase 2: Conexao SP-Jundiai (t: 0.25 – 0.33)
    t2 = np.clip((t - 0.25) / 0.08, 0, 1)
    if t2 > 0:
        lons, lats = route_at_progress(CONN_SP_JUNDIAI, t2)
        if lons:
            ax.plot(lons, lats, color='#E63946', linewidth=2.0,
                    alpha=0.8, linestyle='--', zorder=4)

    # Phase 3: Rota Estrategica (t: 0.33 – 0.43)
    t3 = np.clip((t - 0.33) / 0.10, 0, 1)
    if t3 > 0:
        lons, lats = route_at_progress(STRATEGIC_ROUTE, t3)
        if lons:
            ax.plot(lons, lats, color='#E63946', linewidth=2.5,
                    alpha=0.9, zorder=4)

    # Phase 4: Ramal Leste (t: 0.43 – 0.51)
    t4 = np.clip((t - 0.43) / 0.08, 0, 1)
    if t4 > 0:
        lons, lats = route_at_progress(BRANCH_EAST, t4)
        if lons:
            ax.plot(lons, lats, color='#FF6B6B', linewidth=2.0,
                    alpha=0.7, linestyle='--', zorder=4)

    # Phase 5: Ramal Interior (t: 0.51 – 0.61)
    t5 = np.clip((t - 0.51) / 0.10, 0, 1)
    if t5 > 0:
        lons, lats = route_at_progress(BRANCH_INTERIOR, t5)
        if lons:
            ax.plot(lons, lats, color='#FF6B6B', linewidth=2.0,
                    alpha=0.7, linestyle='--', zorder=4)

    # Phase 6: P-Median branches (t: 0.61 – 0.73)
    t6 = np.clip((t - 0.61) / 0.12, 0, 1)
    if t6 > 0:
        n_branches = len(BRANCH_MEDIAN)
        for i, branch in enumerate(BRANCH_MEDIAN):
            b_prog = np.clip((t6 * n_branches - i), 0, 1)
            if b_prog > 0:
                lons, lats = route_at_progress(branch, b_prog)
                if lons:
                    ax.plot(lons, lats, color='#FFB3B3', linewidth=1.2,
                            alpha=0.5, linestyle='--', zorder=3)

    # ── Curitiba + SP terminal markers (t: 0.25 onwards) ──
    if t > 0.25:
        alpha_t = min((t - 0.25) / 0.05, 1.0)
        cur_lat, cur_lon = -25.43055, -49.26646
        ax.scatter(cur_lon, cur_lat, s=350, c='#FF8C00',
                   edgecolors='white', linewidths=2, marker='s',
                   alpha=alpha_t, zorder=6)
        if t > 0.55:
            ax.annotate('Curitiba (inicio)', (cur_lon, cur_lat),
                        xytext=(12, -30), textcoords='offset points',
                        fontsize=9, color='white', fontweight='bold',
                        alpha=alpha_t, zorder=7)

        sp_lat, sp_lon = -23.5553, -46.6121
        ax.scatter(sp_lon, sp_lat, s=350, c='#FF8C00',
                   edgecolors='white', linewidths=2, marker='s',
                   alpha=alpha_t, zorder=6)
        if t > 0.55:
            ax.annotate('Sao Paulo (terminal)', (sp_lon, sp_lat),
                        xytext=(12, 12), textcoords='offset points',
                        fontsize=9, color='white', fontweight='bold',
                        alpha=alpha_t, zorder=7)

    # ── Santos star (t: 0.25 onwards) ──
    if t > 0.25:
        alpha_s = min((t - 0.25) / 0.05, 1.0)
        s_lon, s_lat = -46.3336, -23.9608
        ax.scatter(s_lon, s_lat, s=280, c='#E63946',
                   edgecolors='white', linewidths=1.5, marker='*',
                   alpha=alpha_s, zorder=6)

    # ── COMEX cities (t: 0.73 – 0.88) ──
    t_cities = np.clip((t - 0.73) / 0.15, 0, 1)
    if t_cities > 0:
        min_val = max(cities_data['valor_movimentado_2025'].max() / 5000, 1)
        max_val = cities_data['valor_movimentado_2025'].max()
        sizes = 10 + 120 * (
            np.log10(np.maximum(cities_data['valor_movimentado_2025'], min_val))
            - np.log10(min_val)
        ) / (np.log10(max_val) - np.log10(min_val))
        ax.scatter(cities_data['longitude'], cities_data['latitude'],
                   s=sizes, c='#3186cc', edgecolors='white',
                   linewidths=0.4, alpha=t_cities * 0.85, zorder=5)

    # ── City labels (t: 0.85 – 1.0) ──
    t_labels = np.clip((t - 0.85) / 0.15, 0, 1)
    if t_labels > 0:
        n_total = len(MAIN_CITIES)
        n_show = int(t_labels * n_total)
        for i, (name, lat, lon) in enumerate(MAIN_CITIES):
            if i >= n_show:
                break
            if name in ('São Paulo', 'Curitiba'):
                continue
            lbl_alpha = min((t_labels * n_total - i) * 0.3, 1.0)
            if name == 'Santos':
                ax.annotate('Porto de Santos', (lon, lat),
                            xytext=(10, -22), textcoords='offset points',
                            fontsize=8, color='white', fontweight='bold',
                            alpha=lbl_alpha, zorder=7)
            elif name in LARGE_CITIES:
                ax.annotate(name, (lon, lat), xytext=(7, 7),
                            textcoords='offset points', fontsize=9,
                            color='white', fontweight='bold',
                            alpha=lbl_alpha, zorder=7)
            else:
                offset = -12 if lat > -23 else 7
                ax.annotate(name, (lon, lat), xytext=(5, offset),
                            textcoords='offset points', fontsize=7,
                            color='#dddddd', alpha=lbl_alpha * 0.85, zorder=7)

    # ── Legend (t: 0.88 onwards) ──
    t_leg = np.clip((t - 0.88) / 0.07, 0, 1)
    if t_leg > 0:
        legend_elements = [
            Line2D([0], [0], color='#FF8C00', lw=3, label='Rota Original (Santos-Cajati)'),
            Line2D([0], [0], color='#E63946', lw=3, label='Rota Estrategica (Jundiai-Paulinia)'),
            Line2D([0], [0], color='#E63946', lw=2, linestyle='--', label='Conexao SP-Jundiai'),
            Line2D([0], [0], color='#FF6B6B', lw=2, linestyle='--', label='Ramais (Leste / Interior)'),
            Line2D([0], [0], color='#FFB3B3', lw=1.2, linestyle='--', label='Ramais P-Median'),
            Line2D([0], [0], marker='o', color='w', markerfacecolor='#3186cc',
                   markersize=8, label='Cidades COMEX'),
            Line2D([0], [0], marker='*', color='w', markerfacecolor='#E63946',
                   markersize=10, label='Porto de Santos'),
        ]
        leg = ax.legend(handles=legend_elements, loc='lower right',
                        facecolor='#1a1a2e', edgecolor='#444444',
                        labelcolor='white', fontsize=8)
        leg.get_frame().set_alpha(t_leg)

    # ── Render ──
    plt.tight_layout()
    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=100, bbox_inches='tight',
                facecolor=fig.get_facecolor())
    plt.close(fig)
    buf.seek(0)
    return plt.imread(buf)


# ── Main ──────────────────────────────────────────────────────
def gerar_video(output='video_ferrovia_tramos.mp4', fps=15, duration_sec=18):
    total_frames = int(fps * duration_sec)
    print(f'  Gerando {total_frames} frames ({duration_sec}s @ {fps}fps)...')

    print('  Carregando dados...')
    df = load_data()
    cities = df[df['valor_movimentado_2025'] > 0].copy()
    sp = load_sp_state()

    frames_dir = None
    try:
        frames_dir = tempfile.mkdtemp()

        for i in range(total_frames):
            progress = i / total_frames
            frame = render_frame(progress, df, cities, sp)
            # save to disk
            fp = os.path.join(frames_dir, f'{i:04d}.png')
            plt.imsave(fp, frame)
            if (i + 1) % 30 == 0:
                print(f'    frame {i + 1}/{total_frames}')

        print('  Compondo video com moviepy...')
        clip = ImageSequenceClip(frames_dir, fps=fps)
        clip.write_videofile(output, codec='libx264',
                             logger=None, bitrate='2000k')
        print(f'  [OK] {output} gerado')
    finally:
        if frames_dir and os.path.exists(frames_dir):
            shutil.rmtree(frames_dir)


if __name__ == '__main__':
    gerar_video()
