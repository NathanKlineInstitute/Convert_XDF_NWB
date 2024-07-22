from pynwb import NWBHDF5IO, NWBFile, TimeSeries
from pynwb.ecephys import LFP, ElectricalSeries
from pynwb.behavior import SpatialSeries, Position, EyeTracking, PupilTracking
from hdmf.backends.hdf5.h5_utils import H5DataIO
import numpy as np
import pandas as pd
import pyxdf
import glob
import os
import re
import mne

#############################################################################################################
#--------------------------Functions to help read and organize XDF and raw files----------------------------#
#############################################################################################################

# Prints the name and effective sampling rate of every stream of an xdf file
def printallinfo(l):
    info_list = []
    for i in l:
        info_list.append([i['info']['name'][0], i['info']['effective_srate']])
    print(*info_list, sep='\n')

# Splits the name of a file into the subject, session, and task_run
def getSubSesTask(fname):
    fnameL = fname.lower()
    split1 = '_ses'
    split2 = '_task'
    split3 = '_lsl'
    subSplit = fnameL.find(split1)
    sesSplit = fnameL.find(split2)
    taskSplit = fnameL.find(split3)
    sub = fname[0:subSplit]
    ses = fname[subSplit+1:sesSplit]
    task = fname[sesSplit+1:taskSplit]
    return sub, ses, task

# Gets the name of each column of a time series
def getLabels(info):
    info_labels = info['desc'][0]['channels'][0]['channel']
    colnames = []
    for i in info_labels:
        colnames.append(i['label'][0])
    return colnames

# Gets the units of each column of a time series
def getUnits(info):
    info_units = info['desc'][0]['channels'][0]['channel']
    units = []
    for i in info_units:
        units.append(i['unit'][0])
    return units

# Finds a specific stream from xdf file
def getspeStream(streams, sname):
    for i in streams:
        try:
            if i['info']['name'][0] == sname:
                s_info = i['info']
                s_data = i['time_series']
                s_time = i['time_stamps']
                return s_info, s_data, s_time
        except Exception:
            s_info = i['info']
            s_data = []
            s_time = []
            return s_info, s_data, s_time
        
# Given a dataframe, extracts the desired columns and converts to numpy array        
def extractdata(df, list):
    extracted_data = df.loc[:, list]
    extracted_array = pd.DataFrame.to_numpy(extracted_data)
    return extracted_array

# Makes a dataframe of the time series
def makedataTable(info, data):
    headers = getLabels(info)
    df = pd.DataFrame(data, columns=headers)
    return df

# Read impedance values from vhdr file
def getImps(file):
    fname = os.path.basename(file)
    split1 = fname.find('run')
    split2 = fname.find('.')
    run_number = fname[split1:split2]
    f = open(file, 'r')
    l = f.readlines()
    f.close
    imp_search = 'Impedance [kOhm]'
    gnd_search = 'Gnd'
    imp_line = [i for i in l if imp_search in i]
    gnd_line = [i for i in l if gnd_search in i]

    if len(imp_line) > 1:
        print(fname)

    impedances = []
    labels = []

    try:
        imp_index = l.index(imp_line[-1])
        gnd_index = l.index(gnd_line[-1])
    except Exception:
        print(l[238])

    imps = l[imp_index+1:gnd_index-1]
    if len(imps) > 0:
        for i in imps:
            imp = i.split()
            try:
                imp[1] = int(imp[1])
            except Exception:
                imp[1] = 'N/A'

            labels.append(imp[0][:-1])
            impedances.append(imp[1])
    else:
        print('no imps')
    
    return(labels, run_number, impedances, fname)

#############################################################################################################
#-------------------Functions to convert given info, data, and time into nwb time series--------------------#
#############################################################################################################

# Compresses data before putting into a TimeSeries Object
def compressData(data):
    wrapped_data = H5DataIO(
        data = data,
        compression = 'gzip'
    )
    return wrapped_data

# Converts Audio stream into a TimeSeries Object
def audio_raw(info, data, time, nwb):
    
    sampling_rate = info["effective_srate"]

    # Creating TimeSeries Object
    audio = TimeSeries(
        name = "Audio",
        description = 'Audio Recording of task. Recorded at {} Hz'.format(sampling_rate),
        data = compressData(data),
        unit = "a.u.",
        timestamps = time
        )
    
    # Adding TimeSeries Object with raw data to acquisition
    nwb.add_acquisition(audio)

