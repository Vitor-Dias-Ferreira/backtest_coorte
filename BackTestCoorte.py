"""Backtest Coorte: simulates monthly contributions to a stock and compares the result with the Ibovespa and the CDI.

Run with:  python -m streamlit run BackTestCoorte.py
"""
import re
from datetime import date

import pandas as pd
import requests
import streamlit as st
import yfinance as yf
from pypdf import PdfReader

IBOVESPA_TICKER = "^BVSP"
CDI_URL = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.12/dados"  # daily CDI rate, % per day (Central Bank of Brazil)
CDI_MAX_YEARS_PER_REQUEST = 9  # the API refuses daily windows longer than 10 years


class InputError(ValueError):
    """Raised when the user's input cannot be used for a backtest."""


class DataError(RuntimeError):
    """Raised when market data cannot be loaded."""


# --- PARSING ---------------------------------------------------------------

def parse_money(text):
    """Reads amounts such as '500', '500.00', '1.500,00', '1,500.00' or 'R$ 1.500'. Returns None if it can't."""
    if text is None:
        return None
    if isinstance(text, (int, float)) and not pd.isna(text):
        return float(text)
    cleaned = re.sub(r"[^\d.,-]", "", str(text))
    if not cleaned or not re.search(r"\d", cleaned):
        return None
    if "," in cleaned and "." in cleaned:
        decimal = "," if cleaned.rfind(",") > cleaned.rfind(".") else "."
        thousands = "." if decimal == "," else ","
        cleaned = cleaned.replace(thousands, "").replace(decimal, ".")
    elif "," in cleaned:
        cleaned = cleaned.replace(",", ".") if len(cleaned.rsplit(",", 1)[1]) != 3 else cleaned.replace(",", "")
    elif cleaned.count(".") > 1 or ("." in cleaned and len(cleaned.rsplit(".", 1)[1]) == 3):
        cleaned = cleaned.replace(".", "")
    try:
        return float(cleaned)
    except ValueError:
        return None


def parse_date(text):
    """Reads YYYY-MM-DD or DD/MM/YYYY. Returns a Timestamp or None."""
    if text is None or (isinstance(text, float) and pd.isna(text)):
        return None
    if isinstance(text, (pd.Timestamp, date)):
        return pd.Timestamp(text).normalize()
    text = str(text).strip()
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%Y/%m/%d", "%d-%m-%Y"):
        try:
            return pd.to_datetime(text, format=fmt)
        except ValueError:
            continue
    return None


LABELS = {
    "ticker": r"(?:ticker|ticket)",
    "start": r"(?:start\s+date|data\s+de\s+in[ií]cio|data\s+inicial)",
    "end": r"(?:end\s+date|data\s+final)",
    "monthly": r"(?:monthly\s+contribution|aporte\s+mensal|aporte)(?:\s*\(R\$\))?",
    "initial": r"(?:initial\s+investment|investimento\s+inicial)(?:\s*\(R\$\))?",
}


def extract_inputs_from_text(text):
    """Finds the backtest fields in free text, in English or Portuguese."""
    found = {}
    for field, label in LABELS.items():
        match = re.search(label + r"\s*[:\-]?\s*([^\n]+?)\s*(?:\n|$)", text, re.IGNORECASE)
        if not match or not match.group(1).strip():
            match = re.search(label + r"\s*[:\-]?\s*\n\s*([^\n]+)", text, re.IGNORECASE)
        found[field] = match.group(1).strip() if match else None
    return {
        "ticker": found["ticker"].split()[0].upper() if found["ticker"] else None,
        "start": parse_date(found["start"]),
        "end": parse_date(found["end"]),
        "monthly": parse_money(found["monthly"]),
        "initial": parse_money(found["initial"]) or 0.0,
    }


COLUMN_ALIASES = {
    "ticker": ["ticker", "ticket"],
    "start": ["start_date", "data_inicial", "data_inicio"],
    "end": ["end_date", "data_final"],
    "monthly": ["monthly_contribution", "aporte_mensal"],
    "initial": ["initial_investment", "investimento_inicial"],
}


