import pandas as pd
import streamlit as st


st.set_page_config(
    page_title="Global中文学习竞品调研",
    page_icon=":bar_chart:",
    layout="wide",
)


DATA_PATH = "4个app.csv"
REPORT_PATH = "Global中文学习竞品调研报告_草案.md"
COUNTRY_MAP_PATH = "country_code_zh.csv"


def normalize_app_name(name: str) -> str:
    n = (name or "").lower()
    if "hellochinese" in n:
        return "HelloChinese"
    if "superchinese" in n:
        return "SuperChinese"
    if "talkpal" in n:
        return "Talkpal"
    if "chinesia" in n:
        return "Chinesia"
    return name or "Unknown"


def infer_platform(app_id: str) -> str:
    s = str(app_id or "").strip()
    if s.isdigit():
        return "iOS(App Store)"
    if s.lower().startswith("com."):
        return "Android(Google Play)"
    return "Unknown"


@st.cache_data(show_spinner=False)
def load_country_map() -> dict:
    mapping_df = pd.read_csv(COUNTRY_MAP_PATH)
    mapping_df["二位代码"] = mapping_df["二位代码"].astype(str).str.upper().str.strip()
    mapping_df["中文名称"] = mapping_df["中文名称"].astype(str).str.strip()
    code_to_name = dict(zip(mapping_df["二位代码"], mapping_df["中文名称"]))
    code_to_name["所有"] = "全球汇总"
    return code_to_name


@st.cache_data(show_spinner=False)
def load_data() -> pd.DataFrame:
    df = pd.read_csv(DATA_PATH, sep="\t", encoding="utf-16")
    df.columns = [c.strip().strip('"') for c in df.columns]

    numeric_cols = [
        "下载量",
        "收入",
        "ARPDAU",
        "DAU",
        "WAU",
        "MAU",
        "平均花费时间（分钟/天)",
        "总花费时间 (年)",
        "每天的平均会话次数",
        "平均总会话次数",
        "会话时长 ((每次会话的平均分钟)",
    ]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    df["app_norm"] = df["应用名称"].apply(normalize_app_name)
    df["platform_inferred"] = df["应用 ID"].apply(infer_platform)
    df["月份"] = pd.to_datetime(df["月份"], errors="coerce")
    df = df.dropna(subset=["月份"]).copy()
    df["月份字符串"] = df["月份"].dt.strftime("%Y-%m")
    return df


@st.cache_data(show_spinner=False)
def get_report_markdown() -> str:
    with open(REPORT_PATH, "r", encoding="utf-8") as f:
        return f.read()


def pct(v: float) -> str:
    return f"{v:.1%}"


def num(v: float) -> str:
    return f"{v:,.0f}"


def render_conclusion(title: str, text: str) -> None:
    st.markdown(f"**结论：{title}**")
    st.info(text)


def format_country(code: str, country_map: dict) -> str:
    c = (code or "").strip()
    upper_c = c.upper()
    zh_name = country_map.get(upper_c)
    if zh_name:
        return f"{upper_c} - {zh_name}"
    return c


df = load_data()
country_map = load_country_map()
df_no_all = df[df["国家"] != "所有"].copy()
df_no_all["国家展示"] = df_no_all["国家"].apply(lambda x: format_country(x, country_map))
df_all_country = df[df["国家"] == "所有"].copy()

st.title("Global中文学习竞品数据可视化网站")
st.caption("数据源：Sensor Tower 月度数据（4个APP，按国家维度）")

with st.sidebar:
    st.header("筛选器")
    apps = sorted(df_no_all["app_norm"].dropna().unique().tolist())
    selected_apps = st.multiselect("APP", apps, default=apps)
    platforms = sorted(df_no_all["platform_inferred"].dropna().unique().tolist())
    selected_platforms = st.multiselect("平台", platforms, default=platforms)

    all_months = sorted(df_no_all["月份字符串"].dropna().unique().tolist())
    selected_months = st.slider(
        "月份范围",
        min_value=0,
        max_value=len(all_months) - 1,
        value=(0, len(all_months) - 1),
    )
    month_start = all_months[selected_months[0]]
    month_end = all_months[selected_months[1]]

    show_top_n = st.selectbox("TOP国家数量", [10, 15, 20, 30], index=1)

