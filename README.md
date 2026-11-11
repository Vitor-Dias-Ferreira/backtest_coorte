# Monthly Investment Backtest

An interactive Streamlit app that simulates fixed monthly investments in a stock using historical Yahoo Finance prices. Enter a ticker, a period, and a monthly amount, and the app shows how the portfolio would have grown.

> **Language note:** this started as a university team project in Brazil, with the interface and code in Portuguese. Both are now in English; the input files still accept the original Portuguese field names.

**Presentation video:** [watch on YouTube](https://youtu.be/UNb9Th7K70s)

## Features

- **Monthly contribution simulation:** buys the asset with a fixed amount each month, plus an optional initial investment, and tracks the total invested and the portfolio value every trading day.
- **Benchmarks:** runs the same contributions, on the same schedule, in the **Ibovespa** and in the **CDI** (Brazil's interbank rate, from the Central Bank of Brazil), so you can see whether the stock beat the market and the risk-free alternative.
- **Annualized return (IRR):** a money-weighted return that accounts for when each contribution was made, which a simple "profit / invested" ratio does not.
- **Dividends, your choice:** by default, prices are adjusted for dividends and splits (total return, as if dividends were reinvested). Turn the option off to see the price change only.
- **Three input options:** a form, a PDF, or a CSV, Excel, or TXT file with one backtest per row.
- **Downloadable report:** a `.txt` summary, generated in your browser.

## Run it

```bash
git clone https://github.com/Vitor-Dias-Ferreira/backtest_coorte.git
cd backtest_coorte
pip install -r requirements.txt
python -m streamlit run BackTestCoorte.py
```

Tested with Python 3.14 and Streamlit 1.67. If the default port is busy, add `--server.port 8504`.

## Input formats

Field names work in English or in Portuguese.

### PDF

```text
Ticker: PETR4.SA
Start date: 2015-09-08
End date: 2018-09-10
Monthly contribution: 500.00
Initial investment: 1,000.00
```

Dates can be `YYYY-MM-DD` or `DD/MM/YYYY`. Amounts can be written as `1500`, `1,500.00`, or `1.500,00`.

### CSV, Excel, or TXT (tab-separated)

```csv
ticker,start_date,end_date,monthly_contribution,initial_investment
PETR4.SA,2015-09-08,2018-09-10,500,10000
ITUB4.SA,2016-01-01,2020-01-01,300,5000
```

The Portuguese column names (`aporte_mensal`, `investimento_inicial`, `data_inicial`, `data_final`) also work. `initial_investment` is optional.

### Form

Enter the ticker (such as `PETR4.SA`), the dates, the monthly contribution, and, optionally, an initial investment.

## How the simulation works

1. The first purchase happens on the first trading day on or after the start date, with the initial investment plus the first monthly contribution.
2. Each following month, the app buys on the first trading day of the month, at that day's closing price.
3. The portfolio is valued on every trading day until the end date, so the final value uses the last available price, not the last purchase date.
4. The benchmarks receive exactly the same amounts on the same schedule.

## Limitations

- **No costs:** taxes and brokerage fees are not included.
- **One asset per backtest:** each row or form run simulates a single ticker (plus the benchmarks).
- **Data sources:** results depend on the prices returned by Yahoo Finance and on the Central Bank of Brazil's CDI series.

This project is educational and is not investment advice.

## Team

Vitor Dias Ferreira, Mariana Vitoria Martins de Miranda, and Adryann Henrique Oliveira Olivatti.
