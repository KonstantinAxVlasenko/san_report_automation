"""Module with auxiliary finctions to perform operations on DataFrames"""

import os
import sys
import xlrd
import pandas as pd
from common_operations_filesystem import save_xlsx_file
from common_operations_servicefile import dct_from_columns, columns_import
from common_operations_miscellaneous import status_info

# # copied service values
# def report_entry_values(max_title):
#     """
#     Function to import entry report values:
#     customer_name, hardware configuration files, directory to save report 
#     """

#     report_entry_df = dataframe_import('report', max_title, 'report_info.xlsx', ['name', 'value'], 'name')

#     customer_name = report_entry_df.loc['customer_name', 'value']
#     project_folder = os.path.normpath(report_entry_df.loc['project_folder', 'value'])
#     ssave_folder = os.path.normpath(report_entry_df.loc['supportsave_folder', 'value'])
#     if not pd.isna(report_entry_df.loc['blade_showall_folder', 'value']):
#         blade_folder = os.path.normpath(report_entry_df.loc['blade_showall_folder', 'value'])
#     else:
#         blade_folder = None

#     return customer_name, project_folder, ssave_folder, blade_folder

# # copied service values
# def dataframe_import(sheet_title, max_title, init_file = 'san_automation_info.xlsx', columns = None, index_name = None):
#     """Function to import dataframe from exel file"""

#     # file to store all required data to process configuratin files
#     # init_file = 'san_automation_info.xlsx'   
#     info = f'Importing {sheet_title} dataframe from {init_file} file'
#     print(info, end = ' ')
#     # try read data in excel
#     try:
#         dataframe = pd.read_excel(init_file, sheet_name = sheet_title, usecols = columns, index_col = index_name)
#     # if file is not found
#     except FileNotFoundError:
#         status_info('fail', max_title, len(info))
#         print(f'File not found. Check if file {init_file} exists.')
#         sys.exit()
#     # if sheet is not found
#     except xlrd.biffh.XLRDError:
#         status_info('fail', max_title, len(info))
#         print(f'Sheet {sheet_title} not found in {init_file}. Check if it exists.')
#         sys.exit()
#     else:
#         status_info('ok', max_title, len(info))
    
#     return dataframe


def dataframe_join(left_df, right_df, columns_lst, columns_join_index = None):
    """
    Auxiliary function to add information from right DataFrame to left DataFrame
    for both parts of left DataFrame (with and w/o _Connecetd suffix columns).
    Function take as parameters ledt and right DataFrames, list with names in right DataFrame and 
    index. Join is performed on columns up to index 
    """

    right_join_df = right_df.loc[:, columns_lst].copy()
    # left join on switch columns
    left_df = left_df.merge(right_join_df, how = 'left', on = columns_lst[:columns_join_index])
    # columns names for connected switch 
    columns_connected_lst = ['Connected_' + column_name for column_name in columns_lst]
    # dictionary to rename columns in right DataFrame
    rename_dct = dict(zip(columns_lst, columns_connected_lst))
    # rename columns in right DataFrame
    right_join_df.rename(columns = rename_dct, inplace = True)
    # left join connected switch columns
    left_df = left_df.merge(right_join_df, how = 'left', on = columns_connected_lst[:columns_join_index])
    
    return left_df


