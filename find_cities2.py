import pandas as pd
coords = pd.read_csv('coordenadas2.csv')
targets = ['Limeira', 'São Carlos', 'Araraquara', 'Ribeirão Preto',
           'LIMEIRA', 'SAO CARLOS', 'ARARAQUARA', 'RIBEIRAO PRETO']
for _, row in coords.iterrows():
    cid = str(row['Cidade'])
    for t in targets:
        if t.lower() in cid.lower():
            print(f"  '{cid}' -> ({row['Latitude']}, {row['Longitude']})")
            break
