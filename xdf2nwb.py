from xdf2nwb_functions import *
from uuid import uuid4
from pynwb.file import Subject
import datetime
import json
import random

# function for finding vhdr files related to given xdf file
def readspevhdrfile(xdf):
    fname = os.path.basename(xdf)
    sub, ses, task = getSubSesTask(fname)
    spe_vhdr = glob.glob("/data2/Projects/NKI_RS2/MoBI/{}/{}*/raw/{}_{}*.vhdr".format(sub,ses,sub,ses))
    return spe_vhdr

# function for finding all xdf files of given task
def getxdftasks(task):
    xdf_list = glob.glob("/data2/Projects/NKI_RS2/MoBI/sub*/**/*task-{}*_lsl.xdf.gz".format(task), recursive = True)
    return xdf_list


task_dict = {
    'trails': 'The subject is given a screen with numbers and is asked to draw a line from one number to the next. They are then given a screen with numbers and letters and asked to draw a line alternating in order between letters and numbers.',
    'rey0':'The subject is given a design and asked to copy it. They are then asked to draw as much of the design as they remember.',
    'recallsherlock':'The subject is asked to describe the video from passivesherlock in as much detail as they can.',
    'recallpresent':'The subject is asked to describe the video from passivepresent in as much detail as they can.',
    'ravlt2':'The subject is asked to list the words they remember from ravlt1. They are then given a second list of words and asked which ones were on the first list and which were not. This is done 20-60 min after ravlt1.',
    'ravlt1':'The subject is given a list of words and is asked to recall them.',
    'cst':'A circle on the screen will drift left or right, the subject is asked to keep it on the screen for as long as possible.',
    'checkerboard':'The subject is asked to press a button when they see a checkerboard on the screen.',
    'mst1':'The subject is given images of objects and is asked if they would find/use each object indoors or outdoors. Halfway through the subject is asked if the object is bigger or smaller than a shoebox.',
    'mst2':'The subject is given images and is asked if the images are new, old, or similar based on the images shown in mst1.',
    'nasa':'The subject is asked to lay down, stand, lean against the wall, and then lay down again.',
    'naturalpresent':'',
    'naturalsherlock':'',
    'segpresent':'',
    'segsherlock':'',
    'flanker':'Multiple arrows exist on a line. The subject is asked to press a button corresponding to the direction the middle arrow is pointing, no matter the direction the other arrows are pointing',
    'alphawrite':'The subject is asked to write the entire alphabet in lowercase and in print. The subject is then asked to write the alphabet in reverse',
    'breathhold':'The subject is asked to hold their breath for a certain amount of time, 6 times in a row.',
    'digisymbol':'The subject is presented with symbols with corresponding numbers. They are then presented with just symbols and they must copy each number that goes with that symbol',
    'rey1':'The subject is asked to draw the same design as rey0. This is done 20-60 minutes after rey0.',
    'spirals':'The subject is asked to trace a spiral 5 times and then draw it from memory 3 times.',
    'WAARTS':'',
    'writesamples':'The subject is asked to write letters and sentences in cursive.',
    'passivepresent':'The subject watches a short animated film',
    'passivesherlock':'The subject watches part of an episode of the TV show "Sherlock"',
    'mst3':'The subject is shown the images from mst1 and is asked which question they answered for that image, indoors/outdoors or smaller/bigger.',
    'tracksanity':''
}

# Base file paths for xdf and nwb files
xdffilepath = '/data2/Projects/NKI_RS2/MoBI/'
nwbfilepath = '/data2/Projects/NKI_RS2/MoBI/NWB/NWB_BIDS_A/'

# Anonimyze?
anonymize = True

# list of all xdf and nwb files
xdf_list = glob.glob(xdffilepath + 'sub*/**/*.xdf.gz', recursive = True)
nwb_list = glob.glob(nwbfilepath + '**/*.nwb', recursive = True)

print('NWB list')
print(*nwb_list, sep='\n')
print('\n')

# Other subsets of xdf files (i.e. for specific tasks)


# finding xdf files that have not been converted to nwb files
working_xdf_list = cstr2list
not_converted = []
for i in working_xdf_list:
    fname = os.path.basename(i)
    sub, ses, task = getSubSesTask(fname)
    nwbFname = fname.replace('_lsl.xdf.gz', '_MoBI.nwb')
    nwbfile_loc = '{}/{}/{}'.format(sub,ses,nwbFname)
    nwbFile = nwbfilepath + nwbfile_loc

    if nwbFile not in nwb_list:
        not_converted.append(i)