def read_table(uploaded):
    """Reads a CSV, TXT (tab-separated) or Excel upload into rows with standard field names."""
    name = uploaded.name.lower()
    if name.endswith(".csv"):
        table = pd.read_csv(uploaded)
    elif name.endswith(".txt"):
        table = pd.read_csv(uploaded, sep="\t")
    else:
        table = pd.read_excel(uploaded)
    table.columns = [str(c).strip().lower() for c in table.columns]
    rename = {}
    for field, aliases in COLUMN_ALIASES.items():
        match = next((a for a in aliases if a in table.columns), None)
        if match:
            rename[match] = field
    table = table.rename(columns=rename)
    missing = [f for f in ("ticker", "start", "end", "monthly") if f not in table.columns]
    if missing:
        raise InputError(
            "Missing columns: " + ", ".join(COLUMN_ALIASES[f][0] for f in missing)
            + ". Expected: ticker, start_date, end_date, monthly_contribution and, optionally, initial_investment.")
    rows = []
    for _, row in table.iterrows():
        rows.append({
            "ticker": str(row["ticker"]).strip().upper(),
            "start": parse_date(row["start"]),
            "end": parse_date(row["end"]),
            "monthly": parse_money(row["monthly"]),
            "initial": parse_money(row.get("initial")) or 0.0,
        })
    return rows


def validate(inputs):
    """Checks one set of inputs and raises InputError with a plain explanation."""
    if not inputs.get("ticker"):
        raise InputError("The ticker is missing.")
    if inputs.get("start") is None or inputs.get("end") is None:
        raise InputError("Both dates are needed, in YYYY-MM-DD or DD/MM/YYYY format.")
    if inputs["start"] >= inputs["end"]:
        raise InputError("The end date must be after the start date.")
    monthly, initial = inputs.get("monthly"), inputs.get("initial") or 0.0
    if monthly is None or monthly < 0 or initial < 0:
        raise InputError("Amounts must be zero or positive numbers.")
    if monthly == 0 and initial == 0:
        raise InputError("Enter a monthly contribution, an initial investment, or both.")
    return inputs


# --- MARKET DATA -----------------------------------------------------------

@st.cache_data(ttl=3600, show_spinner=False)
def load_prices(ticker, start, end, reinvest_dividends):
    """Daily closing prices from Yahoo Finance. With reinvest_dividends, prices are adjusted for dividends and splits."""
    try:
        data = yf.download(ticker, start=start, end=end + pd.Timedelta(days=1),
                           auto_adjust=reinvest_dividends, progress=False)
    except Exception as error:  # yfinance raises many different exception types
        raise DataError(f"Could not download prices for {ticker}.") from error
    if data is None or data.empty or "Close" not in data:
        raise DataError(f"No prices found for {ticker} between {start:%Y-%m-%d} and {end:%Y-%m-%d}.")
    close = data["Close"]
    if isinstance(close, pd.DataFrame):
        close = close.iloc[:, 0]
    close = close.dropna()
    close = close[close > 0]
    close.index = pd.to_datetime(close.index).tz_localize(None).normalize()
    if close.empty:
        raise DataError(f"No valid prices for {ticker} in this period.")
    return close.sort_index()


@st.cache_data(ttl=86400, show_spinner=False)
def load_cdi_index(start, end):
    """CDI accumulated as an index (1.0 on the first day), from the Central Bank of Brazil, in windows of up to 9 years."""
    pieces = []
    window_start = start
    while window_start <= end:
        window_end = min(window_start + pd.DateOffset(years=CDI_MAX_YEARS_PER_REQUEST) - pd.Timedelta(days=1), end)
        params = {"formato": "json", "dataInicial": f"{window_start:%d/%m/%Y}", "dataFinal": f"{window_end:%d/%m/%Y}"}
        try:
            response = requests.get(CDI_URL, params=params, timeout=30)
            response.raise_for_status()
            pieces.extend(response.json())
        except (requests.RequestException, ValueError) as error:
            raise DataError("Could not download the CDI from the Central Bank of Brazil.") from error
        window_start = window_end + pd.Timedelta(days=1)
    if not pieces:
        raise DataError("The Central Bank returned no CDI data for this period.")
    rates = pd.DataFrame(pieces)
    rates["date"] = pd.to_datetime(rates["data"], format="%d/%m/%Y")
    rates["rate"] = pd.to_numeric(rates["valor"], errors="coerce") / 100
    rates = rates.dropna().drop_duplicates("date").set_index("date")["rate"].sort_index()
    return (1 + rates).cumprod()


# --- SIMULATION ------------------------------------------------------------

def contribution_dates(trading_days, start, end):
    """First trading day on or after the start date and on or after the first day of each following month."""
    targets = [start] + list(pd.date_range(start.to_period("M").to_timestamp() + pd.offsets.MonthBegin(1), end, freq="MS"))
    dates = []
    for target in targets:
        position = trading_days.searchsorted(target)
        if position < len(trading_days) and trading_days[position] <= end and trading_days[position] not in dates:
            dates.append(trading_days[position])
    return dates


