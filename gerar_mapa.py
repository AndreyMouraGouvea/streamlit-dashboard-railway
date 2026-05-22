import pandas as pd
import math
import json
import unicodedata

coords = pd.read_csv('coordenadas2.csv')
data = pd.read_csv('dados_comex_stat.csv')

def normalize(name):
    name = str(name).strip()
    for suffix in ['/SP', '/PR', ', SP', ', PR']:
        if name.endswith(suffix):
            name = name[:-len(suffix)]
    nfkd = unicodedata.normalize('NFKD', name)
    plain = nfkd.encode('ASCII', 'ignore').decode('ASCII')
    return plain.strip().lower()

coords['norm'] = coords['Cidade'].apply(normalize)
data['norm'] = data['Cidade'].apply(normalize)

def br_to_float(v):
    if isinstance(v, (int, float)):
        return float(v) if not math.isnan(float(v)) else 0.0
    s = str(v).strip()
    if not s:
        return 0.0
    return float(s.replace('.', '').replace(',', '.'))

circles = []
for idx, row in coords.iterrows():
    match = data[data['norm'] == row['norm']]
    if len(match) > 0:
        d = match.iloc[0]
        circles.append({
            'cidade': row['Cidade'].replace('"', ''),
            'norm': row['norm'],
            'lat': float(row['Latitude']),
            'lon': float(row['Longitude']),
            'valor': float(d['valor_movimentado_2025']),
            'total_empregos': br_to_float(d['total_empregos']),
        })

vals = [c['valor'] for c in circles]
min_v, max_v = min(vals), max(vals)
for c in circles:
    v = max(c['valor'], 1)
    sv = math.sqrt(v)
    sv_min = math.sqrt(max(min_v, 1))
    sv_max = math.sqrt(max(max_v, 1))
    if sv_max == sv_min:
        c['radius'] = 25
    else:
        c['radius'] = 8 + 42 * (sv - sv_min) / (sv_max - sv_min)

# --- Original Railway Route ---
original_route_coords = [
    [-23.5553, -46.6121],
    [-23.8916, -46.424],
    [-23.9608, -46.3336],
    [-23.9631, -46.3919],
    [-24.0058, -46.4028],
    [-24.0948, -46.6208],
    [-24.1856, -46.7889],
    [-24.3129, -47.0012],
    [-24.2892, -47.1744],
    [-24.2747, -47.2328],
    [-24.2814, -47.4625],
    [-24.3208, -47.6347],
    [-24.4971, -47.8449],
    [-24.6925, -48.0022],
    [-24.7358, -48.1228],
    [-25.430549900274357, -49.26646496726389],
]

# --- Specific Route: Jundiaí → Vinhedo → Valinhos → Campinas → Paulínia + ramal São José ---
cidade_coords = {}
for c in circles:
    cidade_coords[c['norm']] = (c['lat'], c['lon'], c['cidade'])

def find_city(target):
    t = unicodedata.normalize('NFKD', target).encode('ASCII', 'ignore').decode('ASCII').strip().lower()
    for norm, (lat, lon, nome) in cidade_coords.items():
        if t in norm:
            return lat, lon, nome
    return None

city_route_names = ['Jundiaí', 'Vinhedo', 'Valinhos', 'Campinas', 'Paulínia']
specific_route = []
for name in city_route_names:
    found = find_city(name)
    if found:
        specific_route.append([found[0], found[1]])
        print(f'  {name} -> {found[2]} ({found[0]:.4f}, {found[1]:.4f})')
    else:
        print(f'  WARNING: {name} not found')

# Guarulhos
guarulhos = find_city('Guarulhos')
guarulhos_coord = [guarulhos[0], guarulhos[1]] if guarulhos else None
if guarulhos:
    print(f'  Guarulhos -> {guarulhos[2]} ({guarulhos[0]:.4f}, {guarulhos[1]:.4f})')

# São José branch (via Guarulhos) - from São Paulo
sjc = find_city('São José dos Campos')
sjc_coord = [sjc[0], sjc[1]] if sjc else None
if sjc:
    print(f'  São José dos Campos -> {sjc[2]} ({sjc[0]:.4f}, {sjc[1]:.4f})')

# Interior branch cities
interior_names = ['Limeira', 'São Carlos', 'Araraquara', 'Ribeirão Preto']
interior_route = []
for name in interior_names:
    found = find_city(name)
    if found:
        interior_route.append([found[0], found[1]])
        print(f'  {name} -> {found[2]} ({found[0]:.4f}, {found[1]:.4f})')
    else:
        print(f'  WARNING: {name} not found')

