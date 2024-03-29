"""
This app offers a valuable educational experience for users interested in exploring investment opportunities in 
companies. By simply entering a company's ticker symbol, users gain access to a wealth of financial metrics and 
insights. From key financial ratios to historical performance data, our platform empowers users to make informed 
decisions by providing a comprehensive view of a company's financial health. Whether you're a seasoned investor 
or just getting started, our user-friendly interface and in-depth financial analysis tools make it easy to delve 
into the world of investment and financial analysis.

The app consists of two main parts:
1- Stock Price Trends: The graph shows the 'Close' price trend of the company selected. You can choose multiple
companies and the earliest 01/01/2001
2- Company Specific Details: This single selection part shows details about company's executive board, its 
business details and financial details, including
    - Revenue Growth
    - Profitability
    - Earnings Per Share (EPS)
    - Debt Levels
    - Cash Flow
    - Dividend History
    - Asset Quality


Disclaimer: Data extracted from Yahoo! Finance's API, and is intended only for research and educational purposes!
"""


# Import Packages

# Dashboard packages
from dash import Dash, dcc, html, Input, Output, State, dash_table
import plotly.express as px


# Connect to Yahoo! Finance's API using 'yfinance' Module
import yfinance as yf

# Smarter scraping
"""
To use a custom 'requests' session (for example to cache calls to the API or customize the 'User-agent' header), 
pass a 'session='' argument to the Ticker constructor.
Combine a 'requests_cache' with rate-limiting to avoid triggering Yahoo's rate-limiter/blocker that can corrupt data.
"""
from requests import Session
from requests_cache import CacheMixin, SQLiteCache
from requests_ratelimiter import LimiterMixin, MemoryQueueBucket
from pyrate_limiter import Duration, RequestRate, Limiter
class CachedLimiterSession(CacheMixin, LimiterMixin, Session):
    pass

# Data manipulation packages
import numpy as np
import pandas as pd

# pandas_datareader to retrieve tickers
import pandas_datareader.nasdaq_trader as nas

# For read_json
from io import StringIO

# Date and Datetime manipulation 
import datetime as dt

# Zipcodes to Lat/Lon
import uszipcode
# Maps
import folium

# Time manipulation
import time


# Get the list of all available equity symbols from Nasdaq
nsdq = nas.get_nasdaq_symbols()

# Filter data
nsdq['Security Name'] = nsdq['Security Name'].str.replace(" Common Stock","").str.replace("-","").str.rstrip()
nsdq_filtered = nsdq[~nsdq['Security Name'].str.contains('%')]
nsdq_filtered = nsdq_filtered[~nsdq_filtered['Security Name'].str.contains('share')]
nsdq_filtered = nsdq_filtered[~nsdq_filtered['Security Name'].str.contains('redeemable')]
nsdq_filtered = nsdq_filtered[~nsdq_filtered['Security Name'].str.contains('exercise')]
nsdq_filtered = nsdq_filtered[~nsdq_filtered['Security Name'].str.contains('representing')]
nsdq_filtered = nsdq_filtered[~nsdq_filtered.index.isnull()]



# options for dropdown menu
options = []
for tic in nsdq_filtered.index:
    tic_dict = {}
    tic_dict['label'] = nsdq.loc[tic]['Security Name']+" - "+tic  # Apple Inc. - AAPL
    tic_dict['value'] = tic
    options.append(tic_dict)

# date limits
end_date = dt.datetime.now()
start_date = dt.datetime(2020,1,1)

# create a session for smart data extraction
session = CachedLimiterSession(
    limiter=Limiter(RequestRate(5, Duration.SECOND*5)),  # max 5 requests per 5 seconds
    bucket_class=MemoryQueueBucket,
    backend=SQLiteCache("yfinance.cache"),
)
session.headers['User-agent'] = 'my-program/1.0'


# symbol to initialize
ticker = 'AAPL'

# columns for officers table
officers_table_columns = ['symbol','name','title','age','fiscalYear',
                          'totalPay', 'website', 'industry']

# columns for company table
company_table_columns = ['shortName','address1','city','state','zip','country','website',
                         'industry', 'sector','longBusinessSummary','governanceEpochDate']


# create app
app = Dash(__name__)
server = app.server