# Converts Video stream into a TimeSeries Object
def video_raw(info, data, time, nwb):
    
    frame_rate = info["effective_srate"]

    #reorganizing data into a list of arrays where each array is a frame with the correct resolution
    frame_data = []
    resolution = [144, 176]
    for frame in data:
        frame_data.append(np.reshape(frame, resolution))

    # Creating TimeSeries Object
    video = TimeSeries(
        name = "Video",
        description = 'Video Recording of task. Resolution of video is {} at {} Hz'.format(resolution.reverse(), frame_rate),
        data = compressData(frame_data),
        unit = "a.u.",
        timestamps = time
        )
    
    # Adding TimeSeries Object with raw data to acquisition
    nwb.add_acquisition(video)


# Converts StimLabels stream into a TimeSeries Object
def stimlabels(info, data, time, nwb):
    
    stimlabel_data = np.array(data)
    stimlabel_timestamps = time

    # Creating TimeSeries Object
    stimlabels = TimeSeries(
        name = "StimLabels",
        description = "Stimlabels",
        data = compressData(stimlabel_data),
        unit = "a.u.",
        timestamps = stimlabel_timestamps
        )
    
    # Adding TimeSeries Object with raw data to acquisition
    nwb.add_acquisition(stimlabels)

# Converts MindLogger stream into a TimeSeries Object
def mindloggerData(info, data, time, nwb):

    # Creating table of all data
    df = makedataTable(info, data)

    # Extracting desired data from inital table
    cols = ['x', 'y']
    xy = extractdata(df, cols)

    # Creating TimeSeries Object
    mindlogger = SpatialSeries(
        name = "Mindlogger",
        description = "x,y",
        data = compressData(xy.astype(float)),
        timestamps = time,
        reference_frame = "placeholder"
    )

    # Adding TimeSeries Object with raw data to acquisition
    nwb.add_acquisition(mindlogger)

# Converts OpenSignals stream into a TimeSeries Object
def opensignalsData(info, data, time, nwb):

    # Getting all relevent column names and units of stream
    headers = getLabels(info)
    headers.remove(headers[0]) #don't need first column
    units = getUnits(info)
    units.remove(units[0]) #don't need first column
    colnames = ','.join(headers)
    unitnames = ','.join(units)

    finaldata = np.delete(data, [0], axis=1) #don't need first column

    # Creating TimeSeries Object
    opensignals = TimeSeries(
        name = 'allOpenSignalsData',
        description = colnames,
        data = compressData(finaldata),
        timestamps = time,
        unit = unitnames
    )
    
    # Adding TimeSeries Object with raw data to acquisition
    nwb.add_acquisition(opensignals)

# Converts cpCST stream into TimeSeries Object
def cstData(info, data, time, nwb):

    # Getting all relavent column names and units of stream
    headers = getLabels(info)
    units = getUnits(info)
    colnames = ','.join(headers)
    unitnames = ','.join(units)

    # Creating TimeSeries Object
    cst = TimeSeries(
        name = 'allCSTdata',
        description = colnames,
        data = compressData(data),
        timestamps = time,
        unit = unitnames
    )

    # Adding TimeSeries Object with raw data to acquisition
    nwb.add_acquisition(cst)


