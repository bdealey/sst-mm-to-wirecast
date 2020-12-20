#!/c/Users/SetonSwimTeam/AppData/Local/Programs/Python/Python39/python
# # ! d/usr/local/bin/python3

#############################################################################################
#############################################################################################
###
### generate_heat_files
###  Will generate files for use in WireCast livestreaming software.  This script will 
###  generate both meet program entry files and meet results files.
###
### reports need to be created with the following options set
###     1 event/heat per page
###     Top How Many needs to be set to ensure all results fit on a single page 
###         Wirecast can only display approx 14 results on their screen
###      Records is not selected
###      Splits is set to None
###
###  meet program entries:
###  Given a Meet Manager generated Meet Program, exported as a TXT file (single column one heat per page)
###   create individual files for every event/heat, with cleaned up text 
###   for optimal visualization on the live webcast for the WireCast application
###
###  meet results:
###  Given a Meet Manager generated Meet Results file, exported as a TXT file (sinle column one event per page)\
###  create individual results file per event for wirecast
###  Also generate a meet results CRAWL, which is a single line file with the results to
###  scroll through the botton of the livecast
###  
#############################################################################################
#############################################################################################

import os, os.path
import re
import argparse
from pathlib import Path
import glob
import logging

###
### Import local modules that were split out for cleaner functionality
import sst_module_common as sst_common
import sst_module_program as sst_program
import sst_module_results as sst_results

## Globals
report_type_results = "result"
report_type_program = "program"
report_type_crawler = "crawler"

## Define the header types in the output list so we can include/exclude as necessary
headerNum1 = -1   ## HyTek licensee and HytTek software
headerNum2 = -2   ## Meet Name
headerNum3 = -3   ## Report type




#####################################################################################
## CLI param to remove existing files from directory.  This is needed when
## old heats won't be overwritten so we need to make sure they are removed
#####################################################################################
def remove_files_from_dir( reporttype: str, directory_name: str ) -> int:

    num_files_removed = 0
    """ Remove files from previous run/meet so there are no extra heats/events left over"""
    for root, dirs, files in os.walk(directory_name):
        for file in files:
            if file.startswith((reporttype)):
                os.remove(os.path.join(root, file)) 
                num_files_removed += 1

    return num_files_removed




#####################################################################################
## create_output_file_crawler
##
## Given a list of tuples (evnt num, crawler_string), generate output files
## Generate crawler files for actual events (event_num > 0) and for meet name (event_num = -2)
#####################################################################################
def create_output_file_crawler( output_dir_root: str, crawler_list: list, num_results_to_display: int, last_num_events: int ):
    """ Given a list of tuples (evnt num, crawler_string), generate output files """
    
    file_name_prefix = "crawler"
    output_dir = f"{output_dir_root}{file_name_prefix}/"
    num_files_generated=0

    ## Create output dir if not exists
    if not os.path.exists( output_dir ):
        os.makedirs( output_dir )

    ## Generate individual files per meet
    for crawler_event in crawler_list:
        event_num = crawler_event[0]
        crawler_text = crawler_event[1]

        logging.info(f"crawler: e: {event_num} t: {crawler_text}")
        ## Generate event specific file
        if event_num > 0:
            output_file_name = output_dir + f"{file_name_prefix}_result_event{event_num:0>2}.txt"
            sst_common.write_output_file( output_file_name, crawler_text )
            num_files_generated += 1
        ## Genreate special file for the meet name
        elif event_num == headerNum2:
            output_file_name = output_dir + f"{file_name_prefix}__MeetName.txt"
            sst_common.write_output_file( output_file_name, crawler_text )
            num_files_generated += 1

    ## Generate single file for all scored events in reverse order
    crawler_text = ""
    crawler_text_last_num_events = ""
    meet_name = ""
    num_events = len(crawler_list)
    last_num_events_generated = 0

    ## Loop through list in reverse order to generate crawler string with multiple events
    for num in range( num_events-1, -1, -1):
        crawler_event = crawler_list[num]
        event_num = crawler_event[0]
        event_text = crawler_event[1]

        ## Save off the meet name, which somes at the end of the procesing as we are looping in reverse order
        if event_num > 0:
            crawler_text += f" | {event_text}"
            if last_num_events_generated <= last_num_events:
                crawler_text_last_num_events += f" | {event_text}"
                last_num_events_generated += 1
        elif event_num == headerNum2:
            meet_name = event_text        

    ## Add meet_name to front of string
    crawler_text = f"{meet_name} {crawler_text}"
    ## Create the crawler file with ALL events completed so far
    all_events_file_name = f"{file_name_prefix}__AllEventsReverse.txt"
    output_file_name = output_dir + all_events_file_name
    sst_common.write_output_file( output_file_name, crawler_text )
    num_files_generated += 1

    ## Create the crawler file with last_num events
    #last_xx_events_file_name = f"{file_name_prefix}__Last_{last_num_events:0>2}_events.txt"
    last_xx_events_file_name = f"{file_name_prefix}__Last_XX_events.txt"
    output_file_name = output_dir + last_xx_events_file_name
    sst_common.write_output_file( output_file_name, crawler_text_last_num_events )
    num_files_generated += 1

    return num_files_generated