app.layout = html.Div([
                html.H1('Stocks Dashboard'),
                html.Div([html.H3('Select or Enter Stock(s) Symbol:', 
                                style={'paddingRight':'30px'}),
                        dcc.Dropdown(id='stock_picker',
                                options=options,
                                value=[ticker],
                                multi=True
                        )
                ], style={'display':'inline-block', 'verticalAlign':'top', 'width':'30%'}),

                html.Div([html.H3('Select a start and end date:'),
                          dcc.DatePickerRange(id='date-picker',
                                                min_date_allowed=dt.datetime(2001,1,1),
                                                max_date_allowed=dt.datetime.today(),
                                                start_date=dt.datetime(2020,1,1),
                                                end_date=dt.datetime.today())
                        ],style={'display':'inline-block','marginLeft':'30px'}),
                
                html.Div([html.Button(id='submit-button',
                                    n_clicks=0,
                                    children='Submit',
                                    style={'fontSize':24,'marginLeft':'30px'})
                        ],style={'display':'inline-block'}),

                dcc.Graph (id='stock_graph',
                        figure={'data':[{'x':[1,5], 'y':[2,8]}],
                                'layout':{'title':'Stock(s)'}}
                            ),

            html.Div([
                html.H5('* IMPORTANT LEGAL DISCLAIMER *'),
                html.H6("Data extracted from Yahoo! Finance's API, and is intended only for research and educational purposes! (Earliest Date is 01/01/2001)", 
                        style={'color':'gray'}),
                ]),
            
            html.Br(),
    
            html.Div([
                html.H2("Company Specific Details (Single)"), 
                html.Div([
                    html.H3('Select or Enter a Stock Symbol:', 
                                    style={'paddingRight':'20px'}
                           ),

                    dcc.Dropdown(id='stock_picker_2',
                                    options=options,
                                    value=ticker,
                                    multi=False,
                                    style={'display':'inline-block',
                                           'verticalAlign':'top', 
                                           'width':'80%'
                                          }
                                ),

                    html.Button(id='submit-button-2',
                                n_clicks=0,
                                children='Submit',
                                style={'fontSize':20,
                                       'marginLeft':'10px',
                                       'display':'inline-block',
                                       'verticalAlign':'top',
                                      }
                               ),
                    
                    # html.Div(id='intermediate-value-ticker-info', 
                    #          style={'display': 'none'}), # hidden from user, only to get data
                    dcc.Store(id='intermediate-value-ticker-info'),  # Use a dcc.Store to store data
                    dcc.Store(id='intermediate-value-ticker-income_stmt_annual'),
                    dcc.Store(id='intermediate-value-ticker-income_stmt_quarterly'),
                    dcc.Store(id='intermediate-value-ticker-balance_sheet'),
                    dcc.Store(id='intermediate-value-ticker-cash_flow'),
                    dcc.Store(id='intermediate-value-ticker-dividends'),
                    # dcc.Store(id='intermediate-value-ticker-assets'),



                    html.Br(),
                    
                    html.H3("Executive Officers"),
                    
                    dash_table.DataTable(id='executive_table',
                                    columns=[{'name':col, 'id':col} for col in officers_table_columns],
                                    style_cell={'textAlign': 'left'},
                                    ),

                    html.Br(),
                    
                    html.H3("Company Details"),                    
                    dash_table.DataTable(id='company_table', 
                                        columns = [{"name": "label", "id": "label"},
                                                   {"name": "value", "id": "value"}],
                                        style_data={'whiteSpace': 'normal',
                                                  'height': 'auto'},
                                         style_cell={'textAlign': 'left', 
    #                                               'minWidth': 95, 
    #                                               'width': 95, 
    #                                               'maxWidth': 95,
                                                 },

                                        ),

                    html.Iframe(id='company_map',
                                srcDoc=open('company.html', 'r').read(),
                                style={'width': '80%', 'height': '400px'}
    #                             height = '350',
    #                             width = '450'
                               ),
                    html.H5("Marker shows a rough location of the company ",
                            style={'color':'gray'}),


                        ]),

                # html.Div(id='intermediate-value-ticker-income_stmt_annual', 
                #         style={'display': 'none'}), # hidden from user, only to get data
                # html.Div(id='intermediate-value-ticker-income_stmt_quarterly', 
                #         style={'display': 'none'}), # hidden from user, only to get data
                # html.Div(id='intermediate-value-ticker-balance_sheet', 
                #         style={'display': 'none'}), # hidden from user, only to get data
                # html.Div(id='intermediate-value-ticker-cash_flow', 
                #         style={'display': 'none'}), # hidden from user, only to get data
                # html.Div(id='intermediate-value-ticker-dividends', 
                #         style={'display': 'none'}), # hidden from user, only to get data
                # html.Div(id='intermediate-value-ticker-assets', 
                #         style={'display': 'none'}), # hidden from user, only to get data
                
                html.Br(),
                
                html.Div([
                html.H3("Company Financial Details"),
                
                dcc.Markdown("""Following Parameters will be analyzed:
                             
1. Revenue Growth

2. Profitability

3. Earnings Per Share (EPS)

4. Debt Levels

5. Cash Flow

6. Dividend History

7. Asset Quality
 """
                         ),
               
                dcc.Markdown("""Before investing:
                
- Look into the company's management team, their track record, and their strategic plans

- Consider the company's position within its industry

- Compare the company's financial metrics to those of its competitors.

- Identify potential risks, i.e. regulatory changes, industry shifts, or economic factors, that could impact the company's financial performance

- Consider the company's long-term growth potential (innovation, expansion, and adapting to changing markets)
             """
                         ),
        
                html.Br(),
                
                html.H3("1. Revenue Growth Trends"),
                html.H5("Analyze the company's revenue trends over the past several years. \
                        Look for consistent or increasing revenue, which indicates a healthy business."),

                dcc.Graph(id='revenue_graph_annual',
                          figure={'data':[{'x':[1,5], 'y':[2,8]}],
                                  'layout':{'title':"Total Revenue Trend Annual"}}
                        ),

                dcc.Graph(id='revenue_graph_quarterly',
                          figure={'data':[{'x':[1,5], 'y':[2,8]}],
                                  'layout':{'title':"Total Revenue Trend Quarterly"}}
                        ),
                
                html.Br(),
                    
                html.H3("2. Profitability"),
                html.H5("Examine the company's net income and profit margins. Consistently positive \
                net income and expanding profit margins are positive signs of profitability."),
                    
                dcc.Graph(id='operating_income_graph_annual',
                          figure={'data':[{'x':[1,5], 'y':[2,8]}],
                                  'layout':{'title':''}}
                        ),

                dcc.Graph(id='operating_income_graph_quarterly',
                          figure={'data':[{'x':[1,5], 'y':[2,8]}],
                                  'layout':{'title':''}}
                        ),
                    
                dcc.Graph(id='net_income_graph_annual',
                          figure={'data':[{'x':[1,5], 'y':[2,8]}],
                                  'layout':{'title':''}}
                        ),

                dcc.Graph(id='net_income_graph_quarterly',
                          figure={'data':[{'x':[1,5], 'y':[2,8]}],
                                  'layout':{'title':''}}
                        ),
                
                dash_table.DataTable(id='profit_table',
                                    columns=[
                                        {'name': 'date', 'id': 'date'},
                                        {'name': 'label', 'id': 'label'},
                                        {'name': 'value', 'id': 'value'},
                                    ],
                                     style_cell={'textAlign': 'left'},
                                    ),

                html.H3("3. Earnings Per Share (EPS)"),
                html.H5("Increasing EPS over time suggests that the company is growing its earnings and \
                    potentially creating value for shareholders. There are two types of EPSs:"),
                html.H5("a) Basic EPS"),
                html.H5("b) Diluted EPS"),
                html.H5("The difference between the two lies in the calculation of treatment of potentially dilutive securities, including \
                    stock options, convertible bonds, convertible preferred stock, and other financial instruments that could be \
                    converted into common shares."),
                html.H5("Generally, the EPS is calculated by dividing a company's net earnings (or profit) by the total number of outstanding \
                    shares of its common stock:"),
                html.H5("EPS = Net Earnings / Total number of outstanding shares of its common stock."),
                html.H5("When it comes to calculation of Basic and Diluted EPS, first Preferred Dividends are subtracted from the Net Earnings, and \
                    the denominator becomes Weighted Average Number of Common Shares Outstanding and Adjusted Weighted Average Number of Common Shares \
                    Outstanding respectively:"),
                html.H5("Basic EPS = (Net Earnings - Preferred Dividends) / Weighted Average Number of Common Shares Outstanding"),
                html.H5("Diluted EPS = (Net Earnings - Preferred Dividends) / Adjusted Weighted Average Number of Common Shares Outstanding"),
                            
#                 dcc.Graph(id='basic_eps_graph_annual',
#                           figure={'data':[{'x':[1,5], 'y':[2,8]}],
#                                   'layout':{'title':''}}
#                         ),
#                 dcc.Graph(id='diluted_eps_graph_annual',
#                           figure={'data':[{'x':[1,5], 'y':[2,8]}],
#                                   'layout':{'title':''}}
#                         ),
                dcc.Graph(id='basic_eps_graph_quarterly',
                          figure={'data':[{'x':[1,5], 'y':[2,8]}],
                                  'layout':{'title':''}}
                        ),
                dcc.Graph(id='diluted_eps_graph_quarterly',
                          figure={'data':[{'x':[1,5], 'y':[2,8]}],
                                  'layout':{'title':''}}
                        ),
                
                html.H3("4. Debts and D/E Ration"),
                html.H5("Assess the company's debt-to-equity ratio and interest coverage ratio. A company with manageable debt and sufficient \
                earnings to cover interest payments is in a stronger financial position"),
                html.H5("The Debt-to-Equity ratio is calculated as follows:"),
                html.H5("Debt-to-Equity Ratio = Total Debt / Total Equity"),
                html.H5("You can use Total Stockholders' Equity as a proxy for Total Equity  when calculating financial ratios like the Debt-to-Equity ratio. \
                        Total Stockholders' Equity represents the ownership interest of the company's shareholders, and can be substitute with Total Equity to \
                        calculate the ratio using the following formula:"),
                html.H5("Debt-to-Equity Ratio = Total Debt / Total Stockholders' Equity"),
                html.H5("The Debt-to-Equity ratio can vary across industries, companies, and economic conditions. While there isn't a universally \
                        defined set of buckets or levels for the D/E ratio that apply to all situations, some general insights can be offered based \
                        on common practices and considerations:"),
                html.H5("Low D/E Ratio (Conservative): \
                A lower D/E ratio indicates that a company relies less on debt financing and has a larger proportion of equity in its capital \
                structure. This is often seen as a conservative approach to financing. Companies with low D/E ratios may be better positioned to\
                withstand economic downturns, as they have lower interest payments and financial obligations. \
                A typical range for a low D/E ratio might be 0 to 0.5, but this can vary widely depending on the industry."),
                html.H5("Moderate D/E Ratio (Balanced): \
                Companies with a moderate D/E ratio strike a balance between debt and equity financing. They use a mix of both to fund their \
                operations, growth, and investments. This allows them to benefit from the advantages of leverage while managing their risk exposure. \
                A common range for a moderate D/E ratio might be 0.5 to 1.5, but again, it depends on the industry and other factors."),
                html.H5("High D/E Ratio (Leveraged): \
                A higher D/E ratio indicates that a company relies more on debt financing, potentially exposing \
                it to higher financial risk. While leverage can amplify returns during favorable economic conditions, it can also magnify losses \
                during downturns. Companies with high D/E ratios may find it challenging to meet debt obligations if their cash flows decline. \
                The upper limit for a high D/E ratio varies significantly across industries but might range from 1.5 to 3 or higher"),
                html.H5("It's important to note that acceptable D/E ratios can vary based on industry norms, business models, and risk tolerance. \
                For example, capital-intensive industries like utilities might have higher D/E ratios due to the nature of their assets and stable \
                cash flows, while technology startups might have lower D/E ratios due to their focus on equity financing.\
                Additionally, macroeconomic conditions, interest rates, and the cost of debt can influence what constitutes a reasonable D/E ratio.\
                When analyzing a company's D/E ratio, it's crucial to consider the broader economic context, industry benchmarks, company-specific \
                factors, and long-term financial strategies."),

                dcc.Graph(id='debt_graph_annual',
                          figure={'data':[{'x':[1,5], 'y':[2,8]}],
                                  'layout':{'title':''}}
                         ),
                dcc.Graph(id='equity_graph_annual',
                          figure={'data':[{'x':[1,5], 'y':[2,8]}],
                                  'layout':{'title':''}}
                         ),
                dcc.Graph(id='d2e_graph_annual',
                          figure={'data':[{'x':[1,5], 'y':[2,8]}],
                                  'layout':{'title':''}}
                         ),
                # ADD Tabular data for D,E, D/E
                    
                html.H3("5. Cash Flow"),
                html.H5("Examine the company's operating cash flow and free cash flow. Positive and increasing cash flow can indicate that the company is generating cash from its core operations and has the ability to invest, pay dividends, or reduce debt."),
                 
                dcc.Graph(id='operating_cashflow_graph_annual',
                          figure={'data':[{'x':[1,5], 'y':[2,8]}],
                                  'layout':{'title':''}}),
                
                dcc.Graph(id='free_cashflow_graph_annual',
                          figure={'data':[{'x':[1,5], 'y':[2,8]}],
                                  'layout':{'title':''}}),     

                html.H3("6. Dividend History"),
                html.H5("If the company pays dividends, review its dividend history. Consistent or increasing dividends indicate stability and potential income for investors."),
                dcc.Graph(id='dividends_graph',
                          figure={'data':[{'x':[1,5], 'y':[2,8]}],
                                  'layout':{'title':''}}),
                
                html.H3("7. Assets"),
                html.H5("Study the company's asset composition. High-quality assets, such as cash and liquid investments, can provide a safety net during challenging times."),
                   
                dcc.Graph(id='total_assets_graph_annual',
                          figure={'data':[{'x':[1,5], 'y':[2,8]}],
                                  'layout':{'title':''}}),
                
                dcc.Graph(id='current_assets_graph_annual',
                          figure={'data':[{'x':[1,5], 'y':[2,8]}],
                                  'layout':{'title':''}}),     
                
                dcc.Graph(id='investment_in_financial_assets_graph_annual',
                          figure={'data':[{'x':[1,5], 'y':[2,8]}],
                                  'layout':{'title':''}}),  
                ])            
            ])  
])

