---
name: criar-mapas-ferroviarios
description: Cria e modifica mapas estáticos temáticos (COMEX, passageiros, rodovias) para o projeto FerroviaCajatiSantos. Tema escuro, matplotlib, shapefiles SP.
license: MIT
compatibility: opencode
metadata:
  project: FerroviaCajatiSantos
  python: 3.14
  deps: matplotlib, geopandas, pandas, numpy, requests, openpyxl
---

## Contexto do Projeto

Mapas estáticos para dashboard ferroviário/COMEX exibido em TV/projetor. Todos os mapas usam **tema escuro** (`#0E1117`), texto branco, saída em PNG com 180 dpi.

Diretório base: `C:\Users\andre\Desktop\Python\FerroviaCajatiSantos`

---

## Fontes de Dados

### Shapefiles de Rodovias
| Tipo | Path | CRS | Coluna código | Filtro estado SP |
|---|---|---|---|---|
| Estaduais | `rodovias estaduais/vw_cide_rod_2021.shp` | EPSG:4674 | `Codigo_Rod` | `Codigo_SNV` contém `'ESP'` |
| Federais | `rodovias federais/vw_snv_rod.shp` | EPSG:4674 | `Codigo_BR` | `Codigo_SNV` contém `'SP'` |

- Snippet de loading:
```python
est = gpd.read_file('rodovias estaduais/vw_cide_rod_2021.shp')
fed = gpd.read_file('rodovias federais/vw_snv_rod.shp')
est_sp = est[est['Codigo_SNV'].str.contains('ESP', na=False)]
fed_sp = fed[fed['Codigo_SNV'].str.contains('SP', na=False)]
```

- Colunas úteis: `Extensao` (km), `geometry`, `Codigo_SNV`, `Local_Inic`, `Local_Fim`, `Quilometra`

### Cache do Estado SP
- `sp_boundary.geojson` (~2 MB) — gerado automaticamente na primeira execução via IBGE (BR_UF_2022.zip)
- Snippet:
```python
sp = gpd.read_file('sp_boundary.geojson')
sp.boundary.plot(ax=ax, color='#555555', linewidth=1.2, alpha=0.6, zorder=1)
```

### Dados COMEX
- `dados_comex_stat.csv` — 50 municípios, colunas:
  - `Cidade`, `Estado`, `latitude`, `longitude`
  - `valor_movimentado_2025`, `valor_movimentado_2026`, `valor_movimentado_total`
  - `empregos_agropecuaria`, `empregos_industria`, `empregos_construção`, `empregos_comercio`, `empregos_servicos`, `total_empregos`
- `industria_share` (derivado: `empregos_industria / total_empregos`)
- `crescimento_valor` (derivado: variação percentual 2025→2026)
- CSV com separador `,` e vírgula como decimal; requer parse manual:
```python
df[col] = df[col].astype(str).str.replace('.', '', regex=False).str.replace(',', '.', regex=False)
df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
```

### Dados da Ferrovia (Passageiros)
- `dataRailway.xlsx` — 171k+ registros, colunas:
  - `ponto_origem_viagem`, `ponto_destino_viagem`
  - `tipo_servico`, `tipo_gratuidade`
  - `media_valor_total`, `dp_valor_total`, `media_valor_passagem`
  - `quantidade_bilhetes`, `mes_emissao_bilhete`, `mes_viagem`
- Colunas de texto devem ser normalizadas: `.str.strip().str.upper()`
- Preço por trecho = `media_valor_total.mean()` (média simples, não ponderada)

---

## Tema Escuro (Matplotlib)

```python
fig, ax = plt.subplots(figsize=(22, 14))
fig.patch.set_facecolor('#0E1117')

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
```

Tamanhos de fonte:
| Elemento | Tamanho |
|---|---|
| Título do mapa | 22 |
| Rótulos eixos (x/y) | 16 |
| Ticks | 14 |
| Anotações de cidades | 11–12 |
| Legenda | 11–12 |
| Colorbar label | 15 |
| Colorbar tick | 12 |

Legenda padrão:
```python
ax.legend(handles=legend_elements, loc='lower left',
          facecolor='#1a1a2e', edgecolor='#444444',
          labelcolor='white', fontsize=12)
```

Salvamento:
```python
fig.savefig(output, dpi=180, bbox_inches='tight', facecolor=fig.get_facecolor())
```

---