def reverse_lastname_firstname( name_last_first ):
    """ Convert the string "lastnane, firstname" to "firstname lastname" """

    name_last, name_first = name_last_first.split(',', 1)
    name_first = name_first.strip()
    name_last  = name_last.strip()
    name_first_last = f"{name_first} {name_last}"

    return name_first_last



#####################################################################################
## get_report_header_info
## Get the header info from the reports first X lines
#####################################################################################
def get_report_header_info( meet_report_filename: str ):
    """ Get the header info from the reports first X lines """
            
    #####################################################################################
    ## Example headers we are processing
    ##
    ## Seton School                             HY-TEK's MEET MANAGER 8.0 - 10:02 AM  11/19/2020
    ##               2020 NoVa Catholic Invitational Championship - 1/11/2020
    ##                                     Meet Program
    #####################################################################################

    line_num = 0
    line1_header = ""
    line2_header = ""
    line3_header = ""

    with open(meet_report_filename, "r") as meet_report_file:
        for line in meet_report_file:
            line_num += 1

            #####################################################################################
            ## Remove the extra newline at end of line
            #####################################################################################
            line = line.strip()

            #####################################################################################
            ## Line1: Seton School                             HY-TEK's MEET MANAGER 8.0 - 10:02 AM  11/19/2020                 
            #####################################################################################
            if line_num == 1:
                line1_header = line
                continue

            #####################################################################################
            ## Line2:               2020 NoVa Catholic Invitational Championship - 1/11/2020                
            #####################################################################################
            if line_num == 2:
                line2_header = line
                continue

            #####################################################################################
            ## Line3:                                    Meet Program               
            #####################################################################################
            if line_num == 3:
                line3_header = line

                ## Stop the loop now. We have our headers
                break

        #####################################################################################
        ## Header1.  Break about license name (school name)       
        #  There can be some garbage on the first line before the license name. Ignore that     
        #####################################################################################
        line1_list = re.findall('^.*?([A-z0-9 \'-]+?)\s+HY-TEK',line1_header )
        license_name = str(line1_list[0].strip())

        #####################################################################################
        ## Header2.  Break about meet name and meet date               
        #####################################################################################
        line2_list = re.findall('^(.*?) - (\d+/\d+/\d+)',line2_header )
        meet_name = line2_list[0][0].strip()
        meet_date = line2_list[0][1].strip()

        #####################################################################################
        ## Header2.  Break about meet name and meet date               
        #####################################################################################
        report_type = line3_header
        report_type_meet_name = ""

        if '-' in line3_header:
            report_type,report_type_meet_name = line3_header.split('-',1)
            report_type = report_type.strip()
            report_type_meet_name = report_type_meet_name.strip()
            
        #logging.debug(f"Header: licensee '{license_name}' meet_name: '{meet_name}' meet_date: '{meet_date}' report_type: '{report_type}'")

        return meet_name, meet_date, license_name, report_type, report_type_meet_name