# ------------------------------------- Time Series ------------------------------------- #
@app.callback(Output('stock_graph','figure'),
            [Input('submit-button','n_clicks')],
            [State('stock_picker','value'),
            State('date-picker','start_date'),
            State('date-picker','end_date')],
            )
def update_stock_trend_graph(n_clicks,stock_ticker,start_date, end_date):
    
    start = dt.datetime.strptime(start_date[:10],'%Y-%m-%d')
    end = dt.datetime.strptime(end_date[:10],'%Y-%m-%d')

    traces = []

    for tic in stock_ticker:
        try:
            df = yf.download(tic, 
                             start=start, 
                             end=end, 
                             threads=False, 
                             session = session,
                             progress=False    #to remove [100%**] 1 of 1 completed message
                            )
        except:
            print("Ticker's min date point is not valid")
            pass
        traces.append({'x':df.index, 'y':df['Close'], 'name':tic})

    fig = {
        'data':traces,
        'layout':{'title':stock_ticker}
    }
    return fig

# Access to Ticker's Info
@app.callback(Output(component_id='intermediate-value-ticker-info',component_property='data'),
    [Input(component_id='submit-button-2', component_property='n_clicks')],
    [State(component_id='stock_picker_2', component_property='value')])
def get_ticker_info(n_clicks,symbol='TSLA'):
    ticker_info_data = None 
    try:
        ticker_info_data = yf.Ticker(symbol, session=session).info
    except:
        pass
    return ticker_info_data
    