## Paletas de Cores

### Rotas Ferroviárias (Fluxo COMEX)
| Rota | Cor | Hex |
|---|---|---|
| Rota Original (Santos–Cajati–Curitiba) | Laranja | `#FF8C00` |
| Rota Estratégica (Jundiaí–Campinas–Paulínia) | Vermelho | `#E63946` |
| Ramal Leste (Guarulhos–SJC) | Ciano | `#00B4D8` |
| Ramal Interior (Paulínia→Ribeirão Preto) | Verde | `#06D6A0` |

### Rodovias
| Rodovia | Cor | Hex |
|---|---|---|
| BR-116 (Regis Bittencourt) — Rota Original | Laranja | `#FF8C00` |
| SP-330 (Anhanguera) — Rota Estratégica | Vermelho | `#E63946` |
| SP-060 (Via Dutra) — Ramal Leste | Ciano | `#00B4D8` |
| SP-310 + SP-326 — Ramal Interior | Verde | `#06D6A0` |
| SP-150 + SP-160 — Acesso Porto | Roxo | `#9B59B6` |
| SP-055 (Padre Nobrega) — Litoral Sul | Rosa | `#FF6B6B` |

### Fluxo de Passageiros (Sentido)
| Direção | Cor | Hex |
|---|---|---|
| Sentido Norte (→ São Paulo) | Ciano | `#00B4D8` |
| Sentido Sul (→ Curitiba) | Laranja | `#FF8C00` |

### Marcadores
| Elemento | Cor | Marker |
|---|---|---|
| Cidade COMEX | `#3186cc` | círculo |
| Porto de Santos | `#E63946` | estrela (`*`) |
| Limite SP | `#555555` | linha (`boundary`) |
| Ferrovia (referência) | `#888888` | tracejado |
| Estação sem dados | `#555555` | quadrado (`s`) |

---

## Cidades Estratégicas

```python
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
```

---

## Rotas Ferroviárias (Coordenadas)

### Rota Original — Santos–Cajati–Curitiba (16 pontos)
```python
RAILWAY_ROUTE = [
    (-23.5553, -46.6121), (-23.8916, -46.4240), (-23.9608, -46.3336),
    (-23.9631, -46.3919), (-24.0058, -46.4028), (-24.0948, -46.6208),
    (-24.1856, -46.7889), (-24.3129, -47.0012), (-24.2892, -47.1744),
    (-24.2747, -47.2328), (-24.2814, -47.4625), (-24.3208, -47.6347),
    (-24.4971, -47.8449), (-24.6925, -48.0022), (-24.7358, -48.1228),
    (-25.43055, -49.26646),
]
```

### Rota Estratégica — Jundiaí–Campinas–Paulínia (5 pontos)
```python
STRATEGIC_ROUTE = [
    (-23.1856528, -46.8892222), (-23.0263471, -46.9818714),
    (-22.9691172, -46.9958185), (-22.9050824, -47.0613327),
    (-22.7410508, -47.1743005),
]
```

### Ramal Leste — SP–Guarulhos–SJC (3 pontos)
```python
BRANCH_SJC = [
    (-23.5553, -46.6121), (-23.4596858, -46.5328559),
    (-23.2198396, -45.8915658),
]
```

### Ramal Interior — Paulínia→Limeira→São Carlos→Araraquara→Ribeirão Preto (5 pontos)
```python
BRANCH_INTERIOR = [
    (-22.7410508, -47.1743005), (-22.5838179, -47.4097569),
    (-22.0123291, -47.8908261), (-21.7742763, -48.1742397),
    (-21.1694018, -47.8110855),
]
```

### Cidades da Rota Original (com dados de passagem)
```python
ROUTE_CITIES = [
    ('SAO PAULO/SP', -23.5553, -46.6121),
    ('CUBATAO/SP', -23.8916, -46.4240),
    ('SANTOS/SP', -23.9608, -46.3336),
    ('SAO VICENTE/SP', -23.9631, -46.3919),
    ('PRAIA GRANDE/SP', -24.0058, -46.4028),
    ('MONGAGUA/SP', -24.0948, -46.6208),  # referência (sem dados)
    ('ITANHAEM/SP', -24.1856, -46.7889),
    ('PERUIBE/SP', -24.3129, -47.0012),
    ('ITARIRI/SP', -24.2892, -47.1744),   # referência
    ('PEDRO DE TOLEDO/SP', -24.2747, -47.2328),  # referência
    ('MIRACATU/SP', -24.2814, -47.4625),
    ('JUQUIA/SP', -24.3208, -47.6347),    # referência
    ('REGISTRO/SP', -24.4971, -47.8449),
    ('JACUPIRANGA/SP', -24.6925, -48.0022),
    ('CAJATI/SP', -24.7358, -48.1228),
    ('CURITIBA/PR', -25.43055, -49.26646),
]
REFERENCE_NAMES = {'MONGAGUA/SP', 'ITARIRI/SP', 'PEDRO DE TOLEDO/SP', 'JUQUIA/SP'}
```