# Takes all data collected from Argus eyetracking and creates several time and spatial series objects
def argusData(info, data, time, nwb):
    
    # Create inital table of all data
    df = makedataTable(info, data)

    # Column names for data to be extracted
    Gaze_Eyes = ["horz_gaze_coord", "vert_gaze_coord"]
    Gaze_Monitor = ["ET3S_horz_gaze_coord", "ET3S_vert_gaze_coord"]
    Pupils = ["pupil_diam"] # sometimes ["pupil_diameter"]
    headxyz = ["hdtrk_X", "hdtrk_Y", "hdtrk_Z"]
    headrotate = ["hdtrk_az", "hdtrk_el", "hdtrk_rl"]

    # Extracting all desired data from initial table
    eyetrack_data = extractdata(df, Gaze_Eyes)
    monitor_eyetracking_data = extractdata(df, Gaze_Monitor)
    pupil_data = extractdata(df, Pupils)
    pupil_diameters = []
    for diameters in pupil_data.tolist():
        pupil_diameters.append(diameters[0].split("/"))
    pupil_diameter_data = np.array(pupil_diameters)
    head_tracking_data_xyz = extractdata(df, headxyz)
    head_tracking_data_rotation = extractdata(df, headrotate)


    # Creating SpatialSeries Object
    eyetrack = SpatialSeries(
        name = "Eyetrack_Argus",
        description = 'Tracking position of eyes',
        data = compressData(eyetrack_data.astype(float)),
        timestamps = time,
        reference_frame = '(0,0) is bottom left corner'
    )
    # Creating Position object for SpatialSeries Object to be stored in
    eyePosition = Position(
        name = 'Eyetrack_Argus',
        spatial_series = eyetrack
    )

    # Creating SpatialSeries Object
    monitor_eyetrack = SpatialSeries(
        name = "Monitor_Eyetrack_Argus",
        description = "Tracking where on the monitor the eyes are looking",
        data = compressData(monitor_eyetracking_data.astype(float)),
        timestamps = time,
        reference_frame = '(0,0) is the center of the monitor'
    )
    # Creating Position object for SpatialSeries Object to be stored in
    monitorPosition = Position(
        name = 'Monitor_Eyetrack_Argus',
        spatial_series = monitor_eyetrack
    )
    
    # Creating TimeSeries Object
    pupil_diameters = TimeSeries(
        name = "Pupil_Diameters_Argus",
        description = "Pupil diameter(mm) extracted from both eyes. [left eye, right eye]",
        data = compressData(pupil_diameter_data.astype(float)),
        timestamps = time,
        unit = "millimeters",
    )

    # Creating SpatialSeries Object
    head_tracking_xyz = SpatialSeries(
        name ="Head_Location_Argus",
        description ='Tracking position of head using the following dimensions [x(cm), y(cm), z(cm)]. X is distance from the monitor, Y is left-right, Z is Up-Down',
        data = compressData(head_tracking_data_xyz.astype(float)),
        timestamps = time,
        reference_frame ='[0, 0, 0] is located at the tracker'
    )
    # Creating Position object for SpatialSeries Object to be stored in
    headPosition = Position(
        name = 'Head_Location_Argus',
        spatial_series = head_tracking_xyz
        )
    
    # Creating TimeSeries Object
    head_tracking_rotation = TimeSeries(
        name ="Head_Rotation_Argus",
        description =','.join(headrotate),
        data = compressData(head_tracking_data_rotation.astype(float)),
        timestamps = time,
        unit = 'degrees'
    )

    # Storing all raw data into acquisition
    totaldata = [pupil_diameters, head_tracking_rotation, eyePosition, monitorPosition, headPosition]
    for i in totaldata:
        nwb.add_acquisition(i)

# Takes all data from Eyelink eyetracking and creates several time and spatial series objects
def eyelinkData(info, data, time, nwb):
    
    # Create inital table of all data
    df = makedataTable(info, data)

    # Adding times as a column
    df['times'] = time

    # Removing all duplicate data
    header = getLabels(info)
    df_trimmed = df.drop_duplicates(subset=header[:-1], ignore_index = True)

    # Column names for data to be extracted
    leftEye = ['leftEyeX', 'leftEyeY']
    rightEye = ['rightEyeX', 'rightEyeY']
    LRpupils = ['leftPupilArea', 'rightPupilArea']
    pupilAngle = ['pixelsPerDegreesX','pixelsPerDegreesY']

    # Extracting all desired data from trimmed table
    left_eye_pos = extractdata(df_trimmed, leftEye)
    right_eye_pos = extractdata(df_trimmed, rightEye)
    pupil_size = extractdata(df_trimmed, LRpupils)
    pupil_angle = extractdata(df_trimmed, pupilAngle)
    times = extractdata(df_trimmed, ['times'])

    # Creating SpatialSeries Object
    lefteyetrack = SpatialSeries(
        name = "Left_eye_gaze",
        description = ','.join(leftEye),
        data = compressData(left_eye_pos.astype(float)),
        timestamps = times,
        reference_frame = 'placeholder'
    )
    # Creating Position object for SpatialSeries Object to be stored in
    leftEyePos = Position(
        name = "Left_eye_gaze",
        spatial_series = lefteyetrack
    )

    # Creating SpatialSeries Object
    righteyetrack = SpatialSeries(
        name = "Right_eye_gaze",
        description = ','.join(rightEye),
        data = compressData(right_eye_pos.astype(float)),
        timestamps = times,
        reference_frame = 'placeholder'
    )
    # Creating Position object for SpatialSeries Object to be stored in
    rightEyePos = Position(
        name = "Right_eye_gaze",
        spatial_series = righteyetrack
    )

    # Creating a TimeSeries Object
    pupil_diameters = TimeSeries(
        name = "Pupil_Diameters_EL",
        description = ','.join(LRpupils),
        data = compressData(pupil_size.astype(float)),
        timestamps = times,
        unit = "placeholder"
    )

    # Creating a TimeSeries Object
    pupil_rotation = TimeSeries(
        name = "Pupil_Rotation_EL",
        description = ','.join(pupilAngle),
        data = compressData(pupil_angle.astype(float)),
        timestamps = times, 
        unit = 'placeholder'
    )

    # Storing all raw data into acquisition
    total_data = [leftEyePos, rightEyePos, pupil_diameters, pupil_rotation]
    for i in total_data:
        nwb.add_acquisition(i)

