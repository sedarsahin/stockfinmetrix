"""
Stock Financial Metrics Explorer
"""
import logging
from dash import Dash
import dash_bootstrap_components as dbc
from modules.layout import create_layout
from modules.callbacks import register_callbacks

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Initialize the Dash app
app = Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
app.title = 'StockFinMetrix'
server = app.server # Expose server for WSGI if needed

def main():
    logger.info("Starting StockFinMetrix Application...")
    
    # Set layout
    logger.info("Initializing layout...")
    app.layout = create_layout()

    # Register callbacks
    logger.info("Registering callbacks...")
    register_callbacks(app)

    # Run server
    logger.info("Running server...")
    app.run(debug=True, port=8051)

if __name__ == '__main__':
    main()
