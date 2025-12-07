import yfinance as yf
import pandas as pd
import streamlit as st
import PyPDF2
import re
import io
import time

resultado_valido = False  # util para tratar erros no codigo

# --- FUNÇÕES AUXILIARES ---

def extrair_dado_por_regex(padroes, texto_completo, converter=None):
    """Extrai um dado usando regex e aplica conversão opcional."""
    for padrao in padroes:
        resultado = re.search(padrao, texto_completo, re.IGNORECASE | re.DOTALL)
        if resultado:
            valor_encontrado = resultado.group(1).strip()
            if converter:
                return converter(valor_encontrado)
            return valor_encontrado
    return None


def converter_aporte_para_float(valor_encontrado):
    """Converte a string do aporte para float."""
    if not valor_encontrado:
        return None
    valor_encontrado = valor_encontrado.replace(",", ".").replace(" ", "")
    try:
        return float(valor_encontrado)
    except ValueError:
        return None


def converter_data_para_string_limpa(valor_encontrado):
    """Remove espaços internos da string de data."""
    if not valor_encontrado:
        return None
    return valor_encontrado.replace(" ", "")


def botao_para_download(modelo, ticker, data_inicial, data_final, aporte_mes):
    documento = f"""
============================================================
                📊 RELATÓRIO DO BACKTEST COMPLETO
============================================================

✔️ Aplicação realizada com sucesso!

📌 Parâmetros Utilizados
- Modelo: {modelo} 
- Ticker: {ticker}
- Data inicial: {data_inicial}
- Data final: {data_final}
- Aporte Mensal: R$ {aporte_mes:,.2f}
------------------------------------------------------------
💰 RESUMO FINAL
- Patrimônio Final: R$ {patrimonio_final:,.2f}
- Total Aportado: R$ {investido_final:,.2f}
- Lucro Bruto: R$ {lucro_bruto:,.2f}
- Rentabilidade: {rentabilidade:,.2f}%

============================================================
"""

    buffer = io.BytesIO()
    buffer.write(documento.encode("utf-8"))  # converte string para bytes
    buffer.seek(0)
    key_download = f"download_button_{ticker}_{data_inicial}"

    st.download_button(
        label="📥 Baixar TXT",
        data=buffer,
        file_name="relatorio.txt",
        mime="text/plain",
        key=key_download
    )


# --- CLASSE DE BACKTESTING ---

class Backtest:
    def __init__(self):
        self.dados = None
        self.ticker_usado = None

    def carregar_dados(self, ticker, start, end):
        #Baixa dados de fechamento do Yahoo Finance, limpa ela e isola em uma unica coluna com preço de fechamento
        try:
            dados_brutos = yf.download(ticker, start=start, end=end)
            dados_limpos = dados_brutos[['Close']].copy()
            dados_limpos.columns = ['Preco']
            self.dados = dados_limpos.dropna()

            if self.dados.empty:
                st.error("Nenhum dado encontrado para o ticker e período informados.")
                return pd.DataFrame()

            self.ticker_usado = ticker
            return self.dados
        except Exception as e:
            st.error(f"Erro ao baixar dados para {ticker}: {e}")
            return pd.DataFrame()

    def simulador_d_carteira(self, aporte, data_inicial_simulacao, data_final_simulacao):
        #Simula a evolução da carteira com aportes mensais fixos
        if self.dados is None or self.dados.empty:
            return pd.DataFrame()

        self.dados = self.dados.sort_index()

        data_inicial_dt = pd.to_datetime(data_inicial_simulacao)
        data_final_dt = pd.to_datetime(data_final_simulacao)

        D_aporte_base = pd.date_range(
            start=data_inicial_dt.normalize(),
            end=data_final_dt.normalize(),
            freq='MS'
        )
        D_aporte = D_aporte_base.tolist()

        if D_aporte and data_inicial_dt > D_aporte[0]:
            D_aporte[0] = data_inicial_dt
        elif not D_aporte and data_inicial_dt <= data_final_dt:
            D_aporte.append(data_inicial_dt)

        D_aporte = [d for d in D_aporte if d <= data_final_dt]

        if not D_aporte:
            return pd.DataFrame()

        dados_filtrados = self.dados[
            (self.dados.index >= data_inicial_dt) &
            (self.dados.index <= data_final_dt)
        ]

        if dados_filtrados.empty:
            return pd.DataFrame()

        lista_evolu = []
        T_investido = 0
        T_cts = 0

        for data_alvo in D_aporte:
            try:
                idx_pos = dados_filtrados.index.searchsorted(data_alvo)

                if idx_pos >= len(dados_filtrados.index):
                    break

                data_valida = dados_filtrados.index[idx_pos]

                if data_valida > data_final_dt:
                    break

                Preco_dia = dados_filtrados.loc[data_valida, 'Preco']

            except Exception:
                continue

            cts_compradas = aporte / Preco_dia
            T_cts += cts_compradas
            T_investido += aporte

            patrimonio = T_cts * Preco_dia

            lista_evolu.append({
                'Data': data_valida,
                'Total Investido': T_investido,
                'Patrimônio': patrimonio
            })

        if not lista_evolu:
            return pd.DataFrame()

        df_resultado = pd.DataFrame(lista_evolu).set_index('Data')
        return df_resultado


