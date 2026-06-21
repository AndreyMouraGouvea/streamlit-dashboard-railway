import pandas as pd
coords = pd.read_csv('coordenadas2.csv')

targets = ['Jundiaí', 'Vinhedo', 'Valinhos', 'Campinas', 'Paulínia',
           'São José dos Campos', 'JUNDIAI', 'VINHEDO', 'VALINHOS',
           'CAMPINAS', 'PAULINIA', 'SAO JOSE DOS CAMPOS',
           'SÃO JOSÉ DOS CAMPOS']

for _, row in coords.iterrows():
    cid = str(row['Cidade'])
    for t in targets:
        if t.lower() in cid.lower():
            print(f"  '{cid}' -> ({row['Latitude']}, {row['Longitude']})")
            break