def dataframe_segmentation(dataframe_to_segment_df, dataframes_to_create_lst, report_columns_usage_dct, max_title):
    """Function to split aggregated table to required DataFrames
    As parameters function get DataFrame to be partitioned and
    list of allocated DataFrames names. Returns list of segmented DataFrames 
    """

    # sheet name with customer report columns
    customer_report_columns_sheet = 'customer_report'
    # construct columns titles from data_names to use in dct_from_columns function
    tables_names_lst = [
        [data_name.rstrip('_report') + '_eng', data_name.rstrip('_report')+'_ru'] 
        for data_name in dataframes_to_create_lst
        ]      

    chassis_column_usage = report_columns_usage_dct['chassis_info_usage']
    fabric_name_usage = report_columns_usage_dct['fabric_name_usage']

    # dictionary used to rename DataFrame english columns names to russian
    data_columns_names_dct = {}
    # for each data element from data_names list import english and russian columns title
    # data_name is key and two lists with columns names are values for data_columns_names_dct
    for dataframe_name, eng_ru_columns in zip(dataframes_to_create_lst, tables_names_lst):
        data_columns_names_dct[dataframe_name]  = \
            dct_from_columns(customer_report_columns_sheet, max_title, *eng_ru_columns, init_file = 'san_automation_info.xlsx')

    # construct english columns titles from tables_names_lst to use in columns_import function
    tables_names_eng_lst = [table_name_lst[0] for table_name_lst in tables_names_lst]
    # dictionary to extract required columns from aggregated DataFrame
    data_columns_names_eng_dct = {}
    # for each data element from data_names list import english columns title
    for dataframe_name, df_eng_column in zip(dataframes_to_create_lst, tables_names_eng_lst):
        # dataframe_name is key and list with columns names is value for data_columns_names_eng_dct
        data_columns_names_eng_dct[dataframe_name] = columns_import(customer_report_columns_sheet, max_title, df_eng_column, init_file = 'san_automation_info.xlsx')
        # if no need to use chassis information in tables
        if not chassis_column_usage:
            if 'chassis_name' in data_columns_names_eng_dct[dataframe_name]:
                data_columns_names_eng_dct[dataframe_name].remove('chassis_name')
            if 'chassis_wwn' in data_columns_names_eng_dct[dataframe_name]:
                data_columns_names_eng_dct[dataframe_name].remove('chassis_wwn')
        # if there is only one Fabric no need to use Fabric name
        if not fabric_name_usage:
            if 'Fabric_name' in data_columns_names_eng_dct[dataframe_name]:
                data_columns_names_eng_dct[dataframe_name].remove('Fabric_name')
            
    # list with partitioned DataFrames
    segmented_dataframes_lst = []
    for dataframe_name in dataframes_to_create_lst:

        df_columns_names_eng_lst = data_columns_names_eng_dct[dataframe_name]
        

        # get required columns from aggregated DataFrame
        # sliced_dataframe = dataframe_to_segment_df[data_columns_names_eng_dct[dataframe_name]].copy() # remove
        sliced_dataframe = dataframe_to_segment_df.reindex(columns = df_columns_names_eng_lst).copy()

        # translate columns to russian
        sliced_dataframe.rename(columns = data_columns_names_dct[dataframe_name], inplace = True)
        # add partitioned DataFrame to list
        segmented_dataframes_lst.append(sliced_dataframe)

    return segmented_dataframes_lst


def dataframe_fillna(left_df, right_df, join_lst, filled_lst, remove_duplicates = True):
    """
    Function to fill null values with values from another DataFrame with the same column names.
    Function accepts left Dataframe with null values, right DataFrame with filled values,
    list of columns join_lst used to join left and right DataFrames on,
    list of columns filled_lst where null values need to be filled. Both join_lst and filled_lst
    columns need to be present in left and right DataFrames.
    If drop duplicate values in join columns of right DataFrame is not required pass remove_duplicates as False.
    Function returns left DataFrame with filled null values in filled_lst columns 
    """
    
    # cut off unnecessary columns from right DataFrame
    right_join_df = right_df.loc[:, join_lst + filled_lst].copy()
    # drop rows with null values in columns to join on
    right_join_df.dropna(subset = join_lst, inplace = True)
    # if required (deafult) drop duplicates values from join columns 
    # to avoid rows duplication in left DataDrame
    if remove_duplicates:
        right_join_df.drop_duplicates(subset = join_lst, inplace = True)
    # rename columns with filled values for right DataFrame
    filled_join_lst = [name+'_join' for name in filled_lst]
    right_join_df.rename(columns = dict(zip(filled_lst, filled_join_lst)), inplace = True)
    # left join left and right DataFrames on join_lst columns
    left_df = left_df.merge(right_join_df, how = 'left', on = join_lst)
    # for each columns pair (w/o (null values) and w _join prefix (filled values)
    for filled_name, filled_join_name in zip(filled_lst, filled_join_lst):
        # copy values from right DataFrame column to left DataFrame if left value ios null 
        left_df[filled_name].fillna(left_df[filled_join_name], inplace = True)
        # drop column with _join prefix
        left_df.drop(columns = [filled_join_name], inplace = True)
        
    return left_df


def list_to_dataframe(data_lst, report_data_lst, sheet_title_export, sheet_title_import = None, 
                        columns = columns_import, columns_title_import = 'columns'):
    """Function to export list to DataFrame and then save it to excel report file
    returns DataFrame
    """

    *_, max_title, _ = report_data_lst 
    
    # checks if columns were passed to function as a list
    if isinstance(columns, list):
        columns_title = columns
    # if not (default) then import columns from excel file
    else:
        columns_title = columns(sheet_title_import, max_title, columns_title_import)
    data_df = pd.DataFrame(data_lst, columns= columns_title)
    save_xlsx_file(data_df, sheet_title_export, report_data_lst)
    
    return data_df