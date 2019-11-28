import pandas as pd
import numpy as np
from files_operations import status_info, load_data, save_data 
from files_operations import force_extract_check, save_xlsx_file, dataframe_import, dct_from_columns, columns_import

"""Module to generate 'Switches', 'Fabric', 'Fabric global parameters', 'Switches parameters', 'Licenses' customer report tables"""


def fabric_main(fabricshow_ag_labels_df, chassis_params_df, switch_params_df, maps_params_df, report_data_lst):
    """Main function to create tables
    """
    # report_data_lst contains [customer_name, dir_report, dir_data_objects, max_title]
    
    print('\n\nSTEP 16. FABRIC AND SWITCHES INFORMATION TABLES...\n')
    
    *_, max_title, report_steps_dct = report_data_lst
    # check if data already have been extracted
    data_names = [
        'Коммутаторы', 'Фабрика', 'Глобальные_параметры_фабрики', 
        'Параметры_коммутаторов', 'Лицензии'
        ]

    # data_auxillary_names = ['fabric_labels_clean', 'fabric_info_aggregated', 'chassis_name_usage']
    # loading data if were saved on previous iterations 
    data_lst = load_data(report_data_lst, *data_names)
    # data_auxillary_lst = load_data(report_data_lst, *data_auxillary_names)
    # chassis_column_usage, = load_data(report_data_lst, 'chassis_column_usage')

    # unpacking DataFrames from the loaded list with data
    switches_report_df, fabric_report_df, global_fabric_parameters_report_df, switches_parameters_report_df, licenses_report_df = data_lst
    
    # data force extract check 
    # if data have been calculated on previous iterations but force key is ON 
    # then data re-calculated again and saved
    # force key for each DataFrame
    force_extract_keys_lst = [report_steps_dct[data_name][1] for data_name in data_names]
    # check if data was loaded and not empty
    data_check = force_extract_check(data_names, data_lst, force_extract_keys_lst, max_title)

    # force_extract_auxillary_keys_lst = [report_steps_dct[data_name][1] for data_name in data_auxillary_names]
    # data_check_auxillary = force_extract_check(data_auxillary_names, data_auxillary_lst, force_extract_keys_lst, max_title)
    
    # flag if fabrics labels was forced to be changed 
    fabric_labels_change = True if report_steps_dct['fabric_labels'][1] else False

    # import data with switch models, firmware and etc
    switch_models_df = dataframe_import('switch_models', max_title)                     
    # clean fabricshow DataFrame from unneccessary data
    fabric_clean_df = fabric_clean(fabricshow_ag_labels_df)
    # create aggregated table by joining DataFrames
    switch_params_aggregated_df, chassis_column_usage = fabric_aggregation(fabric_clean_df, chassis_params_df, switch_params_df, maps_params_df, switch_models_df)
    save_xlsx_file(switch_params_aggregated_df, 'switch_params_aggregated', report_data_lst, report_type = 'service')

    # when no data saved or force extract flag is on or fabric labels have been changed than 
    # analyze extracted config data  
    if not all(data_check) or any(force_extract_keys_lst) or fabric_labels_change:
        # information string if fabric labels force changed was initiated
        # and statistics recounting required
        if fabric_labels_change and not any(force_extract_keys_lst) and all(data_check):
            info = f'Switch information force extract due to change in Fabrics labeling'
            print(info, end =" ")
            status_info('ok', max_title, len(info))

        # partition aggregated DataFrame to required tables
        switches_report_df, fabric_report_df, global_fabric_parameters_report_df, \
            switches_parameters_report_df, licenses_report_df = fabric_segmentation(switch_params_aggregated_df, data_names, chassis_column_usage, max_title)

        # drop rows with empty switch names columns
        fabric_report_df.dropna(subset = ['Имя коммутатора'], inplace = True)
        switches_parameters_report_df.dropna(subset = ['Имя коммутатора'], inplace = True)
        licenses_report_df.dropna(subset = ['Имя коммутатора'], inplace = True)

        # parameters are equal for all switches in one fabric
        global_fabric_parameters_report_df.drop_duplicates(subset=['Фабрика', 'Подсеть'], inplace=True)
        global_fabric_parameters_report_df.reset_index(inplace=True, drop=True)      

        # create list with partitioned DataFrames
        data_lst = [switches_report_df, fabric_report_df, global_fabric_parameters_report_df, \
            switches_parameters_report_df, licenses_report_df]
        
        # current operation information string
        info = f'Generating Fabric and Switches tables'
        print(info, end =" ")   
        # after finish display status
        status_info('ok', max_title, len(info))

        # saving fabric_statistics and fabric_statistics_summary DataFrames to csv file
        save_data(report_data_lst, data_names, *data_lst)
        # save_data(report_data_lst, data_auxillary_names, *data_auxillary_lst)
        
    # save data to service file if it's required
    for data_name, data_frame in zip(data_names, data_lst):
        save_xlsx_file(data_frame, data_name, report_data_lst, report_type = 'SAN_Assessment_tables')


    return switch_params_aggregated_df, chassis_column_usage, fabric_clean_df, switches_report_df, fabric_report_df, \
        global_fabric_parameters_report_df, switches_parameters_report_df, licenses_report_df


