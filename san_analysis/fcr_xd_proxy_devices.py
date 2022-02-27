"""Module to create sensor related DataFrames"""

import numpy as np
import pandas as pd
import utilities.database_operations as dbop
import utilities.dataframe_operations as dfop
import utilities.module_execution as meop


def fcr_xd_device_analysis(switch_params_aggregated_df, portshow_aggregated_df, 
                            fcrproxydev_df, fcrxlateconfig_df, report_creation_info_lst):
    """Main function to create table of devices connected to translate domains"""
        
    # report_steps_dct contains current step desciption and force and export tags
    # report_headers_df contains column titles, 
    # report_columns_usage_dct show if fabric_name, chassis_name and group_name of device ports should be used
    report_constant_lst, report_steps_dct, report_headers_df, report_columns_usage_dct = report_creation_info_lst
    # report_constant_lst contains information: customer_name, project directory, database directory, max_title
    *_, max_title = report_constant_lst

    # names to save data obtained after current module execution
    data_names = ['fcr_xd_proxydev']
    # service step information
    print(f'\n\n{report_steps_dct[data_names[0]][3]}\n')
    
    # reade data from database if they were saved on previos program execution iteration
    data_lst = dbop.read_database(report_constant_lst, report_steps_dct, *data_names)
    
    # list of data to analyze from report_info table
    analyzed_data_names = ['switch_params_aggregated', 'fabric_labels', 'portshow_aggregated', 'fcrfabric', 
                            'fcrproxydev', 'fcredge', 'fcrphydev', 'fcrresource', 'fcrxlateconfig']

    # force run when any data from data_lst was not saved (file not found) or 
    # procedure execution explicitly requested for output data or data used during fn execution  
    force_run = meop.verify_force_run(data_names, data_lst, report_steps_dct, 
                                            max_title, analyzed_data_names)
    if force_run:
        # current operation information string
        info = f'Generating translate domain connected devices table'
        print(info, end =" ") 

        # aggregated DataFrames
        fcr_xd_proxydev_df = fcr_xd_proxydev_aggregation(switch_params_aggregated_df, portshow_aggregated_df, 
                                                            fcrproxydev_df, fcrxlateconfig_df)
        # after finish display status
        meop.status_info('ok', max_title, len(info))
        # create list with partitioned DataFrames
        data_lst = [fcr_xd_proxydev_df]
        # writing data to sql
        dbop.write_database(report_constant_lst, report_steps_dct, data_names, *data_lst) 
    # verify if loaded data is empty and replace information string with empty DataFrame
    else:
        data_lst = dbop.verify_read_data(report_constant_lst, data_names, *data_lst)
        fcr_xd_proxydev_df, *_ = data_lst
    # save data to service file if it's required
    for data_name, data_frame in zip(data_names, data_lst):
        dfop.dataframe_to_excel(data_frame, data_name, report_creation_info_lst)
    return fcr_xd_proxydev_df


def fcr_xd_proxydev_aggregation(switch_params_aggregated_df, portshow_aggregated_df, 
                                fcrproxydev_df, fcrxlateconfig_df):
    """Function to idenitfy devices connected to translate domains"""

    fcrproxydev_cp_df = fcrproxydev_df.copy()
    fcrxlateconfig_cp_df = fcrxlateconfig_df.copy()

    # add fabric_name, fabric_label of the backbone switches
    fcrproxydev_cp_df['switchWwn'] = fcrproxydev_cp_df['principal_switchWwn']
    fcrproxydev_cp_df = dfop.dataframe_fillna(fcrproxydev_cp_df, switch_params_aggregated_df, 
                                                join_lst=['switchWwn'], filled_lst=['Fabric_name', 'Fabric_label'])
    fcrxlateconfig_cp_df = dfop.dataframe_fillna(fcrxlateconfig_cp_df, switch_params_aggregated_df,     
                                                    join_lst=['switchWwn'], filled_lst=['Fabric_name', 'Fabric_label'])
    # identify device connected
    fcr_xd_proxydev_df = identify_proxy_device_wwn_pid(fcrxlateconfig_cp_df, fcrproxydev_cp_df)
    fcr_xd_proxydev_df = add_proxy_device_details(fcr_xd_proxydev_df, portshow_aggregated_df)
    
    # add fabric name, label and switchName of the translate domain
    switch_columns = ['Fabric_name', 'Fabric_label', 'switchName']
    fcr_xd_proxydev_df = dfop.dataframe_fillna(fcr_xd_proxydev_df, switch_params_aggregated_df, join_lst=['switchWwn'], filled_lst=switch_columns)
    # move translate domain columns to the front of DataFrame
    fcr_xd_proxydev_df = dfop.move_column(fcr_xd_proxydev_df, cols_to_move=switch_columns, ref_col='switchWwn', place='before')
    return fcr_xd_proxydev_df


