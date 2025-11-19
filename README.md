# StockFinMetrix

StockFinMetrix is a comprehensive financial dashboard application built with Python and Dash. It allows users to compare multiple stock prices and dig dive into companies' metrics and visualize them interactively.

## 🚀 Features

### 📈 Stock Price Comparison
- **Multi-Stock Selection**: Compare historical price performance of multiple stocks simultaneously.
- **Interactive Charts**: Zoom, pan, and hover over data points for detailed price information.
- **Date Range Filtering**: Customize the analysis period with an intuitive date picker.

### 🏢 Company Deep Dive Analysis
Detailed fundamental analysis for individual companies, organized into intuitive tabs:

- **Overview**:
  - Company profile and executive officers.
  - Interactive map showing the company's headquarters location.
- **Financials**:
  - **Revenue & Profitability**: Annual and quarterly visualizations of Revenue, Operating Income, and Net Income.
  - **EPS**: Earnings Per Share trends (Basic and Diluted).
- **Balance Sheet**:
  - **Assets & Liabilities**: Visual breakdown of Total Assets, Current Assets, Debt, and Equity.
  - **Ratios**: Key financial ratios like Debt-to-Equity.
- **Cash Flow**:
  - Operating and Free Cash Flow trends.
  - Dividend history.

## 🛠️ Technology Stack

- **Frontend**: [Dash](https://dash.plotly.com/) (React-based Python framework), [Dash Bootstrap Components](https://dash-bootstrap-components.opensource.faculty.ai/)
- **Visualization**: [Plotly](https://plotly.com/python/)
- **Data Source**: [yfinance](https://pypi.org/project/yfinance/) (Yahoo Finance API)
- **Geospatial**: [Folium](https://python-visualization.github.io/folium/) for mapping

## 📦 Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd stockfinmetrix
   ```

2. **Install dependencies**
   It is recommended to use a virtual environment.
   ```bash
   pip install -r requirements.txt
   ```

## 🚦 Usage

1. **Run the application**
   ```bash
   python stockfinmetrix.py
   ```

2. **Access the Dashboard**
   Open your web browser and navigate to:
   `http://127.0.0.1:8051/`

## 📂 Project Structure

```
stockfinmetrix/
├── modules/
│   ├── callbacks.py    # Dash callbacks for interactivity
│   ├── data.py         # Data fetching and processing logic
│   ├── layout.py       # UI layout definitions
│   └── utils.py        # Utility functions (e.g., mapping)
├── stockfinmetrix.py   # Main application entry point
├── requirements.txt    # Project dependencies
└── README.md           # Project documentation
```

## 🎨 Design

The application features a modern, professional design with a sophisticated color palette:
- **Deep Blue** for primary financial metrics.
- **Teal** for growth and positive indicators.
- **Red/Coral** for debt and caution indicators.
- **Orange** for dividends and returns.
- **Dark Navy** navbar for a premium feel.

## 📝 License

[MIT](https://choosealicense.com/licenses/mit/)
