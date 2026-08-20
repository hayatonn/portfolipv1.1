import io
import requests
import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

# ==========================================
# 0. あなたのスプレッドシートURL設定
# ==========================================
DEFAULT_SPREADSHEET_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vSrw_rp39tTo9-P0OIZWvtSjP-YZrof4Pbdyk9spQO6lFSYtNJExbYpliIgE8CNJhbsxXUBXZVRYyUN/pub?output=csv"


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
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&family=Noto+Sans+JP:wght@400;500;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Inter', 'Noto Sans JP', sans-serif;
    }
    
    .metric-card {
        background: linear-gradient(135deg, #ffffff 0%, #f8f9fc 100%);
        border: 1px solid #e3e8ee;
        border-radius: 14px;
        padding: 20px 24px;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.03);
        margin-bottom: 12px;
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }
    .metric-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 16px rgba(0, 0, 0, 0.06);
    }
    
    .metric-title {
        font-size: 0.88rem;
        font-weight: 600;
        color: #64748b;
        margin-bottom: 6px;
        display: flex;
        align-items: center;
        gap: 6px;
    }
    
    .metric-value {
        font-size: 1.75rem;
        font-weight: 700;
        color: #1e293b;
        letter-spacing: -0.5px;
    }
    
    .badge-gain {
        display: inline-block;
        background-color: #ecfdf5;
        color: #059669;
        padding: 4px 10px;
        border-radius: 20px;
        font-size: 0.85rem;
        font-weight: 700;
        margin-top: 6px;
        border: 1px solid #a7f3d0;
    }
    
    .badge-loss {
        display: inline-block;
        background-color: #fef2f2;
        color: #dc2626;
        padding: 4px 10px;
        border-radius: 20px;
        font-size: 0.85rem;
        font-weight: 700;
        margin-top: 6px;
        border: 1px solid #fecaca;
    }
    
    .badge-neutral {
        display: inline-block;
        background-color: #f1f5f9;
        color: #475569;
        padding: 4px 10px;
        border-radius: 20px;
        font-size: 0.85rem;
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
# 2. 高速化キャッシュ＆一括データ取得
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
}


@st.cache_data(ttl=900, show_spinner=False)
def fetch_all_market_data_fast(tickers_tuple):
    """全銘柄の株価とUSD/JPY為替レートを1回のリクエストで一括爆速取得（高速化の要）"""
    prices = {}
    valid_tickers = []
    
    # 現金と株式を仕分け
    for t in tickers_tuple:
        t_str = str(t).strip().upper()
        if t_str in ["JPY", "USD", "JPY_CASH", "USD_CASH", "CASH"] or "CASH" in t_str:
            prices[str(t).strip()] = 1.0
        else:
            valid_tickers.append(str(t).strip())
            
    # 為替レート取得用シンボルを追加
    fetch_list = list(set(valid_tickers + ["USDJPY=X"]))
    
    usd_jpy = 155.0
    if fetch_list:
        try:
            # 1回のリクエストですべての銘柄を一括ダウンロード
            df_hist = yf.download(
                tickers=" ".join(fetch_list),
                period="5d",
                interval="1d",
                progress=False,
                threads=True
            )
            
            if not df_hist.empty and "Close" in df_hist:
                close_df = df_hist["Close"]
                # 複数銘柄の場合
                if isinstance(close_df, pd.DataFrame):
                    for col in close_df.columns:
                        last_valid = close_df[col].dropna()
                        if not last_valid.empty:
                            if col == "USDJPY=X":
                                usd_jpy = float(last_valid.iloc[-1])
                            else:
                                prices[col] = float(last_valid.iloc[-1])
                # 1銘柄だけの場合
                elif isinstance(close_df, pd.Series):
                    last_val = close_df.dropna()
                    if not last_val.empty:
                        prices[fetch_list[0]] = float(last_val.iloc[-1])
        except Exception:
            pass

    return prices, usd_jpy