# --- FUNÇÃO DE EXIBIÇÃO ---

def exibir_resultados(df_resultado, ticker_usado):
    #conversa com o front-end e plota os graficos da evolução patrimonial
    st.subheader("Evolução do Patrimônio:")

    df_chart = df_resultado.rename(columns={
        'Patrimônio': 'Patrimônio Total',
        'Total Investido': 'Capital Aportado'
    })

    st.line_chart(df_chart[['Patrimônio Total', 'Capital Aportado']])

    st.write("### 💰 Resumo Final")

    final_data = df_resultado.iloc[-1]

    global patrimonio_final, investido_final, lucro_bruto, rentabilidade
    patrimonio_final = final_data['Patrimônio']
    investido_final = final_data['Total Investido']
    lucro_bruto = patrimonio_final - investido_final
    rentabilidade = (patrimonio_final / investido_final - 1) * 100 if investido_final > 0 else 0

    col1, col2, col3 = st.columns(3)
    global resultado_valido
    resultado_valido = True

    def formatar_moeda(valor):
        return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

    col1.metric("Patrimônio Final", formatar_moeda(patrimonio_final))
    col2.metric("Total Aportado", formatar_moeda(investido_final))
    col3.metric("Lucro Líquido", formatar_moeda(lucro_bruto), f"{rentabilidade:.2f}%")

    with st.expander("Ver Tabela Completa"):
        st.dataframe(df_resultado)


# --- FUNÇÃO PRINCIPAL ---

def executar_backtest(ticker, data_inicial, data_final, aporte):
    #organiza toda a execução do backtest 
    global resultado_valido
    resultado_valido = False

    if not all([ticker, data_inicial, data_final, aporte]):
        st.error("Todos os parâmetros (Ticker, Datas, Aporte) devem ser fornecidos.")
        return

    meu_robo = Backtest()
    st.info("Baixando dados")

    tabela_resultado = meu_robo.carregar_dados(ticker, data_inicial, data_final)

    if tabela_resultado.empty:
        st.error("Erro ao baixar ou dados insuficientes. Verifique o ticker e o intervalo.")
        resultado_valido = False
        return

    st.success("Dados baixados com sucesso! Calculando simulação...")

    resultado_final = meu_robo.simulador_d_carteira(aporte, data_inicial, data_final)

    if resultado_final.empty:
        st.error("Resultado do backtesting vazio. Verifique se o período possui dados válidos.")
        resultado_valido = False
        return
    #passa os parameetros pra função exibir_resultados funcionar
    exibir_resultados(resultado_final, meu_robo.ticker_usado)


# --- INTERFACE PRINCIPAL ---

st.header("📊 Bem vindo ao Backtest Coorte")
#recomendação de formato pro usuario
st.write("""
 --> O formato de entrada para pdf deve ser da forma:

 Ticket :\n
XXXX.SA\n
data de inicio:\n
YYYY-MM-DD\n
data final:\n
YYYY-MM-DD\n
aporte(R$):\n
NNN.NN\n
""")

st.write("""
 --> Exemplo:

Ticket :\n
PETR4.SA\n
data de inicio:\n
2015-09-08\n
data final:\n
2018-09-10\n
aporte(R$):\n
500.00 📍\n
""")

st.write("O manual é só inserir os valores desejados 📌")
st.header("Aproveite nosso aplicativo ✔️")

st.sidebar.header("Selecione as Opções")

opcao_selecionada = st.sidebar.selectbox(
    "Escolha o modelo no qual você quer fazer o backtest:",
    ["Upload PDF", "Upload CSV/Excel/TXT", "Manual (Formulário)"]
)