---

## Grupos Rodoviários

```python
ROAD_GROUPS = [
    {
        'name': 'BR-116 (Regis Bittencourt) — Rota Original',
        'color': '#FF8C00',
        'source': 'federal',
        'codes': [116],
        'code_col': 'Codigo_BR',
    },
    {
        'name': 'SP-330 (Anhanguera) — Rota Estrategica',
        'color': '#E63946',
        'source': 'estadual',
        'codes': ['330'],
    },
    {
        'name': 'SP-060 (Via Dutra) — Ramal Leste',
        'color': '#00B4D8',
        'source': 'estadual',
        'codes': ['060'],
    },
    {
        'name': 'SP-310 + SP-326 — Ramal Interior',
        'color': '#06D6A0',
        'source': 'estadual',
        'codes': ['310', '326'],
    },
    {
        'name': 'SP-150 + SP-160 — Acesso ao Porto',
        'color': '#9B59B6',
        'source': 'estadual',
        'codes': ['150', '160'],
    },
    {
        'name': 'SP-055 (Padre Nobrega) — Litoral Sul',
        'color': '#FF6B6B',
        'source': 'estadual',
        'codes': ['055'],
    },
]
```

Dissolver segmentos por grupo:
```python
combined = pd.concat(segs, ignore_index=True)
geom = combined.geometry.unary_union  # LineString ou MultiLineString
km = combined['Extensao'].sum()
```

Plotar geometria:
```python
if geom.geom_type == 'MultiLineString':
    for line in geom.geoms:
        xs, ys = line.xy
        ax.plot(xs, ys, color=color, linewidth=3.0, alpha=0.85, zorder=4)
elif geom.geom_type == 'LineString':
    xs, ys = geom.xy
    ax.plot(xs, ys, color=color, linewidth=3.0, alpha=0.85, zorder=4)
```

---

## Tipos de Mapa e Arquivos

| Arquivo | Tipo | Dados | Saída |
|---|---|---|---|
| `mapas_estaticos.py` | Fluxo comercial + Heatmap emprego | `dados_comex_stat.csv` | `mapa_fluxo_comercial.png`, `mapa_composicao_emprego.png` |
| `mapas_estaticos_original.py` | Fluxo passageiros + Preços | `dataRailway.xlsx` | `mapa_fluxo_passageiros.png`, `mapa_precos_trechos.png` |
| `mapas_rodoviario.py` | Malha rodoviária | shapefiles + `sp_boundary.geojson` | `mapa_rodoviario.png` |

### Fluxo Comercial (`mapas_estaticos.py`)
- Cidades COMEX conectadas ao segmento ferroviário mais próximo via curva Bézier quadrática
- Grossura/opacidade da linha escala com `log10(valor_movimentado_2025)`
- Espessura: `0.3 + 4.5 * log_frac`; alfa: `0.12 + 0.50 * frac`
- Curvatura: `0.0005 * dist` perpendicular à reta
- Cidades coloridas pela rota mais próxima (ROUTE_DEFS)
- Top 10 cidades anotadas com nome

### Heatmap Emprego (`mapas_estaticos.py`)
- `tricontourf` com 25 níveis, cmap `'plasma'`, alpha 0.75
- Scatter das cidades colorido por `industria_share` mesmas escala/vmin/vmax
- Top 10 cidades com maior participação industrial destacadas (contorno branco)
- Anotação: `"{nome} ({pct:.0f}%)"`

### Fluxo Passageiros (`mapas_estaticos_original.py`)
- Curvas Bézier entre pares origem-destino na rota original
- Cor por sentido: norte (SP) `#00B4D8`, sul (Curitiba) `#FF8C00`
- Grossura: `0.3 + 5.0 * log_frac`; alfa: `0.10 + 0.50 * frac`
- Estações com dados: círculo `#3186cc`; sem dados: quadrado `#555555`
- Legenda mostra total de passagens por sentido

