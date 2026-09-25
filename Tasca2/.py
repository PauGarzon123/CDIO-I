from pystac_client import Client
import geopandas as gpd
import json
from tqdm import tqdm
import pprint


pp = pprint.PrettyPrinter(indent=4)



def search_catalog(catalog):
    if catalog == "element84":
            catalog_url = "https://earth-search.aws.element84.com/v1"
    elif catalog == "copernicus":
        catalog_url = "https://stac.dataspace.copernicus.eu/v1"
    else:
        raise ValueError("Invalid catalog name. Choose 'copernicus' or 'element84'.")

    #breakpoint()
    gdf = gpd.read_file("polygon.geojson")
    aoi = gdf.geometry[0].__geo_interface__
    config = json.load(open("config.json"))

    catalog = Client.open(catalog_url)
    search = catalog.search(
        collections=["sentinel-2-l2a"],
        intersects=aoi,
        datetime=f"{config['START_DATE']}/{config['END_DATE']}",
    )
    items = list(search.items())
    pp.pprint(items[0].to_dict()['assets'].keys())


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="STAC Catalog Demo")
    parser.add_argument("--catalog", type=str, default="element84", choices=["copernicus", "element84"], help="STAC catalog to use")
    args = parser.parse_args()
    search_catalog(args.catalog)