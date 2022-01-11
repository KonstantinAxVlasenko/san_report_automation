"""Module contains functions related to storage connections"""


import re

import numpy as np
import pandas as pd

import utilities.dataframe_operations as dfop
# import utilities.database_operations as dbop
# import utilities.data_structure_operations as dsop
# import utilities.module_execution as meop
# import utilities.servicefile_operations as sfop
# import utilities.filesystem_operations as fsop

# from common_operations_dataframe import (convert_wwn, count_frequency,
#                                          dataframe_fillna,
#                                          extract_values_from_column,
#                                          sequential_equality_note)
# from common_operations_dataframe_presentation import move_column, remove_duplicates_from_column


def storage_3par_fillna(portshow_aggregated_df, system_3par_df, port_3par_df):
    """Function to add 3PAR information collected from 3PAR configuration files to
    portshow_aggregated_df"""

    if not port_3par_df.empty and not system_3par_df.empty:
        # system information
        system_columns = ['configname', 'System_Model', 'System_Name', 
                            'Serial_Number', 'IP_Address', 'Location']
        system_3par_cp_df = system_3par_df[system_columns].copy()
        system_3par_cp_df.drop_duplicates(inplace=True)

        # add system information to 3PAR ports DataFrame
        system_port_3par_df = port_3par_df.merge(system_3par_cp_df, how='left', on=['configname'])
        # convert Wwnn and Wwnp to regular represenatation (lower case with colon delimeter)
        system_port_3par_df = dfop.convert_wwn(system_port_3par_df, ['NodeName', 'PortName'])
        # rename columns to correspond portshow_aggregated_df
        rename_columns = {'System_Name': 'Device_Name',	'System_Model':	'Device_Model', 
                            'Serial_Number': 'Device_SN', 'Location': 'Device_Location'}
        system_port_3par_df.rename(columns=rename_columns, inplace=True)
        system_port_3par_df['Device_Host_Name'] = system_port_3par_df['Device_Name']


        system_port_3par_df = storage_port_partner(system_port_3par_df, portshow_aggregated_df)


        # add 3PAR information to portshow_aggregated_df
        fillna_wwnn_columns = ['Device_Name', 'Device_Host_Name', 'Device_Model', 'Device_SN', 'IP_Address', 'Device_Location']
        portshow_aggregated_df = \
            dfop.dataframe_fillna(portshow_aggregated_df, system_port_3par_df, join_lst=['NodeName'] , filled_lst=fillna_wwnn_columns)

        fillna_wwnp_columns = ['Storage_Port_Partner_Fabric_name', 'Storage_Port_Partner_Fabric_label', 
                                'Storage_Port_Partner', 'Storage_Port_Partner_Wwnp', 
                                'Storage_Port_Mode', 'Storage_Port_Type']
        portshow_aggregated_df = \
            dfop.dataframe_fillna(portshow_aggregated_df, system_port_3par_df, join_lst=['PortName'] , filled_lst=fillna_wwnp_columns)

        portshow_aggregated_df = dfop.sequential_equality_note(portshow_aggregated_df, 
                                                            columns1=['Fabric_name', 'Fabric_label'], 
                                                            columns2=['Storage_Port_Partner_Fabric_name', 'Storage_Port_Partner_Fabric_label'], 
                                                            note_column='Storage_Port_Partner_Fabric_equal')
    # if 3PAR configuration was not extracted apply reserved name (3PAR model and SN combination)
    if 'Device_Name_reserved' in portshow_aggregated_df.columns:
        portshow_aggregated_df['Device_Host_Name'].fillna(portshow_aggregated_df['Device_Name_reserved'], inplace = True)
    return portshow_aggregated_df


def storage_port_partner(system_port_3par_df, portshow_aggregated_df):
    """Function to add 3PAR port partner (faiolver port) Wwnp and fabric connection information to system_port_3par_df"""

    # add port partner Wwnp to system_port_3par_df
    system_port_partner_3par_df = system_port_3par_df[['configname', 'Storage_Port', 'PortName']].copy()
    system_port_partner_3par_df.rename(columns={'Storage_Port': 'Storage_Port_Partner', 'PortName': 'Storage_Port_Partner_Wwnp'}, inplace=True)
    system_port_3par_df = dfop.dataframe_fillna(system_port_3par_df, system_port_partner_3par_df, 
                                            filled_lst=['Storage_Port_Partner_Wwnp'], 
                                            join_lst=['configname', 'Storage_Port_Partner'])

    # DataDrame containing all Wwnp in san
    fabric_wwnp_columns = ['Fabric_name', 'Fabric_label', 'PortName']
    portshow_fabric_wwnp_df = portshow_aggregated_df[fabric_wwnp_columns].copy()
    portshow_fabric_wwnp_df.dropna(subset=fabric_wwnp_columns, inplace=True)
    portshow_fabric_wwnp_df.drop_duplicates(inplace=True)
    
    # rename portshow_fabric_wwnp_df columns to correspond columns in system_port_partner_3par_df DataDrame
    storage_port_partner_columns = ['Storage_Port_Partner_Fabric_name', 'Storage_Port_Partner_Fabric_label', 'Storage_Port_Partner_Wwnp']
    rename_dct = dict(zip(fabric_wwnp_columns, storage_port_partner_columns))
    portshow_fabric_wwnp_df.rename(columns=rename_dct, inplace=True)
    # fill in Fabric connection information of failover ports
    system_port_3par_df = dfop.dataframe_fillna(system_port_3par_df, portshow_fabric_wwnp_df, 
                                            join_lst=storage_port_partner_columns[2:], 
                                            filled_lst=storage_port_partner_columns[:2])
    return system_port_3par_df



