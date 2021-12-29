""""""

import pandas as pd
import numpy as np


from .value_processing import count_bandwidth
from .value_presentation import сoncatenate_columns


def count_statistics(df, connection_grp_columns: list, stat_columns: list, port_qunatity_column: str, speed_column: str):
    """Function to count statistics for each pair of switches connection.
    stat_columns is the list of columns for whish statistics is counted for,
    speed_column - column name containing link speed connecion to count
    connection bandwidth. connection_grp_columns is the list of columns defining 
    individual connection to count statistics and bandwidth for that connection."""

    statistics_df = pd.DataFrame()
    bandwidth_df = count_bandwidth(df, speed_column, connection_grp_columns)
    
    # drop empty columns from the list
    stat_columns = [column for column in stat_columns if df[column].notna().any()]
    # index list to groupby switches connection on to count statistics
    index_lst = [df[column] for column in connection_grp_columns]

    # in case some values in first columns of stat_columns is none
    df['tmp_column'] = 'tmp'

    # count statistcics for each column from stat_columns in df DataFrame
    for column in ['tmp_column', *stat_columns]:
        # count statistics for current column
        current_statistics_df = pd.crosstab(index = index_lst,
                                columns = df[column])

        # add connection bandwidth column after column with port quantity 
        if column == port_qunatity_column:
            current_statistics_df = current_statistics_df.merge(bandwidth_df, how='left',
                                                                left_index=True, right_index=True)
        # add current_statistics_df DataFrame to statistics_df DataFrame
        if statistics_df.empty:
            statistics_df = current_statistics_df.copy()
        else:
            statistics_df = statistics_df.merge(current_statistics_df, how='left', 
                                                left_index=True, right_index=True)
    
    statistics_df.drop(columns=['tmp'], inplace=True)
    statistics_df.reset_index(inplace=True)
    return statistics_df


# count_total from datframe_operations
def count_summary(df, group_columns: list, count_columns: list=None, fn: str='sum'):
    """Function to count total for DataFrame groups. Group columns reduced by one column from the end 
    on each iteration. Count columns defines column names for which total need to be calculated.
    Function in string representation defines aggregation function to find summary values"""

    if not count_columns:
        count_columns = df.columns.tolist()
    elif isinstance(count_columns, str):
            count_columns = [count_columns]
    
    summary_df = pd.DataFrame()
    for _ in range(len(group_columns)):
        current_df = df.groupby(by=group_columns)[count_columns].agg(fn)
        current_df.reset_index(inplace=True)
        if summary_df.empty:
            summary_df = current_df.copy()
        else:
            summary_df = pd.concat([summary_df, current_df])
        # increase group size
        group_columns.pop()
    return summary_df

# TO_REMOVE
# def count_total(df, group_columns: list, count_columns: list=None, fn: str='sum'):
#     """Function to count total for DataFrame groups. Group columns reduced by one column from the end 
#     on each iteration. Count columns defines column names for which total need to be calculated.
#     Function in string representation defines aggregation function to find summary values"""

#     if not count_columns:
#         count_columns = df.columns.tolist()
#     elif isinstance(count_columns, str):
#             count_columns = [count_columns]
    
#     summary_df = pd.DataFrame()
#     for _ in range(len(group_columns)):
#         current_df = df.groupby(by=group_columns)[count_columns].agg(fn)
#         current_df.reset_index(inplace=True)
#         if summary_df.empty:
#             summary_df = current_df.copy()
#         else:
#             summary_df = pd.concat([summary_df, current_df])
#         # increase group size
#         group_columns.pop()
#     return summary_df


def count_all_row(statistics_summary_df):
    """Function to count row with index All containing total values of statistics_summary_df
    for all fabrics"""
    
    # extract row containing total values for Fabric_name
    mask_empty_fabric_label = statistics_summary_df['Fabric_label'].isna()
    statistics_total_df = statistics_summary_df.loc[mask_empty_fabric_label].copy()
    # sum values
    statistics_total_df.loc['All']= statistics_total_df.sum(numeric_only=True, axis=0)
    # rename Fabric_name to All
    statistics_total_df.loc['All', 'Fabric_name'] = 'All'
    # drop all rows except 'All'
    mask_fabric_name_all = statistics_total_df['Fabric_name'] == 'All'
    statistics_total_df = statistics_total_df.loc[mask_fabric_name_all].copy()
    statistics_total_df.reset_index(inplace=True, drop=True)
    return statistics_total_df


