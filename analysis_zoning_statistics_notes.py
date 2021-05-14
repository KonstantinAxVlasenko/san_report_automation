"""Module to add notes to zoning statistics DataFrame"""


import numpy as np
import pandas as pd



def note_zonemember_statistics(zonemember_zonelevel_stat_df):
    """
    Function to verify zone content from target_initiator number (no targets, no initiators, 
    neither target nor initiator (empty zone), zone contains more than one initiator) and
    target models, class (libraries and storages or different storage models in one zone)
    point of view.
    """

    zonemember_stat_notes_df =  zonemember_zonelevel_stat_df.copy()
    # add device classes to the statistics DataFrame if some of them are missing
    # and fill columns with zeroes
    columns_lst = zonemember_stat_notes_df.columns.to_list()
    target_initiators_lst = ['SRV', 'STORAGE', 'LIB']
    add_columns = [column for column in target_initiators_lst if column not in columns_lst]
    if add_columns:
        zonemember_stat_notes_df = zonemember_stat_notes_df.reindex(columns=[*columns_lst, *add_columns])
        zonemember_stat_notes_df[add_columns] = zonemember_stat_notes_df[add_columns].fillna(0)
    # create target number summary column with quantity for each zone
    zonemember_stat_notes_df['STORAGE_LIB'] = zonemember_stat_notes_df['STORAGE'] + zonemember_stat_notes_df['LIB']
    # target_initiator zone check
    zonemember_stat_notes_df['Target_Initiator_note'] =\
        zonemember_stat_notes_df.apply(lambda series: target_initiator_note(series), axis=1)
    zonemember_stat_notes_df.drop(columns=['STORAGE_LIB'], inplace=True)

    # find storage models columns if they exist (should be at least one storage in fabric)
    storage_model_columns = [column for column in columns_lst if 'storage' in column.lower()]
    if len(storage_model_columns) > 1:
        storage_model_columns.remove('STORAGE')

    """
    Explicitly exclude replication zones (considered to be correct and presence of different storage models
    is permitted by zone purpose) and zones without initiator (condsidered to be incorrect).
    No target and empty zones are excluded by defenition (target ports) and considered to be incorrect.
    All incorrect zones are out of scope of verification if different storage models or 
    library and storage presence in a single zone
    """
    mask_exclude_zone = ~zonemember_stat_notes_df['Target_Initiator_note'].isin(['replication_zone', 'no_initiator'])
    # check if zone contains storages of different models
    if len(storage_model_columns) > 1:
        # zonemember_stat_notes_df['Storage_model_note'] = np.nan
        mask_different_storages = (zonemember_stat_notes_df[storage_model_columns] != 0).all(axis=1)
        zonemember_stat_notes_df['Storage_model_note'] = np.where(mask_exclude_zone & mask_different_storages, 'different_storages', pd.NA)
    else:
        zonemember_stat_notes_df['Storage_model_note'] = np.nan


    # check if zone contains storage and library in a single zone
    mask_storage_lib = (zonemember_stat_notes_df[['STORAGE', 'LIB']] != 0).all(axis=1)
    zonemember_stat_notes_df['Storage_library_note'] = np.where(mask_storage_lib, 'storage_library', pd.NA)
    # join both columns in a single column
    zonemember_stat_notes_df['Target_model_note'] = \
        zonemember_stat_notes_df[['Storage_model_note', 'Storage_library_note']].apply(lambda x: x.str.cat(sep=', ') \
            if x.notna().any() else np.nan, axis=1)
    zonemember_stat_notes_df.drop(columns=['Storage_model_note', 'Storage_library_note'], inplace=True)
    # drop columns if all values are NA
    zonemember_stat_notes_df.dropna(how='all', axis='columns', inplace=True)
    # check if there are SRV, STORAGE and LIB devices classes in zones
    # if none of the zones contain any of device class then drop this class from statistcics DataFrame
    for column in target_initiators_lst:
        if (zonemember_stat_notes_df[column] == 0).all():
            zonemember_stat_notes_df.drop(columns=column, inplace=True)

    if not 'Target_Initiator_note' in zonemember_stat_notes_df.columns:
        zonemember_stat_notes_df['Target_Initiator_note'] = np.nan

    # add pair_zone_note
    mask_device_connection = zonemember_stat_notes_df['All_devices_multiple_fabric_label_connection'] == 'Yes'
    mask_no_pair_zone = zonemember_stat_notes_df['zone_paired'].isna()
    # valid zones
    invalid_zone_tags = ['no_target', 'no_initiator', 'no_target, no_initiator', 'no_target, several_initiators']
    mask_valid_zone = ~zonemember_stat_notes_df['Target_Initiator_note'].isin(invalid_zone_tags)
    zonemember_stat_notes_df.loc[mask_valid_zone & mask_device_connection & mask_no_pair_zone, 'Pair_zone_note'] = 'pair_zone_not_found'
    
    return zonemember_stat_notes_df


def target_initiator_note(series):
    """
    Auxiliary function for 'note_zonemember_statistic' function 
    to verify zone content from target_initiator number point of view.
    """

    # if there are no local or imported zonemembers in fabric of zoning config switch
    # current zone is empty (neither actual initiators nor targets are present)
    if series['Total_zonemembers_active'] == 0:
        return 'no_target, no_initiator'
    # if all zonememebrs are storages with local or imported device status 
    # and no absent devices then zone considered to be replication zone 
    if series['STORAGE'] == series['Total_zonemembers'] and series['STORAGE']>1:
        return 'replication_zone'
    """
    If there are no actual server in the zone and number of defined zonemembers exceeds
    local or imported zonemebers (some devices are absent or not in the fabric of
    zoning configuration switch) then it's not a replication zone and considered to be
    initiator's less zone
    """
    if series['SRV'] == 0 and series['Total_zonemembers'] > series['Total_zonemembers_active']:
        if series['STORAGE_LIB'] > 0:
            return 'no_initiator'
    # if zone contains initiator(s) but not targets then zone considered to be target's less zone
    if series['SRV'] == 1 and series['STORAGE_LIB'] == 0:
            return 'no_target'
    # if zone contains more then one initiator and no targets
    # and it's not a peerzone  then 'no_target, several_initiators' tag
    # if it's a peer zone then 'no_target' tag
    if series['SRV'] > 1 and series['STORAGE_LIB'] == 0:
        if 'peer' in series.index and 'property' in series.index:
            if series['peer'] == 0 and series['property'] == 0:
                return 'no_target, several_initiators'
            elif series['peer'] != 0 or series['property'] != 0:
                return 'no_target' 
        else:
            return 'no_target, several_initiators'
    # if zone contains more then one initiator and it's not a peerzone 
    # then initiator number exceeds threshold
    if series['SRV'] > 1:
        if 'peer' in series.index and 'property' in series.index:
            if series['peer'] == 0 and series['peer'] == 0:
                return 'several_initiators'
        else:
            return 'several_initiators'
    
    return np.nan