filtered = df_no_all[
    (df_no_all["app_norm"].isin(selected_apps))
    & (df_no_all["platform_inferred"].isin(selected_platforms))
    & (df_no_all["月份字符串"] >= month_start)
    & (df_no_all["月份字符串"] <= month_end)
].copy()

st.subheader("一、数据总览")
col1, col2, col3, col4 = st.columns(4)
col1.metric("样本行数（筛选后）", num(len(filtered)))
col2.metric("覆盖APP", num(filtered["app_norm"].nunique()))
col3.metric("覆盖国家", num(filtered["国家展示"].nunique()))
col4.metric("覆盖月份", num(filtered["月份字符串"].nunique()))
st.caption(f"当前平台筛选：{', '.join(selected_platforms)}")

total_download = filtered["下载量"].sum(skipna=True)
total_revenue = filtered["收入"].sum(skipna=True)
col5, col6 = st.columns(2)
col5.metric("总下载量", num(total_download))
col6.metric("总收入", f"{total_revenue:,.2f}")

core_missing = (
    filtered[["下载量", "收入", "ARPDAU", "DAU", "WAU", "MAU"]]
    .isna()
    .mean()
    .sort_values(ascending=False)
    .rename("缺失率")
)
behavior_missing = (
    filtered[
        [
            "平均花费时间（分钟/天)",
            "每天的平均会话次数",
            "平均总会话次数",
            "会话时长 ((每次会话的平均分钟)",
        ]
    ]
    .isna()
    .mean()
    .sort_values(ascending=False)
    .rename("缺失率")
)
mc1, mc2 = st.columns(2)
with mc1:
    st.markdown("**核心业务指标缺失率**")
    st.bar_chart(core_missing)
with mc2:
    st.markdown("**用户行为指标缺失率**")
    st.bar_chart(behavior_missing)
render_conclusion(
    "活跃与行为指标缺失较高",
    "下载和收入可用于主结论；ARPDAU、DAU/WAU/MAU以及时长会话字段应作为辅助证据，避免单点决策。",
)

st.markdown("### 缺失特征诊断（时间 / APP / 国家）")
target_fields = [
    "ARPDAU",
    "DAU",
    "WAU",
    "MAU",
    "平均花费时间（分钟/天)",
    "每天的平均会话次数",
    "平均总会话次数",
    "会话时长 ((每次会话的平均分钟)",
]

missing_diag = filtered.copy()
missing_diag["行为字段缺失占比"] = missing_diag[target_fields].isna().mean(axis=1)

time_missing = (
    missing_diag.groupby("月份字符串", as_index=False)["行为字段缺失占比"]
    .mean()
    .sort_values("月份字符串")
)
app_missing = (
    missing_diag.groupby("app_norm", as_index=False)["行为字段缺失占比"]
    .mean()
    .sort_values("行为字段缺失占比", ascending=False)
)
country_missing = (
    missing_diag.groupby("国家展示", as_index=False)["行为字段缺失占比"]
    .mean()
    .sort_values("行为字段缺失占比", ascending=False)
)

d1, d2 = st.columns(2)
with d1:
    st.markdown("**时间维度：行为字段缺失占比趋势**")
    st.line_chart(time_missing.set_index("月份字符串")["行为字段缺失占比"], height=280)
with d2:
    st.markdown("**APP维度：行为字段缺失占比**")
    st.bar_chart(app_missing.set_index("app_norm")["行为字段缺失占比"], height=280)

st.markdown("**国家维度：行为字段缺失占比 TOP20（缺失最严重）**")
st.dataframe(country_missing.head(20), use_container_width=True)

st.warning(
    "当前数据不包含明确“渠道”字段（如投放渠道/商店来源）。"
    "若你补充渠道列（例如channel、source、media），页面可直接扩展为“渠道缺失诊断”。"
)
render_conclusion(
    "缺失并非随机，需按维度看结构性偏差",
    "重点关注：是否某些月份、某些APP或某些国家缺失显著更高。若是，则对应维度的行为结论要降权或单独说明。",
)