working_list = not_converted[-5:]

print('Working List')
print(*working_list, sep='\n')
print('\n')

# Loops through list of unconverted files and converts them
for xdf_file in working_list:
    print('Currently reading:', xdf_file)
    xdffname = os.path.basename(xdf_file)
    sub, ses, taskrun = getSubSesTask(xdffname)
    nwbFileName = xdffname.replace('_lsl.xdf.gz', '_MoBI.nwb')
    fullpath = nwbfilepath + '{}/{}'.format(sub, ses)
    jsonFileName = nwbFileName.replace('.nwb', '.json')
    jsonpath = os.path.join(fullpath, jsonFileName)
    nwbpath = os.path.join(fullpath, nwbFileName)
    print('Will Create: ', nwbpath)
    print('Will Create: ', jsonpath)
    name = xdffname.split('_')
    streams, header = pyxdf.load_xdf(xdf_file)

    # Gets session start time
    time_zero = getTimeZero(streams, 'StimLabels')
    if anonymize:
        time = datetime.datetime(1970, 1, 1) # Used for time anonymization
    else:
        time = datetime.fromtimestamp(time_zero) # Used for true time

    # Retrieves all vhdr files associated with xdf file
    vhdr_list = readspevhdrfile(xdf_file)

    # Start building JSON file
    task, run = taskrun.split('_')
    taskname = task.split('-')
    nwbjson = {}
    nwbjson['InstitutionName'] = 'Nathan Kline Institute'
    nwbjson['InstitutionalDepartmentName'] = 'Center for Biomedical Imaging and Neuromodulation (C-BIN)'
    nwbjson['Subject'] = sub
    nwbjson['Session'] = ses
    nwbjson['Task'] = taskname[1]
    nwbjson['Task Description'] = task_dict[taskname[1]]

    # Initializing NWB file
    nwbfile = NWBFile(
        session_description=name[2],
        identifier=str(uuid4()),
        session_start_time = time,
        lab='C-BIN',
        institution="Nathan Kline Institute",
        experiment_description=name[2],
        session_id=name[1]
    )
    # Subject Info
    subject = Subject(
        subject_id=name[0],
        age='P0D/',
        description='N/A',
        sex='U',
        species="Homo sapiens"
    )
    nwbfile.subject = subject

    # Iterating through all the streams, extracting data and time to insert into nwbfile and building json file
    nwbjson['Streams'] = {}
    streamcount = 0
    for istreams in streams:
        streamcount += 1
        name = istreams['info']['name'][0]
        match name:
            case 'StimLabels':
                if anonymize:
                    new_times_s = anonymizeTime(istreams['time_stamps'], time_zero)
                    stimlabels(istreams['info'], istreams['time_series'], new_times_s, nwbfile, streamcount)
                else:
                    stimlabels(istreams['info'], istreams['time_series'], istreams['time_stamps'], nwbfile, streamcount)
                nwbjson['Streams']['StimLabels'] = {
                    'Description': 'Labels for specific markers during the trial',
                    'Sampling Rate': istreams['info']['effective_srate'],
                }
            case 'Argus_Eye_Tracker':
                if istreams['info']['effective_srate'] > 0:
                    if anonymize:
                        new_times_e = anonymizeTime(istreams['time_stamps'], time_zero)
                        argusData(istreams['info'], istreams['time_series'], new_times_e, nwbfile, streamcount)
                    else:
                        argusData(istreams['info'], istreams['time_series'], istreams['time_stamps'], nwbfile, streamcount)
                    nwbjson['Streams']['Argus_EyeTracker'] = {
                        'Description': 'Tracking movement of eye using Argus eyetracker',
                        'Sampling Rate': istreams['info']['effective_srate']
                    }
            case 'EyeLink':
                if istreams['info']['effective_srate'] > 0:
                    if anonymize:
                        new_times_e = anonymizeTime(istreams['time_stamps'], time_zero)
                        eyelinkData(istreams['info'], istreams['time_series'], new_times_e, nwbfile, streamcount)
                    else:
                        eyelinkData(istreams['info'], istreams['time_series'], istreams['time_stamps'], nwbfile, streamcount)
                    nwbjson['Streams']['EyeLink'] = {
                        'Description': 'Tracking movement of eye using Eyelink eyetracker',
                        'Sampling Rate': istreams['info']['effective_srate']
                    }
            case 'MindLogger':
                if istreams['info']['effective_srate'] > 0:
                    if anonymize:
                        new_times_m = anonymizeTime(istreams['time_stamps'], time_zero)
                        mindloggerData(istreams['info'], istreams['time_series'], new_times_m, nwbfile, streamcount)
                    else:
                        mindloggerData(istreams['info'], istreams['time_series'], istreams['time_stamps'], nwbfile, streamcount)
                    nwbjson['Streams']['MindLogger'] = {
                        'Description': 'Data from Mindlogger',
                        'Sampling Rate': istreams['info']['effective_srate']
                    }
            case 'BrainVision RDA':
                if istreams['info']['effective_srate'] > 0:
                    if anonymize:
                        new_times_b = anonymizeTime(istreams['time_stamps'], time_zero)
                        eegData(istreams['info'], istreams['time_series'], new_times_b, vhdr_list, nwbfile, streamcount)
                    else:
                        eegData(istreams['info'], istreams['time_series'], istreams['time_stamps'], vhdr_list, nwbfile, streamcount)
                    nwbjson['Streams']['Brainvision RDA'] = {
                        'Description': 'Data from EEG',
                        'Sampling Rate': istreams['info']['effective_srate'],
                        'Channel Count': int(istreams['info']['channel_count'][0]) - 1,
                        'Channel Names': getLabels(istreams['info'])[:-1]
                    }
            case 'OpenSignals':
                if istreams['info']['effective_srate'] > 0:
                    if anonymize:
                        new_times_o = anonymizeTime(istreams['time_stamps'], time_zero)
                        opensignalsData(istreams['info'], istreams['time_series'], new_times_o, nwbfile, streamcount)
                    else:
                        opensignalsData(istreams['info'], istreams['time_series'], istreams['time_stamps'], nwbfile, streamcount)
                    nwbjson['Streams']['OpenSignals'] = {
                        'Description': 'Physiological data of subject',
                        'Sampling Rate': istreams['info']['effective_srate'],
                        'Channel Count': int(istreams['info']['channel_count'][0]),
                        'Channel Names': getLabels(istreams['info']) 
                    }
            case 'cpCST':
                if istreams['info']['effective_srate'] > 0:
                    if anonymize:
                        new_times_c = anonymizeTime(istreams['time_stamps'], time_zero)
                        cstData(istreams['info'], istreams['time_series'], new_times_c, nwbfile, streamcount)
                    else:
                        cstData(istreams['info'], istreams['time_series'], istreams['time_stamps'], nwbfile, streamcount)
                    nwbjson['Streams']['cpCST'] = {
                        'Description': 'Data related to CST task',
                        'Sampling Rate': istreams['info']['effective_srate']
                    }
            case 'FaceVideo':
                if istreams['info']['effective_srate'] > 0:
                    if not anonymize:
                        video_raw(istreams['info'], istreams['time_series'], istreams['time_stamps'], nwbfile, streamcount)
                        nwbjson['Streams']['FaceVideo'] = {
                            'Description': 'Video recording of subject performing task',
                            'Sampling Rate': istreams['info']['effective_srate']
                        }
            case 'Audio':
                if istreams['info']['effective_srate'] > 0:
                    if not anonymize:
                        audio_raw(istreams['info'], istreams['time_series'], istreams['time_stamps'], nwbfile, streamcount)
                        nwbjson['Streams']['Audio'] = {
                            'Description': 'Audio recording of subject performing task',
                            'Sampling Rate': istreams['info']['effective_srate']
                        }
    
    # Writing to file
    if os.path.exists(fullpath) is False:
        os.makedirs(fullpath)
    
    print('\n','Creating File: ',nwbFileName,'\n')
    with NWBHDF5IO(nwbpath, 'w') as io:
        io.write(nwbfile)

    print('\n','Creating File: ',jsonFileName,'\n')
    with open(jsonpath, 'w') as outfile:
        json.dump(nwbjson, outfile)

    print('\n','{} is finished'.format(nwbFileName),'\n')
    
