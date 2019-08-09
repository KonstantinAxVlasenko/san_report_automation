import pandas as pd
from files_operations import columns_import, export_lst_to_excel
from san_toolbox_parser import create_parsed_dirs, create_files_list_to_parse, santoolbox_process
from san_chassis_params import chassis_params_extract
from san_switch_params import switch_params_configshow_extract

"""
Main module to run
Define folders where configuration data is stored
Define SAN Assessment project folder to store all data
Define customer name
"""

# This is folder where supportsave files are stored. 
ssave_folder = r'C:\Users\vlasenko\Documents\01.CUSTOMERS\Megafon\All SANs\STF\SSV_coreSTF_20190419'
# This folder with SAN Assessment project
project_folder = r'C:\Users\vlasenko\Documents\01.CUSTOMERS\Megafon\All SANs\STF'
# Customer name
customer_name = r'stf_cust'

# global list with constant vars for report operations 
# (customer name, folder to save report, biggest file name to print info on screen)
report_data_lst = []

print('\n\n')
print(f'ASSESSMENT FOR SAN {customer_name}'.center(125, '.')) 

def config_data_check():
    
    global report_data_lst
    
    # create directories in SAN Assessment project folder 
    dir_parsed_sshow, dir_parsed_others, dir_report = create_parsed_dirs(customer_name, project_folder)

    # check for switches unparsed configuration data
    # returns list with config data files and maximum config filename length
    unparsed_lst, max_title = create_files_list_to_parse(ssave_folder)
    
    # creates list with report data
    report_data_lst = [customer_name, dir_report, max_title]
    
    # export unparsed config filenames to DataFrame and saves it to excel file
    export_lst_to_excel(unparsed_lst, report_data_lst, 'unparsed_files', columns = ['sshow', 'amsmaps'])

    # returns list with parsed data
    parsed_lst, parsed_filenames_lst = santoolbox_process(unparsed_lst, dir_parsed_sshow, dir_parsed_others, max_title)
    parsed_lst_columns = ['switch_name', 'sshow_config', 'ams_maps_log_config']
    # export parsed config filenames to DataFrame and saves it to excel file
    export_lst_to_excel(parsed_filenames_lst, report_data_lst, 'parsed_files', columns = parsed_lst_columns)

    return parsed_lst, report_data_lst , dir_report, max_title

def switch_params_check(parsed_lst, report_data_lst, chassis_params = 0, switch_params = 0):
    
    _, _, max_title = report_data_lst
    
    if chassis_params:
        # check configuration files to extract chassis parameters and save it to the list of lists
        chassis_params_fabric_lst = chassis_params_extract(parsed_lst, max_title)
        # export chassis parameters list to DataFrame and saves it to excel file
        export_lst_to_excel(chassis_params_fabric_lst, report_data_lst, 'chassis_params', 'chassis')
    

    if switch_params:
        # switch_columns_configshow = columns_import('columns', 'switch_columns_configshow', max_title)

        chassis_columns = columns_import('chassis', max_title, 'columns')
        switch_params_configshow_lst = switch_params_configshow_extract(chassis_params_fabric_lst, chassis_columns, max_title)
        export_lst_to_excel(switch_params_configshow_lst, report_data_lst, 'switch_params', 'switch')
        # switch_columns_configshow_df = pd.DataFrame(switch_params_configshow_lst, columns = switch_columns_configshow)

        # save_xlsx_file(switch_columns_configshow_df, 'switch_params_configshow', customer_name, 'service', dir_report, max_title)
        
    
    return chassis_params_fabric_lst

if __name__ == "__main__":
    config_data, report_data_lst, *_  = config_data_check()
    switch_params_check(config_data, report_data_lst, chassis_params = 1, switch_params = 1)
    
    print('\nExecution successfully finished\n')