# --- OPÇÃO PDF ---

if opcao_selecionada == "Upload PDF":

    arquivo_pdf_enviado = st.sidebar.file_uploader("Envie o arquivo PDF", type=["pdf"])

    if arquivo_pdf_enviado:
        executar_pdf = st.sidebar.button("Executar Backtest")

        if executar_pdf:
            with st.spinner("Extraindo texto do PDF..."):
                leitor_pdf = PyPDF2.PdfReader(arquivo_pdf_enviado)
                texto_extraido_completo = ""

                for pagina in leitor_pdf.pages:
                    texto_extraido_completo += pagina.extract_text() + "\n"

            st.subheader("Texto extraído do PDF:")
            st.text(texto_extraido_completo)

            padroes_ticker = [r"ticket[:\s]*([\w\.]+)"]
            padroes_data_inicial = [
                r"data\s+de\s+in[ií]cio\s*[:\s]*([\d\s-]+)",
                r"data\s+inicial\s*[:\s]*([\d\s-]+)"
            ]
            padroes_data_final = [r"data\s+final\s*[:\s]*([\d\s-]+)"]
            padroes_aporte = [
                r"aporte\s*\(R\$\)\s*[:\s]*(\d+[.,]?\d*)",
                r"aporte\s*mensal\s*.*?(\d+[.,]?\d*)",
                r"aporte\s*.*?(\d+[.,]?\d*)",
                r"valor\s*do\s*aporte\s*.*?(\d+[.,]?\d*)",
                r"mensal\s*.*?(\d+[.,]?\d*)"
            ]

            ticker_encontrado = extrair_dado_por_regex(padroes_ticker, texto_extraido_completo)
            data_inicial_encontrada = extrair_dado_por_regex(
                padroes_data_inicial, texto_extraido_completo, converter=converter_data_para_string_limpa)
            data_final_encontrada = extrair_dado_por_regex(
                padroes_data_final, texto_extraido_completo, converter=converter_data_para_string_limpa)
            aporte_convertido = extrair_dado_por_regex(
                padroes_aporte, texto_extraido_completo, converter=converter_aporte_para_float)

            st.subheader("📌 Dados Encontrados no PDF")
            st.write("Ticker:", ticker_encontrado)
            st.write("Data Inicial:", data_inicial_encontrada)
            st.write("Data Final:", data_final_encontrada)
            st.write("Aporte Mensal:", aporte_convertido)

            if not all([ticker_encontrado, data_inicial_encontrada, data_final_encontrada, aporte_convertido]):
                st.error("Erro: Dados essenciais não encontrados no PDF.")
                resultado_valido = False
            else:
                executar_backtest(
                    ticker_encontrado,
                    data_inicial_encontrada,
                    data_final_encontrada,
                    aporte_convertido
                )

            if resultado_valido:
                file = open("Relatorio Simples PDF.txt", "w+", encoding="utf-8")
                file.write(f"""
============================================================
                📊 RELATÓRIO DO BACKTEST SIMPLES
============================================================
💰 RESUMO FINAL
- Patrimônio Final: R$ {patrimonio_final:,.2f}
- Total Aportado: R$ {investido_final:,.2f}
============================================================
""")
                file.close()

                st.subheader("Um relatório simples do Backtest foi instalado automaticamente na pasta em que você executou o comando de entrada.")

                opcao_selecionada2 = st.selectbox(
                    "Você deseja instalar a versão completa do Backtest COORTE?",
                    ["SIM", "NAO"],
                    key="backtest_opcao_3"
                )

                if opcao_selecionada2 == "SIM":
                    botao_para_download(
                        opcao_selecionada,
                        ticker_encontrado,
                        data_inicial_encontrada,
                        data_final_encontrada,
                        aporte_convertido
                    )
                else:
                    st.write("Backtest concluído com sucesso!")

            else:
                st.warning("⚠️ O relatório não pôde ser gerado porque o backtest não foi concluído com sucesso.")


# --- OPÇÃO FORMULÁRIO ---

