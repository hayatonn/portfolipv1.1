import io
import requests
import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, date, timedelta

# ==========================================
# 0. あなたのスプレッドシートURL設定 & 手数料設定
# ==========================================
DEFAULT_SPREADSHEET_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vSrw_rp39tTo9-P0OIZWvtSjP-YZrof4Pbdyk9spQO6lFSYtNJExbYpliIgE8CNJhbsxXUBXZVRYyUN/pub?output=csv"
FIXED_FEE_RATE = 0.004905  # BUY/SELL時は売買代金の 0.4905% を自動計算（DEPOSIT/WITHDRAWは0%）


# ==========================================
# 1. ページ設定 & デザインスタイル
# ==========================================
st.set_page_config(
    page_title="H.Tのポートフォリオ",
    page_icon="🏡",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Noto+Sans+JP:wght@400;500;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Inter', 'Noto Sans JP', sans-serif;
    }
    
    .metric-card {
        background: linear-gradient(135deg, #ffffff 0%, #f8f9fc 100%);
        border: 1px solid #e3e8ee;
        border-radius: 14px;
        padding: 18px 22px;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.03);
        margin-bottom: 12px;
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }
    .metric-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 16px rgba(0, 0, 0, 0.06);
    }
    
    .metric-title {
        font-size: 0.85rem;
        font-weight: 600;
        color: #64748b;
        margin-bottom: 6px;
        display: flex;
        align-items: center;
        gap: 6px;
    }
    
    .metric-value {
        font-size: 1.65rem;
        font-weight: 700;
        color: #1e293b;
        letter-spacing: -0.5px;
        line-height: 1.2;
    }
    
    .badge-gain {
        display: inline-block;
        background-color: #ecfdf5;
        color: #059669;
        padding: 3px 9px;
        border-radius: 20px;
        font-size: 0.82rem;
        font-weight: 700;
        margin-top: 6px;
        border: 1px solid #a7f3d0;
    }
    
    .badge-loss {
        display: inline-block;
        background-color: #fef2f2;
        color: #dc2626;
        padding: 3px 9px;
        border-radius: 20px;
        font-size: 0.82rem;
        font-weight: 700;
        margin-top: 6px;
        border: 1px solid #fecaca;
    }
    
    .badge-neutral {
        display: inline-block;
        background-color: #f1f5f9;
        color: #475569;
        padding: 3px 9px;
        border-radius: 20px;
        font-size: 0.82rem;
        font-weight: 600;
        margin-top: 6px;
    }

    .stDataFrame {
        border-radius: 12px;
        overflow: hidden;
    }