def concat_statistics(statistics_df, summary_df, total_df, sort_columns):
    """Function to concatenate statistics DataFrames. 
    statistics_df - statistics for each connection,
    summary_df statistics for fabric_name, fabric_label and fabric_name,
    total_df - total statistics for All fabrics.
    sort_columns used to sort concatenated statistics_df and summary_df
    to place summary statistics after corresponding fabric rows of statistics_df.
    """
    
    # concatenate statistics dataframes
    statistics_df = pd.concat([statistics_df, summary_df])
    statistics_df.sort_values(by=sort_columns, inplace=True)
    statistics_df = pd.concat([statistics_df, total_df])
    # reset indexes in final statistics DataFrame
    statistics_df.reset_index(inplace=True, drop=True)
    return statistics_df


# should be renamed to verify_symmetry verify_connection_symmetry
def verify_symmetry_regarding_fabric_name(statistics_summary_df, symmetry_columns, summary_column='Asymmetry_note'):
    """Function to verify if connections are symmetric in each Fabrics_name from values in
    connection_symmetry_columns point of view. Function adds Assysmetric_note to statistics_summary_df.
    Column contains parameter name(s) for which connection symmetry condition is not fullfilled"""

    # drop invalid fabric labels
    mask_not_valid = statistics_summary_df['Fabric_label'].isin(['x', '-'])
    # drop fabric summary rows (rows with empty Fabric_label)
    mask_fabric_label_notna = statistics_summary_df['Fabric_label'].notna()
    statistics_summary_cp_df = statistics_summary_df.loc[~mask_not_valid & mask_fabric_label_notna].copy()
    
    # find number of unique values in connection_symmetry_columns
    connection_symmetry_df = \
        statistics_summary_cp_df.groupby(by='Fabric_name')[symmetry_columns].agg('nunique')

    # temporary ineqaulity_notes columns for  connection_symmetry_columns
    connection_symmetry_notes = [column + '_inequality' for column in symmetry_columns]
    for column, column_note in zip(symmetry_columns, connection_symmetry_notes):
        connection_symmetry_df[column_note] = np.nan
        # if fabrics are symmetric then number of unique values in groups should be equal to one 
        # mask_values_nonuniformity = connection_symmetry_df[column] == 1
        mask_values_nonuniformity = connection_symmetry_df[column].isin([0, 1])
        # use current column name as value in column_note for rows where number of unique values exceeds one 
        connection_symmetry_df[column_note].where(mask_values_nonuniformity, column.lower(), inplace=True)
        
    # merge temporary ineqaulity_notes columns to Asymmetry_note column and drop temporary columns
    connection_symmetry_df = сoncatenate_columns(connection_symmetry_df, summary_column, 
                                                 merge_columns=connection_symmetry_notes)
    # drop columns with quantity of unique values
    connection_symmetry_df.drop(columns=symmetry_columns, inplace=True)
    # add Asymmetry_note column to statistics_summary_df
    statistics_summary_df = statistics_summary_df.merge(connection_symmetry_df, how='left', on=['Fabric_name'])
    # clean notes for dropped fabrics
    if mask_not_valid.any():
        statistics_summary_df.loc[mask_not_valid, summary_column] = np.nan

    return statistics_summary_df


def count_group_members(df, group_columns, count_columns: dict):
    """
    Auxiliary function to count how many value instances are in a DataFrame group.
    DataFrame group defined by group_columns. Instances of which column have to be 
    counted and name of the column containing instances number are in ther count_columns
    dict (dictionary key is column name with values to be evaluated, dictionary value is 
    created column name with instances number).
    After counting members in groups information added to df DataFrame
    """

    for count_column, rename_column in count_columns.items():
        if count_column in df.columns:
            current_sr = df.groupby(by=group_columns)[count_column].count()
            current_df = pd.DataFrame(current_sr)
            current_df.rename(columns={count_column: rename_column}, inplace=True)
            current_df.reset_index(inplace=True)
            
            df = df.merge(current_df, how='left', on=group_columns)
    return df



# # # RENAME TO count_summary
# def count_total(df, group_columns: list, count_columns: list, fn: str):
#     """Function to count total for DataFrame groups. Group columns reduced by one column from the end 
#     on each iteration. Count columns defines column names for which total need to be calculated.
#     Function in string representation defines aggregation function to find summary values"""