# Executive Officers Table
@app.callback(Output(component_id='executive_table', component_property='data'),
    [Input(component_id='intermediate-value-ticker-info', component_property='data')])
def update_executive_table(ticker_info_data):
    # create a pandas dataframe (null)
    officers_df = pd.DataFrame()
    
    try:
        # parameters we would like to extract
        parameters_interested = ['name','title','age','fiscalYear','totalPay']
        values_list = []

        # loop through officers
        for o in ticker_info_data['companyOfficers']:
            officer_values = []
            for p in parameters_interested:
                if p not in list(o.keys()):
                    o[p] = None
                officer_values.append(o[p])
            officer_values.insert(0,ticker_info_data['symbol'])
            officer_values.insert(1,ticker_info_data['shortName'])
            officer_values.append(ticker_info_data['website'])
            officer_values.append(ticker_info_data['industry'])
            values_list.append(officer_values)

        # create a pandas dataframe with officers' values
        officers_df = pd.DataFrame(data=values_list, columns = ['symbol','company'] + parameters_interested +['website','industry'])
    except:
        pass
    return officers_df.to_dict(orient='records')

# ------------------------------------- Company Table ------------------------------------- #
@app.callback(Output(component_id='company_table', component_property='data'),
    [Input(component_id='intermediate-value-ticker-info', component_property='data')])
def update_company_table(ticker_info_data):

    company_df = pd.DataFrame()
    
    try:
        # create a dict to store data
        new_dict = {}
        
        # loop through parameters
        for i in company_table_columns:
            
            # convert Unix Timestamp to Date String
            if i == 'governanceEpochDate':
                ts = ticker_info_data['governanceEpochDate']
                ticker_info_data[i] = dt.datetime.utcfromtimestamp(ts).strftime('%m/%d/%Y')
            
            new_dict[i] = ticker_info_data[i]

        # create pandas dataframe
        temp_df = pd.DataFrame(new_dict, index = [0])
        company_df = temp_df.T
        company_df.reset_index(inplace=True)
        company_df.columns=['label','value']
        
        # update parameters names
        company_df.iloc[0,0] = 'company'    # < shortName
        company_df.iloc[1,0] = 'street'    # < address1
        company_df.iloc[9,0] = 'businessSummary'  # < longBusinessSummary
        company_df.iloc[10,0] = 'governanceDate'  # < governanceEpochDate      

    except:
        pass
    return company_df.to_dict(orient='records')


# ------------------------------------- MAP ------------------------------------- #

@app.callback(Output(component_id='company_map', component_property='srcDoc'),
    [Input(component_id='intermediate-value-ticker-info', component_property='data')])
def update_map(ticker_info_data):
    map_html = ''
    try:
        ticker_zip_code = ticker_info_data['zip'][:5]
        zip_details = uszipcode.SearchEngine().by_zipcode(ticker_zip_code)
        lat = zip_details.lat 
        lng = zip_details.lng

        # Company details to show in the pop-up
        address = (ticker_info_data['address1'],
                   ticker_info_data['city'],
                   ticker_info_data['state'],
                   ticker_info_data['zip'][:5],
                   ticker_info_data['country'])
        address = ', '.join(address)
        text = f"Symbol: {ticker_info_data['symbol']} Name: {ticker_info_data['shortName']} Address: {address}"

        # Tiles from OpenStreetMap
        tiles = 'OpenStreetMap'

        # Display the Company Location
        # create basemap
        map_obj = folium.Map(location=[lat,lng],
                            tiles=tiles,
                            zoom_start=5)

        # place ports on the map
        folium.Marker(location=[lat,lng],
                      popup = text,
                      icon = folium.Icon(color='orange', 
                                         icon=f'briefcase',) # if wants to use an icon

                     ).add_to(map_obj)
        map_html = map_obj.get_root().render()
#         map_name = 'company.html'
#         map_obj.save(map_name)
        
    except:
        pass

    return f'{map_html}'
    
# ------------------------------------- FINANCIAL ANALYSIS ------------------------------------- #

# ------------------------------------- 1. Revenue: Annual and Quarterly ------------------------------------- #
# Annual
@app.callback(Output(component_id='intermediate-value-ticker-income_stmt_annual', component_property='data'),
              [Input(component_id='submit-button-2', component_property='n_clicks')],
              [State(component_id='stock_picker_2', component_property='value')])
def get_ticker_income_stmt_annual(n_clicks, symbol='TSLA'):
    """
    Input: symbol
    Output: ticker.income_stmt
    """
    ticker_income_stmt = pd.DataFrame()
    try:
        ticker_income_stmt =  yf.Ticker(symbol, session=session).income_stmt
    except:
        pass
    return ticker_income_stmt.to_json()  # Convert DataFrame to JSON for serialization

@app.callback(Output(component_id='revenue_graph_annual', component_property='figure'),
              [Input(component_id='intermediate-value-ticker-income_stmt_annual', component_property='data')])
def update_revenue_graph_annual(ticker_income_stmt_json):
    """
    Company's Annual Total Revenue Analysis (using income_stmt)
    Input: ticker's income_stmt
    """
    # if not ticker_income_stmt_json:
    #     raise PreventUpdate
        # to load data appropriately 
    time.sleep(1)
    ticker_income_stmt = pd.read_json(StringIO(ticker_income_stmt_json))

    factor = 'Total Revenue'
  
    df = ticker_income_stmt.loc[factor].T.reset_index()
    df.columns = ['Date', factor]
    df.dropna(inplace=True)
    df['Date'] = pd.to_datetime(df['Date']).dt.date
    df[factor] = df[factor].astype(float)
    
    fig = px.bar(df, 
                 x='Date',
                 y=factor,
                 title='Annual Total Revenue',
                 color=factor,
                 text=factor,
    )

    fig.update_layout(
        xaxis=dict(
            type='category',
            # tickangle=315
        ),
    )
    
    return fig


