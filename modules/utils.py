import folium
import uszipcode
import logging

logger = logging.getLogger(__name__)

def generate_company_map(ticker_info_data):
    """Generates a Folium map for the company location."""
    map_html = ''
    try:
        if not ticker_info_data or 'zip' not in ticker_info_data:
            return "<div>Location data not available</div>"

        ticker_zip_code = ticker_info_data['zip'][:5]
        
        # Handle non-US zip codes or failures gracefully
        search = uszipcode.SearchEngine()
        zip_details = search.by_zipcode(ticker_zip_code)
        
        if not zip_details or not zip_details.lat:
            logger.warning(f"Could not find coordinates for zip code: {ticker_zip_code}")
            return "<div>Location not found for this zip code</div>"

        lat = zip_details.lat 
        lng = zip_details.lng

        # Company details to show in the pop-up
        address_parts = [
            ticker_info_data.get('address1', ''),
            ticker_info_data.get('city', ''),
            ticker_info_data.get('state', ''),
            ticker_info_data.get('zip', '')[:5],
            ticker_info_data.get('country', '')
        ]
        address = ', '.join(filter(None, address_parts))
        
        text = f"Symbol: {ticker_info_data.get('symbol', 'N/A')} Name: {ticker_info_data.get('shortName', 'N/A')} Address: {address}"

        # Create basemap
        map_obj = folium.Map(location=[lat,lng],
                            tiles='OpenStreetMap',
                            zoom_start=5)

        # Place marker
        folium.Marker(location=[lat,lng],
                      popup = text,
                      icon = folium.Icon(color='orange', 
                                         icon='briefcase',)
                     ).add_to(map_obj)
        
        map_html = map_obj.get_root().render()
        
    except Exception as e:
        logger.error(f"Error generating map: {e}")
        map_html = f"<div>Error generating map: {e}</div>"

    return map_html