#####################################################################################
#####################################################################################
#####################################################################################
#####################################################################################
########## 
##########    C R A W L E R    R E S U L T S    
##########    process_crawler
##########
#####################################################################################
#####################################################################################
#####################################################################################
#####################################################################################
def process_crawler( meet_report_filename: str, 
                     output_dir: str, 
                     mm_license_name: str, 
                     shorten_school_names_relays: bool, 
                     shorten_school_names_individual: bool, 
                     display_swimmers_in_relay: bool, 
                     quote_output: bool,
                     num_results_to_display: int,
                     last_num_events: int ):
    """  From the Meet Results File, generate the crawler files per event """
    crawler_relay_dict_full_name_len = 22

    event_num = 0
    num_results_generated = 0
    #official_results = "OFFICIAL RESULTS"
    official_results = "UNOFFICIAL RESULTS"
    crawler_string = official_results
    found_header_line = 0
    num_header_lines = 3
    # school_name_dict_full_name_len = 25
    # school_name_dict_short_name_len = 4

    ## Tracking searcing for/finding/processing the three header records on each input file
    ## For crawler, we only want the header once
    processed_header_list = {"found_header_1": False, "found_header_2": False, "found_header_3": False}
    crawler_list = []

    re_crawler_lane = re.compile('^[*]?\d{1,2} ')
    #                                     TIE? place    last first   GR    SCHOOL           SEEDTIME    FINALTIME      POINTS
    #re_crawler_lane_ind   = re.compile('^([*]?\d{1,2})\s+(\w+, \w+)\s+(\w+) ([A-Z \'.].*?)\s*([0-9:.]+|NT)\s+([0-9:.]+)\s*([0-9]*)')
    re_crawler_lane_ind = re.compile('^([*]?\d{1,2})\s+([A-z\' \.]+, [A-z ]+) ([A-Z0-9]{1,2})\s+([A-Z \'.].*?)\s*([0-9:.]+|NT)\s+([0-9:.]+)\s*([0-9]*)')

    #  REGEX Positions                    TIE? PLACE   SCHOOL    RELAY     SEEDTIME    FINALTIME     POINTS
    re_crawler_lane_relay = re.compile('^([*]?\d{1,2})\s+([A-Z \'.].*)\s+([A-Z])\s+([0-9:.]+|NT)\s+([0-9:.]+)\s*([0-9]*)')


    #####################################################################################
    ## CRAWLER: Loop through each line of the input file
    #####################################################################################
    with open(meet_report_filename, "r") as meet_report_file:
        for line in meet_report_file:

            #####################################################################################
            ## CRAWLER: Remove the extra newline at end of line
            #####################################################################################
            line = line.strip()

            #####################################################################################
            ## CRAWLER: Ignore all the blank lines             
            #####################################################################################
            if line == '\n' or line == '':
                continue

            #####################################################################################
            ## CRAWLER: Ignore these meet program header lines    
            ##  Once we find the first header line, the next two lines we process are also headers            
            #####################################################################################
            ## Meet Manager license name
            if re.search("^%s" % mm_license_name, line):
                found_header_line = 1
                #if not recorded_header1:
                if not processed_header_list['found_header_1']:
                    processed_header_list['found_header_1'] = True
                    crawler_list.append( (headerNum1, line ))
                continue

            ## if the previous line was the first header (found_header_line=1)
            ## then ignore the next two lines which are also part of the header
            if 0 < found_header_line < num_header_lines:
                found_header_line += 1
                if not processed_header_list['found_header_2'] and found_header_line == 2:
                    crawler_list.append( (headerNum2, line ))
                    processed_header_list['found_header_2'] = True
                elif not processed_header_list['found_header_3'] and found_header_line == 3:
                    crawler_list.append( (headerNum3, line ))
                    processed_header_list['found_header_3'] = True

                continue

            ## Ignore these lines too
            ## For Individual Events
            if re.search("^Name(\s*)Yr", line):
                continue
            ## For Relay Events
            if re.search("^Team(\s*)Relay", line):
                continue
        
            #####################################################################################
            ## CRAWLER: Start with Event line.  
            ##  Get the Event Number from the report
            ##  Clean it up
            #####################################################################################
            if line.lower().startswith(("event")):
                ## Found an event.  If its not the first one, the we are done generating the string
                ## from the last event. Save this event data and prepare for next event
                if event_num > 0:
                    crawler_list.append( (event_num, crawler_string  ))
                    crawler_string = official_results

                #####################################################################################
                ## Start processing next event
                #####################################################################################
                event_num, clean_event_str = sst_common.get_event_num_from_eventline( line )

                ## Clear out old string and start new for next event
                num_results_generated = 0
                output_str = ""
                for element in clean_event_str:
                    output_str += f" {element}"
                crawler_string += output_str

                #logging.debug(f"CRAWLER: e: {event_num} line: {line}")

            #####################################################################################
            ## CRAWLER: For results on relays, only display relay team, not individual names
            ## TODO: Make this a command line parm
            #####################################################################################
            if not display_swimmers_in_relay and re.search('^1\) ',line):
                continue

            #####################################################################################
            ## CRAWLER: INDIVIDUAL Find the Place Winner line, place, name, school, time, points, etc
            ## i.e. 1 Last, First           SR SCH   5:31.55      5:23.86        16
            ## Note: For ties an asterick is placed before the place number and the points could have a decimal
            #####################################################################################
            if (event_num in sst_common.event_num_individual  or event_num in sst_common.event_num_diving) and re_crawler_lane.search(line):
                place_line_list = re_crawler_lane_ind.findall(line)
                if place_line_list:
                    num_results_generated += 1
                    placeline_place     = str(place_line_list[0][0]).strip()
                    placeline_name      = str(place_line_list[0][1]).strip()
                    #placeline_grade     = str(place_line_list[0][2])
                    placeline_sch_long  = str(place_line_list[0][3]).strip()
                    #placeline_seedtime  = str(place_line_list[0][4])
                    placeline_finaltime = str(place_line_list[0][5])
                    #placeline_points    = str(place_line_list[0][6])
                
                    logging.debug(f"CRAWLER: e: {event_num} line: {line}")

                    #####################################################################################
                    ## CRAWLER: Replace long school name with short name for ALL events
                    #####################################################################################
                    school_name_short = sst_common.short_school_name_lookup( placeline_sch_long, crawler_relay_dict_full_name_len )
                        
                    if shorten_school_names_individual:
                        output_str = f" {placeline_place}) {placeline_name} {school_name_short} {placeline_finaltime}"
                    else:
                        output_str = f" {placeline_place}) {placeline_name} {placeline_sch_long} {placeline_finaltime}"

                    ## Only output given number of results
                    if num_results_generated <= num_results_to_display:
                        crawler_string += output_str



            #####################################################################################
            ## CRAWLER: RELAY Find the Place Winner line, place, name, school, time, points, etc
            ## 1 SST            A                    1:46.82      1:40.65        32
            ## Note: For ties an asterick is placed before the place number and the points could have a decimal
            #####################################################################################
            if event_num in sst_common.event_num_relay and re_crawler_lane.search(line):
                place_line_list = re_crawler_lane_relay.findall(line)

                if place_line_list:
                    num_results_generated += 1
                    placeline_place     = str(place_line_list[0][0]).strip()
                    placeline_sch_long  = str(place_line_list[0][1]).strip()
                    placeline_relay     = str(place_line_list[0][2]).strip()
                    #placeline_seedtime  = str(place_line_list[0][3]).strip()
                    placeline_finaltime = str(place_line_list[0][4]).strip()
                    #placeline_points    = str(place_line_list[0][5]).strip()

                    if shorten_school_names_relays:
                        placeline_sch_short = placeline_sch_long

                        school_name_short = short_school_name_lookup( placeline_sch_long, crawler_relay_dict_full_name_len )
                        output_str = f" {placeline_place}) {school_name_short} {placeline_relay} {placeline_finaltime}"
                    else:
                        output_str = f" {placeline_place}) {placeline_sch_long} {placeline_relay} {placeline_finaltime}"

                    ## Only output given number of results
                    if num_results_generated <= num_results_to_display:
                        crawler_string += output_str  

    #####################################################################################
    ## Save last event string
    #####################################################################################
    crawler_list.append( (event_num, crawler_string ))

    #####################################################################################
    ## Write data saved in list to files
    #####################################################################################
    total_files_generated = create_output_file_crawler( output_dir, crawler_list, num_results_to_display, last_num_events )

    return total_files_generated