</style>
""", unsafe_allow_html=True)


# ==========================================
# 2. 定数・辞書マッピング（爆速化用事前登録）
# ==========================================
SECTOR_JP_MAP = {
    "Technology": "テクノロジー (IT)",
    "Financial Services": "金融",
    "Healthcare": "ヘルスケア・医療",
    "Consumer Cyclical": "一般消費財",
    "Consumer Defensive": "生活必需品",
    "Communication Services": "通信・メディア",
    "Industrials": "資本財・製造",
    "Energy": "エネルギー",
    "Basic Materials": "素材",
    "Real Estate": "不動産",
    "Utilities": "公益事業",
    "Crypto": "暗号資産 (Crypto)",
    "Cash": "現金・預金"
}

POPULAR_JP_NAMES = {
    "MU": "Micron Technology",
    "SNDK": "SanDisk",
    "PLTR": "Palantir Technologies",
    "MSTR": "MicroStrategy",
    "HNGE": "Hinge Health",
    "LPTH": "LightPath Technologies",
    "FNV": "Franco-Nevada",
    "CRDO": "Credo Technology",
    "RBRK": "Rubrik",
    "ONDS": "Ondas Holdings",
    "MRVL": "Marvell Technology",
    "LLY": "Eli Lilly (イーライリリー)",
    "CELH": "Celsius Holdings",
    "ERO": "Ero Copper",
    "OSS": "One Stop Systems",
    "VST": "Vistra",
    "APP": "AppLovin",
    "ALAB": "Astera Labs",
    "7203.T": "トヨタ自動車",
    "9432.T": "日本電信電話 (NTT)",
    "9984.T": "ソフトバンクグループ",
    "6758.T": "ソニーグループ",
    "8306.T": "三菱UFJフィナンシャルG",
    "8058.T": "三菱商事",
    "8001.T": "伊藤忠商事",
    "6861.T": "キーエンス",
    "AAPL": "Apple",
    "MSFT": "Microsoft",
    "NVDA": "NVIDIA",
    "GOOGL": "Google (Alphabet)",
    "AMZN": "Amazon",
    "META": "Meta (Facebook)",
    "TSLA": "Tesla",
    "BTC-USD": "ビットコイン (BTC)",
    "ETH-USD": "イーサリアム (ETH)",
    "SPY": "S&P500 ETF (SPY)",
    "VOO": "バンガード S&P500 (VOO)",
    "VTI": "全米株式 ETF (VTI)",
    "VT": "全世界株式 ETF (VT)",
    "QQQ": "ナスダック100 ETF (QQQ)",
    "USD": "米ドル 預金",
    "JPY": "日本円 預金",
    "USD_CASH": "米ドル 預金",
    "JPY_CASH": "日本円 預金",
}

POPULAR_SECTORS = {
    "MU": "テクノロジー (IT)",
    "SNDK": "テクノロジー (IT)",
    "PLTR": "テクノロジー (IT)",
    "MSTR": "テクノロジー (IT)",
    "HNGE": "ヘルスケア・医療",
    "LPTH": "テクノロジー (IT)",
    "FNV": "素材・貴金属",
    "CRDO": "テクノロジー (IT)",
    "RBRK": "テクノロジー (IT)",
    "ONDS": "テクノロジー (IT)",
    "MRVL": "テクノロジー (IT)",
    "LLY": "ヘルスケア・医療",
    "CELH": "生活必需品 (飲料)",
    "ERO": "素材・鉱業",
    "OSS": "テクノロジー (IT)",
    "VST": "公益事業・電力",
    "APP": "テクノロジー (IT)",
    "ALAB": "テクノロジー (IT)",
    "AAPL": "テクノロジー (IT)",
    "MSFT": "テクノロジー (IT)",
    "NVDA": "テクノロジー (IT)",
    "GOOGL": "通信・メディア",
    "AMZN": "一般消費財",
    "META": "通信・メディア",
    "TSLA": "一般消費財",
    "7203.T": "一般消費財 (自動車)",
    "9432.T": "通信・メディア",
    "8306.T": "金融",
    "USD": "現金・預金",
    "JPY": "現金・預金",
    "USD_CASH": "現金・預金",
    "JPY_CASH": "現金・預金",
}


# ==========================================
# 3. 高速化キャッシュ＆データ取得関数
# ==========================================
@st.cache_data(ttl=1800, show_spinner=False)
def fetch_all_market_data_fast(tickers_tuple):
    """全銘柄の株価とUSD/JPY為替レートを一括爆速取得"""
    prices = {}
    valid_tickers = []
    
    for t in tickers_tuple:
        t_str = str(t).strip().upper()
        if t_str in ["JPY", "USD", "JPY_CASH", "USD_CASH", "CASH"] or t_str.endswith("_CASH"):
            prices[str(t).strip()] = 1.0
        else:
            valid_tickers.append(str(t).strip())
            
    fetch_list = list(set(valid_tickers + ["USDJPY=X"]))
    usd_jpy = 158.0
    if fetch_list:
        try:
            df_hist = yf.download(
                tickers=" ".join(fetch_list),
                period="5d",
                interval="1d",
                progress=False,
                threads=True
            )
            
            if not df_hist.empty and "Close" in df_hist:
                close_df = df_hist["Close"]
                if isinstance(close_df, pd.DataFrame):
                    for col in close_df.columns:
                        last_valid = close_df[col].dropna()
                        if not last_valid.empty:
                            if col == "USDJPY=X":
                                usd_jpy = float(last_valid.iloc[-1])
                            else:
                                prices[col] = float(last_valid.iloc[-1])
                elif isinstance(close_df, pd.Series):
                    last_val = close_df.dropna()
                    if not last_val.empty:
                        prices[fetch_list[0]] = float(last_val.iloc[-1])
        except Exception:
            pass

    return prices, usd_jpy


@st.cache_data(ttl=86400, show_spinner=False)
def get_ticker_meta_info(ticker_str):
    """銘柄名・セクター・通貨などの静的情報を取得（軽量・非同期フォールバック）"""
    t = str(ticker_str).strip()
    t_upper = t.upper()
    
    # 現金
    if t_upper in ["JPY", "USD", "JPY_CASH", "USD_CASH", "CASH"] or t_upper.endswith("_CASH"):
        curr = "JPY" if "JPY" in t_upper else "USD"
        name = "日本円 預金" if curr == "JPY" else "米ドル 預金"
        return {"name": name, "sector": "現金・預金", "currency": curr, "asset_type": "cash"}
        
    # 暗号資産
    if t.endswith("-USD") or t_upper in ["BTC", "ETH"]:
        symbol = t if t.endswith("-USD") else f"{t}-USD"
        name = POPULAR_JP_NAMES.get(symbol, symbol)
        return {"name": name, "sector": "暗号資産 (Crypto)", "currency": "USD", "asset_type": "crypto"}

    # 株式
    curr = "JPY" if t.endswith(".T") else "USD"
    name = POPULAR_JP_NAMES.get(t, t)
    sector = POPULAR_SECTORS.get(t, "その他")

    # 辞書にあれば即座に返却（重い通信を一切行わない爆速化）
    if t in POPULAR_JP_NAMES and t in POPULAR_SECTORS:
        return {"name": name, "sector": sector, "currency": curr, "asset_type": "stock"}

    # 辞書にない場合のみ yfinance の fast_info を確認
    try:
        tk = yf.Ticker(t)
        info = getattr(tk, "fast_info", {})
        if info:
            if t not in POPULAR_JP_NAMES:
                name = getattr(info, "name", t) or t
            if "currency" in dir(info):
                curr = str(getattr(info, "currency", curr)).upper()
    except Exception:
        pass
        
    return {"name": name, "sector": sector, "currency": curr, "asset_type": "stock"}


# ==========================================
# 4. 取引履歴からの資産推移計算エンジン（爆速キャッシュ）
# ==========================================
@st.cache_data(ttl=1800, show_spinner=False)
def calculate_portfolio_from_transactions(df_raw, fallback_fx=158.0, fee_rate=FIXED_FEE_RATE):
    """
    取引履歴から日別の資産推移と現在の保有資産スナップショットを算出
    """
    df_tx = df_raw.copy()
    col_map = {}
    for c in df_tx.columns:
        c_clean = str(c).strip().replace("　", "").lower()
        if c_clean in ["date", "日付", "日時", "取引日"]:
            col_map[c] = "date"
        elif c_clean in ["action", "種別", "取引", "売買", "type"]:
            col_map[c] = "action"
        elif c_clean in ["ticker", "ティッカー", "銘柄コード", "銘柄", "symbol"]:
            col_map[c] = "ticker"
        elif c_clean in ["shares", "株数", "数量", "口数", "amount"]:
            col_map[c] = "shares"
        elif c_clean in ["price", "単価", "価格", "約定価格", "買付単価"]:
            col_map[c] = "price"
        elif c_clean in ["fee", "手数料", "費用"]:
            col_map[c] = "fee"
        elif c_clean in ["memo", "備考", "メモ", "ノート", "note", "メモ・備考"]:
            col_map[c] = "memo"
    df_tx = df_tx.rename(columns=col_map)
    
    if "price" not in df_tx.columns:
        df_tx["price"] = 1.0
    if "fee" not in df_tx.columns:
        df_tx["fee"] = 0.0
    if "memo" not in df_tx.columns:
        df_tx["memo"] = ""
        
    df_tx["date"] = pd.to_datetime(df_tx["date"], errors="coerce").dt.tz_localize(None)
    df_tx = df_tx.dropna(subset=["date"])
    df_tx["action"] = df_tx["action"].astype(str).str.strip().str.upper()
    df_tx["ticker"] = df_tx["ticker"].astype(str).str.strip().str.upper()
    df_tx["shares"] = pd.to_numeric(df_tx["shares"], errors="coerce").fillna(0.0)
    df_tx["price"] = pd.to_numeric(df_tx["price"], errors="coerce").fillna(1.0)
    df_tx["fee"] = pd.to_numeric(df_tx["fee"], errors="coerce").fillna(0.0)
    df_tx["memo"] = df_tx["memo"].fillna("").astype(str).replace(["nan", "None", "<NA>"], "")
    
    # 手数料自動計算
    for idx, r in df_tx.iterrows():
        act_norm = r["action"]
        t_norm = r["ticker"]
        is_cash_trade = (t_norm in ["JPY", "USD", "JPY_CASH", "USD_CASH", "CASH"] or t_norm.endswith("_CASH"))
        if not is_cash_trade and act_norm in ["BUY", "SELL", "買付", "購入", "買い", "売却", "売り"]:
            trade_val = r["shares"] * r["price"]
            df_tx.at[idx, "fee"] = trade_val * fee_rate
        else:
            df_tx.at[idx, "fee"] = 0.0
    
    df_tx = df_tx.sort_values("date").reset_index(drop=True)
    if df_tx.empty:
        return pd.DataFrame(), pd.DataFrame(), df_tx
        
    start_date = df_tx["date"].min()
    today = pd.Timestamp(date.today())
    
    # 銘柄リスト（現金以外）
    all_tickers = df_tx["ticker"].unique()
    stock_tickers = [t for t in all_tickers if t not in ["JPY", "USD", "JPY_CASH", "USD_CASH", "CASH"] and not t.endswith("_CASH")]
    
    fetch_list = list(set(stock_tickers + ["USDJPY=X"]))
    hist_prices = pd.DataFrame()
    if fetch_list:
        try:
            start_str = (start_date - pd.Timedelta(days=7)).strftime("%Y-%m-%d")
            data = yf.download(fetch_list, start=start_str, interval="1d", progress=False, threads=True)
            if not data.empty and "Close" in data:
                close = data["Close"]
                if isinstance(close, pd.Series):
                    hist_prices = pd.DataFrame({fetch_list[0]: close})
                else:
                    hist_prices = close.copy()
        except Exception:
            pass
            
    if not hist_prices.empty:
        hist_prices.index = pd.to_datetime(hist_prices.index).tz_localize(None).floor("D")
        hist_prices = hist_prices[~hist_prices.index.duplicated(keep="last")]
        
    date_range = pd.date_range(start=start_date.floor("D"), end=today, freq="D")
    full_prices = pd.DataFrame(index=date_range)
    for col in hist_prices.columns:
        full_prices[col] = hist_prices[col]
    full_prices = full_prices.ffill().bfill()
    
    if "USDJPY=X" in full_prices.columns:
        fx_series = full_prices["USDJPY=X"].fillna(fallback_fx)
    else:
        fx_series = pd.Series(fallback_fx, index=date_range)
        
    cash_jpy = 0.0
    cash_usd = 0.0
    net_deposit_jpy = 0.0
    realized_pnl_jpy = 0.0
    
    holdings = {}
    for t in stock_tickers:
        curr = "JPY" if t.endswith(".T") else "USD"
        holdings[t] = {"shares": 0.0, "cost_basis_local": 0.0, "currency": curr}
        
    tx_by_date = {}
    for _, row in df_tx.iterrows():
        d = row["date"].floor("D")
        tx_by_date.setdefault(d, []).append(row)
        
    daily_records = []
    
    for current_dt in date_range:
        fx_now = float(fx_series.loc[current_dt]) if current_dt in fx_series.index else fallback_fx
        
        if current_dt in tx_by_date:
            for tx in tx_by_date[current_dt]:
                act = tx["action"]
                t = tx["ticker"]
                sh = tx["shares"]
                pr = tx["price"]
                fee = tx["fee"]
                
                if act in ["BUY", "買付", "買い", "購入"]:
                    act = "BUY"
                elif act in ["SELL", "売却", "売り"]:
                    act = "SELL"
                elif act in ["DEPOSIT", "入金", "入庫"]:
                    act = "DEPOSIT"
                elif act in ["WITHDRAW", "出金", "出庫"]:
                    act = "WITHDRAW"
                elif act in ["DIVIDEND", "配当", "配当金", "利息"]:
                    act = "DIVIDEND"
                    
                is_usd = (t in ["USD", "USD_CASH"])
                
                if act == "DEPOSIT":
                    if is_usd:
                        amt_usd = sh * pr
                        cash_usd += amt_usd
                        net_deposit_jpy += amt_usd * fx_now
                    else:
                        amt_jpy = sh * pr
                        cash_jpy += amt_jpy
                        net_deposit_jpy += amt_jpy
                        
                elif act == "WITHDRAW":
                    if is_usd:
                        amt_usd = sh * pr
                        cash_usd = max(0.0, cash_usd - amt_usd)
                        net_deposit_jpy -= amt_usd * fx_now
                    else:
                        amt_jpy = sh * pr
                        cash_jpy = max(0.0, cash_jpy - amt_jpy)
                        net_deposit_jpy -= amt_jpy
                        
                elif act == "BUY":
                    curr = holdings.get(t, {}).get("currency", "JPY" if t.endswith(".T") else "USD")
                    cost_local = sh * pr + fee
                    
                    if curr == "USD":
                        if cash_usd >= cost_local:
                            cash_usd -= cost_local
                        else:
                            needed_usd = cost_local - cash_usd
                            cash_usd = 0.0
                            needed_jpy = needed_usd * fx_now
                            if cash_jpy >= needed_jpy:
                                cash_jpy -= needed_jpy
                            else:
                                unfunded_jpy = needed_jpy - cash_jpy
                                cash_jpy = 0.0
                                net_deposit_jpy += unfunded_jpy
                    else:
                        if cash_jpy >= cost_local:
                            cash_jpy -= cost_local
                        else:
                            unfunded_jpy = cost_local - cash_jpy
                            cash_jpy = 0.0
                            net_deposit_jpy += unfunded_jpy
                        
                    if t not in holdings:
                        holdings[t] = {"shares": 0.0, "cost_basis_local": 0.0, "currency": curr}
                    holdings[t]["shares"] += sh
                    holdings[t]["cost_basis_local"] += cost_local
                    
                elif act == "SELL":
                    curr = holdings.get(t, {}).get("currency", "JPY" if t.endswith(".T") else "USD")
                    revenue_local = sh * pr - fee
                    
                    if t in holdings and holdings[t]["shares"] > 0:
                        prev_sh = holdings[t]["shares"]
                        prev_cost = holdings[t]["cost_basis_local"]
                        sold_fraction = min(1.0, sh / prev_sh)
                        sold_cost = prev_cost * sold_fraction
                        
                        pnl_local = revenue_local - sold_cost
                        if curr == "USD":
                            realized_pnl_jpy += pnl_local * fx_now
                            cash_usd += revenue_local
                        else:
                            realized_pnl_jpy += pnl_local
                            cash_jpy += revenue_local
                            
                        holdings[t]["shares"] = max(0.0, prev_sh - sh)
                        holdings[t]["cost_basis_local"] = max(0.0, prev_cost - sold_cost)
                        
                elif act == "DIVIDEND":
                    curr = "USD" if (t in ["USD", "USD_CASH"] or not t.endswith(".T")) else "JPY"
                    amt = sh * pr
                    if curr == "USD":
                        cash_usd += amt
                        realized_pnl_jpy += amt * fx_now
                    else:
                        cash_jpy += amt
                        realized_pnl_jpy += amt

        # 本日の評価額
        equity_val_jpy = 0.0
        stock_values = {}
        for t, h in holdings.items():
            sh = h["shares"]
            if sh > 0:
                curr = h["currency"]
                p = 0.0
                if t in full_prices.columns and current_dt in full_prices.index:
                    p = float(full_prices.loc[current_dt, t])
                if np.isnan(p) or p <= 0:
                    p = h["cost_basis_local"] / sh if sh > 0 else 0.0
                val_jpy = sh * p * (fx_now if curr == "USD" else 1.0)
                equity_val_jpy += val_jpy
                stock_values[t] = val_jpy
            else:
                stock_values[t] = 0.0
                
        total_cash_jpy = cash_jpy + (cash_usd * fx_now)
        total_val_jpy = total_cash_jpy + equity_val_jpy
        unrealized_pnl_jpy = total_val_jpy - net_deposit_jpy
        pnl_pct = (unrealized_pnl_jpy / net_deposit_jpy * 100) if net_deposit_jpy > 0 else 0.0
        
        daily_records.append({
            "date": current_dt,
            "total_value_jpy": total_val_jpy,
            "net_deposit_jpy": net_deposit_jpy,
            "cash_jpy": total_cash_jpy,
            "equity_jpy": equity_val_jpy,
            "unrealized_pnl_jpy": unrealized_pnl_jpy,
            "pnl_pct": pnl_pct,
            "realized_pnl_jpy": realized_pnl_jpy,
            "usd_jpy": fx_now,
            **stock_values
        })
        
    df_history = pd.DataFrame(daily_records)
    
    current_holdings = []
    for t, h in holdings.items():
        if h["shares"] > 0:
            avg_price = h["cost_basis_local"] / h["shares"]
            current_holdings.append({
                "ticker": t,
                "shares": h["shares"],
                "buy_price": avg_price
            })
            
    if cash_jpy > 0:
        current_holdings.append({"ticker": "JPY_CASH", "shares": cash_jpy, "buy_price": 1.0})
    if cash_usd > 0:
        current_holdings.append({"ticker": "USD_CASH", "shares": cash_usd, "buy_price": 1.0})
        
    df_current_portfolio = pd.DataFrame(current_holdings)
    return df_history, df_current_portfolio, df_tx


@st.cache_data(ttl=1800, show_spinner=False)
def calculate_holdings_history_fast(df_portfolio, fx_usd_jpy):
    """保有資産一覧形式からの仮想資産推移計算"""
    tickers = [t for t in df_portfolio["ticker"].unique() if not str(t).upper().endswith("CASH") and str(t).upper() not in ["JPY", "USD"]]
    fetch_list = list(set(tickers + ["USDJPY=X"]))
    
    today = pd.Timestamp(date.today())
    start_date = today - pd.Timedelta(days=365)
    
    hist_prices = pd.DataFrame()
    if fetch_list:
        try:
            data = yf.download(fetch_list, start=start_date.strftime("%Y-%m-%d"), interval="1d", progress=False, threads=True)
            if not data.empty and "Close" in data:
                close = data["Close"]
                hist_prices = pd.DataFrame({fetch_list[0]: close}) if isinstance(close, pd.Series) else close.copy()
        except Exception:
            pass
            
    if hist_prices.empty:
        return pd.DataFrame()
        
    hist_prices.index = pd.to_datetime(hist_prices.index).tz_localize(None).floor("D")
    hist_prices = hist_prices[~hist_prices.index.duplicated(keep="last")]
    
    date_range = pd.date_range(start=start_date.floor("D"), end=today, freq="D")
    full_prices = pd.DataFrame(index=date_range)
    for col in hist_prices.columns:
        full_prices[col] = hist_prices[col]
    full_prices = full_prices.ffill().bfill()
    
    fx_series = full_prices["USDJPY=X"].fillna(fx_usd_jpy) if "USDJPY=X" in full_prices.columns else pd.Series(fx_usd_jpy, index=date_range)
    
    total_cost = df_portfolio["cost_basis_jpy"].sum()
    cash_val = df_portfolio[df_portfolio["asset_type"] == "cash"]["market_value_jpy"].sum()
    
    daily_records = []
    for dt in date_range:
        fx_now = float(fx_series.loc[dt]) if dt in fx_series.index else fx_usd_jpy
        equity_val = 0.0
        stock_values = {}
        for _, row in df_portfolio[df_portfolio["asset_type"] != "cash"].iterrows():
            t = row["ticker"]
            sh = row["shares"]
            curr = row["currency"]
            p = float(full_prices.loc[dt, t]) if (t in full_prices.columns and dt in full_prices.index) else row["current_price"]
            v = sh * p * (fx_now if curr == "USD" else 1.0)
            equity_val += v
            stock_values[t] = v
            
        tot = cash_val + equity_val
        pnl = tot - total_cost
        pnl_pct = (pnl / total_cost * 100) if total_cost > 0 else 0.0
        
        daily_records.append({
            "date": dt,
            "total_value_jpy": tot,
            "net_deposit_jpy": total_cost,
            "cash_jpy": cash_val,
            "equity_jpy": equity_val,
            "unrealized_pnl_jpy": pnl,
            "pnl_pct": pnl_pct,
            "realized_pnl_jpy": 0.0,
            "usd_jpy": fx_now,
            **stock_values
        })
    return pd.DataFrame(daily_records)


# ==========================================
# 5. ポートフォリオ計算ロジック（現在状況）
# ==========================================
def calculate_portfolio_fast(df, fx_usd_jpy, fee_rate=FIXED_FEE_RATE):
    df = df.copy()
    df.columns = df.columns.str.strip().str.replace("　", "")
    
    for col in ["ticker", "shares", "buy_price"]:
        if col not in df.columns:
            st.error(f"データに必要な列 '{col}' が見つかりません。")
            return pd.DataFrame()
            
    df["shares"] = pd.to_numeric(df["shares"], errors="coerce").fillna(0)
    df["buy_price"] = pd.to_numeric(df["buy_price"], errors="coerce").fillna(0)
    
    unique_tickers = tuple(df["ticker"].dropna().unique())
    prices, _ = fetch_all_market_data_fast(unique_tickers)
    
    meta_records = [get_ticker_meta_info(t) for t in df["ticker"]]
    meta_df = pd.DataFrame(meta_records)
    
    for col in ["name", "sector", "currency", "asset_type"]:
        if col not in df.columns or df[col].isnull().all():
            df[col] = meta_df[col]
        else:
            df[col] = df[col].fillna(meta_df[col])
        
    df["current_price"] = df["ticker"].map(prices).fillna(df["buy_price"])
    
    fx_map = {"USD": fx_usd_jpy, "JPY": 1.0}
    df["fx_rate"] = df["currency"].map(fx_map).fillna(1.0)
    
    is_equity = df["asset_type"].isin(["stock", "crypto", "fund"])
    df["fee_local"] = 0.0
    df.loc[is_equity, "fee_local"] = df.loc[is_equity, "buy_price"] * df.loc[is_equity, "shares"] * fee_rate
    
    df["cost_basis_local"] = df["shares"] * df["buy_price"] + df["fee_local"]
    df["cost_basis_jpy"] = df["cost_basis_local"] * df["fx_rate"]
    
    df["market_value_local"] = df["shares"] * df["current_price"]
    df["market_value_jpy"] = df["market_value_local"] * df["fx_rate"]
    
    is_cash = df["asset_type"] == "cash"
    df.loc[is_cash, "cost_basis_jpy"] = df.loc[is_cash, "shares"] * df.loc[is_cash, "fx_rate"]
    df.loc[is_cash, "market_value_jpy"] = df.loc[is_cash, "shares"] * df.loc[is_cash, "fx_rate"]
    
    df["pnl_jpy"] = df["market_value_jpy"] - df["cost_basis_jpy"]
    df["pnl_pct"] = (df["pnl_jpy"] / df["cost_basis_jpy"].replace(0, pd.NA)) * 100
    df["pnl_pct"] = df["pnl_pct"].fillna(0.0)
    
    total_val = df["market_value_jpy"].sum()
    df["allocation_pct"] = (df["market_value_jpy"] / total_val * 100) if total_val > 0 else 0.0
    
    return df


# ==========================================
# 6. スプレッドシート読み込み関数（キャッシュ最適化）
# ==========================================
@st.cache_data(ttl=300, show_spinner=False)
def load_sheet_data(url):
    clean_url = url.strip()
    if "/pubhtml" in clean_url:
        clean_url = clean_url.replace("/pubhtml", "/pub?output=csv")
    elif "/edit" in clean_url:
        clean_url = clean_url.split("/edit")[0] + "/export?format=csv"

    sep = "&" if "?" in clean_url else "?"
    busted_url = f"{clean_url}{sep}_t={int(datetime.now().timestamp())}"
    headers = {"Cache-Control": "no-cache", "Pragma": "no-cache"}
    res = requests.get(busted_url, headers=headers, timeout=8)
    res.raise_for_status()
    return pd.read_csv(io.StringIO(res.text), encoding="utf-8-sig")


# ==========================================
# 7. サイドバー & データ連携（Googleスプレッドシート固定）
# ==========================================
configured_url = ""
try:
    if "SPREADSHEET_URL" in st.secrets:
        configured_url = st.secrets["SPREADSHEET_URL"]
except Exception:
    pass

if not configured_url:
    configured_url = DEFAULT_SPREADSHEET_URL

with st.sidebar:
    st.markdown("### ⚙️ 設定 & スプレッドシート連携")
    mask_mode = st.toggle("🔒 金額を伏せる (目隠しモード)", value=False, help="金額（円）を伏せて構成比や損益率(%)のみ表示します。")
    st.markdown("---")
    
    _, default_fx = fetch_all_market_data_fast(("USDJPY=X",))
    st.markdown(f"**💱 為替レート (USD/JPY)**")
    fx_input = st.number_input("為替レート (円/ドル)", value=float(default_fx), step=0.5, format="%.2f")
    
    st.markdown(f"**💳 手数料自動計算**")
    st.caption(f"・BUY / SELL: **{FIXED_FEE_RATE*100:.4f}%** 自動適用\n・DEPOSIT: **0円**（fee列は不要）")
    
    st.markdown("---")
    st.markdown("### ☁️ スプレッドシート設定")
    sheet_url = st.text_input(
        "公開CSV URL",
        value=configured_url,
        help="Googleスプレッドシートの「ウェブに公開(CSV)」URLです。"
    )
    
    if st.button("🔄 スプレッドシートを再読込", use_container_width=True, type="primary"):
        st.cache_data.clear()
        st.rerun()
        
    df_raw = None
    if sheet_url and sheet_url.strip():
        try:
            df_raw = load_sheet_data(sheet_url)
            st.success("✅ スプレッドシートを読み込みました！")
        except Exception as e:
            st.error(f"スプレッドシート読込失敗: {e}")
            
    with st.expander("📎 予備：CSVファイルアップロード"):
        uploaded_file = st.file_uploader("CSVを選択", type=["csv"])
        if uploaded_file:
            df_raw = pd.read_csv(uploaded_file, encoding="utf-8-sig")
            st.success("✅ CSV読込完了")


# ==========================================
# 8. データ処理 & 自動フォーマット判別
# ==========================================
if df_raw is None or df_raw.empty:
    st.warning("表示できるデータがありません。スプレッドシートのURLをご確認ください。")
    st.stop()

# 列名チェック（取引履歴形式かどうかの自動判定）
cols_lower = [str(c).strip().replace("　", "").lower() for c in df_raw.columns]
has_date = any(k in cols_lower for k in ["date", "日付", "日時", "取引日"])
has_action = any(k in cols_lower for k in ["action", "種別", "取引", "売買", "type"])
is_transaction_mode = has_date and has_action

df_history = pd.DataFrame()
df_tx_log = pd.DataFrame()

if is_transaction_mode:
    df_history, df_portfolio_raw, df_tx_log = calculate_portfolio_from_transactions(df_raw, fallback_fx=fx_input, fee_rate=FIXED_FEE_RATE)
    df_portfolio = calculate_portfolio_fast(df_portfolio_raw, fx_usd_jpy=fx_input, fee_rate=FIXED_FEE_RATE)
else:
    df_portfolio = calculate_portfolio_fast(df_raw, fx_usd_jpy=fx_input, fee_rate=FIXED_FEE_RATE)
    df_history = calculate_holdings_history_fast(df_portfolio, fx_usd_jpy=fx_input)

if df_portfolio.empty:
    st.warning("有効なポートフォリオデータが生成できませんでした。データの形式をご確認ください。")
    st.stop()


# ==========================================
# 9. メイン画面 & ヘッダー
# ==========================================
h_col1, h_col2 = st.columns([3, 1])
with h_col1:
    st.title("🏡 H.Tのポートフォリオ")
    mode_badge = "📜 取引履歴モード (完全推移)" if is_transaction_mode else "📋 保有資産一覧モード"
    st.caption(f"最終更新: {datetime.now().strftime('%Y年%m月%d日 %H:%M')} | 為替: 1 USD = {fx_input:.2f} 円 | 手数料: **0.4905%** | モード: **{mode_badge}**")
with h_col2:
    st.markdown("<div style='margin-top: 18px;'></div>", unsafe_allow_html=True)
    if st.button("🔄 最新データに更新", use_container_width=True, help="スプレッドシートや株価の最新データを今すぐ再取得します"):
        st.cache_data.clear()
        st.rerun()

# 集計
total_cost = df_portfolio["cost_basis_jpy"].sum()
total_value = df_portfolio["market_value_jpy"].sum()
total_pnl = total_value - total_cost
total_pnl_pct = (total_pnl / total_cost * 100) if total_cost > 0 else 0.0

realized_pnl_total = df_history["realized_pnl_jpy"].iloc[-1] if (not df_history.empty and "realized_pnl_jpy" in df_history.columns) else 0.0
net_deposit_total = df_history["net_deposit_jpy"].iloc[-1] if (not df_history.empty and "net_deposit_jpy" in df_history.columns) else total_cost
all_time_high = max(df_history["total_value_jpy"].max() if not df_history.empty else 0.0, total_value)

def fmt_yen(val):
    if mask_mode:
        return "¥ •••••••"
    return f"¥{val:,.0f}"

def fmt_pnl_yen(val):
    if mask_mode:
        return "+¥ •••••" if val >= 0 else "-¥ •••••"
    sign = "+" if val >= 0 else ""
    return f"{sign}¥{val:,.0f}"

# トップ指標カード
c1, c2, c3, c4 = st.columns(4)

with c1:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-title">📈 現在の総資産評価額</div>
        <div class="metric-value">{fmt_yen(total_value)}</div>
        <span class="badge-neutral">最高額 (ATH): {fmt_yen(all_time_high)}</span>
    </div>
    """, unsafe_allow_html=True)

