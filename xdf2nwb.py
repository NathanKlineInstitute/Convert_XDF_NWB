from xdf2nwb_functions import *
from uuid import uuid4
from pynwb.file import Subject
import datetime

# function for finding vhdr files related to given xdf file
def readspevhdrfile(xdf):
    fname = os.path.basename(xdf)
    sub, ses, task = getSubSesTask(fname)
    spe_vhdr = glob.glob("/data2/Projects/NKI_RS2/MoBI/{}/{}*/raw/{}_{}*.vhdr".format(sub,ses,sub,ses))
    return spe_vhdr

#list of xdf and nwb files
xdf_list = glob.glob("/data2/Projects/NKI_RS2/MoBI/sub*/**/*.xdf.gz", recursive = True)
nwb_list = glob.glob("/data2/Projects/NKI_RS2/MoBI/NWB/*.nwb", recursive = True)

# finding xdf files that have not been converted to nwb files
not_converted = []
for i in xdf_list:
    nwb_path = '/data2/Projects/NKI_RS2/MoBI/NWB'
    fname = os.path.basename(i)
    nwbFname = fname.replace('_lsl.xdf.gz', '.nwb')
    nwbFile = os.path.join(nwb_path, nwbFname)

    if nwbFile not in nwb_list:
        not_converted.append(i)

# Loops through list of unconverted files and converts them
working_list = not_converted[-3:-1]
errors = []
time = datetime.datetime(1970, 1, 1)

for xdf_file in working_list:
    xdffname = os.path.basename(xdf_file)
    name = xdffname.split('_')
    streams, header = pyxdf.load_xdf(xdf_file)
    vhdr_list = readspevhdrfile(xdf_file)

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

    # Iterating through all the streams, extracting data and time to insert into nwbfile
    for istreams in streams:
        name = istreams['info']['name'][0]
        match name:
            case 'StimLabels':
                stimlabels(istreams['info'], istreams['time_series'], istreams['time_stamps'], nwbfile)
            case 'Argus_EyeTracker':
                argusData(istreams['info'], istreams['time_series'], istreams['time_stamps'], nwbfile)
            case 'EyeLink':
                eyelinkData(istreams['info'], istreams['time_series'], istreams['time_stamps'], nwbfile)
            case 'MindLogger':
                mindloggerData(istreams['info'], istreams['time_series'], istreams['time_stamps'], nwbfile)
            case 'BrainVision RDA':
                eegData(istreams['info'], istreams['time_series'], istreams['time_stamps'], vhdr_list, nwbfile)
            case 'OpenSignals':
                opensignalsData(istreams['info'], istreams['time_series'], istreams['time_stamps'], nwbfile)
            case 'cpCST':
                cstData(istreams['info'], istreams['time_series'], istreams['time_stamps'], nwbfile)
            case 'FaceVideo':
                video_raw(istreams['info'], istreams['time_series'], istreams['time_stamps'], nwbfile)
            case 'Audio':
                audio_raw(istreams['info'], istreams['time_series'], istreams['time_stamps'], nwbfile)
    
    # Writing to file
    nwbFileName = xdffname.replace('_lsl.xdf.gz', '.nwb')
    print(nwbFileName)
    print(nwbfile)
    sub, ses, task = getSubSesTask(xdffname)
    fullpath = '/data2/Projects/NKI_RS2/MobI/NWB/{}/{}/{}'.format(sub, ses, nwbFileName)
    if os.path.exists(fullpath) is False:
        os.makedirs(os.path.dirname(fullpath))
    with NWBHDF5IO(fullpath, 'w') as io:
        io.write(nwbfile)
    