def simulate(prices, start, end, monthly, initial=0.0):
    """Daily portfolio value: buys `initial` on the first date and `monthly` on each contribution date."""
    prices = prices[(prices.index >= start) & (prices.index <= end)]
    if prices.empty:
        raise DataError("There are no prices inside the chosen period.")
    dates = contribution_dates(prices.index, start, end)
    flows = pd.Series(monthly, index=pd.DatetimeIndex(dates))
    flows.iloc[0] += initial
    shares_bought = (flows / prices.reindex(flows.index)).reindex(prices.index, fill_value=0.0)
    invested = flows.reindex(prices.index, fill_value=0.0).cumsum()
    value = shares_bought.cumsum() * prices
    return pd.DataFrame({"Invested": invested, "Value": value}), flows


def xirr(flows, final_date, final_value):
    """Annualized internal rate of return of the contributions (money-weighted). None if it can't be computed."""
    dates = list(flows.index) + [final_date]
    amounts = [-a for a in flows.values] + [final_value]
    years = [(d - dates[0]).days / 365.25 for d in dates]
    if years[-1] <= 0:
        return None

    def npv(rate):
        return sum(a / (1 + rate) ** t for a, t in zip(amounts, years, strict=True))

    low, high = -0.9999, 10.0
    if npv(low) * npv(high) > 0:
        return None
    for _ in range(200):  # bisection: slow but always converges once the root is bracketed
        mid = (low + high) / 2
        if npv(low) * npv(mid) <= 0:
            high = mid
        else:
            low = mid
    return (low + high) / 2


def summarize(name, daily, flows):
    final_value = float(daily["Value"].iloc[-1])
    invested = float(daily["Invested"].iloc[-1])
    return {
        "Asset": name,
        "Final value": final_value,
        "Invested": invested,
        "Profit": final_value - invested,
        "Return on contributions": final_value / invested - 1,
        "Annualized return (IRR)": xirr(flows, daily.index[-1], final_value),
        "Last price date": daily.index[-1].date(),
    }


def run_backtest(inputs, reinvest_dividends, compare):
    """Runs one backtest and, optionally, the same contributions in the Ibovespa and the CDI."""
    validate(inputs)
    start, end = inputs["start"], inputs["end"]
    prices = load_prices(inputs["ticker"], start, end, reinvest_dividends)
    daily, flows = simulate(prices, start, end, inputs["monthly"], inputs["initial"])
    result = {"inputs": inputs, "reinvest": reinvest_dividends, "series": {inputs["ticker"]: daily},
              "summary": [summarize(inputs["ticker"], daily, flows)], "warnings": []}
    if compare:
        benchmarks = [("Ibovespa", lambda: load_prices(IBOVESPA_TICKER, start, end, True)),
                      ("CDI", lambda: load_cdi_index(start, end))]
        for name, loader in benchmarks:
            try:
                bench_daily, bench_flows = simulate(loader(), start, end, inputs["monthly"], inputs["initial"])
            except DataError as error:
                result["warnings"].append(f"{name} left out of the comparison: {error}")
                continue
            result["series"][name] = bench_daily
            result["summary"].append(summarize(name, bench_daily, bench_flows))
    return result


# --- DISPLAY ---------------------------------------------------------------

def brl(value):
    return f"R$ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def report_text(result):
    inputs = result["inputs"]
    lines = [
        "BACKTEST COORTE - REPORT",
        "=" * 60,
        f"Ticker: {inputs['ticker']}",
        f"Period: {inputs['start']:%Y-%m-%d} to {inputs['end']:%Y-%m-%d}",
        f"Monthly contribution: {brl(inputs['monthly'])}",
        f"Initial investment: {brl(inputs['initial'])}",
        f"Prices: {'adjusted, dividends reinvested' if result['reinvest'] else 'not adjusted, dividends ignored'}",
        "-" * 60,
    ]
    for row in result["summary"]:
        irr = row["Annualized return (IRR)"]
        lines += [
            row["Asset"],
            f"  Final value: {brl(row['Final value'])} (on {row['Last price date']})",
            f"  Invested: {brl(row['Invested'])}",
            f"  Profit: {brl(row['Profit'])} ({row['Return on contributions']:.2%} on contributions)",
            f"  Annualized return (IRR): {'n/a' if irr is None else f'{irr:.2%}'}",
        ]
    lines += ["-" * 60, "Taxes and brokerage fees are not included. Educational use only; not investment advice."]
    return "\n".join(lines)