elif opcao_selecionada == "Manual (Formulário)":

    ticker_digitado = st.sidebar.text_input("Ticker:", "PETR4.SA")
    data_inicial_digitada = st.sidebar.text_input("Data inicial:", "2010-01-01")
    data_final_digitada = st.sidebar.text_input("Data final:", "2025-01-01")
    aporte_digitado = st.sidebar.number_input("Aporte Mensal (R$):", value=500.00, step=50.00)

    botao_executar_manual = st.sidebar.button("Executar")

    if botao_executar_manual:

        progress_bar = st.progress(0)

        executar_backtest(
            ticker_digitado,
            data_inicial_digitada,
            data_final_digitada,
            aporte_digitado
        )

        if resultado_valido:
            file = open("Relatorio Simples Manual.txt", "w+" , encoding="utf-8")
            file.write(f"""
============================================================
                📊 RELATÓRIO DO BACKTEST SIMPLES
============================================================
💰 RESUMO FINAL
- Patrimônio Final: R$ {patrimonio_final:,.2f}
- Total Aportado: R$ {investido_final:,.2f}
============================================================
""")
            file.close()

            st.subheader("Um relatório simples do Backtest foi instalado automaticamente na pasta em que você executou o comando de entrada.")

            opcao_selecionada2 = st.selectbox(
                "Você deseja instalar a versão completa do Backtest COORTE?",
                ["SIM", "NAO"],
                key="chave_unica"
            )

            if opcao_selecionada2 == "SIM":
                botao_para_download(
                    opcao_selecionada,
                    ticker_digitado,
                    data_inicial_digitada,
                    data_final_digitada,
                    aporte_digitado
                )
            else:
                st.write("Backtest concluído com sucesso!")

        else:
            st.warning("⚠️ O relatório não pôde ser gerado porque o backtest não foi concluído com sucesso.")


# --- OPÇÃO CSV/EXCEL/TXT ---

elif opcao_selecionada == "Upload CSV/Excel/TXT":

    arquivo = st.sidebar.file_uploader(
        "Envie um arquivo CSV, Excel ou TXT",
        type=["csv", "xlsx", "xls", "txt"]
    )

    if arquivo:
        botao_executar = st.sidebar.button("Executar Backtest")

        if botao_executar:
            try:
                if arquivo.name.endswith(".csv"):
                    df = pd.read_csv(arquivo)
                elif arquivo.name.endswith(".txt"):
                    df = pd.read_csv(arquivo, delimiter="\t")
                else:
                    df = pd.read_excel(arquivo)

                if {"ticker", "investimento_inicial", "aporte_mensal"}.issubset(df.columns) is False:
                    st.error("Arquivo inválido. As colunas obrigatórias são: ticker, investimento_inicial, aporte_mensal.")
                else:

                    st.success("Arquivo carregado com sucesso!")
                    st.dataframe(df)

                    patrimonio_total = 0
                    total_investido = 0
                    lucro_bruto_total = 0

                    for idx, linha in df.iterrows():
                        ticker = linha["ticker"]
                        aporte = linha["aporte_mensal"]
                        investimento = linha["investimento_inicial"]

                        data_inicial = linha.get('data_inicial', '0')
                        data_final = linha.get('data_final', '0')

                        st.write(f"### 🔎 Executando backtest para: **{ticker}**")

                        executar_backtest(ticker, data_inicial, data_final, aporte)

                        if resultado_valido:
                            patrimonio_total += patrimonio_final
                            total_investido += investido_final
                            lucro_bruto_total += lucro_bruto
                            file = open("Relatorio Simples CSV.txt", "w+", encoding="utf-8")
                            file.write(f"""
============================================================
                📊 RELATÓRIO DO BACKTEST SIMPLES
============================================================
💰 RESUMO FINAL
- Patrimônio Final: R$ {patrimonio_total:,.2f}
- Total Aportado: R$ {total_investido:,.2f}
============================================================
""")
                            file.close()

                            st.subheader(
                                "Um relatório simples do Backtest foi instalado automaticamente na pasta em que você executou o comando de entrada."
                            )

                            opcao_selecionada2 = st.selectbox(
                                "Você deseja instalar a versão completa do Backtest COORTE?",
                                ["SIM", "NAO"],
                                key=f"selectbox_{ticker}"
                            )

                            if opcao_selecionada2 == "SIM":
                                botao_para_download(
                                    opcao_selecionada,
                                    ticker,
                                    data_inicial,
                                    data_final,
                                    aporte
                                )
                            else:
                                st.write("Backtest concluído com sucesso!")

                        else:
                            st.warning("⚠️ O relatório não pôde ser gerado porque o backtest não foi concluído com sucesso.")

            except Exception as e:
                st.error(f"Erro ao ler o arquivo: {e}")