# Quarterly
@app.callback(Output('intermediate-value-ticker-income_stmt_quarterly', 'data'),
              [Input('submit-button-2', 'n_clicks')],
              [State('stock_picker_2', 'value')])
def get_ticker_income_stmt_quarterly(n_clicks, symbol='TSLA'):
    """
    Input: symbol
    Output: ticker.income_stmt
    """
    ticker_income_stmt_quarterly = pd.DataFrame()
    try:
        ticker_income_stmt_quarterly =  yf.Ticker(symbol, session=session).quarterly_income_stmt
    except:
        pass
    return ticker_income_stmt_quarterly.to_json()  # Convert DataFrame to JSON for serialization

@app.callback(Output(component_id='revenue_graph_quarterly', component_property='figure'),
              [Input(component_id='intermediate-value-ticker-income_stmt_quarterly', component_property='data')])
def update_revenue_graph_quarterly(ticker_income_stmt_quarterly_json):
    """
    Company's Annual Total Revenue Analysis (using income_stmt)
    Input: ticker's income_stmt
    """
    # if not ticker_income_stmt_quarterly_json:
    #     raise PreventUpdate
    
    # to load data appropriately 
    time.sleep(1)
    
    ticker_income_stmt_quarterly = pd.read_json(StringIO(ticker_income_stmt_quarterly_json))

    factor = 'Total Revenue'
  
    df = ticker_income_stmt_quarterly.loc[factor].T.reset_index()
    df.columns = ['Date', factor]
    df.dropna(inplace=True)
    df['Date'] = pd.to_datetime(df['Date']).dt.date
    df[factor] = df[factor].astype(float)
    
    fig = px.bar(df, 
                 x='Date',  
                 y=factor,  
                 title='Quarterly Total Revenue',
                 color=factor,
                 text=factor,
    )

    fig.update_layout(
        xaxis=dict(
            type='category',
        ),
    )
    
    return fig

# ------------------------------------- 2. Profitability ------------------------------------- #
# Operating Income As Reported
# Annual
@app.callback(Output(component_id='operating_income_graph_annual', component_property='figure'),
              [Input(component_id='intermediate-value-ticker-income_stmt_annual', component_property='data')])
def update_op_inc_graph_annual(ticker_income_stmt_json):
    """
    Company's Annual Total Revenue Analysis (using income_stmt)

    Input: ticker's income_stmt
    """
    # if not ticker_income_stmt_json:
    #     raise PreventUpdate

    # to load data appropriately 
    time.sleep(1)

    ticker_income_stmt = pd.read_json(StringIO(ticker_income_stmt_json))

    factor = 'Total Operating Income As Reported'
  
    df = ticker_income_stmt.loc[factor].T.reset_index()
    df.columns = ['Date', factor]
    df.dropna(inplace=True)
    df['Date'] = pd.to_datetime(df['Date']).dt.date
    df[factor] = df[factor].astype(float)
    
    fig = px.bar(df, 
                 x='Date',
                 y=factor,  
                 title='Annual Total Operating Income As Reported (Operating Profit, EBIT) ',
                 color=factor,
                 text=factor,
    )

    fig.update_layout(
        xaxis=dict(
            type='category',
        ),
    )
    
    return fig



@app.callback(Output(component_id='operating_income_graph_quarterly', component_property='figure'),
              [Input(component_id='intermediate-value-ticker-income_stmt_quarterly', component_property='data')])
def update_op_inc_graph_quarterly(ticker_income_stmt_quarterly_json):
    """
    Company's Annual Total Revenue Analysis (using income_stmt)

    Input: ticker's income_stmt
    """
    # if not ticker_income_stmt_quarterly_json:
    #     raise PreventUpdate

    # to load data appropriately 
    time.sleep(1)

    ticker_income_stmt_quarterly = pd.read_json(StringIO(ticker_income_stmt_quarterly_json))

    factor = 'Total Operating Income As Reported'
  
    df = ticker_income_stmt_quarterly.loc[factor].T.reset_index()
    df.columns = ['Date', factor]
    df.dropna(inplace=True)
    df['Date'] = pd.to_datetime(df['Date']).dt.date
    df[factor] = df[factor].astype(float)
    
    fig = px.bar(df, 
                 x='Date',  
                 y=factor,  
                 title='Quarterly Total Operating Income As Reported (Operating Profit, EBIT)',
                 color=factor,
                 text=factor,
    )

    fig.update_layout(
        xaxis=dict(
            type='category',
        ),
    )
    
    return fig


# NET Income
# Annual
@app.callback(Output(component_id='net_income_graph_annual', component_property='figure'),
              [Input(component_id='intermediate-value-ticker-income_stmt_annual', component_property='data')])
def update_net_inc_graph_annual(ticker_income_stmt_json):
    """
    Company's Annual Total Revenue Analysis (using income_stmt)

    Input: ticker's income_stmt
    """
    # if not ticker_income_stmt_json:
    #     raise PreventUpdate
    
    # to load data appropriately 
    time.sleep(1)

    ticker_income_stmt = pd.read_json(StringIO(ticker_income_stmt_json))

    factor = 'Net Income'
  
    df = ticker_income_stmt.loc[factor].T.reset_index()
    df.columns = ['Date', factor]
    df.dropna(inplace=True)
    df['Date'] = pd.to_datetime(df['Date']).dt.date
    df[factor] = df[factor].astype(float)
    
    fig = px.bar(df, 
                 x='Date',
                 y=factor,
                 title='Annual Net Income',
                 color=factor,
                 text=factor,
    )

    fig.update_layout(
        xaxis=dict(
            type='category',
        ),
    )
    
    return fig


@app.callback(Output(component_id='net_income_graph_quarterly', component_property='figure'),
              [Input(component_id='intermediate-value-ticker-income_stmt_quarterly', component_property='data')])
