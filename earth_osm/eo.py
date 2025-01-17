__author__ = "PyPSA meets Earth"
__copyright__ = "Copyright 2022, The PyPSA meets Earth Initiative"
__license__ = "MIT"

"""
This is the principal module of the earth_osm project.
"""

import logging
import os

import pandas as pd

# from earth_osm.config import primary_feature_element, feature_columns
from earth_osm.filter import get_filtered_data
from earth_osm.gfk_data import get_region_tuple, view_regions
from earth_osm.utils import columns_melt,convert_ways_lines, convert_ways_points, lonlat_lookup, output_creation, tags_melt, way_or_area

logger = logging.getLogger("osm_data_extractor")
logger.setLevel(logging.INFO)

def process_region(region, primary_name, feature_name, mp, update, data_dir):
    """
    Process Country

    Args:
        region: Region object
        primary_name: Primary Feature Name
        feature_name: Feature Name
        mp: Multiprocessing object
        update: Update flag

    Returns:
        None
    """
    primary_dict, feature_dict = get_filtered_data(region, primary_name, feature_name, mp, update, data_dir)

    primary_data = primary_dict['Data']
    feature_data = feature_dict['Data']

    df_node = pd.json_normalize(feature_data["Node"].values())
    df_way = pd.json_normalize(feature_data["Way"].values())

    if df_way.empty:
        logger.debug(f"df_way is empty for {region.short}, {primary_name}, {feature_name}")
        # for df_way, check if way or area
    else:
        type_col = way_or_area(df_way)
        df_way.insert(1, "Type", type_col)
        logger.debug(df_way['Type'].value_counts(dropna=False))

        # Drop rows with None in Type
        logger.debug(f"Dropping {df_way['Type'].isna().sum()} rows with None in Type")
        df_way.dropna(subset=["Type"], inplace=True)

        # convert refs to lonlat
        lonlat_column = lonlat_lookup(df_way, primary_data)
        df_way.insert(1, "lonlat", lonlat_column)

    # check if df_node is empty
    if df_node.empty:
        logger.debug(f"df_node is empty for {region.short}, {primary_name}, {feature_name}")
    else:
        # df node has lonlat as [lon, lat] it should be [(lon, lat)]
        df_node["lonlat"] = df_node["lonlat"].apply(lambda x: [tuple(x)])
        
        # set type to node
        df_node["Type"] = "node"
    
    # concat ways and nodes
    df_feature = pd.concat([df_way, df_node], ignore_index=True)

    if df_feature.empty:
        logger.debug(f"df_feature is empty for {region.short}, {primary_name}, {feature_name}")
    else:
        # melt 85% nan tags
        df_feature = tags_melt(df_feature, 0.95)

        # move refs column to other_tags
        df_feature = columns_melt(df_feature,   ['refs'])

        df_feature.insert(3, 'Region', region.short)
        
    return df_feature


def get_osm_data(
    region_list=['germany'],
    primary_name='power',
    feature_list=['tower'],
    update=False,
    mp=True,
    data_dir=os.path.join(os.getcwd(), 'earth_data'),
    out_format="csv",
    out_aggregate=False,
):
    """
    Get OSM Data for a list of regions and features
    args:
        region_list: list of regions to get data for
        primary_name: primary feature to get data for
        feature_list: list of features to get data for
        update: update data
        mp: use multiprocessing
    returns:
        dict of dataframes
    """
    region_tuple_list = [get_region_tuple(r) for r in region_list]

    for region in region_tuple_list:
        for feature_name in feature_list:
            df_feature = process_region(region, primary_name, feature_name, mp, update, data_dir)

            output_creation(df_feature, primary_name, feature_name, [region], data_dir, out_format)
            # TODO: add out_aggregate


    # combinations = ((region, feature_name) for region in region_tuple_list for feature_name in feature_list)

    # processed_data = map(lambda combo: process_region(combo[0], primary_name, combo[1], mp, update, data_dir), combinations)

    # for i, combo in enumerate(combinations):
    #     output_creation(processed_data[i], primary_name, combo[1], [combo[0]], data_dir, out_format, out_aggregate)

