import re
import pandas as pd
from files_operations import columns_import, status_info, data_extract_objects, load_data, save_data
from files_operations import  line_to_list, force_extract_check, update_dct

"""Module to extract interswitch connection information"""


def interswitch_connection_extract(switch_params_lst, report_data_lst):
    """Function to extract interswitch connection information
    """    
    # report_data_lst contains [customer_name, dir_report, dir_data_objects, max_title]
    
    print('\n\nSTEP 11. INTERSWITCH CONNECTIONS AND TRUNK PORTS INFORMATION ...\n')
    
    *_, max_title, report_steps_dct = report_data_lst
    # check if data already have been extracted
    # data_names = ['isl', 'trunk', 'ag', 'trunkarea']
    data_names = ['isl', 'trunk', 'porttrunkarea']
    data_lst = load_data(report_data_lst, *data_names)
    # isl_lst, trunk_lst, ag_lst, trunkarea_lst = data_lst
    isl_lst, trunk_lst, porttrunkarea_lst = data_lst
    
    # data force extract check. 
    # if data have been extracted already but extract key is ON then data re-extracted
    force_extract_keys_lst = [report_steps_dct[data_name][1] for data_name in data_names]
    force_extract_check(data_names, data_lst, force_extract_keys_lst, max_title)
    
    # if no data saved than extract data from configurtion files 
    if not all(data_lst) or any(force_extract_keys_lst):    
        print('\nEXTRACTING INTERSWITCH CONNECTION INFORMATION (ISL, TRUNK, TRUNKAREA) ...\n')   
        
        # extract chassis parameters names from init file
        switch_columns = columns_import('switch', max_title, 'columns')
        # number of switches to check
        switch_num = len(switch_params_lst)   
     
        # data imported from init file to extract values from config file
        *_, comp_keys, match_keys, comp_dct = data_extract_objects('isl', max_title)


        # lists to store only REQUIRED infromation
        # collecting data for all switches ports during looping
        isl_lst = []
        trunk_lst = []
        porttrunkarea_lst = []

        # switch_params_lst [[switch_params_sw1], [switch_params_sw1]]
        # checking each switch for switch level parameters
        for i, switch_params_data in enumerate(switch_params_lst):       
            # data unpacking from iter param
            # dictionary with parameters for the current switch
            switch_params_data_dct = dict(zip(switch_columns, switch_params_data))
            switch_info_keys = ['configname', 'chassis_name', 'switch_index', 
                                'SwitchName', 'switchWwn', 'switchRole', 'Fabric_ID', 'FC_Router', 'switchMode']
            switch_info_lst = [switch_params_data_dct.get(key) for key in switch_info_keys]
            ls_mode_on = True if switch_params_data_dct['LS_mode'] == 'ON' else False
            
            sshow_file, _, switch_index, switch_name, *_, switch_mode = switch_info_lst
                        
            # current operation information string
            info = f'[{i+1} of {switch_num}]: {switch_name} isl, trunk and trunk area ports. Switch mode: {switch_mode}'
            print(info, end =" ")           
            # search control dictionary. continue to check sshow_file until all parameters groups are found
            collected = {'isl': False, 'trunk': False, 'trunkarea': False}

            if switch_mode == 'Native':
                with open(sshow_file, encoding='utf-8', errors='ignore') as file:
                    # check file until all groups of parameters extracted
                    while not all(collected.values()):
                        line = file.readline()                        
                        if not line:
                            break
                        # isl section start   
                        # switchcmd_islshow_comp
                        if re.search(comp_dct[comp_keys[0]], line) and not collected['isl']:
                            collected['isl'] = True
                            if ls_mode_on:
                                while not re.search(fr'^CURRENT CONTEXT -- {switch_index} *, \d+$',line):
                                    line = file.readline()
                                    if not line:
                                        break                        
                            # switchcmd_end_comp
                            while not re.search(comp_dct[comp_keys[2]], line):
                                line = file.readline()
                                match_dct = {match_key: comp_dct[comp_key].match(line) for comp_key, match_key in zip(comp_keys, match_keys)}
                                # islshow_match
                                if match_dct[match_keys[1]]:
                                    isl_port = line_to_list(comp_dct[comp_keys[1]], line, *switch_info_lst[:-1])
                                    # portcfg parameters
                                    if isl_port[-1]:
                                        isl_port[-1] = isl_port[-1].replace(' ', ', ')
                                    # appending list with only REQUIRED port info for the current loop iteration 
                                    # to the list with all ISL port info
                                    isl_lst.append(isl_port)
                                if not line:
                                    break                                
                        # isl section end
                        # trunk section start   
                        # switchcmd_trunkshow_comp
                        if re.search(comp_dct[comp_keys[3]], line) and not collected['trunk']:
                            collected['trunk'] = True
                            if ls_mode_on:
                                while not re.search(fr'^CURRENT CONTEXT -- {switch_index} *, \d+$',line):
                                    line = file.readline()
                                    if not line:
                                        break                        
                            # switchcmd_end_comp
                            while not re.search(comp_dct[comp_keys[2]], line):                             
                                match_dct = {match_key: comp_dct[comp_key].match(line) for comp_key, match_key in zip(comp_keys, match_keys)}
                                # trunkshow_match
                                if match_dct[match_keys[4]]:
                                    trunk_port = line_to_list(comp_dct[comp_keys[4]], line, *switch_info_lst[:-1])
                                    # if trunk line has trunk number then remove ":" from trunk number
                                    if trunk_port[8]:
                                        trunk_port[8] = trunk_port[8].strip(':')
                                        trunk_num = trunk_port[8]
                                    # if trunk line has no number then use number from previous line
                                    else:
                                        trunk_port[8] = trunk_num
                                    # appending list with only REQUIRED trunk info for the current loop iteration 
                                    # to the list with all trunk port info
                                    trunk_lst.append(trunk_port)
                                line = file.readline()
                                if not line:
                                    break                                
                        # trunk section end
                        # porttrunkarea section start
                        # switchcmd_trunkarea_comp
                        if re.search(comp_dct[comp_keys[5]], line) and not collected['trunkarea']:
                            collected['trunkarea'] = True
                            if ls_mode_on:
                                while not re.search(fr'^CURRENT CONTEXT -- {switch_index} *, \d+$',line):
                                    line = file.readline()
                                    if not line:
                                        break
                            # switchcmd_end_comp
                            while not re.search(comp_dct[comp_keys[2]], line):
                                line = file.readline()
                                match_dct ={match_key: comp_dct[comp_key].match(line) for comp_key, match_key in zip(comp_keys, match_keys)}
                                # 'porttrunkarea_match'
                                if match_dct[match_keys[6]]:
                                    porttrunkarea_port_lst = line_to_list(comp_dct[comp_keys[6]], line, *switch_info_lst[:4])
                                    # due to regular expression master slot appears two times in line
                                    porttrunkarea_port_lst.pop(8)
                                    # for No_light ports port and slot numbers are '--'
                                    if porttrunkarea_port_lst[9] == '--':
                                        porttrunkarea_port_lst[8] = '--'
                                    # if switch has no slots than slot number is 0
                                    for i in [4, 8]:                                    
                                        if not porttrunkarea_port_lst[i]:
                                            porttrunkarea_port_lst[i] = 0
                                    porttrunkarea_lst.append(porttrunkarea_port_lst)                                                       
                                if not line:
                                    break                        
                        # porttrunkarea section end                    
                status_info('ok', max_title, len(info))
            # if switch in Access Gateway mode then skip
            else:
                status_info('skip', max_title, len(info))        
        # save extracted data to json file
        save_data(report_data_lst, data_names, isl_lst, trunk_lst, porttrunkarea_lst)
    
    return isl_lst, trunk_lst, porttrunkarea_lst