from conversion_functions import *
import pprint
import datetime
from uuid import uuid4

spe_xdf_task_list = getxdftasks('spirals')

working_list = spe_xdf_task_list[-5:]
#print(*spirals_list, sep='\n')

#streams, header = pyxdf.load_xdf(spirals_list[-2])
#printallinfo(streams)
#m_info, m_data, m_times = getspeStream(streams, 'MindLogger')
#df = makedataTable(m_info, m_data)
#pprint.pprint(m_info)
#pprint.pprint(m_data)

errors = []

for i in working_list:
    fname = os.path.basename(i)
    streams, header = pyxdf.load_xdf(i)
    time_zero = getTimeZero(streams, 'MindLogger')

    #reading all vhdr files associated with xdf file
    vhdr_list = readspevhdrfile(i)
    raw_info = {}
    raw_imp = {}
    for j in range(len(vhdr_list)):
        filename = os.path.basename(vhdr_list[j])
        filename = filename.replace('.vhdr', '')
        filename = filename.split('_')
        name = filename[2]
        try:
            raw_data = mne.io.read_raw_brainvision(vhdr_list[j], preload=True)
            raw_info['info_{}'.format(name)] = raw_data.info
            raw_imp['{}'.format(name)] = raw_data.impedances
        except Exception:
            errors.append(vhdr_list[j])
            pass
    keys = list(raw_info.keys())

    #Initializing NWB File
    #nwbfile = nwb_init(i, raw_info[keys[0]])
    name = fname.split("_")
    nwbfile = NWBFile(
        session_description=name[2],
        identifier=str(uuid4()),
        session_start_time=datetime.datetime(1970, 1, 1),
        lab="C-BIN",
        institution="Nathan Kline Institute",
        experiment_description=name[2],
        session_id=name[1]
    )

    #Getting all relavent info, data, and times to import into nwb file based on stream names
    for k in streams:
        name = k['info']['name'][0]
        match name:
            case 'StimLabels':
                new_times_s = anonymizeTime(k['time_stamps'], time_zero)
                stimlabels(k['info'], k['time_series'], new_times_s, nwbfile)
            case 'Argus_Eye_Tracker':
                new_times_a = anonymizeTime(k['time_stamps'], time_zero)
                argusData2(k['info'], k['time_series'], new_times_a, nwbfile)
            case 'EyeLink':
                new_times_e = anonymizeTime(k['time_stamps'], time_zero)
                eyelinkData(k['info'], k['time_series'], new_times_e, nwbfile)
            case 'MindLogger':
                if k['info']['effective_srate'] > 0:
                    new_times_m = anonymizeTime(k['time_stamps'], time_zero)
                    mindloggerData(k['info'], k['time_series'], new_times_m, nwbfile)
            case 'BrainVision RDA':
                new_times_b = anonymizeTime(k['time_stamps'], time_zero)
                eegData(k['info'], k['time_series'], new_times_b, raw_info, raw_imp, nwbfile)
            case 'OpenSignals':
                if k['info']['effective_srate'] > 0:
                    new_times_o = anonymizeTime(k['time_stamps'], time_zero)
                    opensignalsData3(k['info'], k['time_series'], new_times_o, nwbfile)

    #writing to nwb file
    nwbfname = fname.replace('_lsl.xdf.gz', '.nwb')
    print(nwbfname)
    print(nwbfile)
    # print(type(nwbfile.session_start_time))
    # print(*nwbfile.acquisition['allOpenSignalsData'].timestamps[:10], sep='\n')
    # for i in list(nwbfile.acquisition.keys()):
        # print(i)
        # print(*nwbfile.acquisition[i].timestamps[:10], sep='\n')
    with NWBHDF5IO('/data2/Projects/NKI_RS2/MoBI/NWB/{}'.format(nwbfname), "w") as io:
        io.write(nwbfile)

print('Problematic vhdr files')
print(*errors, sep='\n')