with c2:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-title">💰 投じた元本 (投資コスト)</div>
        <div class="metric-value">{fmt_yen(total_cost)}</div>
        <span class="badge-neutral">買付代金 + 手数料(0.4905%)</span>
    </div>
    """, unsafe_allow_html=True)

with c3:
    badge_class = "badge-gain" if total_pnl >= 0 else "badge-loss"
    sign = "+" if total_pnl >= 0 else ""
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-title">🎁 現在の含み損益 (未実現)</div>
        <div class="metric-value" style="color: {'#059669' if total_pnl >= 0 else '#dc2626'};">
            {fmt_pnl_yen(total_pnl)}
        </div>
        <span class="{badge_class}">{sign}{total_pnl_pct:.1f}% の増減</span>
    </div>
    """, unsafe_allow_html=True)

with c4:
    if is_transaction_mode and realized_pnl_total != 0:
        badge_class_r = "badge-gain" if realized_pnl_total >= 0 else "badge-loss"
        sign_r = "+" if realized_pnl_total >= 0 else ""
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-title">🏆 通算の確定損益 (利確・配当)</div>
            <div class="metric-value" style="color: {'#059669' if realized_pnl_total >= 0 else '#dc2626'};">
                {fmt_pnl_yen(realized_pnl_total)}
            </div>
            <span class="{badge_class_r}">売却益＋受取配当金 (手数料引後)</span>
        </div>
        """, unsafe_allow_html=True)
    else:
        equity_df = df_portfolio[df_portfolio["asset_type"].isin(["stock", "crypto", "fund"])]
        eq_cost = equity_df["cost_basis_jpy"].sum()
        eq_val = equity_df["market_value_jpy"].sum()
        eq_pnl_pct = ((eq_val - eq_cost) / eq_cost * 100) if eq_cost > 0 else 0.0
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-title">📊 リスク資産のリターン</div>
            <div class="metric-value" style="color: {'#059669' if eq_pnl_pct >= 0 else '#dc2626'};">
                {'+' if eq_pnl_pct >= 0 else ''}{eq_pnl_pct:.1f}%
            </div>
            <span class="badge-neutral">株式・暗号資産のみ</span>
        </div>
        """, unsafe_allow_html=True)