@st.cache_data(ttl=86400, show_spinner=False)
def get_ticker_meta_info(ticker_str):
    """銘柄名・セクター・通貨などの静的情報を取得（24時間キャッシュ）"""
    t = str(ticker_str).strip()
    t_upper = t.upper()
    
    # 現金
    if t_upper in ["JPY", "USD", "JPY_CASH", "USD_CASH", "CASH"] or "CASH" in t_upper:
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

    # 辞書にない場合のみ yfinance の fast_info を確認
    if t not in POPULAR_JP_NAMES or t not in POPULAR_SECTORS:
        try:
            tk = yf.Ticker(t)
            info = getattr(tk, "info", {})
            if isinstance(info, dict):
                if t not in POPULAR_JP_NAMES:
                    name = info.get("shortName") or info.get("longName") or t
                if t not in POPULAR_SECTORS:
                    raw_sec = info.get("sector") or info.get("category") or "その他"
                    sector = SECTOR_JP_MAP.get(raw_sec, raw_sec)
                if "currency" in info and info["currency"]:
                    curr = info["currency"].upper()
        except Exception:
            pass
            
    return {"name": name, "sector": sector, "currency": curr, "asset_type": "stock"}


# ==========================================
# 3. ポートフォリオ計算ロジック（高速版）
# ==========================================
def calculate_portfolio_fast(df, fx_usd_jpy, fee_rate=0.00495):
    df = df.copy()
    df.columns = df.columns.str.strip().str.replace("　", "")
    
    for col in ["ticker", "shares", "buy_price"]:
        if col not in df.columns:
            st.error(f"CSVデータに必要な列 '{col}' が見つかりません。")
            return pd.DataFrame()
            
    df["shares"] = pd.to_numeric(df["shares"], errors="coerce").fillna(0)
    df["buy_price"] = pd.to_numeric(df["buy_price"], errors="coerce").fillna(0)
    
    # 銘柄リストから一括で価格取得
    unique_tickers = tuple(df["ticker"].dropna().unique())
    prices, _ = fetch_all_market_data_fast(unique_tickers)
    
    # 静的メタデータ（名前・セクター）を割り当て
    meta_records = [get_ticker_meta_info(t) for t in df["ticker"]]
    meta_df = pd.DataFrame(meta_records)
    
    if "name" not in df.columns or df["name"].isnull().all():
        df["name"] = meta_df["name"]
    else:
        df["name"] = df["name"].fillna(meta_df["name"])
        
    if "sector" not in df.columns or df["sector"].isnull().all():
        df["sector"] = meta_df["sector"]
    else:
        df["sector"] = df["sector"].fillna(meta_df["sector"])
        
    if "currency" not in df.columns or df["currency"].isnull().all():
        df["currency"] = meta_df["currency"]
    else:
        df["currency"] = df["currency"].fillna(meta_df["currency"])
        
    if "asset_type" not in df.columns or df["asset_type"].isnull().all():
        df["asset_type"] = meta_df["asset_type"]
    else:
        df["asset_type"] = df["asset_type"].fillna(meta_df["asset_type"])
        
    # 現在価格
    df["current_price"] = df["ticker"].map(prices).fillna(df["buy_price"])
    
    # 為替
    fx_map = {"USD": fx_usd_jpy, "JPY": 1.0}
    df["fx_rate"] = df["currency"].map(fx_map).fillna(1.0)
    
    # 手数料
    is_equity = df["asset_type"].isin(["stock", "crypto", "fund"])
    df["fee_local"] = 0.0
    df.loc[is_equity, "fee_local"] = df.loc[is_equity, "buy_price"] * df.loc[is_equity, "shares"] * fee_rate
    
    # 投資元本
    df["cost_basis_local"] = df["shares"] * df["buy_price"] + df["fee_local"]
    df["cost_basis_jpy"] = df["cost_basis_local"] * df["fx_rate"]
    
    # 現在評価額
    df["market_value_local"] = df["shares"] * df["current_price"]
    df["market_value_jpy"] = df["market_value_local"] * df["fx_rate"]
    
    # 現金調整
    is_cash = df["asset_type"] == "cash"
    df.loc[is_cash, "cost_basis_jpy"] = df.loc[is_cash, "shares"] * df.loc[is_cash, "fx_rate"]
    df.loc[is_cash, "market_value_jpy"] = df.loc[is_cash, "shares"] * df.loc[is_cash, "fx_rate"]
    
    # 損益
    df["pnl_jpy"] = df["market_value_jpy"] - df["cost_basis_jpy"]
    df["pnl_pct"] = (df["pnl_jpy"] / df["cost_basis_jpy"].replace(0, pd.NA)) * 100
    df["pnl_pct"] = df["pnl_pct"].fillna(0.0)
    
    total_val = df["market_value_jpy"].sum()
    df["allocation_pct"] = (df["market_value_jpy"] / total_val * 100) if total_val > 0 else 0.0
    
    return df


