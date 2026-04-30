import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path
import streamlit as st
import streamlit.components.v1 as components
import squarify
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
def loadInfo(file):
    return pd.read_excel(file)

dataRailway = loadInfo('dataRailway.xlsx')
dataDestiny = loadInfo('dataDestiny.xlsx')

def filter(dataframe, column, value):
    if value != "Todos":
        return dataframe[dataframe[column] == value]
    return dataframe

cities = ['Todos'] + list(dataRailway['ponto_origem_viagem'].unique())

fromCity = st.sidebar.selectbox('Selecione a Cidade de Origem: ', cities)


tempData = filter(dataRailway, 'ponto_origem_viagem', fromCity)
destinyCities = ['Todos'] + list(tempData['ponto_destino_viagem'].unique())
destinyCity = st.sidebar.selectbox('Selecione a Cidade de Destino: ', destinyCities)


tempData = filter(tempData, 'ponto_destino_viagem', destinyCity)
serviceCities = ['Todos'] + list(tempData['tipo_servico'].unique())
service = st.sidebar.selectbox('Selecione o Tipo de Serviço: ', serviceCities)


tempData = filter(tempData, 'tipo_servico', service)
isFreeCities = ['Todos'] + list(tempData['tipo_gratuidade'].unique())
isFree = st.sidebar.selectbox('Selecione o Tipo de Gratuidade: ', isFreeCities)


tempData = filter(tempData, 'tipo_gratuidade', isFree)
minAvgPriceCities = tempData['media_valor_passagem'].min()
maxAvgPriceCities = tempData['media_valor_passagem'].max()

avgPrice = st.sidebar.slider('Selecione a Média das Passagens: ', 
                             min_value=minAvgPriceCities,
                             max_value=maxAvgPriceCities,
                             value=(minAvgPriceCities, maxAvgPriceCities))


dataRailwayFilter = dataRailway.copy()

dataRailwayFilter = filter(dataRailwayFilter, 'ponto_origem_viagem', fromCity)
dataRailwayFilter = filter(dataRailwayFilter, 'ponto_destino_viagem', destinyCity)
dataRailwayFilter = filter(dataRailwayFilter, 'tipo_servico', service)
dataRailwayFilter = filter(dataRailwayFilter, 'tipo_gratuidade', isFree)
dataRailwayFilter = dataRailwayFilter[
    (dataRailwayFilter['media_valor_passagem'] >= avgPrice[0]) &
    (dataRailwayFilter['media_valor_passagem'] <= avgPrice[1])]

if fromCity == destinyCity and fromCity != "Todos":
    st.warning('Selecione cidades diferentes')
    
elif len(dataRailwayFilter) == 0:
    st.warning('Nenhuma viagem encontrada')
    
else:
    st.header('DASHBOARD ESTUDO DE VIABILIDADE FERROVIA SÃO PAULO X CURITIBA')
    with open('Ferrovia_Santos_Cajati.html','r',encoding='utf-8') as f:
        htmlData = f.read()

    st.components.v1.html(htmlData, height=600)
        
    cityTicket = dataRailwayFilter.groupby('ponto_origem_viagem')['quantidade_bilhetes'].sum().sort_values()
    left, right = st.columns(2, border=True)

    # GRAPH 01
    fig, ax = plt.subplots(figsize=(10,6))
    ax.barh(cityTicket.index,cityTicket.values, color='orange')
    for i, a in enumerate(cityTicket.values):
        ax.text(a + 1, i, str(a), va='center', color='white')
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.grid(axis='x', linestyle='--', alpha=0.4)
    ax.set_facecolor('#0E1117')
    ax.grid(True, alpha=0.3)
    fig.patch.set_facecolor('#0E1117')
    ax.set_xlabel('Total de Passagens', color='white')
    ax.tick_params(axis='both', colors='white')
    ax.set_title('Passagens por Cidade de Origem', color='white')
    left.pyplot(fig)

    # GRAPH 02
    servicePrice = dataRailwayFilter.groupby('tipo_servico')['media_valor_passagem'].mean()
    fig, ax = plt.subplots(figsize = (11,6))
    ax.set_facecolor('#0E1117')
    fig.patch.set_facecolor('#0E1117')
    ax.plot(servicePrice.index, servicePrice.values, color='orange')
    ax.set_xlabel('Total de Passagens', color='white')
    for x, y in zip(servicePrice.index, servicePrice.values):
        ax.text(
            x,
            y + 1,
            f'R$ {y:.2f}',
            color='white',
            ha='center'
        )
    ax.tick_params(axis='both', colors='white')
    ax.set_title('Média de Preço em (R$)', color='white')
    ax.set_ylabel('Passagens por Cidade de Origem', color='white')
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    right.pyplot(fig)

    left, right = st.columns(2, border=True)

    # GRAPH 03
    ticketType = dataRailwayFilter['tipo_gratuidade'].value_counts()
    fig, ax = plt.subplots(figsize=(15, 6))
    ax.set_facecolor('#0E1117')
    fig.patch.set_facecolor('#0E1117')
    ax.tick_params(axis='both', colors='white')
    ax.set_xlabel('% Gratuidade x Total de Passagens ', color='white')
    ax.set_ylabel('Passagens por Cidade de Origem', color='white')
    total = ticketType.sum()
    labels = [
        f"{label}\n{value/total*100:.1f}%" if value/total*100 > 5
        else f"{value/total*100:.1f}%"
        for label, value in zip((ticketType.index), ticketType.values)
    ]
    colors = [
    '#FF6B35',
    '#F7931E',
    '#FFD166',
    '#06D6A0',
    '#118AB2',
    '#073B4C',
    '#9B5DE5',
    '#F15BB5'
]
    squarify.plot(
        label=labels,
        sizes=ticketType.values,
        alpha=0.8,
        color=colors,
        text_kwargs={
            'color':'white'
        }
    )
    left.pyplot(fig)

    # GRAPH 04
    fig, ax = plt.subplots(figsize=(10,6))
    ax.set_title('Distribuição de Tipos de Gratuidade', color='white')
    ax.scatter(dataRailwayFilter['media_valor_passagem'],
               dataRailwayFilter['quantidade_bilhetes'],
               alpha=0.6, s=100, c='white')
    ax.set_xlabel('Preço Médio (R$)', color='white')
    ax.set_ylabel('Quantidade de Bilhetes', color='white')
    ax.tick_params(axis='both', colors='white')
    ax.set_facecolor('#0E1117')
    ax.grid(True, alpha=0.3)
    fig.patch.set_facecolor('#0E1117')
    ax.set_title('Relação entre Volume e Preço', color='white')
    right.pyplot(fig)

    # GRAPH 05
    left, right= st.columns(2, border=True, vertical_alignment='center')
    profit = dataRailwayFilter.groupby(['ponto_origem_viagem','tipo_servico'])['media_valor_total'].sum().unstack().fillna(0)
    fig, ax = plt.subplots(figsize=(10,6))
    profit.plot(kind='bar', ax=ax)
    formatter = ticker.FuncFormatter(lambda x, pos: f'{x:,.0f}'.replace(',','.'))
    ax.yaxis.set_major_formatter(formatter)
    ax.tick_params(axis='both', colors='white')
    ax.set_facecolor('#0E1117')
    fig.patch.set_facecolor('#0E1117')
    ax.set_title('Receita por Cidade e Tipo de Serviço', color='white')
    ax.set_xlabel('Cidade de Origem', color='white')
    ax.set_ylabel('Receita Total (R$)', color='white')
    ax.grid(True, alpha=0.3)
    left.pyplot(fig)