#####################################################################################
#####################################################################################
##  M A I N
#####################################################################################
#####################################################################################
def process_main():
    #####################################################################################
    ## Parse out command line arguments
    #####################################################################################

    spacerelaynames = True
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument('-i', '--inputdir',         dest='inputdir',            default="c:\\Users\\SetonSwimTeam\\mmreports",   
                                                                                                                help="input directory for MM extract report")
    parser.add_argument('-f', '--filename',         dest='filename',            default='results.txt',          help="Input file name")
    parser.add_argument('-o', '--outputdir',        dest='outputdir',           default="c:\\Users\\SetonSwimTeam\\Dropbox\\wirecast",           help="root output directory for wirecast heat files.")
    parser.add_argument('-r', '--shortschrelay',    dest='shortschoolrelay',     action='store_true',           help="Use Long School names for Relays")
    parser.add_argument('-s', '--shortschind',      dest='shortschoolindividual',action='store_false',          help="Use Short School names for Indiviual Entries")
    parser.add_argument('-d', '--delete',           dest='delete',              action='store_true',            help="Delete existing files in OUTPUT_DIR")
    parser.add_argument('-n', '--numresults',       dest='numresults',          type=int, default='14',         help="Number of results listed per event")
    parser.add_argument('-c', '--lastnumevents',    dest='lastnumevents',       type=int, default='3',          help="Crawler outputs a separate file with the last N events")

    ## Parms not used as often
    parser.add_argument('-S', '--splitrelays',      dest='splitrelays',         action='store_true',            help="Split Relays into multiple files")
    parser.add_argument('-R', '--displayRelayNames',dest='displayRelayNames',   action='store_true',            help="Display relay swimmer names, not just the team name in results")
    parser.add_argument('-N', '--namesfirstlast',   dest='namesfirstlast',      action='store_true',            help="Swap Non Relay names to First Last from Last, First")
    parser.add_argument('-T', '--reporttype',       dest='reporttype',          default="auto",                 choices=['auto','program','results', 'crawler', 'headers'], 
                                                                                                                help="Program type, Meet Program or Meet Results")
    ## For debugging
    parser.add_argument('-v', '--log',              dest='loglevel',          default='info', choices=['error', 'warning', 'info', 'debug'],            
                                                                                                                help="Set debugging level2")
    parser.add_argument('-q', '--quote ',           dest='quote',               action='store_true',            help="Quote the output fields for DEBUGGING")
    parser.add_argument('-h', '--help',             dest='help',                action='help', default=argparse.SUPPRESS, help="Tested with MM 8")

    parser.set_defaults(shortschoolrelay=False)
    parser.set_defaults(shortschoolindividual=True)
    parser.set_defaults(splitrelays=False)
    parser.set_defaults(displayRelayNames=False)
    parser.set_defaults(namesfirstlast=False)
    parser.set_defaults(delete=False)
    parser.set_defaults(quote=False)

    args = parser.parse_args()

    inputfile =f"{args.inputdir}/{args.filename}"

    ## Determine logging logleve
    loglevel = logging.DEBUG
    if args.loglevel == "debug":
        loglevel = logging.DEBUG
    elif args.loglevel == "info":
        loglevel = logging.INFO
    elif args.loglevel == "warning":
        loglevel = logging.WARNING
    elif args.loglevel == "error":
        loglevel = logging.ERROR

    #logging.basicConfig(flogging.DEBUGilename='example.log', filemode='w', level=logging.DEBUG) 
    # logging.basicConfig( format='%(levelname)s:%(message)s', level=logging.INFO)
    logging.basicConfig( format='%(message)s', level=loglevel)

    process_to_run = {"program": False, "results": False, "crawler": False}
    
    report_type_to_run = args.reporttype

    ## Set global debug flag
    total_files_generated_program = 0
    total_files_generated_results = 0
    total_files_generated_crawler = 0


    #####################################################################################
    ## Get header info from the meet file
    ## We need to dynamically get the meet name and license_name for use in processing files
    ## The license_name is the first line on the start of every new page/event/heat
    #####################################################################################
    meet_name, meet_date, license_name, report_type, report_type_meet_name = get_report_header_info( inputfile )

    #####################################################################################
    ##
    ## Determine report type based on input file header if not specified on CLI
    #####################################################################################
    if (report_type_to_run == "program")   or  (report_type_to_run == "auto" and report_type == 'Meet Program'):
        process_to_run['program'] = True
    elif (report_type_to_run == "results") or (report_type_to_run == "auto" and report_type == 'Results'):
        process_to_run['results'] = True
        process_to_run['crawler'] = True
    elif (report_type_to_run == "crawler") or (report_type_to_run == "auto" and report_type == 'Results'):
        process_to_run['crawler'] = True

    output_dir = args.outputdir
    ## The outputdir string MUST have a trailing slash.  Check string and add it if necesssary
    if output_dir[-1] != '/':
        output_dir = f"{output_dir}/"
    
    logargs = f"{Path(__file__).stem}  \n" + \
              f"\n   Params: \n" + \
              f"\tOutputReportType \t{args.reporttype} \n" + \
              f"\tInputFile \t\t{inputfile} \n" + \
              f"\tRoot OutputDir \t\t{output_dir} \n" + \
              f"\tShort Sch Names Relays \t{args.shortschoolrelay} \n" + \
              f"\tShort Sch Names Indiv \t{args.shortschoolindividual} \n" + \
              f"\tNamesFirstlast \t\t{args.namesfirstlast} \n" + \
              f"\tSplit Relays \t\t{args.splitrelays} \n"+ \
              f"\tDisplay Relays Names \t{args.displayRelayNames} \n"+ \
              f"\tSpaces in Relay Names \t{spacerelaynames}\n" + \
              f"\tDelete exiting files \t{args.delete}\n" + \
              f"\tCrawler last XX files \t{args.lastnumevents}\n" + \
              f"\tNum Reslts Generate \t{args.numresults}\n" + \
              f"\tQuote output fields \t{args.quote}\n" + \
              f"\tLog Level \t\t{args.loglevel}\n" + \
              f"\n   Headers: \n" + \
              f"\tMeet Name: \t\t'{meet_name}' \n" + \
              f"\tMeet Date: \t\t'{meet_date}' \n" + \
              f"\tHeader3 Meet Name: \t'{report_type_meet_name}' \n" + \
              f"\tLicensee: \t\t'{license_name}' \n" + \
              f"\tSourceReport: \t\t'{report_type}' \n" + \
              f"\n    Reports to generate: \n" + \
              f"\tprogram: \t\t'{ process_to_run['program']}' \n" + \
              f"\tresults: \t\t'{ process_to_run['results']}' \n" + \
              f"\tcrawler: \t\t'{ process_to_run['crawler']}' \n" + \
              ""

    logging.warning( logargs )


    #####################################################################################
    ## Generate wirecast files from a MEET PROGRAM txt file
    #####################################################################################
    if process_to_run['program']:
        if args.delete:
             ## Remove files from last run as we may have old events/heats mixed in
            remove_files_from_dir( 'program', output_dir )

        total_files_generated_program = sst_program.process_program( inputfile, 
                                                         output_dir, 
                                                         license_name, 
                                                         args.shortschoolrelay, 
                                                         args.shortschoolindividual, 
                                                         args.splitrelays, 
                                                         spacerelaynames, 
                                                         args.displayRelayNames, 
                                                         args.namesfirstlast, 
                                                         args.quote )

    #####################################################################################
    ## Generate wirecast files RESULTS and CRAWLER from a MEET RESULTS txt file
    #####################################################################################
    if process_to_run['results']:
        if args.delete:
             ## Remove files from last run as we may have old eventsmixed in
            remove_files_from_dir( 'results', output_dir )

        total_files_generated_results =  sst_results.process_result( inputfile, 
                                                         output_dir, 
                                                         license_name, 
                                                         args.shortschoolrelay, 
                                                         args.shortschoolindividual, 
                                                         args.displayRelayNames, 
                                                         args.displayRelayNames, 
                                                         args.namesfirstlast, 
                                                         args.quote ,
                                                         args.numresults)

    #####################################################################################
    ## Generate wirecast CRAWLER iles from a MEET RESULTS txt file
    #####################################################################################
    if process_to_run['crawler']:
         ## Remove files from last run as we may have old eventsmixed in
        remove_files_from_dir( 'crawler', output_dir )

        total_files_generated_crawler =  process_crawler( inputfile, 
                                                          output_dir, 
                                                          license_name, 
                                                          args.shortschoolrelay, 
                                                          args.shortschoolindividual,
                                                          args.displayRelayNames, 
                                                          args.quote,
                                                          args.numresults,
                                                          args.lastnumevents )


    logging.warning(f"Process Completed:")
    if total_files_generated_program > 0:
        logging.warning(f"\tNumber of 'Program' files generated: {total_files_generated_program}")
    if total_files_generated_results > 0:
        logging.warning(f"\tNumber of 'Results' files generated: {total_files_generated_results}")
    if total_files_generated_crawler > 0:
        logging.warning(f"\tNumber of 'Crawler' files generated: {total_files_generated_crawler}")

#####################################################################################
#####################################################################################
##  M A I N
#####################################################################################
#####################################################################################
if __name__ == "__main__":
    process_main()