# ==========================================
# 4. サンプルデータ
# ==========================================
def get_sample_portfolio():
    return pd.DataFrame([
        {"ticker": "AAPL", "shares": 25, "buy_price": 165.0},
        {"ticker": "MSFT", "shares": 15, "buy_price": 380.0},
        {"ticker": "NVDA", "shares": 20, "buy_price": 95.0},
        {"ticker": "7203.T", "shares": 300, "buy_price": 2400.0},
        {"ticker": "BTC-USD", "shares": 0.05, "buy_price": 55000.0},
        {"ticker": "JPY_CASH", "shares": 1200000, "buy_price": 1.0},
        {"ticker": "USD_CASH", "shares": 3000, "buy_price": 1.0},
    ])


# ==========================================
# 5. サイドバー & データ読込
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
    st.markdown("### ⚙️ 設定 & データ連携")
    
    mask_mode = st.toggle("🔒 金額を伏せる (目隠しモード)", value=False, help="金額（円）を伏せて構成比や損益率(%)のみ表示します。")
    
    st.markdown("---")
    
    # 初期為替レート取得
    _, default_fx = fetch_all_market_data_fast(("USDJPY=X",))
    st.markdown(f"**💱 為替レート (USD/JPY)**")
    fx_input = st.number_input("為替レート (円/ドル)", value=float(default_fx), step=0.5, format="%.2f")
    
    st.markdown("---")
    
    st.markdown("### 📂 ポートフォリオの読込")
    data_source = st.radio(
        "データ取得元を選択",
        ["☁️ Googleスプレッドシート / URL", "📎 CSVファイルをアップロード", "📝 サンプルデータ（デモ）"],
        index=0
    )
    
    df_raw = None
    if data_source == "☁️ Googleスプレッドシート / URL":
        sheet_url = st.text_input(
            "スプレッドシートのCSV公開URL",
            value=configured_url,
            placeholder="https://docs.google.com/spreadsheets/d/.../pub?output=csv",
            help="スプレッドシートの「ファイル」→「共有」→「ウェブに公開」→「CSV」で取得したURLを入力してください。"
        )
        
        if st.button("🔄 スプレッドシートの最新データを再取得", use_container_width=True):
            st.cache_data.clear()
            st.rerun()
            
        if sheet_url and sheet_url.strip():
            try:
                clean_url = sheet_url.strip()
                if "/pubhtml" in clean_url:
                    clean_url = clean_url.replace("/pubhtml", "/pub?output=csv")
                elif "/edit" in clean_url:
                    clean_url = clean_url.split("/edit")[0] + "/export?format=csv"

                sep = "&" if "?" in clean_url else "?"
                busted_url = f"{clean_url}{sep}_t={int(datetime.now().timestamp())}"
                headers = {"Cache-Control": "no-cache", "Pragma": "no-cache"}
                res = requests.get(busted_url, headers=headers, timeout=10)
                res.raise_for_status()
                df_raw = pd.read_csv(io.StringIO(res.text), encoding="utf-8-sig")
                st.success("✅ 最新データを読み込みました！")
            except Exception as e:
                st.error(f"スプレッドシートの読み込みに失敗しました: {e}")
                df_raw = get_sample_portfolio()
        else:
            df_raw = get_sample_portfolio()
            
    elif data_source == "📎 CSVファイルをアップロード":
        uploaded_file = st.file_uploader("保有資産のCSVファイルを選択", type=["csv"])
        if uploaded_file:
            df_raw = pd.read_csv(uploaded_file, encoding="utf-8-sig")
            st.success("✅ CSVファイルを読み込みました！")
        else:
            df_raw = get_sample_portfolio()
    else:
        df_raw = get_sample_portfolio()

# ==========================================
# 6. メイン画面
# ==========================================
h_col1, h_col2 = st.columns([3, 1])
with h_col1:
    st.title("🏡 H.Tのポートフォリオ")
    st.caption(f"最終更新: {datetime.now().strftime('%Y年%m月%d日 %H:%M')} | 為替: 1 USD = {fx_input:.2f} 円")
with h_col2:
    st.markdown("<div style='margin-top: 18px;'></div>", unsafe_allow_html=True)
    if st.button("🔄 最新データに更新", use_container_width=True, help="スプレッドシートや株価の最新データを今すぐ再取得します"):
        st.cache_data.clear()
        st.rerun()

# 高速計算
df_portfolio = calculate_portfolio_fast(df_raw, fx_usd_jpy=fx_input)

if df_portfolio.empty:
    st.warning("表示できるデータがありません。")
    st.stop()