st.markdown("<div style='margin-top: 15px;'></div>", unsafe_allow_html=True)


# ==========================================
# 10. タブ画面
# ==========================================
tab_titles = [
    "📈 【資産推移・パフォーマンス】",
    "📊 【買値 vs いまの価値】", 
    "🏆 【銘柄別 利益ランキング】", 
    "🥧 【資産・セクター配分】", 
    "📋 【保有銘柄 一覧表】"
]
if is_transaction_mode:
    tab_titles.append("📜 【取引履歴 ログ一覧】")

tabs = st.tabs(tab_titles)

# ----------------------------------------------------
# TAB 1: 資産推移・パフォーマンス
# ----------------------------------------------------
with tabs[0]:
    st.subheader("📈 ポートフォリオの資産推移")
    st.caption("過去から現在までの総資産評価額の推移と、投じた元本の軌跡です。")
    
    if not df_history.empty:
        period_choice = st.radio(
            "表示期間",
            ["全期間 (ALL)", "1年 (1Y)", "6ヶ月 (6M)", "3ヶ月 (3M)", "1ヶ月 (1M)", "年初来 (YTD)"],
            horizontal=True,
            index=0
        )
            
        latest_dt = df_history["date"].max()
        if period_choice == "1ヶ月 (1M)":
            filter_start = latest_dt - timedelta(days=30)
        elif period_choice == "3ヶ月 (3M)":
            filter_start = latest_dt - timedelta(days=90)
        elif period_choice == "6ヶ月 (6M)":
            filter_start = latest_dt - timedelta(days=180)
        elif period_choice == "1年 (1Y)":
            filter_start = latest_dt - timedelta(days=365)
        elif period_choice == "年初来 (YTD)":
            filter_start = datetime(latest_dt.year, 1, 1)
        else:
            filter_start = df_history["date"].min()
            
        view_hist = df_history[df_history["date"] >= filter_start].copy()
        
        fig_timeline = go.Figure()
        
        # 投資元本ライン
        fig_timeline.add_trace(go.Scatter(
            x=view_hist["date"],
            y=view_hist["net_deposit_jpy"] if not mask_mode else [100] * len(view_hist),
            name="投資元本 (投入資金)",
            mode="lines",
            line=dict(color="#94a3b8", width=2, dash="dash"),
            hovertemplate="<b>%{x|%Y/%m/%d}</b><br>投資元本: " + ("¥%{y:,.0f}" if not mask_mode else "マスク中") + "<extra></extra>"
        ))
        
        # 総資産額ライン
        fig_timeline.add_trace(go.Scatter(
            x=view_hist["date"],
            y=view_hist["total_value_jpy"] if not mask_mode else [100 * (1 + row.pnl_pct/100) for _, row in view_hist.iterrows()],
            name="総資産評価額",
            mode="lines",
            line=dict(color="#10b981", width=3),
            fill="tonexty" if not mask_mode else None,
            fillcolor="rgba(16, 185, 129, 0.08)",
            hovertemplate="<b>%{x|%Y/%m/%d}</b><br>総資産額: " + ("¥%{y:,.0f}" if not mask_mode else "相対指数") + "<extra></extra>"
        ))
        
        fig_timeline.update_layout(
            hovermode="x unified",
            margin=dict(l=20, r=20, t=30, b=30),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            yaxis_title="金額 (円)" if not mask_mode else "パフォーマンス指数",
            height=430,
            xaxis=dict(showgrid=True, gridcolor="#f1f5f9"),
            yaxis=dict(showgrid=True, gridcolor="#f1f5f9")
        )
        st.plotly_chart(fig_timeline, use_container_width=True)
        
        # 資産内訳推移（積み上げエリアチャート）
        st.markdown("##### 🧱 資産内訳のボリューム推移")
        
        stock_cols = [c for c in view_hist.columns if c not in [
            "date", "total_value_jpy", "net_deposit_jpy", "cash_jpy", "equity_jpy",
            "unrealized_pnl_jpy", "pnl_pct", "realized_pnl_jpy", "usd_jpy"
        ]]
        
        fig_area = go.Figure()
        if (view_hist["cash_jpy"] > 0).any():
            fig_area.add_trace(go.Scatter(
                x=view_hist["date"],
                y=view_hist["cash_jpy"] if not mask_mode else [1] * len(view_hist),
                name="現金・預金",
                mode="lines",
                stackgroup="one",
                line=dict(width=0.5, color="#cbd5e1"),
                fillcolor="#e2e8f0",
                hovertemplate="現金: " + ("¥%{y:,.0f}" if not mask_mode else "マスク中") + "<extra></extra>"
            ))
        
        colors_palette = px.colors.qualitative.Pastel + px.colors.qualitative.Safe
        for idx, s_col in enumerate(stock_cols):
            if (view_hist[s_col] > 0).any():
                s_name = POPULAR_JP_NAMES.get(s_col, s_col)
                col_c = colors_palette[idx % len(colors_palette)]
                fig_area.add_trace(go.Scatter(
                    x=view_hist["date"],
                    y=view_hist[s_col] if not mask_mode else [1] * len(view_hist),
                    name=s_name,
                    mode="lines",
                    stackgroup="one",
                    line=dict(width=0.5),
                    hovertemplate=f"{s_name}: " + ("¥%{y:,.0f}" if not mask_mode else "マスク中") + "<extra></extra>"
                ))
                
        fig_area.update_layout(
            hovermode="x unified",
            margin=dict(l=20, r=20, t=30, b=30),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            yaxis_title="評価額 (円)" if not mask_mode else "構成比",
            height=370,
            xaxis=dict(showgrid=True, gridcolor="#f1f5f9"),
            yaxis=dict(showgrid=True, gridcolor="#f1f5f9")
        )
        st.plotly_chart(fig_area, use_container_width=True)
        
    else:
        st.info("資産推移データがありません。")