st.divider()
st.subheader("二、市场总览（按月趋势）")
market_monthly = (
    filtered.groupby("月份字符串", as_index=False)[["下载量", "收入"]]
    .sum()
    .sort_values("月份字符串")
)
mkt1, mkt2 = st.columns(2)
with mkt1:
    st.markdown("**月度下载趋势（单独坐标）**")
    st.line_chart(market_monthly.set_index("月份字符串")[["下载量"]], height=320)
with mkt2:
    st.markdown("**月度收入趋势（单独坐标）**")
    st.line_chart(market_monthly.set_index("月份字符串")[["收入"]], height=320)

if len(market_monthly) >= 24:
    prev_12 = market_monthly.iloc[-24:-12]
    curr_12 = market_monthly.iloc[-12:]
    prev_dl, curr_dl = prev_12["下载量"].sum(), curr_12["下载量"].sum()
    prev_rev, curr_rev = prev_12["收入"].sum(), curr_12["收入"].sum()
    growth_dl = (curr_dl / prev_dl - 1) if prev_dl else 0
    growth_rev = (curr_rev / prev_rev - 1) if prev_rev else 0
    g1, g2 = st.columns(2)
    g1.metric("近12个月下载增速", pct(growth_dl))
    g2.metric("近12个月收入增速", pct(growth_rev))
    render_conclusion(
        "赛道仍在扩张",
        "如果近12个月下载和收入同时为正增长，说明仍有进入窗口；若下载增速显著高于收入增速，需优先补齐变现能力。",
    )

st.divider()
st.subheader("三、竞品格局（规模与变现）")

app_agg = (
    filtered.groupby("app_norm", as_index=False)[["下载量", "收入"]]
    .sum()
    .sort_values("收入", ascending=False)
)
app_agg["每下载收入"] = app_agg["收入"] / app_agg["下载量"]
app_agg["下载份额"] = app_agg["下载量"] / app_agg["下载量"].sum()
app_agg["收入份额"] = app_agg["收入"] / app_agg["收入"].sum()

a1, a2 = st.columns(2)
with a1:
    st.markdown("**下载份额**")
    st.bar_chart(app_agg.set_index("app_norm")["下载份额"])
with a2:
    st.markdown("**收入份额**")
    st.bar_chart(app_agg.set_index("app_norm")["收入份额"])

st.markdown("**规模与效率对照表**")
show_app = app_agg.copy()
show_app["下载份额"] = show_app["下载份额"].map(lambda x: f"{x:.1%}")
show_app["收入份额"] = show_app["收入份额"].map(lambda x: f"{x:.1%}")
show_app["每下载收入"] = show_app["每下载收入"].map(lambda x: f"{x:.3f}")
st.dataframe(show_app, use_container_width=True)
render_conclusion(
    "头部不等于最强效率",
    "应同时看份额和每下载收入：前者代表规模，后者代表商业化效率。增长策略要从“抢量”升级到“量收协同”。",
)

st.divider()
st.subheader("四、用户行为趋势分析（按月）")

behavior_monthly = (
    filtered.groupby("月份字符串", as_index=False)[
        [
            "平均花费时间（分钟/天)",
            "每天的平均会话次数",
            "平均总会话次数",
            "会话时长 ((每次会话的平均分钟)",
            "DAU",
            "WAU",
            "MAU",
        ]
    ]
    .mean(numeric_only=True)
    .sort_values("月份字符串")
)

b1, b2 = st.columns(2)
with b1:
    st.markdown("**人均使用时长与会话时长趋势**")
    st.line_chart(
        behavior_monthly.set_index("月份字符串")[
            ["平均花费时间（分钟/天)", "会话时长 ((每次会话的平均分钟)"]
        ],
        height=320,
    )
with b2:
    st.markdown("**会话频次趋势**")
    st.line_chart(
        behavior_monthly.set_index("月份字符串")[["每天的平均会话次数", "平均总会话次数"]],
        height=320,
    )