def fabric_clean(fabricshow_ag_labels_df):
    """Function to prepare fabricshow_ag_labels DataFrame for join operation"""
    # create copy of fabricshow_ag_labels DataFrame
    fabric_clean_df = fabricshow_ag_labels_df.copy()
    # remove switches which are not part of research 
    # (was not labeled during Fabric labeling procedure)
    fabric_clean_df.dropna(subset=['Fabric_name', 'Fabric_label'], inplace = True)

    # remove Front and Translate Domain switches
    mask = fabric_clean_df.Enet_IP_Addr != '0.0.0.0'
    fabric_clean_df = fabric_clean_df.loc[mask]
    # reset fabrics DataFrame index after droping switches
    fabric_clean_df.reset_index(inplace=True, drop=True)
    # extract required columns
    fabric_clean_df = fabric_clean_df.loc[:, ['Fabric_name', 'Fabric_label', 'Worldwide_Name', 'Name']]
    # rename columns as in switch_params DataFrame
    fabric_clean_df.rename(columns={'Worldwide_Name': 'switchWwn', 'Name': 'switchName'}, inplace=True)

    return fabric_clean_df


def fabric_aggregation(fabric_clean_df, chassis_params_df, switch_params_df, maps_params_df, switch_models_df):
    """Function to complete fabric DataFrame with information from 
    chassis_params_fabric, switch_params, maps_params DataFrames """

    # complete fabric DataFrame with information from switch_params DataFrame
    f_s_df = fabric_clean_df.merge(switch_params_df, how = 'left', on = ['switchWwn', 'switchName'])
    # complete f_s DataFrame with information from chassis_params DataFrame
    f_s_c_df = f_s_df.merge(chassis_params_df, how = 'left', on=['configname', 'chassis_name', 'chassis_wwn'])

    # convert switch_index in f_s_c and maps_params DataFrames to same type
    maps_params_df.switch_index = maps_params_df.switch_index.astype('float64', errors='ignore')
    f_s_c_df.switch_index = f_s_c_df.switch_index.astype('float64', errors='ignore')

    # complete f_s_c DataFrame with information from maps_params DataFrame
    f_s_c_m_df = f_s_c_df.merge(maps_params_df, how = 'left', on = ['configname', 'chassis_name', 'switch_index'])

    # convert switchType in f_s_c_m and switch_models DataFrames to same type
    # convert f_s_c_m_df.switchType from string to float
    f_s_c_m_df.switchType = f_s_c_m_df.switchType.astype('float64', errors='ignore')
    # remove fractional part from f_s_c_m_df.switchType
    f_s_c_m_df.switchType = np.floor(f_s_c_m_df.switchType)
    switch_models_df.switchType = switch_models_df.switchType.astype('float64', errors='ignore')
    # complete f_s_c_m DataFrame with information from switch_models DataFrame
    f_s_c_m_i_df = f_s_c_m_df.merge(switch_models_df, how='left', on='switchType')
    # sorting DataFrame
    f_s_c_m_i_df.sort_values(by=['Fabric_name', 'Fabric_label', 'switchType', 'chassis_name', 'switch_index'], \
        ascending=[True, True, False, True, True], inplace=True)
    # reset index values
    f_s_c_m_i_df.reset_index(inplace=True, drop=True)

    # set DHCP to 'off' for Directors
    director_type = [42.0, 62.0, 77.0, 120.0, 121.0, 165.0, 166.0]
    f_s_c_m_i_df.loc[f_s_c_m_i_df.switchType.isin(director_type), 'DHCP'] = 'Off'

    # check if chassis_name and switch_name columns are equal
    # if yes then no need to use chassis information in tables
    # remove switches with unparsed data
    chassis_names_check_df = f_s_c_m_i_df.dropna(subset=['chassis_name', 'SwitchName'], how = 'all')
    if all(chassis_names_check_df.chassis_name == chassis_names_check_df.SwitchName):
        chassis_column_usage = False
    else:
        chassis_column_usage = True
    
    

    return f_s_c_m_i_df, chassis_column_usage


def fabric_segmentation(f_s_c_m_i_df, data_names, chassis_column_usage, max_title):
    """Function to split aggregated table to required DataFrames"""
    # construct columns titles from data_names to use in dct_from_columns function
    tables_names_lst = [
        [data_name.rstrip('_report') + '_eng', data_name.rstrip('_report')+'_ru'] 
        for data_name in data_names
        ]      

    # dictionary used to rename DataFrame english columns names to russian
    data_columns_names_dct = {}
    # for each data element from data_names list import english and russian columns title
    # data_name is key and two lists with columns names are values for data_columns_names_dct
    for data_name, eng_ru_columns in zip(data_names, tables_names_lst):
        data_columns_names_dct[data_name]  = \
            dct_from_columns('tables_columns_names', max_title, *eng_ru_columns, init_file = 'san_automation_info.xlsx')

    # construct english columns titles from tables_names_lst to use in columns_import function
    tables_names_eng_lst = [table_name_lst[0] for table_name_lst in tables_names_lst]
    # dictionary to extract required columns from aggregated DataFrame f_s_c_m_i
    data_columns_names_eng_dct = {}
    # for each data element from data_names list import english columns title
    for data_name, df_eng_column in zip(data_names, tables_names_eng_lst):
        # data_name is key and list with columns names is value for data_columns_names_eng_dct
        data_columns_names_eng_dct[data_name] = columns_import('customer_report', max_title, df_eng_column, init_file = 'san_automation_info.xlsx')
        # if no need to use chassis information in tables
        if not chassis_column_usage:
            if 'chassis_name' in data_columns_names_eng_dct[data_name]:
                data_columns_names_eng_dct[data_name].remove('chassis_name')
            if 'chassis_wwn' in data_columns_names_eng_dct[data_name]:
                data_columns_names_eng_dct[data_name].remove('chassis_wwn')
            
    # list with partitioned DataFrames
    fabric_df_lst = []
    for data_name in data_names:
        # get required columns from aggregated DataFrame
        data_frame = f_s_c_m_i_df[data_columns_names_eng_dct[data_name]].copy()

        # translate columns to russian
        data_frame.rename(columns = data_columns_names_dct[data_name], inplace = True)
        # add partitioned DataFrame to list
        fabric_df_lst.append(data_frame)

    return fabric_df_lst