# Connect from original route (near São Paulo) to Jundiaí as starting point
sp_orig = [-23.5553, -46.6121]  # SAO PAULO/SP from original route
connection_to_jundiai = [sp_orig, specific_route[0]]  # SP -> Jundiaí

# Branch from São Paulo to Guarulhos to São José dos Campos
if guarulhos and sjc:
    sjc_branch = [sp_orig, guarulhos_coord, sjc_coord]
elif sjc:
    sjc_branch = [sp_orig, sjc_coord]
else:
    sjc_branch = None

# Interior branch from Paulínia to Ribeirão Preto
if interior_route:
    paulinia_end = specific_route[-1]  # Paulínia is the last point
    interior_full = [paulinia_end] + interior_route
else:
    interior_full = None

# --- P-Median Clustering for remaining cities ---
original_norms = set()
for c in coords.head(16)['norm']:
    original_norms.add(c)

route_norms = set()
for name in city_route_names:
    found = find_city(name)
    if found:
        route_norms.add(found[0])
if guarulhos:
    route_norms.add(normalize(guarulhos[2]))
for found_name in [find_city(n) for n in interior_names]:
    if found_name:
        route_norms.add(normalize(found_name[2]))

new_cities = [c for c in circles if c['norm'] not in original_norms and c['norm'] not in route_norms]

def haversine(lat1, lon1, lat2, lon2):
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))

p = 6
new_cities.sort(key=lambda x: x['valor'], reverse=True)

if len(new_cities) >= p:
    hubs = new_cities[:p]
    remaining = new_cities[p:]

    changed = True
    max_iter = 20
    iter_count = 0
    while changed and iter_count < max_iter:
        changed = False
        iter_count += 1
        clusters = {h['norm']: [h] for h in hubs}
        for city in remaining + hubs:
            if city['norm'] in clusters:
                continue
            best_hub = min(hubs, key=lambda h: haversine(city['lat'], city['lon'], h['lat'], h['lon']))
            clusters[best_hub['norm']].append(city)

        new_hubs = []
        for hub in hubs:
            cluster_cities = clusters[hub['norm']]
            best_median = min(cluster_cities,
                key=lambda c: sum(haversine(c['lat'], c['lon'], oc['lat'], oc['lon']) for oc in cluster_cities))
            new_hubs.append(best_median)
            if best_median['norm'] != hub['norm']:
                changed = True

        if changed:
            hubs = new_hubs
            remaining = [c for c in new_cities if c['norm'] not in {h['norm'] for h in hubs}]
else:
    hubs = []

if hubs:
    clusters = {h['norm']: [h] for h in hubs}
    for city in new_cities:
        if city['norm'] not in {h['norm'] for h in hubs}:
            best_hub = min(hubs, key=lambda h: haversine(city['lat'], city['lon'], h['lat'], h['lon']))
            clusters[best_hub['norm']].append(city)

# Build branch routes from the new route to each p-median hub
all_route_coords = connection_to_jundiai + specific_route
if sjc_branch:
    all_route_coords.append(sjc_branch[1])

branch_routes = []
for hub in hubs:
    min_dist = float('inf')
    best_point = None
    for pt in all_route_coords:
        d = haversine(hub['lat'], hub['lon'], pt[0], pt[1])
        if d < min_dist:
            min_dist = d
            best_point = pt
    if best_point:
        branch = [[best_point[0], best_point[1]], [hub['lat'], hub['lon']]]
        branch_routes.append({'hub': hub, 'branch': branch, 'cluster': clusters[hub['norm']]})

# --- Generate HTML ---
mid_lat = sum(c['lat'] for c in circles) / len(circles)
mid_lon = sum(c['lon'] for c in circles) / len(circles)

def fmt_br_full(val):
    s = f'{val:,.0f}'
    return f'$ {s.replace(",", ".")}'

html_lines = []
html_lines.append('<!DOCTYPE html>')
html_lines.append('<html>')
html_lines.append('<head>')
html_lines.append('<meta http-equiv="content-type" content="text/html; charset=UTF-8" />')
html_lines.append('<script src="https://cdn.jsdelivr.net/npm/leaflet@1.9.3/dist/leaflet.js"></script>')
html_lines.append('<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/leaflet@1.9.3/dist/leaflet.css"/>')
html_lines.append('<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no" />')
html_lines.append('<style>')
html_lines.append('  html, body { width: 100%; height: 100%; margin: 0; padding: 0; }')
html_lines.append('  #map_comex { position: relative; width: 100%; height: 100%; }')
html_lines.append('  .leaflet-container { font-size: 1rem; }')
html_lines.append('</style>')
html_lines.append('</head>')
html_lines.append('<body>')
html_lines.append('<div class="folium-map" id="map_comex"></div>')
html_lines.append('<script>')
html_lines.append(f'var map_comex = L.map("map_comex", {{ center: [{mid_lat:.4f}, {mid_lon:.4f}], zoom: 8, zoomControl: true }});')
html_lines.append('')
html_lines.append('L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {')
html_lines.append('  minZoom: 0, maxZoom: 19, maxNativeZoom: 19, noWrap: false,')
html_lines.append('  attribution: "&copy; <a href=\'https://www.openstreetmap.org/copyright\'>OpenStreetMap</a> contributors",')
html_lines.append('  subdomains: "abc"')
html_lines.append('}).addTo(map_comex);')
html_lines.append('')