# ----------------------------------------------------
# TAB 2: 買値 vs いまの価値
# ----------------------------------------------------
with tabs[1]:
    st.subheader("銘柄ごとの「買値」と「現在の価値」の比較")
    
    plot_df = df_portfolio[df_portfolio["asset_type"] != "cash"].copy()
    if not plot_df.empty:
        plot_df = plot_df.sort_values("market_value_jpy", ascending=False)
        
        fig_bar = go.Figure()
        fig_bar.add_trace(go.Bar(
            x=plot_df["name"],
            y=plot_df["cost_basis_jpy"] if not mask_mode else [1] * len(plot_df),
            name=f"投資元本 (買値+手数料 0.4905%)",
            marker_color="#94a3b8",
            hovertemplate="<b>%{x}</b><br>投資元本: " + ("¥%{y:,.0f}" if not mask_mode else "マスク中") + "<extra></extra>"
        ))
        fig_bar.add_trace(go.Bar(
            x=plot_df["name"],
            y=plot_df["market_value_jpy"] if not mask_mode else [1 * (1 + row.pnl_pct/100) for _, row in plot_df.iterrows()],
            name="現在の評価額",
            marker_color="#10b981",
            hovertemplate="<b>%{x}</b><br>現在価値: " + ("¥%{y:,.0f}" if not mask_mode else "マスク中") + "<extra></extra>"
        ))
        
        fig_bar.update_layout(
            barmode="group",
            hovermode="x unified",
            margin=dict(l=20, r=20, t=30, b=30),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            yaxis_title="金額 (円)" if not mask_mode else "相対比率",
            height=400
        )
        st.plotly_chart(fig_bar, use_container_width=True)
    else:
        st.info("株式・暗号資産のデータがありません。")