def identify_proxy_device_wwn_pid(fcrxlateconfig_cp_df, fcrproxydev_cp_df):
    """Function to identify proxy device portWwn and PIDs (physical and proxy)"""

    # ImportedFID - Fabric ID where translate domain is created
    fcrproxydev_cp_df['ImportedFid'] = fcrproxydev_cp_df['Proxy_Created_in_Fabric']
    # ExportedFid - FabricID proxy devices are imported from
    fcrproxydev_cp_df['ExportedFid'] = fcrproxydev_cp_df['Device_Exists_in_Fabric']
    # remove leading zeroes
    for column in ['ImportedFid', 'ExportedFid', 'Domain', 'OwnerDid']:
        fcrxlateconfig_cp_df[column] = fcrxlateconfig_cp_df[column].str.lstrip('0')

    fcr_xd_proxydev_columns = ['Fabric_name', 'Fabric_label', 'XlateWWN', 'ImportedFid', 'ExportedFid', 'Domain', 'OwnerDid']
    fcr_xd_proxydev_df = fcrxlateconfig_cp_df[fcr_xd_proxydev_columns].copy()

    # add device portWwn, PID in fabric where device connected, PID in fabric where device imported based FIDs
    fcr_xd_proxydev_df = dfop.dataframe_fillna(fcr_xd_proxydev_df, fcrproxydev_cp_df, 
                                                join_lst=['Fabric_name', 'Fabric_label', 'ImportedFid', 'ExportedFid'], 
                                                filled_lst=['Device_portWwn', 'Proxy_PID', 'Physical_PID'], remove_duplicates=False)
    return fcr_xd_proxydev_df


def add_proxy_device_details(fcr_xd_proxydev_df, portshow_aggregated_df):
    """Function to add proxy device details (device_columns) connected to translate domain"""

    # rename column to join on
    fcr_xd_proxydev_df.rename(columns={'Device_portWwn': 'Connected_portWwn'}, inplace=True)
    # drop fabric name and label of backbone switches 
    # coz we are interested in fabric name and label of the fabric where translate domain created and where real device connected
    fcr_xd_proxydev_df.drop(columns=['Fabric_name', 'Fabric_label'], inplace=True)

    device_columns = ['Fabric_name', 'Fabric_label', 
                    'chassis_name', 'chassis_wwn', 'switchName', 'switchWwn',
                    'portIndex', 'slot', 'port', 'Connected_portId',
                    'speed', 'portType',
                    'Device_Host_Name', 'Device_Port', 'alias',
                    'LSAN', 'deviceType', 'deviceSubtype']
    # add proxy device information based in portWwn
    fcr_xd_proxydev_df = dfop.dataframe_fillna(fcr_xd_proxydev_df, portshow_aggregated_df, join_lst=['Connected_portWwn'], filled_lst=device_columns)
    # add Device_ flag for columns related to proxy device
    device_rename_dct = {column: 'Device_' + column for column in device_columns[:6]}
    device_rename_dct['XlateWWN'] = 'switchWwn'
    # rename columns of the proxy device and Wwn of the traslate domain 
    fcr_xd_proxydev_df.rename(columns=device_rename_dct, inplace=True)
    return fcr_xd_proxydev_df