def update_net_inc_graph_quarterly(ticker_income_stmt_quarterly_json):
    """
    Company's Annual Total Revenue Analysis (using income_stmt)
    Input: ticker's income_stmt
    """
    # if not ticker_income_stmt_quarterly_json:
    #     raise PreventUpdate

    ticker_income_stmt_quarterly = pd.read_json(StringIO(ticker_income_stmt_quarterly_json))

    factor = 'Net Income'
  
    df = ticker_income_stmt_quarterly.loc[factor].T.reset_index()
    df.columns = ['Date', factor]
    df.dropna(inplace=True)
    df['Date'] = pd.to_datetime(df['Date']).dt.date
    df[factor] = df[factor].astype(float)
    
    fig = px.bar(df, 
                 x='Date',  # "Date"
                 y=factor,  # factor
                 title='Quarterly Net Income',
                 color=factor,
                 text=factor,
    )

    fig.update_layout(
        xaxis=dict(
            type='category',
        ),
    )
    
    return fig


@app.callback(Output(component_id='profit_table', component_property='data'),
    [Input(component_id='intermediate-value-ticker-info', component_property='data')])
def update_profit_table(ticker_info_data):
       
    df = pd.DataFrame()
    
    try:
        margins = [m for m in list(ticker_info_data.keys()) if 'margin' in m.lower()]
        margin_dict={}
        
        for m in margins:
            margin_dict[m] = np.round(ticker_info_data[m],4)
            
        df = pd.DataFrame(margin_dict,index=[0])
        df = df.T.reset_index()
        df.columns=['label','value']
        df.insert(0,'date', dt.datetime.today().date().strftime('%m/%d/%Y'))
    except:
        pass
    
    return df.to_dict(orient='records')


# ------------------------------------- 3. Earnings Per Share (EPS) ------------------------------------- #
# # Annual 
# @app.callback(Output(component_id='basic_eps_graph_annual', component_property='figure'),
#               [Input(component_id='intermediate-value-ticker-income_stmt_annual', component_property='data')])
# def update_basic_eps_graph_annual(ticker_income_stmt_json):
#     """
#     Company's Annual Basic EPS Analysis (using income_stmt)
#     Input: ticker's income_stmt
#     """
#     fig = None
#     try:
#         if not ticker_income_stmt_json:
#             raise PreventUpdate

#         ticker_income_stmt = pd.read_json(ticker_income_stmt_json)

#         factor = 'Basic EPS'
#         df = ticker_income_stmt.loc[factor].T.reset_index()
#         df.columns = ['Date', factor]
#         df.dropna(inplace=True)
#         df['Date'] = pd.to_datetime(df['Date']).dt.date
#         df[factor] = df[factor].astype(float)

#         fig = px.bar(df, 
#                      x='Date',  # "Date"
#                      y=factor,  # factor
#                      title=factor + ' Annual',
#                      color=factor,
#                      text=factor,
#         )

#         fig.update_layout(
#             xaxis=dict(
#                 type='category',
#             ),
#         )
#     except KeyError:
#         print("No Annual Basic EPS Data")
    
#     return fig


# @app.callback(Output(component_id='diluted_eps_graph_annual', component_property='figure'),
#               [Input(component_id='intermediate-value-ticker-income_stmt_annual', component_property='data')])
# def update_diluted_eps_graph_annual(ticker_income_stmt_json):
#     """
#     Company's Annual Diluted EPS Analysis (using income_stmt)

#     Input: ticker's income_stmt
#     """
#     fig = None
#     try:
#         if not ticker_income_stmt_json:
#             raise PreventUpdate

#         ticker_income_stmt = pd.read_json(ticker_income_stmt_json)
#         factor = 'Diluted EPS'
#         df = ticker_income_stmt.loc[factor].T.reset_index()
#         df.columns = ['Date', factor]
#         df.dropna(inplace=True)
#         df['Date'] = pd.to_datetime(df['Date']).dt.date
#         df[factor] = df[factor].astype(float)

#         fig = px.bar(df, 
#                      x='Date',  # "Date"
#                      y=factor,  # factor
#                      title=factor + ' Annual',
#                      color=factor,
#                      text=factor,
#         )
#         fig.update_layout(
#             xaxis=dict(
#                 type='category',
#             ),
#         )
#     except KeyError:
#         print("No Annual Diluted EPS Data")
#     return fig

# Quarterly 
@app.callback(Output(component_id='basic_eps_graph_quarterly', component_property='figure'),
              [Input(component_id='intermediate-value-ticker-income_stmt_quarterly', component_property='data')])
def update_basic_eps_graph_quarterly(ticker_income_stmt_quarterly_json):
    """
    Company's Quarterly Basic EPS Analysis (using income_stmt)
    Input: ticker's income_stmt
    """
    # if not ticker_income_stmt_quarterly_json:
    #     raise PreventUpdate

    ticker_income_stmt_quarterly = pd.read_json(StringIO(ticker_income_stmt_quarterly_json))

    factor = 'Basic EPS'
  
    df = ticker_income_stmt_quarterly.loc[factor].T.reset_index()
    df.columns = ['Date', factor]
    df.dropna(inplace=True)
    df['Date'] = pd.to_datetime(df['Date']).dt.date
    df[factor] = df[factor].astype(float)
    
    fig = px.bar(df, 
                 x='Date', 
                 y=factor,
                 title=factor + ' Quarterly',
                 color=factor,
                 text=factor,
    )

    fig.update_layout(
        xaxis=dict(
            type='category',
        ),
    )
    
    return fig

@app.callback(Output(component_id='diluted_eps_graph_quarterly', component_property='figure'),
              [Input(component_id='intermediate-value-ticker-income_stmt_quarterly', component_property='data')])
def update_diluted_eps_graph_quarterly(ticker_income_stmt_quarterly_json):
    """
    Company's Quarterly Diluted EPS Analysis (using income_stmt)

    Input: ticker's income_stmt
    """
    # if not ticker_income_stmt_quarterly_json:
    #     raise PreventUpdate

    ticker_income_stmt_quarterly = pd.read_json(StringIO(ticker_income_stmt_quarterly_json))

    factor = 'Diluted EPS'
  
    df = ticker_income_stmt_quarterly.loc[factor].T.reset_index()
    df.columns = ['Date', factor]
    df.dropna(inplace=True)
    df['Date'] = pd.to_datetime(df['Date']).dt.date
    df[factor] = df[factor].astype(float)
    
    fig = px.bar(df, 
                 x='Date',  # "Date"
                 y=factor,  # factor
                 title=factor + ' Quarterly',
                 color=factor,
                 text=factor,
    )

    fig.update_layout(
        xaxis=dict(
            type='category',
        ),
    )
    
    return fig


# ------------------------------------- 4. Debt Levels ------------------------------------- #
@app.callback(Output(component_id = 'intermediate-value-ticker-balance_sheet', component_property='data'),
              [Input('submit-button-2', 'n_clicks')],
              [State('stock_picker_2', 'value')])