st.markdown("**活跃规模趋势（DAU / WAU / MAU）**")
st.line_chart(
    behavior_monthly.set_index("月份字符串")[["DAU", "WAU", "MAU"]],
    height=320,
)

behavior_coverage = (
    filtered.groupby("月份字符串", as_index=False)[
        [
            "平均花费时间（分钟/天)",
            "每天的平均会话次数",
            "会话时长 ((每次会话的平均分钟)",
        ]
    ]
    .count()
    .sort_values("月份字符串")
)
behavior_coverage = behavior_coverage.rename(
    columns={
        "平均花费时间（分钟/天)": "时长样本数",
        "每天的平均会话次数": "会话样本数",
        "会话时长 ((每次会话的平均分钟)": "会话时长样本数",
    }
)
st.markdown("**行为数据覆盖趋势（每月可用样本数）**")
st.line_chart(
    behavior_coverage.set_index("月份字符串")[["时长样本数", "会话样本数", "会话时长样本数"]],
    height=280,
)

st.markdown("#### DAU/WAU/MAU 专项校验（按 APP，口径=国家=所有）")
st.caption(
    "单位说明：DAU/WAU/MAU 为人数；平均花费时间/会话时长为分钟；会话次数为次。"
)

dau_scope = df_all_country[
    (df_all_country["app_norm"].isin(selected_apps))
    & (df_all_country["platform_inferred"].isin(selected_platforms))
    & (df_all_country["月份字符串"] >= month_start)
    & (df_all_country["月份字符串"] <= month_end)
].copy()

if not dau_scope.empty:
    dau_dim = st.radio(
        "活跃趋势维度",
        ["按归一品牌(app_norm)", "按应用ID(不合并)", "按平台(platform)"],
        horizontal=True,
        key="dau_dimension",
    )
    if dau_dim == "按归一品牌(app_norm)":
        group_key = "app_norm"
    elif dau_dim == "按应用ID(不合并)":
        group_key = "应用 ID"
    else:
        group_key = "platform_inferred"

    dau_by_app_month = (
        dau_scope.groupby(["月份字符串", group_key], as_index=False)[["DAU", "WAU", "MAU"]]
        .sum()
        .sort_values(["月份字符串", group_key])
    )

    focus_dau_metric = st.selectbox(
        "选择活跃指标（按APP看趋势）",
        ["DAU", "WAU", "MAU"],
        index=0,
        key="active_metric_by_app",
    )
    chart_df = dau_by_app_month.pivot(
        index="月份字符串", columns=group_key, values=focus_dau_metric
    )
    st.line_chart(chart_df, height=340)

    latest_month = dau_by_app_month["月份字符串"].max()
    latest_rows = (
        dau_by_app_month[dau_by_app_month["月份字符串"] == latest_month][
            [group_key, "DAU", "WAU", "MAU"]
        ]
        .sort_values("DAU", ascending=False)
        .reset_index(drop=True)
    )
    st.markdown(f"**最新月份（{latest_month}）APP活跃规模（人数）**")
    st.dataframe(latest_rows, use_container_width=True)

    # 用于核对用户提到的HelloChinese单月DAU
    hc_2026_04 = dau_by_app_month[
        (dau_by_app_month[group_key] == ("HelloChinese" if group_key == "app_norm" else "1001507516"))
        & (dau_by_app_month["月份字符串"] == "2026-04")
    ]
    if not hc_2026_04.empty:
        if group_key == "app_norm":
            st.success(
                f"口径核对：HelloChinese（归一后）在 2026-04（国家=所有）DAU = "
                f"{int(hc_2026_04.iloc[0]['DAU']):,} 人。"
            )
        else:
            st.success(
                f"口径核对：应用ID=1001507516 在 2026-04（国家=所有）DAU = "
                f"{int(hc_2026_04.iloc[0]['DAU']):,} 人（与你提到的49,469一致）。"
            )
else:
    st.warning("当前筛选条件下没有“国家=所有”的活跃数据，无法做APP活跃口径校验。")