for i, c in enumerate(circles):
    radius = f'{c["radius"]:.2f}'
    cidade_escaped = c['cidade'].replace('\\', '\\\\').replace("'", "\\'")
    valor_str = fmt_br_full(c['valor'])
    empregos_val = int(c['total_empregos'])
    emp_str = f'{empregos_val:,}'.replace(',', '.')

    html_lines.append(f'var circle_{i} = L.circleMarker([{c["lat"]:.6f}, {c["lon"]:.6f}], {{')
    html_lines.append(f'  "bubblingMouseEvents": true, "color": "#3186cc",')
    html_lines.append(f'  "dashArray": null, "dashOffset": null, "fill": true,')
    html_lines.append(f'  "fillColor": "#3186cc", "fillOpacity": 0.6,')
    html_lines.append(f'  "radius": {radius}, "stroke": true, "weight": 2')
    html_lines.append(f'}}).addTo(map_comex);')
    html_lines.append(f'')
    html_lines.append(f'circle_{i}.bindTooltip(')
    html_lines.append(f"  '<div><b>{cidade_escaped}</b><br>Valor Movimentado (2025): {valor_str}<br>Total Empregos: {emp_str}</div>',")
    html_lines.append(f'  {{ "sticky": true }}')
    html_lines.append(f');')
    html_lines.append('')

# Original route (orange)
html_lines.append('// Original Railway Route')
html_lines.append(f'var originalRoute = L.polyline(')
html_lines.append(f'  {json.dumps(original_route_coords)},')
html_lines.append(f'  {{ "bubblingMouseEvents": true, "color": "orange", "dashArray": null, "dashOffset": null, "fill": false, "fillColor": "orange", "fillOpacity": 0.2, "lineCap": "round", "lineJoin": "round", "noClip": false, "opacity": 0.9, "smoothFactor": 1.0, "stroke": true, "weight": 5 }}')
html_lines.append(f').addTo(map_comex);')
html_lines.append('')
html_lines.append(f'originalRoute.bindTooltip("<b>Rota Original</b><br>Ferrovia Santos-Cajati", {{ "sticky": true }});')
html_lines.append('')

# Connection SP -> Jundiaí (red)
html_lines.append('// Connection to Jundiaí')
html_lines.append(f'var connToJundiai = L.polyline(')
html_lines.append(f'  {json.dumps(connection_to_jundiai)},')
html_lines.append(f'  {{ "bubblingMouseEvents": true, "color": "#E63946", "dashArray": "6, 4", "dashOffset": null, "fill": false, "lineCap": "round", "lineJoin": "round", "opacity": 0.9, "smoothFactor": 1.0, "stroke": true, "weight": 4 }}')
html_lines.append(f').addTo(map_comex);')
html_lines.append('')
html_lines.append(f'connToJundiai.bindTooltip("<b>Conexão SP → Jundiaí</b>", {{ "sticky": true }});')
html_lines.append('')

# Specific route (red solid)
html_lines.append('// Specific Route: Jundiaí → Vinhedo → Valinhos → Campinas → Paulínia')
html_lines.append(f'var specificRoute = L.polyline(')
html_lines.append(f'  {json.dumps(specific_route)},')
html_lines.append(f'  {{ "bubblingMouseEvents": true, "color": "#E63946", "dashArray": null, "dashOffset": null, "fill": false, "lineCap": "round", "lineJoin": "round", "opacity": 0.9, "smoothFactor": 1.0, "stroke": true, "weight": 5 }}')
html_lines.append(f').addTo(map_comex);')
html_lines.append('')
html_lines.append(f'specificRoute.bindTooltip("<b>Rota Estratégica</b><br>Jundiaí → Vinhedo → Valinhos → Campinas → Paulínia", {{ "sticky": true }});')
html_lines.append('')