def get_ticker_balance_sheet(n_clicks, symbol='TSLA'):
    """
    Input: symbol
    Output: ticker.balance_sheet
    """
    ticker_balance_sheet = pd.DataFrame()
    try:
        ticker_balance_sheet =  yf.Ticker(symbol, session=session).balance_sheet
    except:
        pass
    return ticker_balance_sheet.to_json()  # Convert DataFrame to JSON for serialization

@app.callback(Output(component_id='debt_graph_annual', component_property='figure'),
              [Input(component_id='intermediate-value-ticker-balance_sheet', component_property='data')])
def update_debt_graph(ticker_balance_sheet_json):
    """
    Company's Annual Total Debt Analysis (using balance_sheet)
    Input: ticker's balance_sheet
    """
    # if not ticker_balance_sheet_json:
    #     raise PreventUpdate

    ticker_balance_sheet = pd.read_json(StringIO(ticker_balance_sheet_json))

    factor = 'Total Debt'
    df = ticker_balance_sheet[ticker_balance_sheet.index == factor]
    df = df.T.reset_index()
    df.columns = ['Date', factor]
    df.dropna(inplace=True)
    df['Date'] = pd.to_datetime(df['Date']).dt.date
    df[factor] = df[factor].astype(float)
    
    fig = px.bar(df, 
                 x='Date',  # "Date"
                 y=factor,  # factor
                 title=factor ,
                 color=factor,
                 text=factor,
    )

    fig.update_layout(
        xaxis=dict(
            type='category',
        ),
    )
    
    return fig


@app.callback(Output(component_id='equity_graph_annual', component_property='figure'),
              [Input(component_id='intermediate-value-ticker-balance_sheet', component_property='data')])
def update_equity_graph(ticker_balance_sheet_json):
    """
    Company's Annual Total Debt Analysis (using balance_sheet)

    Input: ticker's balance_sheet
    """
    # if not ticker_balance_sheet_json:
    #     raise PreventUpdate

    ticker_balance_sheet = pd.read_json(StringIO(ticker_balance_sheet_json))

    factor = 'Stockholders Equity'  
    df = ticker_balance_sheet[ticker_balance_sheet.index == factor]
    df = df.T.reset_index()
    df.columns = ['Date', factor]
    df.dropna(inplace=True)
    df['Date'] = pd.to_datetime(df['Date']).dt.date
    df[factor] = df[factor].astype(float)
    
    fig = px.bar(df, 
                 x='Date',  # "Date"
                 y=factor,  # factor
                 title=factor ,
                 color=factor,
                 text=factor,
    )

    fig.update_layout(
        xaxis=dict(
            type='category',
        ),
    )
    
    return fig

@app.callback(Output(component_id='d2e_graph_annual', component_property='figure'),
              [Input(component_id='intermediate-value-ticker-balance_sheet', component_property='data')])
def update_d2e_graph(ticker_balance_sheet_json):
    """
    Company's Annual Total Debt/Equity Ratio Analysis (using balance_sheet)

    Input: ticker's balance_sheet
    """
    # if not ticker_balance_sheet_json:
    #     raise PreventUpdate

    ticker_balance_sheet = pd.read_json(StringIO(ticker_balance_sheet_json))

    f1 = 'Total Debt'
    f2 = 'Stockholders Equity'
    debt_df = ticker_balance_sheet[ticker_balance_sheet.index == f1]
    equity_df = ticker_balance_sheet[ticker_balance_sheet.index == f2]
    df =  pd.concat([equity_df,debt_df])
    debt_to_equity_row = df.iloc[1] / df.iloc[0]
    temp_df = pd.DataFrame(debt_to_equity_row).T
    temp_df.index = ['Debt to Equity Ratio']
    df = pd.concat([df,temp_df])
    df.iloc[-1] = df.iloc[-1].apply(lambda x: round(x,4))
    df = df.T
    df.index = pd.to_datetime(df.index).date
    df.reset_index(inplace=True)
    df.columns =['Date','Stockholders Equity','Total Debt', 'Debt to Equity Ratio']
    
    factor = 'Debt to Equity Ratio'
    
    fig = px.bar(df, 
                 x='Date',  # "Date"
                 y=factor,  # factor
                 title=factor ,
                 color=factor,
                 text=factor,
    )

    fig.update_layout(
        xaxis=dict(
            type='category',
        ),
    )
    
    return fig


# ------------------------------------- 5. Cash Flows ------------------------------------- #
@app.callback(Output('intermediate-value-ticker-cash_flow', 'data'),
             [Input('submit-button-2','n_clicks')],
             [State('stock_picker_2','value')]) 
def get_ticker_cash_flow(n_clicks, symbol='TSLA'):
    """
    Input: symbol
    Output: ticker.cash_flow
    """
    ticker_cash_flow = pd.DataFrame()
    try:
        ticker_cash_flow =  yf.Ticker(symbol, session=session).cash_flow
    except:
        pass
    return ticker_cash_flow.to_json()  # Convert DataFrame to JSON for serialization

@app.callback(Output(component_id='operating_cashflow_graph_annual', component_property='figure'),
              [Input(component_id='intermediate-value-ticker-cash_flow', component_property='data')])
def update_op_cashflow_graph(ticker_cash_flow_json):
    """
    Company's Annual Operating Cash Flow Analysis (using cash_flow)
    Input: ticker's cash_flow
    """
    # if not ticker_cash_flow_json:
    #     raise PreventUpdate

    ticker_cash_flow = pd.read_json(StringIO(ticker_cash_flow_json))
    
    factor = 'Operating Cash Flow'  
    df = ticker_cash_flow[ticker_cash_flow.index == factor]
    df = df.T.reset_index()
    df.columns = ['Date',factor]
    df.dropna(inplace=True)
    df['Date'] = pd.to_datetime(df['Date']).dt.date

    fig = px.bar(df, 
                 x='Date',  # "Date"
                 y=factor,  # factor
                 title=factor ,
                 color=factor,
                 text=factor,
    )

    fig.update_layout(
        xaxis=dict(
            type='category',
        ),
    )
    
    return fig


@app.callback(Output(component_id='free_cashflow_graph_annual', component_property='figure'),
              [Input(component_id='intermediate-value-ticker-cash_flow', component_property='data')])