# ----------------------------------------------------
# TAB 3: 銘柄別 利益ランキング
# ----------------------------------------------------
with tabs[2]:
    st.subheader("買値からどれくらい利益が出ているか（銘柄別ランキング）")
    pnl_df = df_portfolio[df_portfolio["asset_type"] != "cash"].copy()
    if not pnl_df.empty:
        pnl_df = pnl_df.sort_values("pnl_jpy", ascending=True)
        colors = ["#10b981" if val >= 0 else "#ef4444" for val in pnl_df["pnl_jpy"]]
        
        fig_pnl = go.Figure(go.Bar(
            x=pnl_df["pnl_jpy"] if not mask_mode else pnl_df["pnl_pct"],
            y=pnl_df["name"],
            orientation='h',
            marker_color=colors,
            text=[f"{'+' if p>=0 else ''}{p:.1f}%" for p in pnl_df["pnl_pct"]],
            textposition="auto",
            hovertemplate="<b>%{y}</b><br>" + ("損益: ¥%{x:,.0f}" if not mask_mode else "損益率: %{x:.1f}%") + "<extra></extra>"
        ))
        
        fig_pnl.update_layout(
            margin=dict(l=20, r=20, t=30, b=30),
            xaxis_title="損益額 (円)" if not mask_mode else "損益率 (%)",
            height=max(320, len(pnl_df) * 42)
        )
        st.plotly_chart(fig_pnl, use_container_width=True)