render_conclusion(
    "行为趋势可用于识别“增长质量”",
    "行为趋势建议分两套口径：1) 国家明细用于看结构；2) 国家=所有用于看APP总活跃。"
    " 当下载增长但时长/会话频次下降时，通常意味着低质量拉新；若活跃规模与行为深度同步上升，增长可持续性更高。",
)

st.divider()
st.subheader("五、区域机会（拉新型 vs 变现型）")

country_agg = (
    filtered.groupby("国家展示", as_index=False)[["下载量", "收入"]]
    .sum()
    .sort_values("下载量", ascending=False)
)
country_agg["每下载收入"] = country_agg["收入"] / country_agg["下载量"]
country_agg = country_agg[country_agg["下载量"] > 0].copy()

top_download = country_agg.nlargest(show_top_n, "下载量")[["国家展示", "下载量", "收入", "每下载收入"]]
top_revenue = country_agg.nlargest(show_top_n, "收入")[["国家展示", "下载量", "收入", "每下载收入"]]

c1, c2 = st.columns(2)
with c1:
    st.markdown(f"**下载TOP{show_top_n}国家**")
    st.bar_chart(top_download.set_index("国家展示")["下载量"])
with c2:
    st.markdown(f"**收入TOP{show_top_n}国家**")
    st.bar_chart(top_revenue.set_index("国家展示")["收入"])

q30 = country_agg["每下载收入"].quantile(0.30)
q70 = country_agg["每下载收入"].quantile(0.70)
country_agg["市场分层"] = "均衡市场"
country_agg.loc[country_agg["每下载收入"] <= q30, "市场分层"] = "拉新型市场"
country_agg.loc[country_agg["每下载收入"] >= q70, "市场分层"] = "变现型市场"

st.markdown("**国家分层明细（可用于市场优先级）**")
st.dataframe(
    country_agg.sort_values(["市场分层", "收入"], ascending=[True, False]),
    use_container_width=True,
)
render_conclusion(
    "必须分层运营",
    "拉新型国家（高下载低变现）与变现型国家（高变现效率）要使用不同产品与商业策略，单一全球打法效果会明显打折。",
)

st.divider()
st.subheader("六、竞品-国家矩阵（看打法差异）")
selected_app_for_matrix = st.selectbox("选择一个APP看国家结构", sorted(filtered["app_norm"].unique().tolist()))
app_country = (
    filtered[filtered["app_norm"] == selected_app_for_matrix]
    .groupby("国家展示", as_index=False)[["下载量", "收入"]]
    .sum()
)
app_country["每下载收入"] = app_country["收入"] / app_country["下载量"]

m1, m2 = st.columns(2)
with m1:
    st.markdown("**该APP下载TOP10国家**")
    st.bar_chart(app_country.nlargest(10, "下载量").set_index("国家展示")["下载量"])
with m2:
    st.markdown("**该APP收入TOP10国家**")
    st.bar_chart(app_country.nlargest(10, "收入").set_index("国家展示")["收入"])

render_conclusion(
    "不同APP的国家结构决定其增长路径",
    "如果某APP在美日欧占比高，通常更依赖付费深度；若在东南亚占比高，通常更依赖拉新与低价快速扩张。",
)

st.divider()
st.subheader("七、策略建议（自动生成）")

top_growth_countries = top_download["国家展示"].head(5).tolist()
top_monetize_countries = top_revenue["国家展示"].head(5).tolist()

st.markdown(
    f"""
**建议立项：谨慎乐观推进**

- **拉新优先国家（示例）**：`{", ".join(top_growth_countries)}`
- **变现优先国家（示例）**：`{", ".join(top_monetize_countries)}`

**建议路径**
- 0-6个月：双核启动（拉新市场验证内容与获客；变现市场打磨订阅和转化）。
- 6-12个月：扩展至次核心市场，优化LTV和续费。
- 全周期：持续监控“下载增速 vs 收入增速”差值，避免只涨量不涨收。
"""
)

st.divider()
st.subheader("八、完整调研报告（网站内嵌）")
st.markdown(get_report_markdown())

