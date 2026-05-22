import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import streamlit as st
import streamlit.components.v1 as components
import matplotlib.ticker as ticker

st.set_page_config(layout='wide')

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Source+Code+Pro:wght@400;600&display=swap');

html, body, [class*="css"] {
    font-family: 'Source Code Pro', monospace;
}
</style>
""", unsafe_allow_html=True)

@st.cache_data
def load_data():
    df = pd.read_csv('dados_comex_stat.csv')
    num_cols = ['valor_movimentado_2025', 'valor_movimentado_2026', 'valor_movimentado_total',
                'empregos_agropecuaria', 'empregos_industria', 'empregos_construção',
                'empregos_comercio', 'empregos_servicos', 'total_empregos']
    for col in num_cols:
        if col in df.columns:
            df[col] = (
                df[col]
                .astype(str)
                .str.replace('.', '', regex=False)
                .str.replace(',', '.', regex=False)
            )
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    return df

def br_num(val):
    s = f'{val:,.0f}'
    return s.replace(',', '.')

def br_money(val):
    s = f'{val:,.2f}'
    partes = s.split('.')
    int_part = partes[0].replace(',', '.')
    return f'$ {int_part},{partes[1]}'

df = load_data()

st.sidebar.header('Filtros')

filtered = df.copy()

cidades = ['Todas'] + sorted(filtered['Cidade'].unique().tolist())
cidade = st.sidebar.selectbox('Cidade:', cidades)

if cidade != 'Todas':
    filtered = filtered[filtered['Cidade'] == cidade]

min_valor = float(filtered['valor_movimentado_2025'].min())
max_valor = float(filtered['valor_movimentado_2025'].max())

valor_range = st.sidebar.slider(
    'Faixa de valor ($):',
    min_value=min_valor,
    max_value=max_valor,
    value=(min_valor, max_valor)
)
c1, c2 = st.sidebar.columns(2)
c1.markdown(f'**Mín:** {br_money(valor_range[0])}')
c2.markdown(f'**Máx:** {br_money(valor_range[1])}', unsafe_allow_html=True)

filtered = filtered[
    (filtered['valor_movimentado_2025'] >= valor_range[0]) &
    (filtered['valor_movimentado_2025'] <= valor_range[1])
]

min_empregos = int(filtered['total_empregos'].min())
max_empregos = int(filtered['total_empregos'].max())

empregos_range = st.sidebar.slider(
    'Faixa de empregos:',
    min_value=min_empregos,
    max_value=max_empregos,
    value=(min_empregos, max_empregos)
)
c3, c4 = st.sidebar.columns(2)
c3.markdown(f'**Mín:** {br_num(empregos_range[0])}')
c4.markdown(f'**Máx:** {br_num(empregos_range[1])}')

filtered = filtered[
    (filtered['total_empregos'] >= empregos_range[0]) &
    (filtered['total_empregos'] <= empregos_range[1])
]

excluir_cidades = st.sidebar.multiselect(
    'Excluir cidades das análises:',
    options=sorted(filtered['Cidade'].unique().tolist()),
    default=[],
    placeholder='Selecione as opções'
)
filtered = filtered[~filtered['Cidade'].isin(excluir_cidades)]

st.header('DASHBOARD COMEX - ESTUDO FERROVIA SANTOS X CAJATI')

with open('novo_mapa.html', 'r', encoding='utf-8') as f:
    html_data = f.read()
st.components.v1.html(html_data, height=550)

col1, col2, col3, col4 = st.columns(4, border=True)
with col1:
    total_valor = filtered['valor_movimentado_2025'].sum()
    st.metric('Valor Movimentado 2025', br_money(total_valor))
with col2:
    total_empregos = int(filtered['total_empregos'].sum())
    st.metric('Total de Empregos', br_num(total_empregos))
with col3:
    qtd_cidades = len(filtered)
    st.metric('Cidades Analisadas', qtd_cidades)
with col4:
    media_valor = filtered['valor_movimentado_2025'].mean()
    st.metric('Média por Cidade', br_money(media_valor))

if filtered.empty:
    st.warning('Nenhum dado encontrado para os filtros selecionados.')
else:
    left, right = st.columns(2, border=True)

    fig, ax = plt.subplots(figsize=(10, 6))
    top15 = filtered.sort_values('valor_movimentado_2025', ascending=True).tail(15)
    ax.barh(top15['Cidade'], top15['valor_movimentado_2025'], color='orange')
    for i, v in enumerate(top15['valor_movimentado_2025']):
        ax.text(v + 1, i, br_money(v), va='center', color='white', fontsize=8)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.grid(axis='x', linestyle='--', alpha=0.4)
    ax.set_facecolor('#0E1117')
    ax.grid(True, alpha=0.3)
    fig.patch.set_facecolor('#0E1117')
    ax.set_xlabel('Valor Movimentado ($)', color='white')
    ax.tick_params(axis='both', colors='white')
    ax.xaxis.set_major_formatter(ticker.FuncFormatter(lambda x, pos: br_money(x)))
    ax.set_title('Top 15 Cidades por Valor Movimentado (2025)', color='white')
    left.pyplot(fig)

    emp_sectors = ['empregos_agropecuaria', 'empregos_industria', 'empregos_construção',
                   'empregos_comercio', 'empregos_servicos']
    sector_totals = filtered[emp_sectors].sum()
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.set_facecolor('#0E1117')
    fig.patch.set_facecolor('#0E1117')
    colors_sector = ['#2ECC71', '#3498DB', '#E74C3C', '#F39C12', '#9B59B6']
    wedges, texts, autotexts = ax.pie(
        sector_totals.values,
        labels=sector_totals.index.str.replace('empregos_', '').str.capitalize(),
        autopct='%1.1f%%',
        colors=colors_sector,
        textprops={'color': 'white', 'fontsize': 9}
    )
    for at in autotexts:
        at.set_color('white')
    ax.set_title('Distribuição de Empregos por Setor', color='white')
    right.pyplot(fig)

    left2, right2 = st.columns(2, border=True)

    fig, ax = plt.subplots(figsize=(10, 6))
    ax.set_facecolor('#0E1117')
    fig.patch.set_facecolor('#0E1117')
    ax.scatter(
        filtered['total_empregos'],
        filtered['valor_movimentado_2025'],
        alpha=0.6, s=100, c='orange'
    )
    for _, row in filtered.iterrows():
        ax.annotate(
            row['Cidade'].split('/')[0] if '/' in str(row['Cidade']) else str(row['Cidade'])[:12],
            (row['total_empregos'], row['valor_movimentado_2025']),
            fontsize=7, color='white', alpha=0.7
        )
    ax.set_xlabel('Total de Empregos', color='white')
    ax.set_ylabel('Valor Movimentado ($)', color='white')
    ax.tick_params(axis='both', colors='white')
    ax.grid(True, alpha=0.3)
    ax.xaxis.set_major_formatter(ticker.FuncFormatter(lambda x, pos: br_num(x)))
    ax.yaxis.set_major_formatter(ticker.FuncFormatter(lambda x, pos: br_money(x)))
    ax.set_title('Relação Empregos vs Valor Movimentado', color='white')
    left2.pyplot(fig)

    fig, ax = plt.subplots(figsize=(10, 6))
    ax.set_facecolor('#0E1117')
    fig.patch.set_facecolor('#0E1117')
    sorted_val = filtered.sort_values('valor_movimentado_2025', ascending=False).head(10)
    ax.bar(sorted_val['Cidade'], sorted_val['valor_movimentado_2025'], color='#3186cc', alpha=0.8)
    ax.tick_params(axis='x', rotation=45, colors='white')
    ax.tick_params(axis='y', colors='white')
    ax.set_xlabel('Cidade', color='white')
    ax.set_ylabel('Valor Movimentado ($)', color='white')
    ax.grid(True, axis='y', alpha=0.3)
    ax.yaxis.set_major_formatter(ticker.FuncFormatter(lambda x, pos: br_money(x)))
    ax.set_title('Top 10 Cidades (2025)', color='white')
    right2.pyplot(fig)

    left3, right3 = st.columns(2, border=True)

    fig, ax = plt.subplots(figsize=(10, 6))
    ax.set_facecolor('#0E1117')
    fig.patch.set_facecolor('#0E1117')
    sorted_emp = filtered.sort_values('total_empregos', ascending=True).tail(10)
    ax.barh(sorted_emp['Cidade'], sorted_emp['total_empregos'], color='#2ECC71')
    for i, v in enumerate(sorted_emp['total_empregos']):
        ax.text(v + 1, i, br_num(v), va='center', color='white', fontsize=8)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.grid(axis='x', linestyle='--', alpha=0.4)
    ax.set_facecolor('#0E1117')
    fig.patch.set_facecolor('#0E1117')
    ax.set_xlabel('Total de Empregos', color='white')
    ax.tick_params(axis='both', colors='white')
    ax.xaxis.set_major_formatter(ticker.FuncFormatter(lambda x, pos: br_num(x)))
    ax.set_title('Top 10 Cidades por Empregos', color='white')
    left3.pyplot(fig)

    crescimento = filtered.copy()
    crescimento['crescimento'] = (
        (crescimento['valor_movimentado_2026'] - crescimento['valor_movimentado_2025'])
        / crescimento['valor_movimentado_2025'] * 100
    )
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.set_facecolor('#0E1117')
    fig.patch.set_facecolor('#0E1117')
    top_cresc = crescimento.sort_values('crescimento', ascending=False).head(10)
    cores = ['#2ECC71' if v >= 0 else '#E74C3C' for v in top_cresc['crescimento']]
    ax.bar(top_cresc['Cidade'], top_cresc['crescimento'], color=cores, alpha=0.8)
    ax.tick_params(axis='x', rotation=45, colors='white')
    ax.tick_params(axis='y', colors='white')
    ax.set_xlabel('Cidade', color='white')
    ax.set_ylabel('Crescimento (%)', color='white')
    ax.grid(True, axis='y', alpha=0.3)
    ax.set_title('Crescimento 2025-2026 (%) - Top 10', color='white')
    ax.axhline(y=0, color='white', linewidth=0.5)
    right3.pyplot(fig)
