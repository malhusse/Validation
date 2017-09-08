#!/usr/bin/env python
"""Create CRAB submission script for L1 rate change 
when L1TriggerObjects conditions are updated"""
import sys
import os
import argparse
import json

# Relatively stable parameters can have defaults.
# era should never change within a year
ERA = 'Run2_2017'
# current data global tag
CONDITIONS = '92X_dataRun2_HLT_v7'
# L1 calibrations; needs to be updated when L1 calibrations change
CALOSTAGE2PARAMS = '2017_v1_8_2_updateHFSF_v6MET'
# dummy value needed so that cmsDriver.py will
# assume that there is an input file
DEFAULTINPUT = '/store/express/Run2017B/ExpressPhysics/FEVT/Express-v1/000/297/562/00000/EE1F5F26-145B-E711-A146-02163E019C23.root'
# frontier database (needs to be specified when overriding conditions)
FRONTIER = 'frontier://FrontierProd/CMS_CONDITIONS'

def check_setup():
    if not ("CMSSW_BASE" in os.environ):
        sys.exit("Please issue 'cmsenv' before running")
    if not ("crabclient" in os.environ['PATH']):
        sys.exit("Please set up crab environment before running")

def generate_ntuple_config(configtype, newtag):
    """Generates ntuple python file for a given 
    config type (default or new conditions) and 
    a new HcalL1TriggerObjects tag"""
    cmd = 'cmsDriver.py l1Ntuple -s RAW2DIGI '
    cmd += '--python_filename=ntuple_maker_' + configtype + '.py '
    # number of events; overridden by CRAB
    cmd += "-n 10 "
    # should always be set to Run2_2017 for 2017 data
    cmd += '--era=' + ERA +  ' '
    # validations are always run on data, not MC
    cmd += '--data '
    # default conditions
    cmd += '--conditions=' + CONDITIONS + ' '
    # run re-emulation including re-emulation of HCAL TPs
    cmd += '--customise=L1Trigger/Configuration/customiseReEmul.L1TReEmulFromRAWsimHcalTP '
    # include emulated quantities in L1Ntuple
    cmd += '--customise=L1Trigger/L1TNtuples/customiseL1Ntuple.L1NtupleRAWEMU '
    # use correct CaloStage2Params; should only change if Layer2 calibration changes
    cmd += '--customise=L1Trigger/Configuration/customiseSettings.L1TSettingsToCaloStage2Params_' + CALOSTAGE2PARAMS + ' '
    # override HcalL1TriggerObjects
    if(configtype == 'new_cond'):
        cmd += '--custom_conditions=' + newtag + ',HcalL1TriggerObjectsRcd,' + FRONTIER + ' '
    # need to use LUTGenerationMode = False because we are using L1TriggerObjects
    cmd += "--customise_commands='process.HcalTPGCoderULUT.LUTGenerationMode=cms.bool(False)' "
    # default input file
    cmd += '--filein=' + DEFAULTINPUT + ' '
    cmd += '--no_exec '
    return cmd

PARSER = argparse.ArgumentParser()
PARSER.add_argument('-t', '--newtag', required=True)
PARSER.add_argument('-l', '--lumimask', required=True)
PARSER.add_argument('-d', '--dataset', required=True)
PARSER.add_argument('-o', '--outputsite', required=True)
PARSER.add_argument('-n', '--no_exec')
ARGS = PARSER.parse_args()

# check environment setup
check_setup()

FILE = file(ARGS.lumimask)
GOOD_RUN_STRING = FILE.read()
GOOD_RUN_DATA = json.loads(GOOD_RUN_STRING)
if len(GOOD_RUN_DATA) != 1:
    sys.exit("Only running on a single run at a time is supported.")
RUN = GOOD_RUN_DATA.keys()[0]
# generate configs both for default and new conditions
for jobtype in ['def', 'new_cond']:
    tmpfile = 'submit_tmp.py'
    crab_submit_script = open(tmpfile, 'w')
    crab_submit_script.write("RUN = " + str(RUN) + '\n')
    if jobtype == 'def':
        crab_submit_script.write("NEWCONDITIONS = False\n")
    else:
        crab_submit_script.write("NEWCONDITIONS = True\n")
    crab_submit_script.write("OUTPUTSITE = '" + ARGS.outputsite + "'\n")
    crab_submit_script.write("LUMIMASK = '" + ARGS.lumimask + "'\n")
    crab_submit_script.write("DATASET = '" + ARGS.dataset + "'\n\n")
    crab_submit_script.close()
    
    # concatenate crab submission file with template
    filename = 'submit_run_' + str(RUN) + '_' + jobtype + '.py'
    command = "cat submit_tmp.py ntuple_submit_template.py > " + filename
    os.system(command)
    os.remove(tmpfile)

    # generate cmsDriver commands
    print generate_ntuple_config(jobtype, ARGS.newtag)
    os.system(generate_ntuple_config(jobtype, ARGS.newtag))
    if(not ARGS.no_exec):
        crabcmd = "crab submit " + filename
        os.system(crabcmd)