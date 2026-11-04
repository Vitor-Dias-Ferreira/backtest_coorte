# Monthly Investment Backtest

An interactive Streamlit app that simulates fixed monthly investments in a stock using historical Yahoo Finance prices. Enter a ticker, a period, and a monthly amount, and the app shows how the portfolio would have grown.

> **Language note:** this was a university team project in Brazil, so the app's interface and code are in Portuguese.

**Presentation video:** [watch on YouTube](https://youtu.be/UNb9Th7K70s)

## Features

- **Monthly contribution simulation:** buys the asset with a fixed amount each month and tracks total invested and portfolio value.
- **Three input options:** PDF upload, CSV, Excel, or TXT upload, or a manual form.
- **Results view:** charts and a numeric summary with final value, total invested, profit, and return.
- **Downloadable report:** exports the results as a `.txt` file.

## Run it

Use Python 3.13 or earlier. The app does not run on Python 3.14.

```bash
git clone https://github.com/Vitor-Dias-Ferreira/backtest_coorte.git
cd backtest_coorte
pip install streamlit yfinance pandas PyPDF2 openpyxl
python -m streamlit run BackTestCoorte.py
```

If the default port is busy, add `--server.port 8504`.

## Input formats

The app reads these field names in Portuguese.

### PDF

The file should contain these fields:

```text
Ticket:
PETR4.SA
data de inicio:
2015-09-08
data final:
2018-09-10
aporte(R$):
500.00
```

### CSV, Excel, or TXT

```csv
ticker,investimento_inicial,aporte_mensal,data_inicial,data_final
PETR4.SA,10000,500,2015-09-08,2018-09-10
ITUB4.SA,5000,300,2016-01-01,2020-01-01
```

### Manual form

Enter the ticker (such as `PETR4.SA`), start date, end date, and monthly amount, using dates in `YYYY-MM-DD` format.

## How the simulation works

On each contribution date, the app finds the first available trading day, buys the asset at that day's closing price, and records the total invested and portfolio value.

## Limitations

- **Single asset:** each simulation covers one ticker at a time.
- **No benchmark:** results are not compared with an index or a risk-free rate.
- **No costs:** taxes and brokerage fees are not included.
- **Valuation dates:** portfolio value is recorded on contribution dates, so the last value may be earlier than the selected end date.
- **Data source:** results depend on the prices returned by Yahoo Finance.

This project is educational and is not investment advice.

## Team

Vitor Dias Ferreira, Mariana Vitoria Martins de Miranda, and Adryann Henrique Oliveira Olivatti.
