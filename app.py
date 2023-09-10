import streamlit as st
import requests
import json
import pandas as pd
import plotly.express as px
import base64
import io

anos = ['2023']

# Função para buscar despesas dos deputados
@st.cache
def despesas_dep(ano, ids):
    despesas = []

    for ano in ano:
        for i in ids:
            pagina = 1
            while True:
                try:
                    url = f'https://dadosabertos.camara.leg.br/api/v2/deputados/{i}/despesas?ano={ano}&pagina={pagina}&ordem=ASC&ordenarPor=ano'
                    resposta = requests.get(url)
                    resposta.raise_for_status()
                    objetos = json.loads(resposta.text)
                    gasto = objetos['dados']

                    if not gasto:
                        break

                    despesas.extend(gasto)
                    pagina += 1

                except requests.exceptions.RequestException:
                    pass

    return pd.DataFrame(despesas)

# Função para criar o primeiro gráfico
@st.cache
def criar_grafico_1(despesas):
    df_grouped = despesas.groupby(['tipoDespesa', 'tipoDocumento'])['valorLiquido'].sum().reset_index()
    fig = px.bar(df_grouped, x='valorLiquido', y='tipoDocumento', color='tipoDespesa',
                 labels={'valorLiquido': 'Soma do Valor Líquido', 'tipoDocumento': 'Tipo de Documento'},
                 title='Soma do Valor Líquido por Tipo de Despesa e Tipo de Documento', orientation='h')
    fig.update_yaxes(categoryorder='total ascending')
    fig.update_xaxes(title_text='Soma do Valor Líquido')
    fig.update_yaxes(title_text='Tipo de Documento')
    fig.update_layout(legend_title_text='Tipo de Despesa')
    return fig

# Função para criar o segundo gráfico
@st.cache
def criar_grafico_2(despesas):
    df_grouped = despesas.groupby('nomeFornecedor')['valorLiquido'].sum().reset_index()
    df_grouped = df_grouped.sort_values(by='valorLiquido', ascending=False)
    top_10_fornecedores = df_grouped.head(10)
    fig_2 = px.bar(top_10_fornecedores, y='nomeFornecedor', x='valorLiquido',
                   labels={'valorLiquido': 'Total do Valor Líquido', 'nomeFornecedor': 'Fornecedor'},
                   title='Top 10 Maiores Fornecedores por Valor Líquido', text='valorLiquido', orientation='h')
    fig_2.update_traces(texttemplate='%{text:.2s}', textposition='outside')
    fig_2.update_xaxes(title_text='Total do Valor Líquido')
    fig_2.update_yaxes(title_text='Fornecedor')
    fig_2.update_layout(legend_title_text='Fornecedor')
    return fig_2

# Função para listar notas relacionadas a um fornecedor
def listar_notas(selected_fornecedor, despesas):
    notas_relacionadas = despesas[(despesas['nomeFornecedor'].str.contains(selected_fornecedor, case=False))
                                  & (despesas['urlDocumento'].notnull())]['urlDocumento'].tolist()
    return notas_relacionadas

# Início da aplicação Streamlit
st.title('Análise de Despesas de Deputados')

# Layout da página
st.sidebar.markdown("## Opções:")

# Caixas de seleção para partido e deputado
partidos = [''] + sorted(df_deputados['siglaPartido'].unique())
option_1 = st.sidebar.selectbox('Selecione o partido', partidos)

if option_1 != "":
    deputados_filtrados = df_deputados[df_deputados['siglaPartido'] == option_1]
    deputados = [''] + sorted(deputados_filtrados['nome'].unique())
    option_2 = st.sidebar.selectbox('Selecione o deputado', deputados)

    if option_2 != "":
        ids = list((df_deputados[df_deputados['nome'] == option_2].id))

        # Chame as funções para buscar despesas e criar gráficos
        despesas = despesas_dep(anos, ids)
        fig = criar_grafico_1(despesas)
        fig_2 = criar_grafico_2(despesas)

        # Exiba os gráficos
        st.plotly_chart(fig)
        st.plotly_chart(fig_2)

        # Exibir a selectbox dos top 10 fornecedores
        st.sidebar.markdown("## Top 10 Maiores Fornecedores")
        top_10_fornecedores_list = despesas.groupby('nomeFornecedor')['valorLiquido'].sum().nlargest(10).index.tolist()
        selected_fornecedor = st.sidebar.selectbox('Selecione um fornecedor', top_10_fornecedores_list)

        if selected_fornecedor:
            # Chame a função para listar notas relacionadas ao fornecedor selecionado
            notas_relacionadas = listar_notas(selected_fornecedor, despesas)

            if not notas_relacionadas:
                st.write("O Fornecedor não possui documentos para Visualização.")
            else:
                # Exiba as notas relacionadas
                st.write("Notas relacionadas ao fornecedor selecionado:")
                for nota in notas_relacionadas:
                    st.markdown(f"[{nota}]({nota})")
        else:
            st.write("Selecione um fornecedor antes de listar as notas.")

        # Adicione uma seção lateral para download
        st.sidebar.markdown("## Download Data")

        if st.sidebar.button("Gerar despesas em excel"):
            # Crie um objeto StringIO para armazenar os dados do Excel
            excel_buffer = io.BytesIO()
            with pd.ExcelWriter(excel_buffer, engine="openpyxl") as writer:
                despesas.to_excel(writer, index=False, sheet_name="Despesas")
            excel_buffer.seek(0)

            # Configure o link de download
            b64 = base64.b64encode(excel_buffer.read()).decode()
            href = f'<a href="data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,{b64}" download="despesas.xlsx">Link Baixar arquivo</a>'
            st.sidebar.markdown(href, unsafe_allow_html=True)
