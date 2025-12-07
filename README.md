
# Nome dos envolvidos:
# Vitor Dias Ferreira
# Mariana Vitoria Martins de Miranda
# Adryann Henrique Oliveira Olivatti 

------------------------
# Projeto: Backtest Coorte

O **Backtesting Coorte** é uma aplicação interativa criada com **Streamlit**, que permite aos usuários realizar simulações de **backtesting de investimentos**. Através desta aplicação, o usuário pode simular a evolução do patrimônio de uma carteira de investimentos, utilizando aportes mensais fixos e dados históricos de preços de ativos financeiros. Os dados podem ser fornecidos por meio de **PDFs**, **arquivos CSV/Excel/TXT**, ou inseridos manualmente através de um formulário.

## Funcionalidades

- **Simulação de Investimentos**: Realiza a simulação de aportes mensais fixos e calcula a evolução do patrimônio ao longo do tempo, com base nos preços de fechamento do ativo.
- **Entrada de Dados**:
  - **Upload de PDF**: Extração de dados de um arquivo PDF contendo informações sobre o investimento.
  - **Upload de arquivos CSV/Excel/TXT**: Leitura de dados de arquivos CSV, Excel ou TXT.
  - **Entrada Manual**: Preenchimento de um formulário diretamente na interface para fornecer os dados necessários.
- **Exibição de Resultados**: Após a simulação, a aplicação apresenta gráficos interativos e um resumo numérico com informações sobre o patrimônio final, total investido, lucro e rentabilidade.
- **Geração de Relatório**: A aplicação gera um relatório detalhado em formato `.txt`, que pode ser baixado pelo usuário.

## Como Executar 
# O site só roda para versões do python abaixo de 3.14.0 (recomendado que seja menor ou igual a versão 3.13.5)

### 1. **Executando o Backtest com PDF**
   - Prepare um arquivo PDF com as seguintes informações:
     - **Ticket**: O código do ativo (ex: PETR4.SA).
     - **Data de início**: A data de início do período de simulação (formato: YYYY-MM-DD).
     - **Data final**: A data de término do período de simulação (formato: YYYY-MM-DD).
     - **Aporte (R$)**: O valor a ser investido mensalmente.
   - Faça o **upload** do PDF na aplicação.
   - Clique em **"Executar Backtest"** para realizar a simulação.
   Ex:
  Ticket : 
  PETR4.SA 
  data de inicio: 
  2015-09-08 
  data final: 
  2018-09-10 
  aporte(R$): 
  500.00

### 2. **Executando o Backtest com Arquivo CSV/Excel/TXT**
   - Prepare um arquivo com as seguintes colunas:
     - **ticker**: O código do ativo (ex: PETR4.SA).
     - **investimento_inicial**: O valor inicial investido.
     - **aporte_mensal**: O valor a ser aportado mensalmente.
   - Faça o **upload** do arquivo CSV, Excel ou TXT na aplicação.
   - Clique em **"Executar Backtest"** para realizar a simulação.
   Ex:
ticker,investimento_inicial,aporte_mensal,data_inicial,data_final
PETR4.SA,10000,500,2015-09-08,2018-09-10
ITUB4.SA,5000,300,2016-01-01,2020-01-01
VALE3.SA,20000,1000,2017-05-15,2022-05-15
B3SA3.SA,15000,700,2018-07-20,2023-07-20




### 3. **Executando o Backtest Manualmente**
   - Insira os dados manualmente:
     - **Ticker**: O código do ativo (ex: PETR4.SA).
     - **Data inicial**: A data de início do período de simulação (formato: YYYY-MM-DD).
     - **Data final**: A data de término do período de simulação (formato: YYYY-MM-DD).
     - **Aporte Mensal (R$)**: O valor a ser investido mensalmente.
   - Clique em **"Executar"** para realizar a simulação.

## Como Rodar o Projeto

### 1. **Instalando Dependências**

Primeiro, você precisa instalar as dependências necessárias. Para isso, basta rodar o seguinte comando no terminal:

pip install yfinance pandas streamlit PyPDF2

### 2. **Importando Bibliotecas**

import yfinance as yf  
import pandas as pd 
import streamlit as st  
import PyPDF2  
import re 
import io  
import time  

### 3. **Executando o código no terminal**
Entre no diretório(pasta) em que o arquivo está instalado atraves do comando "cd ..."
Execute o codigo :
 
streamlit run app.py (App é o nome generico do arquivo do Backtest)
Se não der certo , tente:
python -m streamlit run app.py
se não der certo , tente:
streamlit run app.py --server.port 8504


-----

### Link para video de apresentação:

https://youtu.be/UNb9Th7K70s?si=kd9iOSqOcP5EvGiX