def show_result(result, key):
    inputs = result["inputs"]
    st.subheader(f"{inputs['ticker']}: {inputs['start']:%Y-%m-%d} to {inputs['end']:%Y-%m-%d}")
    main = result["summary"][0]
    col1, col2, col3 = st.columns(3)
    col1.metric("Final value", brl(main["Final value"]))
    col2.metric("Total invested", brl(main["Invested"]))
    col3.metric("Profit before taxes", brl(main["Profit"]), f"{main['Return on contributions']:.2%}")

    chart = pd.DataFrame({name: series["Value"] for name, series in result["series"].items()})
    chart["Invested"] = result["series"][inputs["ticker"]]["Invested"]
    st.line_chart(chart.ffill())

    table = pd.DataFrame(result["summary"]).set_index("Asset")
    st.dataframe(table.style.format({
        "Final value": brl, "Invested": brl, "Profit": brl,
        "Return on contributions": "{:.2%}", "Annualized return (IRR)": lambda v: "n/a" if v is None else f"{v:.2%}",
    }))
    st.caption("Same contributions, on the same schedule, in each asset. The IRR accounts for when each "
               "contribution was made. The Ibovespa and the CDI already include reinvested income.")
    for warning in result["warnings"]:
        st.warning(warning)
    st.download_button("Download report (TXT)", report_text(result), file_name=f"backtest_{inputs['ticker']}.txt",
                       mime="text/plain", key=f"download_{key}")


def main():
    st.set_page_config(page_title="Backtest Coorte", page_icon="📊")
    st.header("📊 Backtest Coorte")
    st.write("Simulates a fixed monthly contribution to a stock and compares it with the Ibovespa and the CDI.")

    st.sidebar.header("Options")
    mode = st.sidebar.selectbox("Input", ["Form", "Upload PDF", "Upload CSV/Excel/TXT"])
    reinvest = st.sidebar.toggle("Reinvest dividends (adjusted prices)", value=True,
                                 help="On: total return, as if dividends were reinvested. Off: price change only.")
    compare = st.sidebar.toggle("Compare with Ibovespa and CDI", value=True)

    requests_to_run = None
    if mode == "Form":
        ticker = st.sidebar.text_input("Ticker", "PETR4.SA")
        start = st.sidebar.date_input("Start date", date(2015, 1, 1))
        end = st.sidebar.date_input("End date", date(2025, 1, 1))
        monthly = st.sidebar.number_input("Monthly contribution (R$)", min_value=0.0, value=500.0, step=50.0)
        initial = st.sidebar.number_input("Initial investment (R$)", min_value=0.0, value=0.0, step=500.0)
        if st.sidebar.button("Run backtest"):
            requests_to_run = [{"ticker": ticker.strip().upper(), "start": pd.Timestamp(start),
                                "end": pd.Timestamp(end), "monthly": monthly, "initial": initial}]
    elif mode == "Upload PDF":
        st.sidebar.caption("Fields: Ticker, Start date, End date, Monthly contribution and, optionally, "
                           "Initial investment (English or Portuguese labels).")
        uploaded = st.sidebar.file_uploader("PDF file", type=["pdf"])
        if uploaded and st.sidebar.button("Run backtest"):
            text = "\n".join(page.extract_text() or "" for page in PdfReader(uploaded).pages)
            requests_to_run = [extract_inputs_from_text(text)]
    else:
        st.sidebar.caption("Columns: ticker, start_date, end_date, monthly_contribution and, optionally, "
                           "initial_investment (the Portuguese names also work).")
        uploaded = st.sidebar.file_uploader("CSV, Excel or TXT file", type=["csv", "xlsx", "xls", "txt"])
        if uploaded and st.sidebar.button("Run backtest"):
            try:
                requests_to_run = read_table(uploaded)
            except InputError as error:
                st.error(str(error))
            except (ValueError, OSError) as error:
                st.error("Could not read the file. Check that it is a valid CSV, TXT or Excel file.")
                with st.expander("Technical details"):
                    st.code(repr(error))

    if requests_to_run is not None:
        results, errors = [], []
        with st.spinner("Downloading prices and simulating..."):
            for inputs in requests_to_run:
                try:
                    results.append(run_backtest(inputs, reinvest, compare))
                except (InputError, DataError) as error:
                    errors.append(f"{inputs.get('ticker') or 'Row'}: {error}")
        st.session_state["results"] = results
        st.session_state["errors"] = errors

    for message in st.session_state.get("errors", []):
        st.error(message)
    for index, result in enumerate(st.session_state.get("results", [])):
        show_result(result, index)
    if not st.session_state.get("results") and not st.session_state.get("errors"):
        st.info("Choose the inputs in the sidebar and click **Run backtest**.")
    st.caption("Taxes and brokerage fees are not included. Educational project; not investment advice.")


if __name__ == "__main__":
    main()
