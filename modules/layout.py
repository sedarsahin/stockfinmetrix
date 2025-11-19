from dash import dcc, html, dash_table
import dash_bootstrap_components as dbc
import datetime as dt
from .data import get_ticker_options

def create_layout():
    """Creates the Dash application layout with Bootstrap and Tabs."""
    
    # Initial ticker
    ticker = 'AAPL'
    
    # Get options
    options = get_ticker_options()
    
    # Columns for officers table
    officers_table_columns = ['symbol','name','title','age','fiscalYear',
                              'totalPay', 'website', 'industry']

    # Navbar
    navbar = dbc.NavbarSimple(
        brand="StockFinMetrix",
        brand_href="#",
        color="dark",
        dark=True,
        className="mb-4",
        brand_style={"fontSize": "2rem", "fontWeight": "bold"},
        style={"backgroundColor": "#1a1a2e"}
    )

    # Stores
    stores = html.Div([
        dcc.Store(id='intermediate-value-ticker-info'),
        dcc.Store(id='intermediate-value-ticker-income_stmt_annual'),
        dcc.Store(id='intermediate-value-ticker-income_stmt_quarterly'),
        dcc.Store(id='intermediate-value-ticker-balance_sheet'),
        dcc.Store(id='intermediate-value-ticker-cash_flow'),
        dcc.Store(id='intermediate-value-ticker-dividends'),
    ])

    # Tab 1: Overview
    tab_overview = dbc.Card(
        dbc.CardBody(
            [
                dbc.Row([
                    dbc.Col([
                        html.H5("Company Details"),
                        dash_table.DataTable(id='company_table', 
                                            columns = [{"name": "label", "id": "label"},
                                                       {"name": "value", "id": "value"}],
                                            style_data={'whiteSpace': 'normal', 'height': 'auto'},
                                            style_cell={'textAlign': 'left'},
                                            style_as_list_view=True,
                                            ),
                    ], width=6),
                    dbc.Col([
                        html.H5("Location"),
                        html.Iframe(id='company_map',
                                    srcDoc="<div>Select a company to view map</div>",
                                    style={'width': '100%', 'height': '400px', 'border': 'none'}
                                   ),
                    ], width=6),
                ]),
                html.Hr(),
                html.H5("Executive Officers"),
                dash_table.DataTable(id='executive_table',
                                columns=[{'name':col, 'id':col} for col in officers_table_columns],
                                style_cell={'textAlign': 'left'},
                                style_as_list_view=True,
                                page_size=5,
                                ),
            ]
        ),
        className="mt-3"
    )

    # Tab 2: Financials (Revenue, Profit, EPS)
    tab_financials = dbc.Card(
        dbc.CardBody(
            [
                html.H4("Revenue & Profitability"),
                dbc.Row([
                    dbc.Col(dcc.Graph(id='revenue_graph_annual'), width=6),
                    dbc.Col(dcc.Graph(id='revenue_graph_quarterly'), width=6),
                ]),
                dbc.Row([
                    dbc.Col(dcc.Graph(id='operating_income_graph_annual'), width=6),
                    dbc.Col(dcc.Graph(id='operating_income_graph_quarterly'), width=6),
                ]),
                dbc.Row([
                    dbc.Col(dcc.Graph(id='net_income_graph_annual'), width=6),
                    dbc.Col(dcc.Graph(id='net_income_graph_quarterly'), width=6),
                ]),
                html.Hr(),
                html.H4("Earnings Per Share (EPS)"),
                dbc.Row([
                    dbc.Col(dcc.Graph(id='basic_eps_graph_quarterly'), width=6),
                    dbc.Col(dcc.Graph(id='diluted_eps_graph_quarterly'), width=6),
                ]),
                 dash_table.DataTable(id='profit_table', style_table={'display': 'none'}), # Hidden for now or use if needed
            ]
        ),
        className="mt-3"
    )

    # Tab 3: Balance Sheet & Cash Flow
    tab_balance_sheet = dbc.Card(
        dbc.CardBody(
            [
                html.H4("Debts & Equity"),
                dbc.Row([
                    dbc.Col(dcc.Graph(id='debt_graph_annual'), width=4),
                    dbc.Col(dcc.Graph(id='equity_graph_annual'), width=4),
                    dbc.Col(dcc.Graph(id='d2e_graph_annual'), width=4),
                ]),
                html.Hr(),
                html.H4("Cash Flow"),
                dbc.Row([
                    dbc.Col(dcc.Graph(id='operating_cashflow_graph_annual'), width=6),
                    dbc.Col(dcc.Graph(id='free_cashflow_graph_annual'), width=6),
                ]),
                html.Hr(),
                html.H4("Assets & Dividends"),
                dbc.Row([
                    dbc.Col(dcc.Graph(id='total_assets_graph_annual'), width=4),
                    dbc.Col(dcc.Graph(id='current_assets_graph_annual'), width=4),
                    dbc.Col(dcc.Graph(id='investment_in_financial_assets_graph_annual'), width=4),
                ]),
                dbc.Row([
                    dbc.Col(dcc.Graph(id='dividends_graph'), width=12),
                ]),
            ]
        ),
        className="mt-3"
    )

    # Tabs Component
    tabs = dbc.Tabs(
        [
            dbc.Tab(tab_overview, label="Overview", tab_id="tab-overview"),
            dbc.Tab(tab_financials, label="Financials", tab_id="tab-financials"),
            dbc.Tab(tab_balance_sheet, label="Balance Sheet & Cash Flow", tab_id="tab-bs-cf"),
        ],
        id="tabs",
        active_tab="tab-overview",
    )

    # Final Layout Assembly
    layout = dbc.Container(
        [
            navbar,
            stores,
            
            # ==================== SECTION 1: Stock Price Comparison ==================== #
            html.Div(
                [
                    dbc.Card(
                        [
                            dbc.CardHeader(
                                html.H3([
                                    html.I(className="bi bi-graph-up-arrow me-2"),
                                    "📈 Stock Price Comparison"
                                ], className="mb-0"),
                                style={"backgroundColor": "#0f4c81", "color": "white"}
                            ),
                            dbc.CardBody(
                                [
                                    html.P("Compare closing prices of multiple stocks over time", className="text-muted mb-3"),
                                    dbc.Row(
                                        [
                                            dbc.Col(
                                                [
                                                    html.Label([
                                                        html.I(className="bi bi-graph-up me-2"),
                                                        "Select Stock(s)"
                                                    ], style={"fontWeight": "600", "fontSize": "1.1rem", "color": "#2c3e50"}),
                                                    dcc.Dropdown(id='stock_picker',
                                                            options=options,
                                                            value=[ticker],
                                                            multi=True,
                                                            className="mb-3"
                                                    ),
                                                ], width=5
                                            ),
                                            dbc.Col(
                                                [
                                                    html.Label([
                                                        html.I(className="bi bi-calendar-range me-2"),
                                                        "Select Date Range"
                                                    ], style={"fontWeight": "600", "fontSize": "1.1rem", "color": "#2c3e50"}),
                                                    dcc.DatePickerRange(id='date-picker',
                                                                          min_date_allowed=dt.datetime(2001,1,1),
                                                                          max_date_allowed=dt.datetime.today(),
                                                                          start_date=dt.datetime(2020,1,1),
                                                                          end_date=dt.datetime.today(),
                                                                          className="mb-3"
                                                                        ),
                                                ], width=5
                                            ),
                                            dbc.Col(
                                                [
                                                    html.Label("\u00a0"),  # Spacer
                                                    html.Br(),
                                                    dbc.Button("Compare", id='submit-button', style={"backgroundColor": "#0f4c81", "border": "none"}, className="w-100"),
                                                ], width=2
                                            ),
                                        ],
                                        className="align-items-end"
                                    ),
                                    html.Hr(),
                                    dcc.Graph(id='stock_graph', figure={'layout':{'title':'Stock(s)'}}),
                                    html.Small("* Data extracted from Yahoo! Finance's API. For research purposes only.", className="text-muted"),
                                ]
                            )
                        ],
                        className="mb-5 shadow"
                    ),
                ],
            ),
            
            # ==================== SECTION 2: Company Deep Dive Analysis ==================== #
            html.Div(
                [
                    dbc.Card(
                        [
                            dbc.CardHeader(
                                html.H3([
                                    html.I(className="bi bi-building me-2"),
                                    "🏢 Company Deep Dive Analysis"
                                ], className="mb-0"),
                                style={"backgroundColor": "#16697a", "color": "white"}
                            ),
                            dbc.CardBody(
                                [
                                    html.P("Deep dive into a single company's financials, leadership, and metrics", className="text-muted mb-3"),
                                    dbc.Row(
                                        [
                                            dbc.Col(
                                                [
                                                    html.Label([
                                                        html.I(className="bi bi-building me-2"),
                                                        "Select Single Stock for Details"
                                                    ], style={"fontWeight": "600", "fontSize": "1.1rem", "color": "#2c3e50"}),
                                                    dcc.Dropdown(id='stock_picker_2',
                                                                    options=options,
                                                                    value=ticker,
                                                                    multi=False,
                                                                    className="mb-2"
                                                                ),
                                                ], width=10
                                            ),
                                            dbc.Col(
                                                [
                                                    html.Label("\u00a0"),  # Spacer
                                                    dbc.Button("Update Details", id='submit-button-2', style={"backgroundColor": "#16697a", "border": "none"}, className="w-100"),
                                                ], width=2
                                            )
                                        ],
                                        className="mb-3 align-items-end"
                                    ),
                                    html.Hr(),
                                    tabs,
                                ]
                            )
                        ],
                        className="mb-4 shadow"
                    ),
                ],
            ),
            
            # Educational Notes at the bottom
            html.Div(
                [
                    html.H5("📚 Educational Notes"),
                    dbc.Accordion(
                        [
                            dbc.AccordionItem(
                                dcc.Markdown("""
                                1. **Revenue Growth**: Look for consistent or increasing revenue.
                                2. **Profitability**: Consistently positive net income and expanding margins.
                                3. **EPS**: Increasing EPS suggests growth and value creation.
                                """),
                                title="Key Financial Metrics Explained"
                            ),
                            dbc.AccordionItem(
                                dcc.Markdown("""
                                - **Low D/E (< 0.5)**: Conservative, less debt.
                                - **Moderate D/E (0.5 - 1.5)**: Balanced.
                                - **High D/E (> 1.5)**: Leveraged, higher risk.
                                """),
                                title="Debt-to-Equity Ratio Guide"
                            ),
                        ],
                        start_collapsed=True,
                    )
                ],
                className="mb-5"
            )
        ],
        fluid=True,
    )
    
    return layout
