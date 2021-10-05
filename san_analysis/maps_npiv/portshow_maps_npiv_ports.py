"""
Module to create NPIV and MAPS ports DataFrames.
Verify if all switches and vc-fc of the same blade systems bay parity group are in the same fabric_label
"""

import numpy as np
import pandas as pd

from .portshow_maps_ports import maps_db_ports
from .portshow_npiv import npiv_link_aggregated, npiv_statistics
from common_operations_dataframe_presentation import (drop_all_identical,
                                                      drop_equal_columns,
                                                      generate_report_dataframe,
                                                      translate_values, drop_zero, drop_column_if_all_na)
from common_operations_dataframe import dataframe_fillna
from common_operations_filesystem import load_data, save_data
from common_operations_miscellaneous import (status_info,
                                             verify_data, verify_force_run)
from common_operations_servicefile import data_extract_objects
                                           
from common_operations_switch import statistics_report
from common_operations_table_report import dataframe_to_report

from .switch_connection_statistics import switch_connection_statistics_aggregated
from common_operations_database import read_db, write_db


def maps_npiv_ports_analysis(portshow_sfp_aggregated_df, switch_params_aggregated_df, 
                            isl_statistics_df, blade_module_loc_df, report_creation_info_lst):
    """Main function to add porterr, transceiver and portcfg information to portshow DataFrame"""
    
    # report_steps_dct contains current step desciption and force and export tags
    # report_headers_df contains column titles, 
    # report_columns_usage_dct show if fabric_name, chassis_name and group_name of device ports should be used
    report_constant_lst, report_steps_dct, report_headers_df, report_columns_usage_dct = report_creation_info_lst
    # report_constant_lst contains information: customer_name, project directory, database directory, max_title
    *_, max_title = report_constant_lst
    

    # names to save data obtained after current module execution
    data_names = ['MAPS_ports', 'NPIV', 'NPIV_statistics', 'Connection_statistics', 'blade_module_loc',
                    'MAPS_порты', 'NPIV_порты', 'Статистика_NPIV', 'Статистика_соединений', 'Blade_шасси']
    # service step information
    print(f'\n\n{report_steps_dct[data_names[0]][3]}\n')
    
    # load data if they were saved on previos program execution iteration
    # data_lst = load_data(report_constant_lst, *data_names)
    # reade data from database if they were saved on previos program execution iteration
    data_lst = read_db(report_constant_lst, report_steps_dct, *data_names)


    # # unpacking DataFrames from the loaded list with data
    # # pylint: disable=unbalanced-tuple-unpacking
    # maps_ports_df, portshow_npiv_df, npiv_statistics_df, sw_connection_statistics_df, \
    #     maps_ports_report_df, npiv_report_df, npiv_statistics_report_df, sw_connection_statistics_report_df = data_lst

    # list of data to analyze from report_info table
    analyzed_data_names = ['portshow_aggregated', 'portshow_sfp_aggregated', 'sfpshow', 'portcfgshow', 'portcmd', 
                            'switchshow_ports', 'switch_params_aggregated', 'maps_parameters', 'fdmi', 
                            'device_rename', 'report_columns_usage_upd', 'nscamshow', 
                            'nsshow', 'alias', 'blade_servers', 'fabric_labels', 'isl', 'isl_statistics',
                            'blade_interconnect', 'synergy_interconnect']

    # force run when any data from data_lst was not saved (file not found) or 
    # procedure execution explicitly requested for output data or data used during fn execution  
    force_run = verify_force_run(data_names, data_lst, report_steps_dct, max_title, analyzed_data_names)

    if force_run:

        # data imported from init file (regular expression patterns) to extract values from data columns
        # re_pattern list contains comp_keys, match_keys, comp_dct    
        # _, _, *re_pattern_lst = data_extract_objects('common_regex', max_title)
        # *_, comp_dct = re_pattern_lst

        # _, _, *re_pattern_lst = data_extract_objects('common_regex', max_title)
        *_, comp_dct = data_extract_objects('common_regex', max_title)
    
        # current operation information string
        info = f'MAPS and NPIV ports verification'
        print(info, end =" ") 

        portshow_npiv_df = npiv_link_aggregated(portshow_sfp_aggregated_df, switch_params_aggregated_df)
        maps_ports_df = maps_db_ports(portshow_sfp_aggregated_df, switch_params_aggregated_df, comp_dct)
        # verify if all switches and vc-fc of the same bay parity group are in the same fabric_label
        blade_module_loc_df = verify_interconnect_slot_fabric(blade_module_loc_df, switch_params_aggregated_df, portshow_npiv_df)
        # after finish display status
        status_info('ok', max_title, len(info))

        info = f'Counting NPIV link and Native switch connection statistics'
        print(info, end =" ") 

        npiv_statistics_df = npiv_statistics(portshow_npiv_df, comp_dct)
        sw_connection_statistics_df = \
            switch_connection_statistics_aggregated(switch_params_aggregated_df, isl_statistics_df, npiv_statistics_df, comp_dct)
        # after finish display status
        status_info('ok', max_title, len(info))

        # create report tables from port_complete_df DataFrtame
        maps_ports_report_df, npiv_report_df, npiv_statistics_report_df, sw_connection_statistics_report_df = \
            maps_npiv_report(maps_ports_df, portshow_npiv_df, npiv_statistics_df, sw_connection_statistics_df,
                                    data_names, report_headers_df, report_columns_usage_dct)

        # create Blade chassis report table
        blade_module_report_df = blademodule_report(blade_module_loc_df, data_names, report_headers_df, report_columns_usage_dct)

        # saving data to json or csv file
        data_lst = [maps_ports_df, portshow_npiv_df, npiv_statistics_df, sw_connection_statistics_df, blade_module_loc_df,
                    maps_ports_report_df, npiv_report_df, npiv_statistics_report_df, sw_connection_statistics_report_df, blade_module_report_df]
        # saving data to json or csv file
        # save_data(report_constant_lst, data_names, *data_lst)
        # writing data to sql
        write_db(report_constant_lst, report_steps_dct, data_names, *data_lst)  
    # verify if loaded data is empty and reset DataFrame if yes
    else:
        maps_ports_df, portshow_npiv_df, npiv_statistics_df, sw_connection_statistics_df, blade_module_loc_df, \
            maps_ports_report_df, npiv_report_df, npiv_statistics_report_df, sw_connection_statistics_report_df, blade_module_report_df \
            = verify_data(report_constant_lst, data_names, *data_lst)
        data_lst = [maps_ports_df, portshow_npiv_df, npiv_statistics_df, sw_connection_statistics_df, blade_module_loc_df,
                    maps_ports_report_df, npiv_report_df, npiv_statistics_report_df, sw_connection_statistics_report_df, blade_module_report_df]
    # save data to excel file if it's required
    for data_name, data_frame in zip(data_names, data_lst):
        dataframe_to_report(data_frame, data_name, report_creation_info_lst)

    return portshow_npiv_df



