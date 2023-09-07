
import streamlit as st
import requests
import json
import pandas as pd
import plotly.express as px
import base64
import openpyxl
import io

anos=['2023']

#função 1  -----------------------------------------------------------------------------

def despesas_dep (ano, ids):
  despesas = pd.DataFrame()

  for ano in ano:
      for i in ids:
          gasto=1
          pagina =1
          while gasto !=[]:
              try:
                  url='https://dadosabertos.camara.leg.br/api/v2/deputados/'+str(i)+'/despesas?ano='+str(ano)+'&pagina='+str(pagina)+'&ordem=ASC&ordenarPor=ano'
                  resposta   = requests.request("GET", url)
                  objetos    = json.loads(resposta.text)
                  gasto     = objetos['dados']
                  df_gasto = pd.DataFrame(gasto)
                  df_gasto['ID_PARLAMENTAR'] = i
                  despesas = pd.concat([despesas, df_gasto], ignore_index=True)

                  pagina=pagina+1

              except requests.exceptions.RequestException:
                  pass


  return despesas




#-------------------------------------------
#função 2---------------------------------

def criar_grafico_1 (despesas):
  #Criar graáfico agrupando por tipo de despesas de Cada grupo.
  # Agrupe os dados por 'tipoDespesa' e 'tipoDocumento' e some o 'valorLiquido'
  df_grouped = despesas.groupby(['tipoDespesa', 'tipoDocumento'])['valorLiquido'].sum().reset_index()

  # Crie um gráfico de colunas interativo
  fig = px.bar(df_grouped, x='valorLiquido', y='tipoDocumento', color='tipoDespesa',
              labels={'valorLiquido': 'Soma do Valor Líquido', 'tipoDocumento': 'Tipo de Documento'},
              title='Soma do Valor Líquido por Tipo de Despesa e Tipo de Documento',
              orientation='h')

  # Personalize o gráfico
  fig.update_yaxes(categoryorder='total ascending')
  fig.update_xaxes(title_text='Soma do Valor Líquido')
  fig.update_yaxes(title_text='Tipo de Documento')
  fig.update_layout(legend_title_text='Tipo de Despesa')

  # Exiba o gráfico interativo
  return fig

#funcao 3 -------------------

def criar_grafico_2(despesas):

  # Supondo que seu DataFrame seja chamado 'despesas'
  # Agrupe os dados por 'nomeFornecedor' e some o 'valorLiquido'
  df_grouped = despesas.groupby('nomeFornecedor')['valorLiquido'].sum().reset_index()

  # Ordene o DataFrame pelos maiores valores líquidos
  df_grouped = df_grouped.sort_values(by='valorLiquido', ascending=False)

  # Pegue os 10 maiores fornecedores
  top_10_fornecedores = df_grouped.head(10)

  # Crie um gráfico de colunas interativo
  fig_2 = px.bar(top_10_fornecedores, y='nomeFornecedor', x='valorLiquido',
              labels={'valorLiquido': 'Total do Valor Líquido', 'nomeFornecedor': 'Fornecedor'},
              title='Top 10 Maiores Fornecedores por Valor Líquido',
              text='valorLiquido', orientation='h')

  # Personalize o gráfico
  fig_2.update_traces(texttemplate='%{text:.2s}', textposition='outside')
  fig_2.update_xaxes(title_text='Total do Valor Líquido')
  fig_2.update_yaxes(title_text='Fornecedor')
  fig_2.update_layout(legend_title_text='Fornecedor')

  # Exiba o gráfico interativo
  return fig_2

#------------------------------------FUNÇÃO 3 --------------------------------



def listar_notas(selected_fornecedor, despesas):
    notas_relacionadas = list(despesas[(despesas['nomeFornecedor'].str.contains(selected_fornecedor, case=False))
                                       & (despesas['urlDocumento'].notnull())]['urlDocumento'])

    if not notas_relacionadas:
        return None

    return notas_relacionadas




# CRIANDO CONEXAO COM API EXTRAIR DADOS DEPUTADOS
url = 'https://dadosabertos.camara.leg.br/api/v2/deputados'
resposta = requests.get(url)
resposta.raise_for_status()  # Verifica se houve erros na solicitação
objetos = json.loads(resposta.text)
dados_T = objetos['dados']

# Data Frame dos dados do parlamentar
df_deputados = pd.DataFrame(dados_T)

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


        despesas  = despesas_dep(anos,ids)
        fig  = criar_grafico_1(despesas)
        fig_2 =criar_grafico_2(despesas)
        st.plotly_chart(fig)
        st.plotly_chart(fig_2)
        # Crie a lista de top 10 fornecedores aqui
        top_10_fornecedores = despesas.groupby('nomeFornecedor')['valorLiquido'].sum().reset_index()
        top_10_fornecedores = top_10_fornecedores.sort_values(by='valorLiquido', ascending=False).head(10)

        # Exibir a selectbox dos top 10 fornecedores
        st.sidebar.markdown("## Top 10 Maiores Fornecedores")
        top_10_fornecedores_list = top_10_fornecedores['nomeFornecedor'].tolist()
        selected_fornecedor = st.sidebar.selectbox('Selecione um fornecedor', top_10_fornecedores_list)

        if selected_fornecedor:
          # Chame a função listar_notas com o fornecedor selecionado
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





        # Add a sidebar section for download
        st.sidebar.markdown("## Download Data")

        if st.sidebar.button("Gerar despesas em excel"):
            # Create a streamlit StringIO object to store the Excel data
            excel_buffer = io.BytesIO()
            with pd.ExcelWriter(excel_buffer, engine="openpyxl") as writer:
                despesas.to_excel(writer, index=False, sheet_name="Despesas")
            excel_buffer.seek(0)

            # Set up the download link
            b64 = base64.b64encode(excel_buffer.read()).decode()
            href = f'<a href="data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,{b64}" download="despesas.xlsx">Link Baixar arquivo</a>'
            st.sidebar.markdown(href, unsafe_allow_html=True)
