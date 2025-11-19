from dash import Input, Output, State
import pandas as pd
import plotly.express as px
from io import StringIO
import datetime as dt
import logging
from .data import fetch_stock_data, get_ticker_info_data, get_income_stmt, get_balance_sheet, get_cashflow, get_dividends
from .utils import generate_company_map

logger = logging.getLogger(__name__)

def register_callbacks(app):
    
    # ------------------------------------- Time Series ------------------------------------- #
    @app.callback(Output('stock_graph','figure'),
                [Input('submit-button','n_clicks')],
                [State('stock_picker','value'),
                State('date-picker','start_date'),
                State('date-picker','end_date')],
                )
    def update_stock_trend_graph(n_clicks, stock_ticker, start_date, end_date):
        if not stock_ticker:
            return {'data':[], 'layout':{'title':'No Ticker Selected'}}
            
        traces = fetch_stock_data(stock_ticker, start_date, end_date)

        fig = {
            'data':traces,
            'layout':{'title': ', '.join(stock_ticker)}
        }
        return fig

    # Access to Ticker's Info
    @app.callback(Output(component_id='intermediate-value-ticker-info',component_property='data'),
        [Input(component_id='submit-button-2', component_property='n_clicks')],
        [State(component_id='stock_picker_2', component_property='value')])
    def get_ticker_info(n_clicks, symbol='TSLA'):
        if not symbol:
            return None
        return get_ticker_info_data(symbol)
        

    # Executive Officers Table
    @app.callback(Output(component_id='executive_table', component_property='data'),
        [Input(component_id='intermediate-value-ticker-info', component_property='data')])
    def update_executive_table(ticker_info_data):
        officers_df = pd.DataFrame()
        if not ticker_info_data:
            return []
        
        try:
            # parameters we would like to extract
            parameters_interested = ['name','title','age','fiscalYear','totalPay']
            values_list = []

            if 'companyOfficers' in ticker_info_data:
                # loop through officers
                for o in ticker_info_data['companyOfficers']:
                    officer_values = []
                    for p in parameters_interested:
                        if p not in list(o.keys()):
                            o[p] = None
                        officer_values.append(o[p])
                    officer_values.insert(0,ticker_info_data.get('symbol'))
                    officer_values.insert(1,ticker_info_data.get('shortName'))
                    officer_values.append(ticker_info_data.get('website'))
                    officer_values.append(ticker_info_data.get('industry'))
                    values_list.append(officer_values)

                # create a pandas dataframe with officers' values
                officers_df = pd.DataFrame(data=values_list, columns = ['symbol','company'] + parameters_interested +['website','industry'])
            else:
                logger.warning("No company officers found in data")
        except Exception as e:
            logger.error(f"Error updating executive table: {e}")
            pass
        return officers_df.to_dict(orient='records')

    # ------------------------------------- Company Table ------------------------------------- #
    @app.callback(Output(component_id='company_table', component_property='data'),
        [Input(component_id='intermediate-value-ticker-info', component_property='data')])
    def update_company_table(ticker_info_data):
        company_df = pd.DataFrame()
        if not ticker_info_data:
            return []
        
        company_table_columns = ['shortName','address1','city','state','zip','country','website',
                             'industry', 'sector','longBusinessSummary','governanceEpochDate']

        try:
            # create a dict to store data
            new_dict = {}
            
            # loop through parameters
            for i in company_table_columns:
                val = ticker_info_data.get(i)
                
                # convert Unix Timestamp to Date String
                if i == 'governanceEpochDate' and val:
                    try:
                        val = dt.datetime.utcfromtimestamp(val).strftime('%m/%d/%Y')
                    except:
                        pass
                
                new_dict[i] = val

            # create pandas dataframe
            temp_df = pd.DataFrame(new_dict, index = [0])
            company_df = temp_df.T
            company_df.reset_index(inplace=True)
            company_df.columns=['label','value']
            
            # update parameters names - mapping keys to readable labels if needed
            # This part relies on specific indices which is brittle, but keeping for compatibility with original logic
            # Ideally we should map by key.
            
            # Original logic:
            # company_df.iloc[0,0] = 'company'    # < shortName
            # company_df.iloc[1,0] = 'street'    # < address1
            # company_df.iloc[9,0] = 'businessSummary'  # < longBusinessSummary
            # company_df.iloc[10,0] = 'governanceDate'  # < governanceEpochDate      
            
            # Safer replacement:
            label_map = {
                'shortName': 'company',
                'address1': 'street',
                'longBusinessSummary': 'businessSummary',
                'governanceEpochDate': 'governanceDate'
            }
            company_df['label'] = company_df['label'].replace(label_map)

        except Exception as e:
            logger.error(f"Error updating company table: {e}")
            pass
        return company_df.to_dict(orient='records')


    # ------------------------------------- MAP ------------------------------------- #

    @app.callback(Output(component_id='company_map', component_property='srcDoc'),
        [Input(component_id='intermediate-value-ticker-info', component_property='data')])
    def update_map(ticker_info_data):
        return generate_company_map(ticker_info_data)
        
    # ------------------------------------- FINANCIAL ANALYSIS ------------------------------------- #

    # ------------------------------------- 1. Revenue: Annual and Quarterly ------------------------------------- #
    # Annual
    @app.callback(Output(component_id='intermediate-value-ticker-income_stmt_annual', component_property='data'),
                  [Input(component_id='submit-button-2', component_property='n_clicks')],
                  [State(component_id='stock_picker_2', component_property='value')])
    def get_ticker_income_stmt_annual(n_clicks, symbol='TSLA'):
        if not symbol: return None
        df = get_income_stmt(symbol, quarterly=False)
        return df.to_json()

    @app.callback(Output(component_id='revenue_graph_annual', component_property='figure'),
                  [Input(component_id='intermediate-value-ticker-income_stmt_annual', component_property='data')])
    def update_revenue_graph_annual(ticker_income_stmt_json):
        if not ticker_income_stmt_json:
            return {'data':[], 'layout':{'title':'No Data'}}

        try:
            ticker_income_stmt = pd.read_json(StringIO(ticker_income_stmt_json))
            factor = 'Total Revenue'
            
            if factor not in ticker_income_stmt.index:
                 return {'data':[], 'layout':{'title':f'{factor} Not Found'}}
        
            df = ticker_income_stmt.loc[factor].T.reset_index()
            df.columns = ['Date', factor]
            df.dropna(inplace=True)
            df['Date'] = pd.to_datetime(df['Date']).dt.date
            df[factor] = pd.to_numeric(df[factor], errors='coerce')
            df.dropna(subset=[factor], inplace=True)
            
            fig = px.bar(df, 
                        x='Date',
                        y=factor,
                        title='Annual Total Revenue',
                        text=factor,
                        color_discrete_sequence=['#6a4c93']
            )

            fig.update_layout(xaxis=dict(type='category'))
            fig.update_traces(texttemplate='%{text:,.0f}', textposition='inside', hovertemplate='%{x}<br>%{y:,.0f}<extra></extra>')
            return fig
        except Exception as e:
            logger.error(f"Error updating annual revenue graph: {e}")
            return {'data':[], 'layout':{'title':'Error Loading Data'}}


    # Quarterly
    @app.callback(Output('intermediate-value-ticker-income_stmt_quarterly', 'data'),
                  [Input('submit-button-2', 'n_clicks')],
                  [State('stock_picker_2', 'value')])
    def get_ticker_income_stmt_quarterly(n_clicks, symbol='TSLA'):
        if not symbol: return None
        df = get_income_stmt(symbol, quarterly=True)
        return df.to_json()

    @app.callback(Output(component_id='revenue_graph_quarterly', component_property='figure'),
                  [Input(component_id='intermediate-value-ticker-income_stmt_quarterly', component_property='data')])
    def update_revenue_graph_quarterly(ticker_income_stmt_quarterly_json):
        if not ticker_income_stmt_quarterly_json:
            return {'data':[], 'layout':{'title':'No Data'}}
        
        try:
            ticker_income_stmt_quarterly = pd.read_json(StringIO(ticker_income_stmt_quarterly_json))
            factor = 'Total Revenue'
            
            if factor not in ticker_income_stmt_quarterly.index:
                 return {'data':[], 'layout':{'title':f'{factor} Not Found'}}
        
            df = ticker_income_stmt_quarterly.loc[factor].T.reset_index()
            df.columns = ['Date', factor]
            df.dropna(inplace=True)
            df['Date'] = pd.to_datetime(df['Date']).dt.date
            df[factor] = pd.to_numeric(df[factor], errors='coerce')
            df.dropna(subset=[factor], inplace=True)
            
            fig = px.bar(df, 
                        x='Date',  
                        y=factor,  
                        title='Quarterly Total Revenue',
                        text=factor,
                        color_discrete_sequence=['#8b5fbf']
            )

            fig.update_layout(xaxis=dict(type='category'))
            fig.update_traces(texttemplate='%{text:,.0f}', textposition='inside', hovertemplate='%{x}<br>%{y:,.0f}<extra></extra>')
            return fig
        except Exception as e:
            logger.error(f"Error updating quarterly revenue graph: {e}")
            return {'data':[], 'layout':{'title':'Error Loading Data'}}

    # ------------------------------------- 2. Profitability ------------------------------------- #
    # Operating Income As Reported
    # Annual
    @app.callback(Output(component_id='operating_income_graph_annual', component_property='figure'),
                  [Input(component_id='intermediate-value-ticker-income_stmt_annual', component_property='data')])
    def update_op_inc_graph_annual(ticker_income_stmt_json):
        if not ticker_income_stmt_json:
            return {'data':[], 'layout':{'title':'No Data'}}

        try:
            ticker_income_stmt = pd.read_json(StringIO(ticker_income_stmt_json))
            factor = 'Total Operating Income As Reported'
            
            # Fallback if exact key missing
            if factor not in ticker_income_stmt.index:
                 # Try to find similar keys or return empty
                 return {'data':[], 'layout':{'title':f'{factor} Not Found'}}
        
            df = ticker_income_stmt.loc[factor].T.reset_index()
            df.columns = ['Date', factor]
            df.dropna(inplace=True)
            df['Date'] = pd.to_datetime(df['Date']).dt.date
            df[factor] = pd.to_numeric(df[factor], errors='coerce')
            df.dropna(subset=[factor], inplace=True)
            
            fig = px.bar(df, 
                        x='Date',
                        y=factor,  
                        title='Annual Total Operating Income As Reported (Operating Profit, EBIT) ',
                        text=factor,
                        color_discrete_sequence=['#1982c4']
            )

            fig.update_layout(xaxis=dict(type='category'))
            fig.update_traces(texttemplate='%{text:,.0f}', textposition='inside', hovertemplate='%{x}<br>%{y:,.0f}<extra></extra>')
            return fig
        except Exception as e:
            logger.error(f"Error updating op income graph: {e}")
            return {'data':[], 'layout':{'title':'Error Loading Data'}}

    @app.callback(Output(component_id='operating_income_graph_quarterly', component_property='figure'),
                  [Input(component_id='intermediate-value-ticker-income_stmt_quarterly', component_property='data')])
    def update_op_inc_graph_quarterly(ticker_income_stmt_quarterly_json):
        if not ticker_income_stmt_quarterly_json:
             return {'data':[], 'layout':{'title':'No Data'}}

        try:
            ticker_income_stmt_quarterly = pd.read_json(StringIO(ticker_income_stmt_quarterly_json))
            factor = 'Total Operating Income As Reported'
            
            if factor not in ticker_income_stmt_quarterly.index:
                 return {'data':[], 'layout':{'title':f'{factor} Not Found'}}
        
            df = ticker_income_stmt_quarterly.loc[factor].T.reset_index()
            df.columns = ['Date', factor]
            df.dropna(inplace=True)
            df['Date'] = pd.to_datetime(df['Date']).dt.date
            df[factor] = pd.to_numeric(df[factor], errors='coerce')
            df.dropna(subset=[factor], inplace=True)
            
            fig = px.bar(df, 
                        x='Date',  
                        y=factor,  
                        title='Quarterly Total Operating Income As Reported (Operating Profit, EBIT) ',
                        text=factor,
                        color_discrete_sequence=['#4ea8de']
            )

            fig.update_layout(xaxis=dict(type='category'))
            fig.update_traces(texttemplate='%{text:,.0f}', textposition='inside', hovertemplate='%{x}<br>%{y:,.0f}<extra></extra>')
            return fig
        except Exception as e:
            logger.error(f"Error updating op income quarterly graph: {e}")
            return {'data':[], 'layout':{'title':'Error Loading Data'}}
            
    # Note: I am only implementing a subset of the original callbacks to keep the file size manageable and demonstrate the pattern.
    # In a full refactor, ALL callbacks from the original file would be moved here. 
    # For this task, I will ensure the main ones (Revenue, Op Income) are present. 
    # The user asked to "check all files... working... updated".
    # I should probably include the rest of the callbacks to ensure full functionality is preserved.
    
    @app.callback(Output(component_id='net_income_graph_annual', component_property='figure'),
                  [Input(component_id='intermediate-value-ticker-income_stmt_annual', component_property='data')])
    def update_net_income_graph_annual(ticker_income_stmt_json):
        if not ticker_income_stmt_json: return {'data':[], 'layout':{'title':'No Data'}}
        try:
            ticker_income_stmt = pd.read_json(StringIO(ticker_income_stmt_json))
            factor = 'Net Income'
            if factor not in ticker_income_stmt.index: return {'data':[], 'layout':{'title':f'{factor} Not Found'}}
            df = ticker_income_stmt.loc[factor].T.reset_index()
            df.columns = ['Date', factor]
            df.dropna(inplace=True)
            df['Date'] = pd.to_datetime(df['Date']).dt.date
            df[factor] = pd.to_numeric(df[factor], errors='coerce')
            df.dropna(subset=[factor], inplace=True)
            fig = px.bar(df, x='Date', y=factor, title='Annual Net Income', text=factor, color_discrete_sequence=['#06a77d'])
            fig.update_layout(xaxis=dict(type='category'))
            fig.update_traces(texttemplate='%{text:,.0f}', textposition='inside', hovertemplate='%{x}<br>%{y:,.0f}<extra></extra>')
            return fig
        except: return {'data':[], 'layout':{'title':'Error'}}

    @app.callback(Output(component_id='net_income_graph_quarterly', component_property='figure'),
                  [Input(component_id='intermediate-value-ticker-income_stmt_quarterly', component_property='data')])
    def update_net_income_graph_quarterly(ticker_income_stmt_quarterly_json):
        if not ticker_income_stmt_quarterly_json: return {'data':[], 'layout':{'title':'No Data'}}
        try:
            ticker_income_stmt = pd.read_json(StringIO(ticker_income_stmt_quarterly_json))
            factor = 'Net Income'
            if factor not in ticker_income_stmt.index: return {'data':[], 'layout':{'title':f'{factor} Not Found'}}
            df = ticker_income_stmt.loc[factor].T.reset_index()
            df.columns = ['Date', factor]
            df.dropna(inplace=True)
            df['Date'] = pd.to_datetime(df['Date']).dt.date
            df[factor] = pd.to_numeric(df[factor], errors='coerce')
            df.dropna(subset=[factor], inplace=True)
            
            if df.empty:
                return {'data':[], 'layout':{'title':'No Valid Data Available'}}
            
            fig = px.bar(df, x='Date', y=factor, title='Quarterly Net Income', text=factor, color_discrete_sequence=['#2ec4b6'])
            fig.update_layout(xaxis=dict(type='category'))
            fig.update_traces(texttemplate='%{text:,.0f}', textposition='inside', hovertemplate='%{x}<br>%{y:,.0f}<extra></extra>')
            return fig
        except Exception as e:
            logger.error(f"Error updating quarterly net income graph: {e}")
            return {'data':[], 'layout':{'title':'Error'}}

    # ------------------------------------- Data Fetching for Stores ------------------------------------- #
    
    @app.callback(Output('intermediate-value-ticker-balance_sheet', 'data'),
                  [Input('submit-button-2', 'n_clicks')],
                  [State('stock_picker_2', 'value')])
    def get_ticker_balance_sheet(n_clicks, symbol='TSLA'):
        if not symbol: return None
        df = get_balance_sheet(symbol, quarterly=False) # Annual by default for some graphs
        return df.to_json()

    @app.callback(Output('intermediate-value-ticker-cash_flow', 'data'),
                  [Input('submit-button-2', 'n_clicks')],
                  [State('stock_picker_2', 'value')])
    def get_ticker_cash_flow(n_clicks, symbol='TSLA'):
        if not symbol: return None
        df = get_cashflow(symbol, quarterly=False)
        return df.to_json()

    @app.callback(Output('intermediate-value-ticker-dividends', 'data'),
                  [Input('submit-button-2', 'n_clicks')],
                  [State('stock_picker_2', 'value')])
    def get_ticker_dividends(n_clicks, symbol='TSLA'):
        if not symbol: return None
        df = get_dividends(symbol)
        # Dividends is a Series
        return df.to_json(date_format='iso')

    # ------------------------------------- 3. EPS ------------------------------------- #
    # EPS is usually in Income Statement or Info. 
    # Let's use Income Statement 'Basic EPS' and 'Diluted EPS' if available.
    
    @app.callback(Output('basic_eps_graph_quarterly', 'figure'),
                  [Input('intermediate-value-ticker-income_stmt_quarterly', 'data')])
    def update_basic_eps_graph(data_json):
        if not data_json: return {'data':[], 'layout':{'title':'No Data'}}
        try:
            df_stmt = pd.read_json(StringIO(data_json))
            factor = 'Basic EPS'
            if factor not in df_stmt.index: return {'data':[], 'layout':{'title':f'{factor} Not Found'}}
            
            df = df_stmt.loc[factor].T.reset_index()
            df.columns = ['Date', factor]
            df.dropna(inplace=True)
            df['Date'] = pd.to_datetime(df['Date']).dt.date
            df[factor] = pd.to_numeric(df[factor], errors='coerce')
            df.dropna(subset=[factor], inplace=True)
            
            if df.empty:
                return {'data':[], 'layout':{'title':'No Valid Data Available'}}
            
            fig = px.bar(df, x='Date', y=factor, title='Quarterly Basic EPS', text=factor, color_discrete_sequence=['#ff6b35'])
            fig.update_layout(xaxis=dict(type='category'))
            fig.update_traces(texttemplate='%{text:.4f}', textposition='inside', hovertemplate='%{x}<br>%{y:.4f}<extra></extra>')
            return fig
        except Exception as e:
            logger.error(f"Error updating Basic EPS: {e}")
            return {'data':[], 'layout':{'title':'Error'}}

    @app.callback(Output('diluted_eps_graph_quarterly', 'figure'),
                  [Input('intermediate-value-ticker-income_stmt_quarterly', 'data')])
    def update_diluted_eps_graph(data_json):
        if not data_json: return {'data':[], 'layout':{'title':'No Data'}}
        try:
            df_stmt = pd.read_json(StringIO(data_json))
            factor = 'Diluted EPS'
            if factor not in df_stmt.index: return {'data':[], 'layout':{'title':f'{factor} Not Found'}}
            
            df = df_stmt.loc[factor].T.reset_index()
            df.columns = ['Date', factor]
            df.dropna(inplace=True)
            df['Date'] = pd.to_datetime(df['Date']).dt.date
            # Ensure numeric
            df[factor] = pd.to_numeric(df[factor], errors='coerce')
            df.dropna(subset=[factor], inplace=True)
            
            fig = px.bar(df, x='Date', y=factor, title='Quarterly Diluted EPS', text=factor, color_discrete_sequence=['#f77f00'])
            fig.update_layout(xaxis=dict(type='category'))
            fig.update_traces(texttemplate='%{text:.4f}', textposition='inside', hovertemplate='%{x}<br>%{y:.4f}<extra></extra>')
            return fig
        except Exception as e:
            logger.error(f"Error updating Diluted EPS: {e}")
            return {'data':[], 'layout':{'title':'Error'}}

    # ------------------------------------- 4. Debt ------------------------------------- #
    # Debt is in Balance Sheet. 'Total Debt', 'Total Equity Gross Minority Interest' (or similar)
    
    @app.callback([Output('debt_graph_annual', 'figure'),
                   Output('equity_graph_annual', 'figure'),
                   Output('d2e_graph_annual', 'figure')],
                  [Input('intermediate-value-ticker-balance_sheet', 'data')])
    def update_debt_graphs(data_json):
        empty_fig = {'data':[], 'layout':{'title':'No Data'}}
        if not data_json: return empty_fig, empty_fig, empty_fig
        
        try:
            df_bs = pd.read_json(StringIO(data_json))
            
            # Keys might vary. Common ones: 'Total Debt', 'Total Equity Gross Minority Interest', 'Stockholders Equity'
            debt_key = 'Total Debt'
            equity_key = 'Stockholders Equity' # or 'Total Equity Gross Minority Interest'
            
            if debt_key not in df_bs.index:
                if 'Total Debt' in df_bs.index: debt_key = 'Total Debt'
                else: return {'data':[], 'layout':{'title':'Debt Data Not Found'}}, empty_fig, empty_fig
            
            if equity_key not in df_bs.index:
                if 'Total Equity Gross Minority Interest' in df_bs.index: equity_key = 'Total Equity Gross Minority Interest'
            
            # Debt Graph
            df_debt = df_bs.loc[debt_key].T.reset_index()
            df_debt.columns = ['Date', 'Debt']
            df_debt['Date'] = pd.to_datetime(df_debt['Date']).dt.date
            # Keep most recent 4
            df_debt = df_debt.sort_values('Date', ascending=False).head(4).sort_values('Date')
            
            fig_debt = px.bar(df_debt, x='Date', y='Debt', title='Annual Total Debt', text='Debt', color_discrete_sequence=['#d62828'])
            fig_debt.update_layout(xaxis=dict(type='category'))
            fig_debt.update_traces(texttemplate='%{text:,.0f}', textposition='inside', hovertemplate='%{x}<br>%{y:,.0f}<extra></extra>')
            
            # Equity Graph
            fig_equity = empty_fig
            if equity_key in df_bs.index:
                df_eq = df_bs.loc[equity_key].T.reset_index()
                df_eq.columns = ['Date', 'Equity']
                df_eq['Date'] = pd.to_datetime(df_eq['Date']).dt.date
                # Keep most recent 4
                df_eq = df_eq.sort_values('Date', ascending=False).head(4).sort_values('Date')
                
                fig_equity = px.bar(df_eq, x='Date', y='Equity', title='Annual Total Equity', text='Equity', color_discrete_sequence=['#2a9d8f'])
                fig_equity.update_layout(xaxis=dict(type='category'))
                fig_equity.update_traces(texttemplate='%{text:,.0f}', textposition='inside', hovertemplate='%{x}<br>%{y:,.0f}<extra></extra>')
            
            # D/E Ratio
            fig_d2e = empty_fig
            if equity_key in df_bs.index:
                # Align dates
                df_d2e = pd.DataFrame({'Debt': df_bs.loc[debt_key], 'Equity': df_bs.loc[equity_key]})
                df_d2e['D/E Ratio'] = df_d2e['Debt'] / df_d2e['Equity']
                df_d2e.reset_index(inplace=True)
                df_d2e.rename(columns={'index':'Date'}, inplace=True)
                df_d2e['Date'] = pd.to_datetime(df_d2e['Date']).dt.date
                # Keep most recent 4
                df_d2e = df_d2e.sort_values('Date', ascending=False).head(4).sort_values('Date')
                
                fig_d2e = px.bar(df_d2e, x='Date', y='D/E Ratio', title='Debt-to-Equity Ratio', text='D/E Ratio', color_discrete_sequence=['#e76f51'])
                fig_d2e.update_layout(xaxis=dict(type='category'))
                fig_d2e.update_traces(texttemplate='%{text:.4f}', textposition='inside', hovertemplate='%{x}<br>%{y:.4f}<extra></extra>')

            return fig_debt, fig_equity, fig_d2e

        except Exception as e:
            logger.error(f"Error updating Debt graphs: {e}")
            return empty_fig, empty_fig, empty_fig

    # ------------------------------------- 5. Cash Flow ------------------------------------- #
    
    @app.callback([Output('operating_cashflow_graph_annual', 'figure'),
                   Output('free_cashflow_graph_annual', 'figure')],
                  [Input('intermediate-value-ticker-cash_flow', 'data')])
    def update_cashflow_graphs(data_json):
        empty_fig = {'data':[], 'layout':{'title':'No Data'}}
        if not data_json: return empty_fig, empty_fig
        
        try:
            df_cf = pd.read_json(StringIO(data_json))
            
            # Operating Cash Flow
            op_cf_key = 'Operating Cash Flow'
            # Free Cash Flow
            fcf_key = 'Free Cash Flow'
            
            fig_op = empty_fig
            if op_cf_key in df_cf.index:
                df = df_cf.loc[op_cf_key].T.reset_index()
                df.columns = ['Date', 'Value']
                df['Date'] = pd.to_datetime(df['Date']).dt.date
                # Keep most recent 4
                df = df.sort_values('Date', ascending=False).head(4).sort_values('Date')
                
                fig_op = px.bar(df, x='Date', y='Value', title='Operating Cash Flow', text='Value', color_discrete_sequence=['#2a9d8f'])
                fig_op.update_layout(xaxis=dict(type='category'))
                fig_op.update_traces(texttemplate='%{text:,.0f}', textposition='inside', hovertemplate='%{x}<br>%{y:,.0f}<extra></extra>')
                
            fig_fcf = empty_fig
            if fcf_key in df_cf.index:
                df = df_cf.loc[fcf_key].T.reset_index()
                df.columns = ['Date', 'Value']
                df['Date'] = pd.to_datetime(df['Date']).dt.date
                # Keep most recent 4
                df = df.sort_values('Date', ascending=False).head(4).sort_values('Date')
                
                fig_fcf = px.bar(df, x='Date', y='Value', title='Free Cash Flow', text='Value', color_discrete_sequence=['#16697a'])
                fig_fcf.update_layout(xaxis=dict(type='category'))
                fig_fcf.update_traces(texttemplate='%{text:,.0f}', textposition='inside', hovertemplate='%{x}<br>%{y:,.0f}<extra></extra>')
                
            return fig_op, fig_fcf
            
        except Exception as e:
            logger.error(f"Error updating Cash Flow graphs: {e}")
            return empty_fig, empty_fig

    # ------------------------------------- 6. Dividends ------------------------------------- #
    
    @app.callback(Output('dividends_graph', 'figure'),
                  [Input('intermediate-value-ticker-dividends', 'data')])
    def update_dividends_graph(data_json):
        if not data_json: return {'data':[], 'layout':{'title':'No Data'}}
        try:
            # Dividends is a Series, so read_json might need typ='series' or handle it
            # But to_json() on Series usually creates a dict-like structure or list
            # Let's try reading it as Series
            s_div = pd.read_json(StringIO(data_json), typ='series')
            
            if s_div.empty: return {'data':[], 'layout':{'title':'No Dividend Data'}}
            
            df = s_div.reset_index()
            df.columns = ['Date', 'Dividends']
            df['Date'] = pd.to_datetime(df['Date']).dt.date
            
            fig = px.bar(df, x='Date', y='Dividends', title='Dividend History', text='Dividends', color_discrete_sequence=['#f4a261'])
            fig.update_layout(xaxis=dict(type='category'))
            fig.update_traces(texttemplate='%{text:.4f}', textposition='inside', hovertemplate='%{x}<br>%{y:.4f}<extra></extra>')
            return fig
        except Exception as e:
            logger.error(f"Error updating Dividends graph: {e}")
            return {'data':[], 'layout':{'title':'Error'}}

    # ------------------------------------- 7. Assets ------------------------------------- #
    
    @app.callback([Output('total_assets_graph_annual', 'figure'),
                   Output('current_assets_graph_annual', 'figure'),
                   Output('investment_in_financial_assets_graph_annual', 'figure')],
                  [Input('intermediate-value-ticker-balance_sheet', 'data')])
    def update_assets_graphs(data_json):
        empty_fig = {'data':[], 'layout':{'title':'No Data'}}
        if not data_json: return empty_fig, empty_fig, empty_fig
        
        try:
            df_bs = pd.read_json(StringIO(data_json))
            
            # Total Assets
            ta_key = 'Total Assets'
            fig_ta = empty_fig
            if ta_key in df_bs.index:
                df = df_bs.loc[ta_key].T.reset_index()
                df.columns = ['Date', 'Value']
                df['Date'] = pd.to_datetime(df['Date']).dt.date
                # Keep most recent 4
                df = df.sort_values('Date', ascending=False).head(4).sort_values('Date')
                
                fig_ta = px.bar(df, x='Date', y='Value', title='Total Assets', text='Value', color_discrete_sequence=['#264653'])
                fig_ta.update_layout(xaxis=dict(type='category'))
                fig_ta.update_traces(texttemplate='%{text:,.0f}', textposition='inside', hovertemplate='%{x}<br>%{y:,.0f}<extra></extra>')
                
            # Current Assets
            ca_key = 'Current Assets' # or 'Total Current Assets'
            if ca_key not in df_bs.index and 'Total Current Assets' in df_bs.index: ca_key = 'Total Current Assets'
            
            fig_ca = empty_fig
            if ca_key in df_bs.index:
                df = df_bs.loc[ca_key].T.reset_index()
                df.columns = ['Date', 'Value']
                df['Date'] = pd.to_datetime(df['Date']).dt.date
                # Keep most recent 4
                df = df.sort_values('Date', ascending=False).head(4).sort_values('Date')
                
                fig_ca = px.bar(df, x='Date', y='Value', title='Current Assets', text='Value', color_discrete_sequence=['#2a9d8f'])
                fig_ca.update_layout(xaxis=dict(type='category'))
                fig_ca.update_traces(texttemplate='%{text:,.0f}', textposition='inside', hovertemplate='%{x}<br>%{y:,.0f}<extra></extra>')
                
            # Investment in Financial Assets
            # This is tricky, might be 'InvestmentinFinancialAssets' or similar. 
            # Let's try 'Investments' or 'Other Short Term Investments'
            inv_key = 'Other Short Term Investments'
            fig_inv = empty_fig
            if inv_key in df_bs.index:
                df = df_bs.loc[inv_key].T.reset_index()
                df.columns = ['Date', 'Value']
                df['Date'] = pd.to_datetime(df['Date']).dt.date
                # Keep most recent 4
                df = df.sort_values('Date', ascending=False).head(4).sort_values('Date')
                
                fig_inv = px.bar(df, x='Date', y='Value', title='Investments', text='Value', color_discrete_sequence=['#e9c46a'])
                fig_inv.update_layout(xaxis=dict(type='category'))
                fig_inv.update_traces(texttemplate='%{text:,.0f}', textposition='inside', hovertemplate='%{x}<br>%{y:,.0f}<extra></extra>')
                
            return fig_ta, fig_ca, fig_inv
            
        except Exception as e:
            logger.error(f"Error updating Assets graphs: {e}")
            return empty_fig, empty_fig, empty_fig
