import ee
import os
import pandas as pd

ee.Initialize()


def get_tropical_countries(country_list):
    """
    Get a list of tropical countries using Earth Engine's country vector layer. 
    Filter our non-tropical EMS activations. 
    Args:
        country_list (List): List of countries with EMS flood and storm activations. 
    """

    tropics = ee.Geometry.Polygon(
        [[-179.99, -23.5], [179.99, -23.5], [179.99, 23.5], [-179.99, 23.5], [-179.99, -23.5]], None, False)

    tropics_countries = ee.FeatureCollection('FAO/GAUL/2015/level0') \
        .filterBounds(tropics)

    tropics_countries_list = list(
        tropics_countries.aggregate_array('ADM0_NAME').getInfo())

    tropics_countries_set = set(tropics_countries_list)

    country_list_set = set(country_list)

    in_tropics = country_list_set.intersection(tropics_countries_set)

    return (list(in_tropics))


def get_static_images(year, bounds):
    """
    Get Google Earth Engine Image assets for water and land cover intersecting EMS flood extent.
    """

    # permananet water files are only available pre-2021
    if year >= 2020:
        year = 2020

    # cast to float to match terrain bands
    water = ee.Image(f"JRC/GSW1_3/YearlyHistory/{year}").clip(bounds).int32()
    land_cover = ee.ImageCollection(
        "ESA/WorldCover/v100").first().clip(bounds).int32()
        
    output = water.addBands(land_cover).rename(['water', 'land_cover'])

    return output