# ----------------------------------------------------
# TAB 4: 資産・セクター配分
# ----------------------------------------------------
with tabs[3]:
    st.subheader("資産のバランス・分散状況（円グラフ）")
    c_pie1, c_pie2 = st.columns(2)
    
    with c_pie1:
        st.markdown("##### 📌 資産種別の比率")
        asset_summary = df_portfolio.groupby("asset_type")["market_value_jpy"].sum().reset_index()
        type_jp = {"stock": "株式・ETF", "crypto": "暗号資産", "cash": "現金・預金", "fund": "投資信託"}
        asset_summary["asset_name"] = asset_summary["asset_type"].map(type_jp).fillna(asset_summary["asset_type"])
        
        fig_asset_pie = px.pie(
            asset_summary,
            values="market_value_jpy",
            names="asset_name",
            hole=0.45,
            color_discrete_sequence=px.colors.qualitative.Safe
        )
        fig_asset_pie.update_traces(textinfo="label+percent", hovertemplate="<b>%{label}</b><br>構成比: %{percent}")
        fig_asset_pie.update_layout(showlegend=False, margin=dict(l=20, r=20, t=20, b=20), height=330)
        st.plotly_chart(fig_asset_pie, use_container_width=True)
        
    with c_pie2:
        st.markdown("##### 🏢 セクター・業界別の比率")
        sector_summary = df_portfolio.groupby("sector")["market_value_jpy"].sum().reset_index()
        fig_sec_pie = px.pie(
            sector_summary,
            values="market_value_jpy",
            names="sector",
            hole=0.45,
            color_discrete_sequence=px.colors.qualitative.Pastel
        )
        fig_sec_pie.update_traces(textinfo="label+percent", hovertemplate="<b>%{label}</b><br>構成比: %{percent}")
        fig_sec_pie.update_layout(showlegend=False, margin=dict(l=20, r=20, t=20, b=20), height=330)
        st.plotly_chart(fig_sec_pie, use_container_width=True)

