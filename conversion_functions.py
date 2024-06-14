#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri May  3 13:07:01 2024

@author: mislam
"""

from pynwb import NWBHDF5IO, NWBFile, TimeSeries
from pynwb.ecephys import LFP, ElectricalSeries
from pynwb.behavior import SpatialSeries, Position, EyeTracking, PupilTracking
import numpy as np
import pandas as pd
import pyxdf
import glob
import os
import re
import mne

def readXDFfile(sub,ses):
    xdf_dir = glob.glob("/data2/Projects/NKI_RS2/MoBI/{}/{}/**/*xdf*".format(sub, ses), recursive = True)
    xdf_dir_hr = []
    for i in xdf_dir:
        xdf_dir_hr.append(i[38:])
    print(*list(enumerate(xdf_dir_hr)),sep='\n')
    inp = input("Pick a file [0-{}]: ".format(len(xdf_dir_hr)-1))
    inp = int(inp)
    xdf_streams, xdf_header = pyxdf.load_xdf(xdf_dir[inp])
    return xdf_streams

def printallinfo(l):
    info_list = []
    for i in l:
        info_list.append([i['info']['name'][0], i['info']['effective_srate']])
    print(*info_list, sep='\n')

def xdffname(sub, ses, task):
    fname = "/data2/Projects/NKI_RS2/MoBI/{}/{}/lsl/{}_{}_{}_lsl.xdf.gz".format(sub,ses,sub,ses,task)
    return fname

def getxdftasks(task):
    xdf_list = glob.glob("/data2/Projects/NKI_RS2/MoBI/sub*/**/*task-{}*.xdf.gz".format(task), recursive = True)
    return xdf_list

def getSubSesTask(fname):
    split1 = '_ses'
    split2 = '_task'
    split3 = '_lsl'
    subSplit = fname.find(split1)
    sesSplit = fname.find(split2)
    taskSplit = fname.find(split3)
    sub = fname[0:subSplit]
    ses = fname[subSplit+1:sesSplit]
    task = fname[sesSplit+1:taskSplit]
    return sub, ses, task

def readspeXDFfile(sub,ses,task):
    fname = "/data2/Projects/NKI_RS2/MoBI/{}/{}/lsl/{}_{}_{}_lsl.xdf.gz".format(sub,ses,sub,ses,task)
    xs, xh = pyxdf.load_xdf(fname)
    return xs, fname

def readspevhdrfile(xdf):
    fname = os.path.basename(xdf)
    sub, ses, task = getSubSesTask(fname)
    #name = fname.split("_")
    spe_vhdr = glob.glob("/data2/Projects/NKI_RS2/MoBI/{}/{}*/raw/{}_{}*.vhdr".format(sub,ses,sub,ses))
    return spe_vhdr

def getLabels(info):
    info_labels = info['desc'][0]['channels'][0]['channel']
    colnames = []
    for i in info_labels:
        colnames.append(i['label'][0])
    return colnames

def getUnits(info):
    info_units = info['desc'][0]['channels'][0]['channel']
    units = []
    for i in info_units:
        units.append(i['unit'][0])
    return units

def getspeStream(streams, sname):
    for i in streams:
        if i['info']['name'][0] == sname:
            s_info = i['info']
            s_data = i['time_series']
            s_time = i['time_stamps']
            return s_info, s_data, s_time
        
def extractdata(df, list):
    extracted_data = df.loc[:, list]
    extracted_array = pd.DataFrame.to_numpy(extracted_data)
    return extracted_array
        
def makedataTable(info, data):
    headers = getLabels(info)
    df = pd.DataFrame(data, columns=headers)
    return df

def vhdrfix(file):
    fname = os.path.basename(file)
    f = open(file, 'r')
    l = f.readlines()
    f.close
    newfile = file.replace('.vhdr', '_FIXED.vhdr')
    fw = open(newfile, 'w')
    l[5] = 'DataFile={}\n'.format(fname.replace('vhdr', 'eeg'))
    l[6] = 'MarkerFile={}\n'.format(fname.replace('vhdr', 'vmrk'))
    for i in l:
        fw.write(i)
    fw.close()
    return newfile

def locdata(vhdr):
    raw_eeg = mne.io.read_raw_brainvision(vhdr, preload=True)
    raw_eeg_info = raw_eeg.info
    loc_data = raw_eeg_info['dig']
    electrode_group_names = raw_eeg.info.ch_names
    xyz_coor = []
    x = []
    y = []
    z = []
    for i in loc_data[3:67]:
        xyz_coor.append(i['r']*1000)
    xyz_coor = np.array(xyz_coor)
    for i in range(xyz_coor.shape[0]):
        x.append(xyz_coor[i][0])
        y.append(xyz_coor[i][1])
        z.append(xyz_coor[i][2])
    #return(loc_data)
    #print(*loc_data, sep='\n')
    #print(*enumerate(electrode_group_names), sep='\n')
    return xyz_coor, electrode_group_names
    #print(*enumerate(xyz_coor), sep='\n')

def nwb_init(fname, info):
    #Don't Use
    #Manually initialize nwb file
    filename = os.path.basename(fname)
    name = filename.split("_")

    nwbfile = NWBFile(
        session_description=name[2],
        identifier=name[0],
        session_start_time=info['meas_date'],
        experimenter= info['experimenter'],
        lab="C-BIN",
        institution="Nathan Kline Institute",
        experiment_description=name[2],
        session_id=name[1]
        )
    return nwbfile

def audio_raw(info, data, time, nwb):
    
    audio_data = data
    sampling_rate = info["effective_srate"]
    recorded_time = time

    #creating time series for audio
    audio = TimeSeries(
        name = "Audio",
        description = 'Audio Recording of task. Recorded at {} Hz'.format(sampling_rate),
        data = audio_data,
        unit = "",
        starting_time = recorded_time[0],
        rate = sampling_rate
        )
    nwb.add_acquisition(audio)
    #return audio

def video_raw(info, data, time, nwb):
    
    video_data = data
    frame_rate = info["effective_srate"]
    recorded_time = time

    #reorganizing data into a list of arrays where each array is a frame with the correct resolution
    frame_data = []

    for frame in video_data:
        frame_data.append(np.reshape(frame, [144,176]))

    #creating time series for video
    video = TimeSeries(
        name = "Video",
        description = 'Video Recording of task. Resolution of video is 176x144',
        data = frame_data,
        unit = "",
        starting_time = recorded_time[0],
        rate = frame_rate
        )
    nwb.add_acquisition(video)
    #return video

def stimlabels(info, data, time, nwb):
    
    stimlabel_data = np.array(data)
    stimlabel_timestamps = time

    #creating time series for stimlabels
    stimlabels = TimeSeries(
        name = "StimLabels",
        description = "Stimlabels",
        data = stimlabel_data,
        unit = "",
        timestamps = stimlabel_timestamps
        )
    nwb.add_acquisition(stimlabels)
    #return stimlabels

def argusData(info, data, time, nwb):
    #use argusData2
    #----------------All General Argus Eyetracking Data----------------------------#
    gaze_array = np.array(data)
    labels = ["current_time", "start_of_record", "Gaze_LAOI", "pupil_diameter", 
              "horz_gaze_coord", "vert_gaze_coord","hdtrk_X", "hdtrk_Y", "hdtrk_Z",
              "hdtrk_az", "hdtrk_el", "hdtrk_rl", "ET3S_scene_number", "ET3S_gaze_length",
              "ET3S_vert_gaze_coord", "ET3S_horz_gaze_coord", "eyelid_upper_vert", "eyelid_lower_vert",
              "blink_confidence", "XDAT", "LAOI_horz_gaze_coord", "LAOI_vert_gaze_coord"]
    gaze_array_labeled = [labels]

    #labeling all columns in gaze array
    for i in gaze_array:
        gaze_array_labeled.append(i)
        
    gaze_array = np.array(gaze_array_labeled)
    #time_array = gaze_array[1:,0].astype(float)
    time_array = time

    #------------------------Gaze Data (eyes)--------------------------------------#
    #pulling positional eye tracking data
    eyetrack_data = gaze_array[1:,[4,5]].astype(float)

    #creating spatial series for eye tracking 
    eyetrack = SpatialSeries(
        name = "Eyetrack_Argus",
        description = 'Tracking position of eyes',
        data = eyetrack_data,
        timestamps = time_array,
        reference_frame = '(0,0) is bottom left corner'
    )

    #------------------------Gaze Data (monitor)-----------------------------------#
    #pulling monitor eye tracking data
    monitor_eyetracking_data = gaze_array[1:,[14,15]].astype(float)

    #creating spatial series for monitor eye track
    monitor_eyetrack = SpatialSeries(
        name = "Monitor_Eyetrack_Argus",
        description = "Tracking where on the monitor the eyes are looking",
        data = monitor_eyetracking_data,
        timestamps = time_array,
        reference_frame = '(0,0) is the center of the monitor'
        )


    #-----------------------Pupil Data---------------------------------------------#
    #pulling pupil diameter data
    pupil_data = gaze_array[1:,3]
    pupil_diameters = []

    #separating the left and right pupil data
    for diameters in pupil_data:
        pupil_diameters.append(diameters.split("/"))

    pupil_diameter_data = np.array(pupil_diameters)

    #creating pupil data time series
    pupil_diameters = TimeSeries(
        name = "Pupil_Diameters_Argus",
        description = "Pupil diameter(mm) extracted from both eyes. [left eye, right eye]",
        data = pupil_diameter_data,
        timestamps = time_array,
        unit = "millimeters",
    )

    #-----------------------Head Tracking Data XYZ---------------------------------#
    #pulling cartesian head tracking data
    head_tracking_data_xyz = gaze_array[1:,6:9].astype(float)

    #creating spatial series for head tracking
    head_tracking_xyz = SpatialSeries(
        name ="Head_Location_Argus",
        description ='Tracking position of head using the following dimensions [x(cm), y(cm), z(cm)]. X is distance from the monitor, Y is left-right, Z is Up-Down',
        data = head_tracking_data_xyz,
        timestamps = time_array,
        reference_frame ='[0, 0, 0] is located at the tracker'
        )


    #-----------------------Head Tracking Data Rotation----------------------------#
    #pulling rotational head tracking data
    head_tracking_data_rotation = gaze_array[1:,9:12].astype(float)

    #creating spatial series for head tracking
    head_tracking_rotation = SpatialSeries(
        name ="Head_Rotation_Argus",
        description ='Tracking position of head using the following dimensions [azimuth (degrees), elevation (degrees), roll (degrees)]',
        data = head_tracking_data_rotation,
        timestamps = time_array,
        reference_frame ='[-180, 0, 0] is the head upright and looking straight ahead at the monitor'
        )
    
    totaldata = [eyetrack, monitor_eyetrack, pupil_diameters, head_tracking_xyz, head_tracking_rotation]
    
    for i in totaldata:
        nwb.add_acquisition(i)

def argusData2(info, data, time, nwb):
    df = makedataTable(info, data)
    Gaze_Eyes = ["horz_gaze_coord", "vert_gaze_coord"]
    Gaze_Monitor = ["ET3S_horz_gaze_coord", "ET3S_vert_gaze_coord"]
    if 'pupil_diam' in list(df.columns):
        Pupils = ["pupil_diam"]
    else:
        Pupils = ["pupil_diameters"]
    headxyz = ["hdtrk_X", "hdtrk_Y", "hdtrk_Z"]
    headrotate = ["hdtrk_az", "hdtrk_el", "hdtrk_rl"]

    eyetrack_data = extractdata(df, Gaze_Eyes)
    monitor_eyetracking_data = extractdata(df, Gaze_Monitor)
    pupil_data = extractdata(df, Pupils)
    pupil_diameters = []
    for diameters in pupil_data.tolist():
        pupil_diameters.append(diameters[0].split("/"))
    pupil_diameter_data = np.array(pupil_diameters)
    head_tracking_data_xyz = extractdata(df, headxyz)
    head_tracking_data_rotation = extractdata(df, headrotate)

    eyetrack = SpatialSeries(
        name = "Eyetrack_Argus",
        description = ','.join(Gaze_Eyes),
        data = eyetrack_data.astype(float),
        timestamps = time,
        reference_frame = '(0,0) is bottom left corner'
    )

    monitor_eyetrack = SpatialSeries(
        name = "Monitor_Eyetrack_Argus",
        description = ','.join(Gaze_Monitor),
        data = monitor_eyetracking_data.astype(float),
        timestamps = time,
        reference_frame = '(0,0) is the center of the monitor'
    )
    
    pupil_diameters = TimeSeries(
        name = "Pupil_Diameters_Argus",
        description = "left eye,right eye",
        data = pupil_diameter_data,
        timestamps = time,
        unit = "mm,mm",
    )

    head_tracking_xyz = SpatialSeries(
        name ="Head_Location_Argus",
        description =','.join(headxyz),
        data = head_tracking_data_xyz.astype(float),
        timestamps = time,
        reference_frame ='[0, 0, 0] is located at the tracker'
    )
    
    head_tracking_rotation = SpatialSeries(
        name ="Head_Rotation_Argus",
        description =','.join(headrotate),
        data = head_tracking_data_rotation.astype(float),
        timestamps = time,
        reference_frame ='[-180, 0, 0] is the head upright and looking straight ahead at the monitor'
    )

    totaldata = [eyetrack, monitor_eyetrack, pupil_diameters, head_tracking_xyz, head_tracking_rotation]
    for i in totaldata:
        nwb.add_acquisition(i)

def eyelinkData(info, data, time, nwb):
    #-----------------------Cleaning up Eyelink Data----------------------------#
    eyelink_labels = info['desc'][0]['channels'][0]['channel']
    header = []
    for i in eyelink_labels:
        header.append(i['label'][0])
    df = pd.DataFrame(data, columns=header)
    df['times'] = time
    df_trimmed = df.drop_duplicates(subset=header[:-1], ignore_index= True)

    times = df_trimmed['times'].tolist()

    #-----------------------Left Eye Positional Data----------------------------#
    #pulling left eye data
    left_eye_pos = df_trimmed.loc[:,['leftEyeX', 'leftEyeY']]
    left_eye_pos_arr = pd.DataFrame.to_numpy(left_eye_pos)

    lefteyetrack = SpatialSeries(
        name = "Left_eye_gaze",
        description = ','.join(list(left_eye_pos.columns)),
        data = left_eye_pos_arr,
        timestamps = times,
        reference_frame = 'placeholder'
    )

    #-----------------------Right Eye Positional Data----------------------------#
    #pulling right eye data
    right_eye_pos = df_trimmed.loc[:,['rightEyeX', 'rightEyeY']]
    right_eye_pos_arr = pd.DataFrame.to_numpy(right_eye_pos)

    righteyetrack = SpatialSeries(
        name = "Right_eye_gaze",
        description = ','.join(list(right_eye_pos.columns)),
        data = right_eye_pos_arr,
        timestamps = times,
        reference_frame = 'placeholder'
    )

    #-----------------------Pupil Data----------------------------#
    #pulling pupil size data
    pupil_size = df_trimmed.loc[:, ['leftPupilArea', 'rightPupilArea']]
    pupil_size_arr = pd.DataFrame.to_numpy(pupil_size)

    pupil_diameters_eyelink = TimeSeries(
        name = "Pupil_Diameters_Eyelink",
        description = ','.join(list(pupil_size.columns)),
        data = pupil_size_arr,
        timestamps = times,
        unit = "placeholder",
    )

    #------------------------------Eye Rotation-----------------------#
    #pulling rotation data
    pupil_angle = df_trimmed.loc[:, ['pixelsPerDegreesX','pixelsPerDegreesY']]
    pupil_angle_arr = pd.DataFrame.to_numpy(pupil_angle)

    pupil_rotation_eyelink = SpatialSeries(
        name = "Pupil_Rotation_Eyelink",
        description = ','.join(list(pupil_angle.columns)),
        data = pupil_angle_arr,
        timestamps = times,
        reference_frame = "placeholder",
    )

    total_data = [lefteyetrack, righteyetrack, pupil_diameters_eyelink, pupil_rotation_eyelink]

    for i in total_data:
        nwb.add_acquisition(i)

def mindloggerData(info, data, time, nwb):
    #pulling mindloggger data
    header = getLabels(info)
    mindlogger_data = pd.DataFrame(data, columns=header)
    xy = mindlogger_data.loc[:, ['x','y']]
    xy = pd.DataFrame.to_numpy(xy)

    mindlogger = SpatialSeries(
        name = "Mindlogger",
        description = "x,y",
        data = xy.astype(float),
        timestamps = time,
        reference_frame = "placeholder"
    )
    nwb.add_acquisition(mindlogger)

def opensignalsData(info, data, time, nwb):
    #use opensignalsData3
    #--------------------------Opensignals Data-----------------------#
    header = getLabels(info)    
    allopensignalsData = pd.DataFrame(data, columns=header)

    #ECG0
    ecg0 = allopensignalsData.loc[:, ['ECG0']]
    ecg0 = pd.DataFrame.to_numpy(ecg0)

    ecg = TimeSeries(
        name = 'ECG',
        description = 'Electrocardiography recording of subject',
        data = ecg0,
        timestamps = time,
        unit = 'mV'
    )

    #EDA1
    eda1 = allopensignalsData.loc[:, ['EDA1']]
    eda1 = pd.DataFrame.to_numpy(eda1)

    eda = TimeSeries(
        name = 'EDA',
        description = 'Electrodermal activity of subject',
        data = eda1,
        timestamps = time,
        unit = 'uS'
    )

    #EMG2
    emg2 = allopensignalsData.loc[:, ['EMG2', 'EMG3']]
    emg2 = pd.DataFrame.to_numpy(emg2)

    emg = TimeSeries(
        name = 'EMG',
        description = 'Electromyography recording of subject [left, right]',
        data = emg2,
        timestamps = time,
        unit = 'mV'
    )

    #RESPIRATION4
    resp4 = allopensignalsData.loc[:, ['RESPIRATION4']]
    resp4 = pd.DataFrame.to_numpy(resp4)

    resp = TimeSeries(
        name = 'Respiration',
        description = 'respiration recording of subject',
        data = resp4,
        timestamps = time,
        unit = 'V'
    )

    #XYZ5
    xyz5 = allopensignalsData.loc[:, ['XYZ5', 'XYZ6', 'XYZ7']]
    xyz5 = pd.DataFrame.to_numpy(xyz5)

    xyz = TimeSeries(
        name = 'XYZ',
        description = "Accelerometer recordings of subject's dominant hand",
        data = xyz5,
        timestamps = time,
        unit = 'g'
    )

    total_data = [ecg, eda, emg, resp, xyz]
    for i in total_data:
        nwb.add_acquisition(i)

def opensignalsData2(info, data, time, nwb):
    #use opensignalsData3
    df = makedataTable(info, data)
    headers = getLabels(info)
    units = getUnits(info)

    one = df.loc[:, [headers[1]]]
    one = pd.DataFrame.to_numpy(one)

    two = df.loc[:, [headers[2]]]
    two = pd.DataFrame.to_numpy(two)
    
    three = df.loc[:, [headers[3]]]
    three = pd.DataFrame.to_numpy(three)

    four = df.loc[:, [headers[4]]]
    four = pd.DataFrame.to_numpy(four)

    first = TimeSeries(
        name = headers[1][:-1],
        description = headers[1][:-1],
        data = one,
        timestamps = time,
        unit = units[1]
    )

    second = TimeSeries(
        name = headers[2][:-1],
        description = headers[2][:-1],
        data = two,
        timestamps = time,
        unit = units[2]
    )

    third = TimeSeries(
        name = headers[3][:-1],
        description = headers[3][:-1],
        data = three,
        timestamps = time,
        unit = units[3]
    )

    fourth = TimeSeries(
        name = headers[4][:-1],
        description = headers[4][:-1],
        data = four,
        timestamps = time,
        unit = units[4]
    )

    total_data  = [first, second, third, fourth]
    for i in total_data:
        nwb.add_acquisition(i)

def opensignalsData3(info, data, time, nwb):
    headers = getLabels(info)
    headers.remove(headers[0])
    units = getUnits(info)
    units.remove(units[0])
    colnames = ','.join(headers)
    unitnames = ','.join(units)

    opensignals = TimeSeries(
        name = 'allOpenSignalsData',
        description = colnames,
        data = np.delete(data, [0], axis=1),
        timestamps = time,
        unit = unitnames
    )

    nwb.add_acquisition(opensignals)

def cstData(info, data, time, nwb):
    headers = getLabels(info)
    units = getUnits(info)
    colnames = ','.join(headers)
    unitnames = ','.join(units)

    cst = TimeSeries(
        name = 'allCSTdata',
        description = colnames,
        data = data,
        timestamps = time,
        unit = unitnames
    )

    nwb.add_acquisition(cst)


def eegData(info, data, time, vhdr_info, vhdr_imp, nwb):
    #--------------------------Device Creation-----------------------#
    device = nwb.create_device(
    name=info["name"][0], description=info["name"][0]
    )
    #create custom column to hold all impedance values
    nwb.add_electrode_column(name="impedances", description="all impedance values")

    #gathering location data (coordinates)
    keys = list(vhdr_info.keys())
    loc_data = vhdr_info[keys[0]]['dig']
    xyz_coor = []
    for i in loc_data[3:67]:
        xyz_coor.append(i['r']*1000)
    xyz_coor = np.array(xyz_coor)

    #gathering location data (brain area)
    electrode_group_names = getLabels(info)
    locations = []
    f_locations = []

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

    #removing numbers from electrode group names
    for names in electrode_group_names[:-1]:
        name = re.sub("[0-9,z]",'',names)
        locations.append(name)

    #using dictionary to change initials to location name
    for i in locations:
        if i in location_dict.keys():
            f_locations.append(location_dict[i])
    else:
        f_locations.append(i)

    imp_values = []
    for i in vhdr_imp.keys():
        row = []
        for j in electrode_group_names[:-1]:
            row.append(vhdr_imp[i][j]['imp'])
        imp_values.append(row)
    
    imp_values = pd.DataFrame(imp_values, index=vhdr_imp.keys(), columns=electrode_group_names[:-1])
    
    #creating electrode groups with all the metadata
    electrode_counter = 0
    for i in range(data.shape[1] - 1):
        electrode_group = nwb.create_electrode_group(
            name=info["name"][0] + " {}".format(electrode_group_names[i]),
            description="desc",
            device=device,
            location=f_locations[i],
            )
    
        nwb.add_electrode(
            group=electrode_group,
            group_name=electrode_group.name,
            location=f_locations[i],
            x=xyz_coor[i][0],
            y=xyz_coor[i][1],
            z=xyz_coor[i][2],
            impedances=imp_values[electrode_group_names[i]]
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