# 集計
total_cost = df_portfolio["cost_basis_jpy"].sum()
total_value = df_portfolio["market_value_jpy"].sum()
total_pnl = total_value - total_cost
total_pnl_pct = (total_pnl / total_cost * 100) if total_cost > 0 else 0.0

def fmt_yen(val):
    if mask_mode:
        return "¥ •••••••"
    return f"¥{val:,.0f}"

def fmt_pnl_yen(val):
    if mask_mode:
        return "+¥ •••••" if val >= 0 else "-¥ •••••"
    sign = "+" if val >= 0 else ""
    return f"{sign}¥{val:,.0f}"

# トップカード
c1, c2, c3, c4 = st.columns(4)

with c1:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-title">📈 現在の総評価額</div>
        <div class="metric-value">{fmt_yen(total_value)}</div>
        <span class="badge-neutral">すべての資産の合計</span>
    </div>
    """, unsafe_allow_html=True)

with c2:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-title">💰 投資した元本 (買値+手数料)</div>
        <div class="metric-value">{fmt_yen(total_cost)}</div>
        <span class="badge-neutral">投じた現金合計</span>
    </div>
    """, unsafe_allow_html=True)

with c3:
    badge_class = "badge-gain" if total_pnl >= 0 else "badge-loss"
    sign = "+" if total_pnl >= 0 else ""
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-title">🎁 買値からの損益 (含み益/損)</div>
        <div class="metric-value" style="color: {'#059669' if total_pnl >= 0 else '#dc2626'};">
            {fmt_pnl_yen(total_pnl)}
        </div>
        <span class="{badge_class}">{sign}{total_pnl_pct:.1f}% の増減</span>
    </div>
    """, unsafe_allow_html=True)

with c4:
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
        <span class="badge-neutral">株式・投信・暗号資産のみ</span>
    </div>
    """, unsafe_allow_html=True)

st.markdown("<div style='margin-top: 15px;'></div>", unsafe_allow_html=True)

# タブ
tab1, tab2, tab3, tab4 = st.tabs([
    "📊 【買値 vs いまの価値】", 
    "🏆 【銘柄別 利益ランキング】", 
    "🥧 【資産・セクター配分】", 
    "📋 【保有銘柄 一覧表】"
])

# TAB 1
with tab1:
    st.subheader("銘柄ごとの「買値」と「現在の価値」の比較")
    st.caption("投資した元本（青）に対して、現在の価値（緑）がどれだけ増えたかが分かります。")
    
    plot_df = df_portfolio[df_portfolio["asset_type"] != "cash"].copy()
    if not plot_df.empty:
        plot_df = plot_df.sort_values("market_value_jpy", ascending=False)
        
        fig_bar = go.Figure()
        fig_bar.add_trace(go.Bar(
            x=plot_df["name"],
            y=plot_df["cost_basis_jpy"] if not mask_mode else [1] * len(plot_df),
            name="投資元本 (買値+手数料)",
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
            height=420
        )
        st.plotly_chart(fig_bar, use_container_width=True)
    else:
        st.info("株式・暗号資産のデータがありません。")

# TAB 2
with tab2:
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
            height=max(350, len(pnl_df) * 45)
        )
        st.plotly_chart(fig_pnl, use_container_width=True)

# TAB 3
with tab3:
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
        fig_asset_pie.update_layout(showlegend=False, margin=dict(l=20, r=20, t=20, b=20), height=350)
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
        fig_sec_pie.update_layout(showlegend=False, margin=dict(l=20, r=20, t=20, b=20), height=350)
        st.plotly_chart(fig_sec_pie, use_container_width=True)

# TAB 4
with tab4:
    st.subheader("保有銘柄の詳細リスト（名前・セクターは自動取得）")
    
    display_df = pd.DataFrame()
    display_df["銘柄名 (自動取得)"] = df_portfolio["name"]
    display_df["ティッカー"] = df_portfolio["ticker"]
    display_df["セクター (自動分類)"] = df_portfolio["sector"]
    display_df["保有数"] = df_portfolio["shares"].apply(lambda x: f"{x:,.2f}" if x % 1 != 0 else f"{int(x):,}")
    display_df["買付単価"] = df_portfolio.apply(lambda r: f"{r['buy_price']:,.2f} {r['currency']}", axis=1)
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
        
    st.dataframe(styled_table, use_container_width=True, hide_index=True)

st.markdown("---")
st.caption("💡 スプレッドシートを更新すれば、この画面にも自動で最新データが反映されます。")