def update_free_cashflow_graph(ticker_cash_flow_json):
    """
    Company's Annual Free Cash Flow Analysis (using cash_flow)

    Input: ticker's cash_flow
    """
    # if not ticker_cash_flow_json:
    #     raise PreventUpdate

    ticker_cash_flow = pd.read_json(StringIO(ticker_cash_flow_json))
    
    
    factor = 'Free Cash Flow'  
    df = ticker_cash_flow[ticker_cash_flow.index == factor]
    df = df.T.reset_index()
    df.columns = ['Date',factor]
    df.dropna(inplace=True)
    df['Date'] = pd.to_datetime(df['Date']).dt.date
    df

    fig = px.bar(df, 
                 x='Date',  # "Date"
                 y=factor,  # factor
                 title=factor ,
                 color=factor,
                 text=factor,
    )

    fig.update_layout(
        xaxis=dict(
            type='category',
        ),
    )
    
    return fig


# ------------------------------------- 6. Dividend History ------------------------------------- #
@app.callback(Output('intermediate-value-ticker-dividends', 'data'),
             [Input('submit-button-2','n_clicks')],
             [State('stock_picker_2','value')]) 
def get_ticker_dividends(n_clicks, symbol=ticker):
    """
    Input: symbol
    Output: ticker.dividends
    """
    ticker_dividends = pd.DataFrame()
    try:
        ticker_dividends =  yf.Ticker(symbol, session=session).dividends.reset_index()
    except:
        pass
    return ticker_dividends.to_json()  # Convert DataFrame to JSON for serialization

@app.callback(Output(component_id='dividends_graph', component_property='figure'),
              [Input(component_id='intermediate-value-ticker-dividends', component_property='data')])
def update_dividends_graph(ticker_dividends_json):
    """
    Company's Dividend Analysis (using dividends)
    Input: ticker's dividends
    """
    # if not ticker_dividends_json:
    #     raise PreventUpdate

    ticker_dividends = pd.read_json(StringIO(ticker_dividends_json))
    
    # check if there is data available
    if len(ticker_dividends) == 0:
        return {
            'data': [],
            'layout': {
                'annotations': [
                    {
                        'text': 'No Dividends Data',
                        'x': 1,
                        'y': 0.5,
                        'showarrow': False,
                        'font': {'size': 24}
                    }
                ]
            }
        }

    factor = 'Dividends'
    try:
        df = ticker_dividends.copy(deep=True)
        df.columns = ['Date',factor]
        df.dropna(inplace=True)
        df['Date'] = pd.to_datetime(df['Date']).dt.date

        fig = px.bar(df, 
                    x='Date',  
                    y=factor,  
                    title=factor ,
                    color=factor,
                    text=factor,
                    )

        fig.update_layout(
            xaxis=dict(
                type='category',
            ),
        )
    
    except:
        pass
    return fig


# ------------------------------------- 7. Asset Quality ------------------------------------- #

@app.callback(Output(component_id='total_assets_graph_annual', component_property='figure'),
              [Input(component_id='intermediate-value-ticker-balance_sheet', component_property='data')])
def update_total_assets_graph_annual(ticker_balance_sheet_json):
    """
    Company's Annual Total Assets Analysis (using balance_sheet)

    Input: ticker's balance_sheet
    """
    # if not ticker_balance_sheet_json:
    #     raise PreventUpdate

    ticker_balance_sheet = pd.read_json(StringIO(ticker_balance_sheet_json))
    
    try: 
        factor = 'Total Assets'  
        df = ticker_balance_sheet[ticker_balance_sheet.index == factor]
        df = df.T.reset_index()
        df.columns = ['Date',factor]
        df.dropna(inplace=True)
        df['Date'] = pd.to_datetime(df['Date']).dt.date

        fig = px.bar(df, 
                    x='Date',
                    y=factor,
                    title=factor ,
                    color=factor,
                    text=factor,
        )

        fig.update_layout(
            xaxis=dict(
                type='category',
            ),
        )
    except:
        pass

    return fig


@app.callback(Output(component_id='current_assets_graph_annual', component_property='figure'),
              [Input(component_id='intermediate-value-ticker-balance_sheet', component_property='data')])
def update_current_assets_graph_annual(ticker_balance_sheet_json):
    """
    Company's Annual Current Assets Analysis (using balance_sheet)

    Input: ticker's balance_sheet
    """
    # if not ticker_balance_sheet_json:
    #     raise PreventUpdate

    ticker_balance_sheet = pd.read_json(StringIO(ticker_balance_sheet_json))
    
    factor = 'Current Assets'  
    df = ticker_balance_sheet[ticker_balance_sheet.index == factor]
    df = df.T.reset_index()
    df.columns = ['Date',factor]
    df.dropna(inplace=True)
    df['Date'] = pd.to_datetime(df['Date']).dt.date
    df

    fig = px.bar(df, 
                 x='Date',  # "Date"
                 y=factor,  # factor
                 title=factor ,
                 color=factor,
                 text=factor,
    )

    fig.update_layout(
        xaxis=dict(
            type='category',
        ),
    )
    
    return fig


@app.callback(Output(component_id='investment_in_financial_assets_graph_annual', component_property='figure'),
              [Input(component_id='intermediate-value-ticker-balance_sheet', component_property='data')])
def update_inv_in_fin_assets_graph_annual(ticker_balance_sheet_json):
    """
    Company's Annual Investment in Financial Assets Analysis (using balance_sheet)
    Input: ticker's balance_sheet
    """
    # if not ticker_balance_sheet_json:
    #     raise PreventUpdate

    ticker_balance_sheet = pd.read_json(StringIO(ticker_balance_sheet_json))
    



    factor = 'Investmentin Financial Assets'  
    df = ticker_balance_sheet[ticker_balance_sheet.index == factor]
    # check if there is data available
    if len(df) == 0:
        return {
            'data': [],
            'layout': {
                'annotations': [
                    {
                        'text': 'No Investment in Financial Assets Data',
                        'x': 1,
                        'y': 0.5,
                        'showarrow': False,
                        'font': {'size': 24}
                    }
                ]
            }
        }

    try:
        df = df.T.reset_index()
        df.columns = ['Date','Investment in Financial Assets']
        df.dropna(inplace=True)
        df['Date'] = pd.to_datetime(df['Date']).dt.date



        fig = px.bar(df, 
                    x='Date',  
                    y=df.columns[1], 
                    title=df.columns[1] ,
                    color=df.columns[1],
                    text=df.columns[1],
        )

        fig.update_layout(
            xaxis=dict(
                type='category',
            ),
        )
    
    except:
        pass

    return fig
                    
                    

if __name__ == '__main__':
    app.run_server(debug=True, port=8051)