# Creating device, electrode data, and ElectricalSeries from EEG stream of XDF file
def eegData(info, data, time, vhdr_list, nwb):

    # Creating Device
    device = nwb.create_device(
    name=info["name"][0], description=info["name"][0]
    )

    # Create custom column to hold all impedance values
    # nwb.add_electrode_column(name="impedances_1", description="all impedance values for run-001")
    # nwb.add_electrode_column(name="impedances_2", description="all impedance values for run-002")
    # nwb.add_electrode_column(name="impedances_FINAL", description="all impedance values for run-IMPTESTFINAL")

    # Getting all electrode group names
    electrode_group_names = getLabels(info)

    #gathering location data (coordinates)
    standard_df = pd.read_csv('standard_coordinates.csv', index_col=0)

    #gathering location data (brain area)
    location_dict={
    "Fp":"Frontal Pole",
    "AF":"Antero-Frontal",
    "F":"Frontal",
    "C":"Central",
    "P":"Parietal",
    "T":"Temporal",
    "O":"Occipital",
    "FC":"Frontal-Central",
    "CP":"Central-Pareital",
    "TP":"Temporal-Pareital",
    "FT":"Frontal-Temporal",
    "PO":"Pareital-Occipital",
    "I":"Inion"
    }

    # Getting all impedance values
    headers = ['File', 'Run' 'Electrode', 'Impedance(kohms)']
    # imp_dict = {}
    table = []

    for i in vhdr_list:
        labels, run_number, impedances, fname = getImps(i)
        row = [fname, run_number, labels, impedances]
        table.append(row)
        # df = pd.DataFrame(impedances, index=labels)
        # imp_dict['{}'.format(fname)] = df
    
    df2 = pd.DataFrame(table, columns=headers)
    runlist = list(df2['Run'])
    allimpvalues = []
    for i in runlist:
        impvalues = list(df2[df2['Run'] == i]['Impedance(kohms)'])
        allimpvalues.append(impvalues[0])

    # Create custom column to hold all impedance values
    nwb.add_electrode_column(name='allImpedances', description='Impedance values from {}'.format(runlist))

    #creating electrode groups with all the metadata
    electrode_counter = 0
    for i in electrode_group_names:
        electrode_group = nwb.create_electrode_group(
            name=info["name"][0] + " {}".format(i),
            description="desc",
            device=device,
            location=location_dict[i],
            )
    
        nwb.add_electrode(
            group=electrode_group,
            group_name=electrode_group.name,
            location=location_dict[i],
            x=standard_df.loc[i, 'x'],
            y=standard_df.loc[i, 'y'],
            z=standard_df.loc[i, 'z'],
            allImpedances=allimpvalues
        )
        electrode_counter += 1

    nwb.electrodes.to_dataframe()

    all_table_region = nwb.create_electrode_table_region(
        region=list(range(electrode_counter)),
        description="all electrodes",
    )
    
    #-------------------Adding EEG Data to NWB-------------------------------------------#

    eeg_data = data[:,:-1]
    colnames = ','.join(electrode_group_names[:-1])

    raw_electrical_series = ElectricalSeries(
        name = "ElectricalSeries",
        description = colnames,
        data = eeg_data,
        electrodes = all_table_region,
        timestamps = time
    )
    nwb.add_acquisition(raw_electrical_series)

#---------------------Time Anonymization----------------------------------------------#

def getTimeZero(streams, sname):
    s_info, s_data, s_time = getspeStream(streams, sname)
    if s_info['effective_srate'] > 0 or sname == 'StimLabels':
        try:
            time_zero = s_time[0]
        except Exception:
            time_zero = 0
    else:
        time_zero = 0
    return time_zero

def anonymizeTime(times, time_zero):
    new_times = []
    for time in times:
        new_time = time - time_zero
        new_times.append(new_time)
    return new_times