def verify_interconnect_slot_fabric(blade_module_loc_df, switch_params_aggregated_df, portshow_npiv_df):
    """Function to verify if all switches and vc-fc of the same blade systems bay parity group
    are in the same fabric_label"""

    if blade_module_loc_df.empty:
        return blade_module_loc_df

    # add switch fabric_name and fabric_label
    switch_params_cp_df = switch_params_aggregated_df.copy()
    switch_params_cp_df['Interconnect_SN'] = switch_params_cp_df['ssn']
    blade_module_loc_df = dataframe_fillna(blade_module_loc_df, switch_params_cp_df, join_lst=['Interconnect_SN'],
                                            filled_lst=['Fabric_name', 'Fabric_label'])
    # add vc-fc fabric_name and fabric_label
    if not portshow_npiv_df.empty:
        portshow_npiv_cp_df = portshow_npiv_df.copy()
        portshow_npiv_cp_df['Interconnect_Name'] = portshow_npiv_cp_df['Device_Host_Name']
        blade_module_loc_df = dataframe_fillna(blade_module_loc_df, portshow_npiv_cp_df, join_lst=['Interconnect_Name'],
                                            filled_lst=['Fabric_name', 'Fabric_label'])

    # add Bay_parity column
    blade_module_loc_df['Bay_parity'] = pd.to_numeric(blade_module_loc_df['Interconnect_Bay'])
    mask_even = blade_module_loc_df['Bay_parity'] % 2 == 0
    mask_notna = blade_module_loc_df['Bay_parity'].notna()
    blade_module_loc_df['Bay_parity'] = np.select([mask_notna & mask_even, mask_notna & ~mask_even], ['even', 'odd'], default=np.nan)
    # verify if all switches and vc-fc of the same bay parity group are in the same fabric_label
    mask_mixed_bays_in_fabric = blade_module_loc_df.groupby(by=['Fabric_name', 'Bay_parity'])['Fabric_label'].transform('nunique') > 1
    blade_module_loc_df.loc[mask_mixed_bays_in_fabric, 'Mixed_bay_parity_note'] = 'mixed_bay_parity_in_fabric_label'
    return blade_module_loc_df


