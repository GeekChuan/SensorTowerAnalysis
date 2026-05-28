# SensorTower Visualization

基于 Streamlit 的 SensorTower 中文学习竞品可视化分析应用。

## 文件说明

- `streamlit_global_chinese_report.py`：主应用
- `.streamlit/config.toml`：局域网访问配置（`0.0.0.0:8501`）
- `country_code_zh.csv`：国家代码中文对照表
- `4个app.csv`：业务数据文件（需自行放在项目根目录，默认不提交）

## 运行

```bash
pip install streamlit pandas
streamlit run streamlit_global_chinese_report.py
```

## 访问

- 本机：`http://localhost:8501`
- 局域网：`http://<你的局域网IP>:8501`