### Preços (`mapas_estaticos_original.py`)
- `LineCollection` com cmap `'plasma'` ao longo da rota
- Preço por segmento = `np.nanmean([price_orig, price_dest])`
- `media_valor_total.mean()` por cidade origem (média simples)
- Estações anotadas com nome e `R$ {valor:.0f}`
- Formato colorbar: `'R$ {x:.2f}'`

### Malha Rodoviária (`mapas_rodoviario.py`)
- Ferrovia Santos-Cajati como referência (tracejado `#888888`)
- 6 grupos rodoviários plotados com `linewidth=3.0`, `alpha=0.85`
- Cidades estratégicas como scatter `#3186cc`, Porto de Santos estrela `#E63946`
- Limites do mapa: bounding box das cidades + 10% padding

---

## Convenções de Plotagem

- **Tamanho figura:** `(22, 14)` ou `(20, 14)` — widescreen
- **Aspect ratio:** `ax.set_aspect(1.3)` para COMEX/rodoviário, `1.2` para passageiros
- **Limites:** calculados dinamicamente a partir dos dados com padding de 8–15%
- **Nomes de cidades:** truncar em 14 caracteres (`nome[:14]`)
- **Import:** `matplotlib.use('Agg')` antes de `import matplotlib.pyplot as plt`
- **Warnings:** `warnings.filterwarnings('ignore')`
- **Formatação numérica BR:** `.` como separador milhar, `,` como decimal

---

## Snippets Úteis

### Haversine (km)
```python
def haversine_km(lat1, lon1, lat2, lon2):
    R = 6371.0
    dlat = np.radians(lat2 - lat1)
    dlon = np.radians(lon2 - lon1)
    a = (np.sin(dlat/2)**2 + np.cos(np.radians(lat1)) * np.cos(np.radians(lat2)) * np.sin(dlon/2)**2)
    return R * 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))
```

### Curva Bézier quadrática (50 pontos)
```python
t = np.linspace(0, 1, 50)
mx, my = (ox + dx) / 2, (oy + dy) / 2
dix, diy = dx - ox, dy - oy
dist = np.hypot(dix, diy)
curvature = 0.0005 * dist
cpx = mx - diy * curvature
cpy = my + dix * curvature
bx = (1-t)**2 * ox + 2*(1-t)*t * cpx + t**2 * dx
by = (1-t)**2 * oy + 2*(1-t)*t * cpy + t**2 * dy
```

### Projetar ponto no segmento mais próximo
```python
def project_point_to_segment(px, py, ax, ay, bx, by):
    abx, aby = bx - ax, by - ay
    apx, apy = px - ax, py - ay
    t = (apx*abx + apy*aby) / (abx*abx + aby*aby + 1e-12)
    t = np.clip(t, 0, 1)
    cx = ax + t*abx
    cy = ay + t*aby
    dist = haversine_km(cy, cx, py, px)
    return (cx, cy), dist
```

### Loading SP Boundary (com cache e fallback IBGE)
Usar `load_sp_state()` dos scripts existentes — baixa do IBGE se cache não existir.

---

## Como Adicionar Novas Funcionalidades

1. **Nova rota ferroviária:** adicionar tupla de coordenadas `(lat, lon)` em `ROUTE_DEFS` com nome e cor
2. **Nova cidade:** adicionar em `STRATEGIC_CITIES` e/ou `ROUTE_CITIES`
3. **Nova rodovia:** adicionar entrada em `ROAD_GROUPS` com código, fonte e cor
4. **Novo tipo de mapa:** criar função `gerar_mapa_*()` seguindo o padrão: load data → setup dark ax → plot → save PNG
5. **Alterar tema:** modificar `setup_dark_ax()` e/ou constantes de cor
6. **Cores existentes:** usar sempre as hex definidas na paleta para consistência visual

---

## Comandos de Verificação

```bash
# Rodar todos os mapas
python mapas_estaticos.py
python mapas_estaticos_original.py
python mapas_rodoviario.py
```

Arquivos gerados: `mapa_fluxo_comercial.png`, `mapa_composicao_emprego.png`, `mapa_fluxo_passageiros.png`, `mapa_precos_trechos.png`, `mapa_rodoviario.png`