def maps_npiv_report(maps_ports_df, portshow_npiv_df, npiv_statistics_df, sw_connection_statistics_df,
                            data_names, report_headers_df, report_columns_usage_dct):
    """Function to create required report DataFrames out of aggregated DataFrame"""


    data_names = ['MAPS_ports', 'NPIV', 'NPIV_statistics', 'Connection_statistics', 'blade_module_loc',
                    'MAPS_порты', 'NPIV_порты', 'Статистика_NPIV', 'Статистика_соединений', 'Blade_шасси']

    # maps ports report
    maps_ports_report_df = drop_all_identical(maps_ports_df, 
                                                {'portState': 'Online', 'Connected_through_AG': 'No'},
                                                dropna=True)                   
    maps_ports_report_df = generate_report_dataframe(maps_ports_report_df, report_headers_df, report_columns_usage_dct, data_names[5])    
    maps_ports_report_df.dropna(axis=1, how = 'all', inplace=True)
    maps_ports_report_df = translate_values(maps_ports_report_df)

    

    # npiv ports report
    npiv_report_df = portshow_npiv_df.copy()
    # drop allna columns
    npiv_report_df.dropna(axis=1, how='all', inplace=True)
    # drop columns where all values after dropping NA are equal to certian value
    possible_identical_values = {'Slow_Drain_Device': 'No'}
    
    
    
    npiv_report_df = drop_all_identical(npiv_report_df, possible_identical_values, dropna=True)
    # if all devices connected to one fabric_label only
    npiv_report_df = drop_equal_columns(npiv_report_df, columns_pairs=[
                                                                ('Device_Host_Name_per_fabric_name_and_label', 'Device_Host_Name_per_fabric_label'),
                                                                ('Device_Host_Name_total_fabrics', 'Device_Host_Name_per_fabric_name')])
    

    
    npiv_report_df = translate_values(npiv_report_df)
    npiv_report_df = generate_report_dataframe(npiv_report_df, report_headers_df, report_columns_usage_dct, data_names[6])
    # npiv statistics report
    npiv_statistics_report_df = statistics_report(npiv_statistics_df, report_headers_df, 'Статистика_ISL_перевод', 
                                                    report_columns_usage_dct, drop_columns=['switchWwn', 'NodeName'])
    # remove zeroes to clean view
    drop_zero(npiv_statistics_report_df)
    
    # switch connection statistics
    report_columns_usage_cp_dct = report_columns_usage_dct.copy()
    report_columns_usage_cp_dct['fabric_name_usage'] = True
    sw_connection_statistics_report_df = generate_report_dataframe(sw_connection_statistics_df, report_headers_df, 
                                                                    report_columns_usage_cp_dct, data_names[8])
    sw_connection_statistics_report_df = translate_values(sw_connection_statistics_report_df, report_headers_df, data_names[8])   
    # drop allna columns
    sw_connection_statistics_report_df.dropna(axis=1, how='all', inplace=True)

    return maps_ports_report_df, npiv_report_df, npiv_statistics_report_df, sw_connection_statistics_report_df


def blademodule_report(blade_module_loc_df, data_names, report_headers_df, report_columns_usage_dct):
    """Function to create Blade IO modules report table"""

    # report_columns_usage_dct = {'fabric_name_usage': False, 'chassis_info_usage': False}

    blade_module_report_df = drop_column_if_all_na(blade_module_loc_df, columns='Mixed_bay_parity_note')
    blade_module_report_df = generate_report_dataframe(blade_module_loc_df, report_headers_df, report_columns_usage_dct, data_names[9])
    blade_module_report_df = translate_values(blade_module_report_df, report_headers_df, data_names[9])
    

    return blade_module_report_df