# São José branch (dashed red/pink)
if sjc_branch:
    html_lines.append('// Branch to São José dos Campos')
    html_lines.append(f'var sjcBranch = L.polyline(')
    html_lines.append(f'  {json.dumps(sjc_branch)},')
    html_lines.append(f'  {{ "bubblingMouseEvents": true, "color": "#FF6B6B", "dashArray": "8, 6", "dashOffset": null, "fill": false, "lineCap": "round", "lineJoin": "round", "opacity": 0.8, "smoothFactor": 1.0, "stroke": true, "weight": 4 }}')
    html_lines.append(f').addTo(map_comex);')
    html_lines.append('')
    html_lines.append(f'sjcBranch.bindTooltip("<b>Ramal Leste</b><br>São Paulo → Guarulhos → São José dos Campos", {{ "sticky": true }});')
    html_lines.append('')

# Interior branch from Paulínia to Ribeirão Preto (red solid)
if interior_full:
    html_lines.append('// Interior Branch to Ribeirão Preto')
    html_lines.append(f'var interiorRoute = L.polyline(')
    html_lines.append(f'  {json.dumps(interior_full)},')
    html_lines.append(f'  {{ "bubblingMouseEvents": true, "color": "#FF6B6B", "dashArray": "8, 6", "dashOffset": null, "fill": false, "lineCap": "round", "lineJoin": "round", "opacity": 0.8, "smoothFactor": 1.0, "stroke": true, "weight": 4 }}')
    html_lines.append(f').addTo(map_comex);')
    html_lines.append('')
    html_lines.append(f'interiorRoute.bindTooltip("<b>Ramal Interior</b><br>Paulínia → Limeira → São Carlos → Araraquara → Ribeirão Preto", {{ "sticky": true }});')
    html_lines.append('')

# P-Median branch routes (pink dashed) from the strategic route
html_lines.append('// Branch Routes (P-Median)')
for idx, br in enumerate(branch_routes):
    hub_name = br['hub']['cidade'].replace("'", "\\'")
    cluster_size = len(br['cluster'])
    html_lines.append(f'var branch_{idx} = L.polyline(')
    html_lines.append(f'  {json.dumps(br["branch"])},')
    html_lines.append(f'  {{ "bubblingMouseEvents": true, "color": "#FFB3B3", "dashArray": "5, 5", "dashOffset": null, "fill": false, "lineCap": "round", "lineJoin": "round", "opacity": 0.7, "smoothFactor": 1.0, "stroke": true, "weight": 2 }}')
    html_lines.append(f').addTo(map_comex);')
    html_lines.append(f'')
    html_lines.append(f'branch_{idx}.bindTooltip("<b>Ramal: {hub_name}</b><br>{cluster_size} cidades", {{ "sticky": true }});')
    html_lines.append('')

# Legend
html_lines.append('var legend = L.control({position: "bottomright"});')
html_lines.append('legend.onAdd = function(map) {')
html_lines.append('  var div = L.DomUtil.create("div", "info legend");')
html_lines.append('  div.style.padding = "10px";')
html_lines.append('  div.style.background = "rgba(255,255,255,0.9)";')
html_lines.append('  div.style.borderRadius = "5px";')
html_lines.append('  div.innerHTML = "<h4 style=\\"margin:0 0 5px\\">Legenda</h4>" +')
html_lines.append('    "<i style=\\"background:orange;width:18px;height:4px;display:inline-block;margin-right:8px\\"></i> Rota Original<br>" +')
html_lines.append('    "<i style=\\"background:#E63946;width:18px;height:4px;display:inline-block;margin-right:8px\\"></i> Rotas Estratégicas<br>" +')
html_lines.append('    "<i style=\\"background:#FF6B6B;width:18px;height:2px;display:inline-block;margin-right:8px;border-top:2px dashed #FF6B6B\\"></i> Ramais<br>" +')
html_lines.append('    "<i style=\\"background:#3186cc;width:10px;height:10px;border-radius:50%;display:inline-block;margin-right:8px\\"></i> Cidades COMEX";')
html_lines.append('  return div;')
html_lines.append('};')
html_lines.append('legend.addTo(map_comex);')

html_lines.append('</script>')
html_lines.append('</body>')
html_lines.append('</html>')

with open('novo_mapa.html', 'w', encoding='utf-8') as f:
    f.write('\n'.join(html_lines))

cities_in_specific = [c['cidade'] for c in circles if c['norm'] in route_norms]
print(f'novo_mapa.html created with {len(circles)} circles')
print(f'Original route: {len(original_route_coords)} points')
print(f'Specific route: {len(specific_route)} points: {city_route_names}')
print(f'São José branch: {sjc is not None}')
print(f'P-Median branches: {len(branch_routes)}')
for br in branch_routes:
    names = [c['cidade'] for c in br['cluster']]
    print(f'  Hub: {br["hub"]["cidade"]} -> {len(br["cluster"])} cities')