#     if isinstance(count_columns, str):
#         count_columns = [count_columns]
    
#     total_df = pd.DataFrame()
#     for _ in range(len(group_columns)):
#         current_df = df.groupby(by=group_columns)[count_columns].agg(fn)
#         current_df.reset_index(inplace=True)
#         if total_df.empty:
#             total_df = current_df.copy()
#         else:
#             total_df = pd.concat([total_df, current_df])
#         # increase group size
#         group_columns.pop()
        
#     return total_df


def count_frequency(df, count_columns: list, group_columns=['Fabric_name', 'Fabric_label'], margin_column_row:tuple=None):
    """Auxiliary function to count values in groups for columns in count_columns.
    Parameter margin_column_row is tuple of doubled booleans tuples ((False, True), (True, False), etc). 
    It defines if margin for column and row should be calculated for column values from count_columns list.
    By default column All is dropped and row All is kept. If margin_column_row is defined as tuple of booleans pair
    than it's repeated for all columns from count_columns"""

    if margin_column_row and len(margin_column_row) == 2:
        if all([isinstance(element, bool) for element in margin_column_row]):
            margin_column_row =  ((False, False),) * len(count_columns)

    # by default keep summary row but remove summary column
    if not margin_column_row:
        margin_column_row =  ((False, True),) * len(count_columns)
    if len(count_columns) != len(margin_column_row):
        print('\n')
        print('Parameters count_columns and margin_column_row in count_frequency function have different length')
        exit()

    index_lst = [df[column] for column in group_columns if column in df.columns]
    frequency_df = pd.DataFrame()

    for column, (margin_column, margin_row) in zip(count_columns, margin_column_row):
        if column in df.columns and df[column].notna().any():
            df[column].fillna(np.nan, inplace=True)
            current_df = pd.crosstab(index=index_lst, columns=df[column], margins=any((margin_column, margin_row)))
            current_df = current_df.sort_index()
            if any((margin_column, margin_row)):
                # drop column All
                if not margin_column:
                    current_df.drop(columns=['All'], inplace=True)
                # drop row All
                if not margin_row:
                    current_df.drop(index=['All'], inplace=True)
            if frequency_df.empty:
                frequency_df = current_df.copy()
            else:
                frequency_df = frequency_df.merge(current_df, how='outer', on=group_columns)

    frequency_df.fillna(0, inplace=True)            
    frequency_df.reset_index(inplace=True)                
    return frequency_df


def find_mean_max_min(df, count_columns: dict, group_columns = ['Fabric_name', 'Fabric_label']):
    """Auxiliary function to find mean, max and min values in groups for columns in count_columns
    and rename columns with corresponding keys from count_columns"""
    
    summary_df = pd.DataFrame()
    for count_column, rename_column in count_columns.items():
        current_df = df.groupby(by = group_columns)[count_column].agg(['mean', 'max', 'min'])
        current_df['mean'] = current_df['mean'].round(1)
        rename_dct = {}
        for column in current_df.columns:
            rename_dct[column] = rename_column + '_' + column
        current_df.rename(columns=rename_dct, inplace=True)
        current_df.reset_index(inplace=True)
        if summary_df.empty:
            summary_df = current_df.copy()
        else:
            summary_df = summary_df.merge(current_df, how='outer', on=group_columns)            
    return summary_df


def summarize_statistics(statistics_df, count_columns, connection_symmetry_columns, sort_columns):
    """Function to summarize statistics by adding values in fabric_name and fabric_label, fabric_name,
    all fabrics"""

    count_columns = [column for column in statistics_df.columns if statistics_df[column].notna().any()]
    # summary_statistics for fabric_name and fabric_label, fabric_name
    statistics_summary_df = \
        count_summary(statistics_df, group_columns=['Fabric_name', 'Fabric_label'], count_columns=count_columns, fn=sum)
    # verify if fabrics are symmetrical from connection_symmetry_columns point of view
    statistics_summary_df = \
        verify_symmetry_regarding_fabric_name(statistics_summary_df, connection_symmetry_columns)
    # total statistics for all fabrics
    statistics_total_df = count_all_row(statistics_summary_df)
    # concatenate all statistics in certain order
    statistics_df = concat_statistics(statistics_df, statistics_summary_df, statistics_total_df, sort_columns)
    return statistics_df