# ----------------------------------------------------
# TAB 5: 保有銘柄 一覧表
# ----------------------------------------------------
with tabs[4]:
    st.subheader("保有銘柄の詳細リスト")
    
    display_df = pd.DataFrame()
    display_df["銘柄名"] = df_portfolio["name"]
    display_df["ティッカー"] = df_portfolio["ticker"]
    display_df["セクター"] = df_portfolio["sector"]
    display_df["保有数"] = df_portfolio["shares"].apply(lambda x: f"{x:,.4f}" if (x % 1 != 0 and x < 1) else (f"{x:,.2f}" if x % 1 != 0 else f"{int(x):,}"))
    display_df["買付単価 (平均)"] = df_portfolio.apply(lambda r: f"{r['buy_price']:,.2f} {r['currency']}", axis=1)
    display_df["現在価格"] = df_portfolio.apply(lambda r: f"{r['current_price']:,.2f} {r['currency']}", axis=1)
    
    if not mask_mode:
        display_df["投資元本 (円)"] = df_portfolio["cost_basis_jpy"].apply(lambda x: f"¥{x:,.0f}")
        display_df["現在評価額 (円)"] = df_portfolio["market_value_jpy"].apply(lambda x: f"¥{x:,.0f}")
        display_df["買値からの損益 (円)"] = df_portfolio["pnl_jpy"].apply(lambda x: f"{'+' if x>=0 else ''}¥{x:,.0f}")
    else:
        display_df["投資元本 (円)"] = "¥ ••••••"
        display_df["現在評価額 (円)"] = "¥ ••••••"
        display_df["買値からの損益 (円)"] = df_portfolio["pnl_jpy"].apply(lambda x: "+¥ •••••" if x >= 0 else "-¥ •••••")
        
    display_df["損益率 (リターン)"] = df_portfolio["pnl_pct"].apply(lambda x: f"{'+' if x>=0 else ''}{x:.2f}%")
    display_df["構成比"] = df_portfolio["allocation_pct"].apply(lambda x: f"{x:.1f}%")
    
    def color_pnl(val):
        if str(val).startswith("+"):
            return "color: #059669; font-weight: 600;"
        elif str(val).startswith("-"):
            return "color: #dc2626; font-weight: 600;"
        return ""

    try:
        styled_table = display_df.style.map(color_pnl, subset=["買値からの損益 (円)", "損益率 (リターン)"])
    except AttributeError:
        styled_table = display_df.style.applymap(color_pnl, subset=["買値からの損益 (円)", "損益率 (リターン)"])
        
    st.dataframe(
        styled_table,
        use_container_width=True,
        hide_index=True,
        column_config={
            "銘柄名": st.column_config.TextColumn("銘柄名", width="medium"),
            "ティッカー": st.column_config.TextColumn("ティッカー", width="small"),
            "セクター": st.column_config.TextColumn("セクター", width="small"),
            "保有数": st.column_config.TextColumn("保有数", width="small"),
            "買付単価 (平均)": st.column_config.TextColumn("買付単価", width="small"),
            "現在価格": st.column_config.TextColumn("現在価格", width="small"),
            "投資元本 (円)": st.column_config.TextColumn("投資元本", width="small"),
            "現在評価額 (円)": st.column_config.TextColumn("現在評価額", width="small"),
            "買値からの損益 (円)": st.column_config.TextColumn("損益額", width="small"),
            "損益率 (リターン)": st.column_config.TextColumn("リターン", width="small"),
            "構成比": st.column_config.TextColumn("構成比", width="small"),
        }
    )

# ----------------------------------------------------
# TAB 6: 取引履歴 ログ一覧（列幅最適化 & メモ見やすく表示）
# ----------------------------------------------------
if is_transaction_mode and len(tabs) > 5:
    with tabs[5]:
        st.subheader("📜 登録されている取引履歴（売買ログ一覧）")
        st.caption("スプレッドシートから読み込まれた全取引の記録です。（BUY/SELL時は手数料0.4905%自動適用、入金時は0円）")
        
        log_df = df_tx_log.copy()
        log_df["取引日"] = pd.to_datetime(log_df["date"]).dt.strftime("%Y/%m/%d")
        
        act_trans = {
            "BUY": "🟢 買付 (BUY)",
            "SELL": "🔴 売却 (SELL)",
            "DEPOSIT": "💰 入金 (DEPOSIT)",
            "WITHDRAW": "💸 出金 (WITHDRAW)",
            "DIVIDEND": "🎁 配当 (DIVIDEND)"
        }
        log_df["取引種別"] = log_df["action"].map(act_trans).fillna(log_df["action"])
        
        def format_ticker_name(t):
            t_clean = str(t).strip()
            name = POPULAR_JP_NAMES.get(t_clean, "")
            if name and name != t_clean:
                return f"{name} ({t_clean})"
            return t_clean

        log_df["銘柄"] = log_df["ticker"].apply(format_ticker_name)
        log_df["数量"] = log_df["shares"].apply(lambda x: f"{x:,.4f}" if (x % 1 != 0 and x < 1) else (f"{x:,.2f}" if x % 1 != 0 else f"{int(x):,}"))
        log_df["約定単価"] = log_df["price"].apply(lambda p: f"{p:,.2f}")
        log_df["手数料 (0.4905%)"] = log_df["fee"].apply(lambda f: f"{f:,.2f}" if f > 0 else "0")
        
        # None や nan を完全に除去
        log_df["メモ・備考"] = log_df.get("memo", "").fillna("").astype(str).replace(["nan", "None", "<NA>"], "")
        
        disp_log = log_df[["取引日", "取引種別", "銘柄", "数量", "約定単価", "手数料 (0.4905%)", "メモ・備考"]]
        
        st.dataframe(
            disp_log,
            use_container_width=True,
            hide_index=True,
            column_config={
                "取引日": st.column_config.TextColumn("取引日", width=100),
                "取引種別": st.column_config.TextColumn("取引種別", width=130),
                "銘柄": st.column_config.TextColumn("銘柄", width=220),
                "数量": st.column_config.TextColumn("数量", width=90),
                "約定単価": st.column_config.TextColumn("約定単価", width=100),
                "手数料 (0.4905%)": st.column_config.TextColumn("手数料", width=90),
                "メモ・備考": st.column_config.TextColumn("メモ・備考", width="large"),
            }
        )

st.markdown("---")
st.caption("💡 スプレッドシートを更新すれば、この画面にも自動で最新データが反映されます。")
