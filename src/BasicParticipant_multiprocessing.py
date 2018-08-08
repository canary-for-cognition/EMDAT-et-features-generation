"""
UBC Eye Movement Data Analysis Toolkit (EMDAT), Version 3
Created on 2014-09-16

Sample code showing how to instantiate the "Participant" class for a given experiment (multiprocessing version).

Authors: Sebastien Lalle (creator), Samad Kardan.
Institution: The University of British Columbia.
"""

from math import ceil, floor
from multiprocessing import Process, Queue
import os.path

params=__import__('params')
from EMDAT_core.data_structures import *
from EMDAT_core.Participant import *
from EMDAT_core.Recording import *
from EMDAT_core.AOI import AOI
from EMDAT_core.Scene import Scene
from EMDAT_core.utils import *

from EMDAT_eyetracker.TobiiV2Recording import TobiiV2Recording
from EMDAT_eyetracker.TobiiV3Recording import TobiiV3Recording
from EMDAT_eyetracker.SMIRecording import SMIRecording


class BasicParticipant(Participant):
    """
    This is a sample child class based on the Participant class that implements all the
    placeholder methods in the Participant class for a basic project
    """
    def __init__(self, rec, pid, segfile, log_time_offset = None, aoifile = None, prune_length= None,
                 require_valid_segs = True, auto_partition_low_quality_segments = False, rpsdata = None, export_pupilinfo = False,
                 disjoint_window = False, padding = 0, across_tasks = False, tasks_to_include = 0):
        """Inits BasicParticipant class
        Args:
            pid: Participant id

            eventfile: a string containing the name of the "Event-Data.tsv" file for this participant

            datafile: a string containing the name of the "All-Data.tsv" file for this participant

            fixfile: a string containing the name of the "Fixation-Data.tsv" file for this participant

            segfile: a string containing the name of the '.seg' file for this participant

            log_time_offset: If not None, an integer indicating the time offset between the
                external log file and eye tracking logs

            aoifile: If not None, a string containing the name of the '.aoi' file
                with definitions of the "AOI"s.

            prune_length: If not None, an integer that specifies the time
                interval (in ms) from the beginning of each Segment in which
                samples are considered in calculations.  This can be used if,
                for example, you only wish to consider data in the first
                1000 ms of each Segment. In this case (prune_length = 1000),
                all data beyond the first 1000ms of the start of the "Segment"s
                will be disregarded.

            auto_partition_low_quality_segments: a boolean indicating whether EMDAT should
                split the "Segment"s which have low sample quality, into two new
                sub "Segment"s discarding the largest gap of invalid samples.

            rpsdata: rest pupil sizes for all scenes if available

        Yields:
            a BasicParticipant object
        """


        Participant.__init__(self, pid, segfile, log_time_offset, aoifile, prune_length,
                 require_valid_segs, auto_partition_low_quality_segments, rpsdata)   #calling the Participant's constructor

        print "Participant \""+str(pid)+"\"..."

        self.features={}
        scenelist,self.numofsegments = partition(segfile, prune_length, disjoint_window, padding, across_tasks)
        if self.numofsegments == 0:
            print("No segments found.")
            self.whole_scene = None
            return
        if (across_tasks):
            print(scenelist)
            scenelist,self.numofsegments = select_tasks(scenelist, tasks_to_include)
            print(scenelist)
        if aoifile is not None:
            aois = read_aois(aoifile)
        else:
            aois = None

        self.features['numofsegments'] = self.numofsegments

        if params.VERBOSE != "QUIET":
            print "Generating features..."
        if (len(rec.all_data) == 0):
            print("WRONG")
            print("WRONG")
            print("WRONG")

        self.segments, self.scenes = rec.process_rec(scenelist = scenelist,aoilist = aois,prune_length = prune_length, require_valid_segs = require_valid_segs,
                                                     auto_partition_low_quality_segments = auto_partition_low_quality_segments, rpsdata = rpsdata, export_pupilinfo=export_pupilinfo,
                                                     disjoint_window = disjoint_window, padding = padding)
        if (self.segments == []):
            print("All segments are too short")
            self.whole_scene = None
            return

        # Don't need that for the current task
        all_segs = sorted(self.segments, key=lambda x: x.start)
        self.whole_scene = Scene(str(pid)+'_allsc',[],rec.all_data,rec.fix_data, saccade_data = rec.sac_data, event_data = rec.event_data, Segments = all_segs, aoilist = aois,prune_length = prune_length, require_valid = require_valid_segs, export_pupilinfo=export_pupilinfo )
        if (across_tasks):
            self.scenes = []
        self.scenes.insert(0,self.whole_scene)

        #Clean memory
        for sc in self.scenes:
            sc.clean_memory()
        #rec.clean_memory()

        if params.VERBOSE != "QUIET":
            print "Done!"

def select_tasks(scenelist, tasks_to_include):
    included_tasks = {}
    task_names = ['3', '5', '9', '11', '18', '20', '27', '28',
                  '30', '60', '62', '66', '72', '74', '76']
    for task in task_names:
        if (tasks_to_include > 0):
            included_tasks[task] = scenelist[task]
            tasks_to_include -= 1
        else:
            break
    return included_tasks, len(included_tasks)

def read_participants_Basic(q, datadir, user_list, pids, prune_length = None, aoifile = None, log_time_offsets=None,
                          require_valid_segs = True, auto_partition_low_quality_segments = False, rpsfile = None, export_pupilinfo = False,
                          disjoint_window = False, across_tasks = False, tasks_to_include = 0, time_windows = []):
    """Generates list of Participant objects. Relevant information is read from input files

    Args:
        q: Queue to which all processes must add return values.

        datadir: directory with user data (including "All-Data.tsv", "Fixation-Data.tsv", "Event-Data.tsv" files)
        for all participants

        user_list: list of user recordings (files extracted for one participant from Tobii studio)

        pids: User ID that is used in the external logs (can be different from above but there should be a 1-1 mapping)

        prune_length: If not None, an integer that specifies the time
            interval (in ms) from the beginning of each Segment in which
            samples are considered in calculations.  This can be used if,
            for example, you only wish to consider data in the first
            1000 ms of each Segment. In this case (prune_length = 1000),
            all data beyond the first 1000ms of the start of the "Segment"s
            will be disregarded.

        aoifile: If not None, a string containing the name of the '.aoi' file
            with definitions of the "AOI"s.

        log_time_offset: If not None, an integer indicating the time offset between the
            external log file and eye tracking logs

        require_valid_segs: a boolean determining whether invalid "Segment"s
            will be ignored when calculating the features or not. default = True

        auto_partition_low_quality_segments: a boolean indicating whether EMDAT should
            split the "Segment"s which have low sample quality, into two new
            sub "Segment"s discarding the largest gap of invalid samples.

        rpsfile: If not None, a string containing the name of the '.tsv' file
            with rest pupil sizes for all scenes and for each user.

    Returns:
        a list Participant objects (in queue)
    """
    recordings_dict = {}
    if log_time_offsets == None:    #setting the default offset which is 1 sec
        log_time_offsets = [0]*len(pids)

    for rec,pid,offset in zip(user_list,pids,log_time_offsets):
        #extract pupil sizes for the current user. Set to None if not available

        if params.EYETRACKERTYPE == "TobiiV2":
            allfile = datadir+'/P'+str(rec)+'-All-Data.tsv'
            fixfile = datadir+'/P'+str(rec)+'-Fixation-Data.tsv'
            evefile = datadir+'/P'+str(rec)+'-Event-Data.tsv'
            sacfile = None
            segfile = datadir+'/P'+str(rec)+'.seg'
        elif params.EYETRACKERTYPE == "TobiiV3":
            allfile = "{dir}/MMD Study 1_Rec {rec}.tsv".format(dir=datadir, rec=rec)
            fixfile = "{dir}/MMD Study 1_Rec {rec}.tsv".format(dir=datadir, rec=rec)
            sacfile = "{dir}/MMD Study 1_Rec {rec}.tsv".format(dir=datadir, rec=rec)
            evefile = "{dir}/MMD Study 1_Rec {rec}.tsv".format(dir=datadir, rec=rec)
            segfile = "{dir}/Segs/{rec}.seg".format(dir=datadir, rec=rec)
            aoifile = "{dir}/aois_refined/dynamic_{rec}.aoi".format(dir=datadir, rec=rec)
        elif params.EYETRACKERTYPE == "SMI":
            allfile = "{dir}/SMI_Sample_{rec}_Samples.txt".format(dir=datadir, rec=rec)
            fixfile = "{dir}/SMI_Sample_{rec}_Events.txt".format(dir=datadir, rec=rec)
            sacfile = "{dir}/SMI_Sample_{rec}_Events.txt".format(dir=datadir, rec=rec)
            evefile = "{dir}/SMI_Sample_{rec}_Events.txt".format(dir=datadir, rec=rec)
            segfile = "{dir}/SMI_Sample_{rec}.seg".format(dir=datadir, rec=rec)

        if params.VERBOSE != "QUIET":
            print "Reading input files:"
            print "--Scenes/Segments file: "+segfile
            print "--Eye tracking samples file: "+allfile
            print "--Fixations file: "+fixfile
            print "--Saccades file: "+sacfile if sacfile is not None else "--No saccades file"
            print "--Events file: "+evefile if evefile is not None else "--No events file"
            print "--AOIs file: "+aoifile if aoifile is not None else "--No AOIs file"
            print

        if params.EYETRACKERTYPE == "TobiiV2":
            rec = TobiiRecording(allfile, fixfile, event_file=sacfile, media_offset=params.MEDIA_OFFSET , segfile=segfile, aoifile = aoifile)
        elif params.EYETRACKERTYPE == "TobiiV3":
            rec = TobiiV3Recording(allfile, fixfile, saccade_file=sacfile, event_file=evefile, media_offset=params.MEDIA_OFFSET, segfile=segfile, aoifile = aoifile)
        elif params.EYETRACKERTYPE == "SMI":
            rec = SMIRecording(allfile, fixfile, saccade_file=sacfile, event_file=evefile, media_offset=params.MEDIA_OFFSET)
        else:
            raise Exception("Unknown eye tracker type.")
        recordings_dict[pid] = rec
        print("PID:%d, ALL_data size %d" % (pid, len(rec.all_data)))

    rpsdata = read_rest_pupil_sizes()
    if (disjoint_window):
        participants_window_lists = {}
        for window in time_windows:
            participants_window_lists[window] = {}
            for i in range(0, 59001 / window):
                participants_window_lists[window][i] = []
                participants = []
                for pid in pids:
                    participants_window_lists[window][i] = {}

                    if rpsdata != None:
                        currpsdata = rpsdata["P%d" % (pid)]
                    else:
                        currpsdata = None

                    if os.path.exists(allfile):
                        print("PID:%d inside loop, ALL_data size %d" % (pid, len(recordings_dict[pid].all_data)))

                        p = BasicParticipant(recordings_dict[pid], pid, recordings_dict[pid].segfile, log_time_offset = offset,
                                            aoifile=recordings_dict[pid].aoifile, prune_length = window, require_valid_segs = require_valid_segs,
                                            auto_partition_low_quality_segments = auto_partition_low_quality_segments, rpsdata = currpsdata,
                                            disjoint_window = disjoint_window, padding = window * i, across_tasks = False)
                        if (p.numofsegments != 0):
                            participants.append(p)
                    else:
                        print("Error reading participant files for: %d" % pid)
                participants_window_lists[window][i] = participants
        q.put(participants_window_lists)
    elif(not across_tasks):
        participants_lists = {}
        for i in range(1, 59001 / 1000):
            participants_lists[i] = []
            participants = []
            for pid in pids:
                if rpsdata != None:
                    currpsdata = rpsdata["P%d" % (pid)]
                else:
                    currpsdata = None
                if os.path.exists(allfile):
                    print("PID:%d inside loop, ALL_data size %d" % (pid, len(recordings_dict[pid].all_data)))

                    p = BasicParticipant(recordings_dict[pid], pid, recordings_dict[pid].segfile, log_time_offset = offset,
                                        aoifile=recordings_dict[pid].aoifile, prune_length = 1000 * i, require_valid_segs = require_valid_segs,
                                        auto_partition_low_quality_segments = auto_partition_low_quality_segments, rpsdata = currpsdata,
                                        disjoint_window = False, padding = 0, across_tasks = across_tasks)
                    if (p.numofsegments != 0):
                        participants.append(p)
                else:
                    print("Error reading participant files for: %d" % pid)
            participants_lists[i] = participants
        q.put(participants_lists)
    else:
        participants_lists = {}
        for i in range(1, 16):
            participants_lists[i] = []
            participants = []
            for pid in pids:
                if rpsdata != None:
                    currpsdata = rpsdata["P%d" % (pid)]
                else:
                    currpsdata = None
                if os.path.exists(allfile):
                    print("PID:%d inside loop, ALL_data size %d" % (pid, len(recordings_dict[pid].all_data)))

                    p = BasicParticipant(recordings_dict[pid], pid, recordings_dict[pid].segfile, log_time_offset = offset,
                                            aoifile=recordings_dict[pid].aoifile, prune_length = None, require_valid_segs = require_valid_segs,
                                        auto_partition_low_quality_segments = auto_partition_low_quality_segments, rpsdata = currpsdata,
                                        disjoint_window = False, padding = 0, across_tasks = across_tasks, tasks_to_include = i)
                    if (p.numofsegments != 0):
                        participants.append(p)
                else:
                    print("Error reading participant files for: %d" % pid)
            participants_lists[i] = participants
        q.put(participants_lists)

    return

def read_participants_Basic_multiprocessing(nbprocesses, datadir, user_list, pids, prune_length = None, aoifile = None, log_time_offsets = None,
                          require_valid_segs = True, auto_partition_low_quality_segments = False, rpsfile = None, export_pupilinfo = False,
                          disjoint_window = False, padding = 0, across_tasks = False, time_windows = []):
    """Generates list of Participant objects in parallel computing. Relevant information is read from input files

    Args:
        nbprocesses: number of processes to run in parallel (number of CPU cores is a good option).

        datadir: directory with user data (including "All-Data.tsv", "Fixation-Data.tsv", "Event-Data.tsv" files)
        for all participants

        user_list: list of user recordings (files extracted for one participant from Tobii studio)

        pids: User ID that is used in the external logs (can be different from above but there should be a 1-1 mapping)

        prune_length: If not None, an integer that specifies the time
            interval (in ms) from the beginning of each Segment in which
            samples are considered in calculations.  This can be used if,
            for example, you only wish to consider data in the first
            1000 ms of each Segment. In this case (prune_length = 1000),
            all data beyond the first 1000ms of the start of the "Segment"s
            will be disregarded.

        aoifile: If not None, a string containing the name of the '.aoi' file
            with definitions of the "AOI"s.

        log_time_offset: If not None, an integer indicating the time offset between the
            external log file and eye tracking logs

        require_valid_segs: a boolean determining whether invalid "Segment"s
            will be ignored when calculating the features or not. default = True

        auto_partition_low_quality_segments: a boolean indicating whether EMDAT should
            split the "Segment"s which have low sample quality, into two new
            sub "Segment"s discarding the largest gap of invalid samples.

        rpsfile: If not None, a string containing the name of the '.tsv' file
            with rest pupil sizes for all scenes and for each user.

        disjoint_window: if true, use padding to pad the beginning of the segments
            to compute features within the window

        padding: in ms, by how much the segments should be padded
    Returns:
        a list Participant objects
    """

    q = Queue()
    listprocess = []
    participants = []

    if nbprocesses < 1:
        nbprocesses = 1
    if nbprocesses > len(user_list):
        nbprocesses = len(user_list)
    for i in range(0, nbprocesses): #create a sublist of participants for each process
        user_listsplit = chunks(user_list, nbprocesses)
        pidssplit = chunks(pids, nbprocesses)
        log_time_offsets_list = chunks(log_time_offsets, nbprocesses) if log_time_offsets is not None else None

    print user_listsplit
    try:
        for i in range(0, nbprocesses):
            if log_time_offsets is None:
			    p = Process(target=read_participants_Basic, args=(q, datadir, user_listsplit[i], pidssplit[i], prune_length, aoifile, log_time_offsets,
                          require_valid_segs, auto_partition_low_quality_segments, rpsfile, export_pupilinfo, disjoint_window,  across_tasks, time_windows))
            else:
			    p = Process(target=read_participants_Basic, args=(q, datadir, user_listsplit[i], pidssplit[i], prune_length, aoifile, log_time_offsets_list[i],
                          require_valid_segs, auto_partition_low_quality_segments, rpsfile, export_pupilinfo, disjoint_window,  across_tasks, time_windows))

            listprocess.append(p)
            p.start() # start the process

        for i in range(0, nbprocesses):
            participants.append(q.get(True)) # wait for the results of all processes

        for pr in listprocess:
            pr.terminate()
            pr.join() #kill the process

    except  Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        print "Exception", sys.exc_info()
        print "Line ", exc_tb.tb_lineno
    if (disjoint_window):
        for window in time_windows:
            for i in range(0, 59001 / window):
                cur_participants = []
                for j in range(len(participants)):
                    print(i, j)
                    cur_participants = cur_participants + participants[j][window][i]
                if params.VERBOSE != "QUIET":
                    print
                    print "Exporting:\n--General:", params.featurelist
                write_features_tsv(cur_participants, './outputfolder/disjoint_refined/window_%d/chunk_%d.tsv' % (window, i), featurelist=params.featurelist, id_prefix=False, require_valid = True)
    elif (not across_tasks):
        for i in range(1, 59001 / 1000):
            cur_participants = []
            for j in range(len(participants)):
                cur_participants = cur_participants + participants[j][i]
            if params.VERBOSE != "QUIET":
                print
                print "Exporting:\n--General:", params.featurelist
            write_features_tsv(cur_participants, './outputfolder/cumul_3/pruning_%d.tsv' % (1000 * i), featurelist=params.featurelist, id_prefix=False, require_valid = True)
    else:
        # Number of tasks
        for i in range(1, 16):
            cur_participants = []
            for j in range(len(participants)):
                cur_participants = cur_participants + participants[j][i]
            if params.VERBOSE != "QUIET":
                print
                print "Exporting:\n--General:", params.featurelist
            write_features_tsv(cur_participants, './outputfolder/across_tasks/tasks_included_%d.tsv' % (i), featurelist=params.featurelist, id_prefix=False, require_valid = True)

    return participants

def chunks(l, n):
    """Split a list in balanced sub-lists. If equal sublits are not possible, remaining elements are distribute evenly among sublists.

    Args:
        l: the list to split.

        n: the number of sublists to generate.

    Returns:
        a list of n sublists
    """
    if n < 1:
        n = 1
    if len(l) < n:
        n = len(l)

    nsize = len(l)/n #number of elements in the sublists
    if len(l)%n == 0:
        return [l[i:i + nsize] for i in range(0, len(l), nsize)]
    else:
        l2 = [l[i:i + nsize] for i in range(0, len(l[0:nsize*n]), nsize)]
        i=0
        for j in l[nsize*n:len(l)]: #distribute remaining elements
            l2[i].append(j)
            i = (i+1) % n
        return l2

def partition_Basic(segfile):
    """Generates the scenelist based on a .seg file

    Args:
        segfile: a string containing the name of the '.seg' file

    Returns:
        a dict with scid as the key and tuples of (segid, start , end) for segments that belong to
            that scene as value
        an integer determining the number of segments
    """
    scenelist = read_segs(segfile)
    segcount = 0
    for l in scenelist.itervalues():
        segcount += len(l)
    return scenelist, segcount



def read_events(evfile):
    """Returns a list of Event objects read from an 'Event-Data.tsv' file.

    Args:
        evfile: a string containing the name of the 'Event-Data.tsv' file exported by
            Tobii software

    Returns:
        a list of Event objects
    """
    with open(evfile, 'r') as f:
        lines = f.readlines()

    return map(Event, lines[(params.EVENTSHEADERLINES+params.NUMBEROFEXTRAHEADERLINES):])

def read_rest_pupil_sizes():
    return {'P21': 3.294234187140609,
            'P35': 3.042856648199449,
            'P40': 3.0620283018867944,
            'P26': 3.047674205378968,
            'P30': 3.1034735857877482,
            'P18': 2.885563282336579,
            'P12': 3.364172240802662,
            'P58': 3.082895953757233,
            'P42': 2.4192066805845513,
            'P59': 3.688688558446926,
            'P60': 2.6284354154032745,
            'P25': 3.391893158388006,
            'P61': 3.125104094378899,
            'P16': 2.559051976573942,
            'P62': 2.446809078771691,
            'P9': 2.7987005988023936,
            'P63': 2.95377952755906,
            'P64': 2.8154315628191973,
            'P65': 2.5716238381629233,
            'P38': 3.3063704206241504,
            'P66': 3.268320105820107,
            'P67': 3.2290529801324466,
            'P36': 2.8757863013698657,
            'P68': 3.317506500260017,
            'P52': 2.5995952023988034,
            'P69': 2.780373588184186,
            'P70': 3.121313594662215,
            'P71': 3.8676908979841182,
            'P55': 3.119199466310872,
            'P72': 3.07012006003001,
            'P19': 3.4835575167376747,
            'P73': 2.663658909981633,
            'P74': 2.77560419235512,
            'P77': 2.488447043534764,
            'P45': 3.5782149532710212,
            'P75': 2.8168278965129296,
            'P76': 2.9916612200435764,
            'P31': 3.0412572161642104,
            'P78': 3.2618630382775113,
            'P79': 2.692619331742239,
            'P81': 3.0359703860391334,
            'P82': 2.610252996005327,
            'P84': 3.031542176432708,
            'P85': 2.451942307692308,
            'P46': 3.2230479643056342,
            'P50': 3.039736321687549,
            'P88': 3.1375530660377358,
            'P91': 2.403347759674135,
            'P89': 2.5133685800604266,
            'P92': 2.6111814345991564,
            'P90': 2.5844733581164823,
            'P93': 3.207753759398504,
            'P95': 2.835974102413183,
            'P97': 2.634023652365236,
            'P80': 2.8079452506596194,
            'P1': 2.660198902606308 }
"""
def read_rest_pupil_sizes(rpsfile):

    Returns a dictionary of rest pupil sizes for all scenes if rpsfile is provided. None otherwise
    The input file has the following format:
        pid\t<scene name 1>\t<scene name 2>....\n
        <pid 1>\t<rest pupil size 1>\t<rest pupil size 2>

    Args:
        rpsfile: a string containing the name of the '.tsv' file
            with rest pupil sizes for all partiicpants and all scenes.

    Returns:
        a dictionary of rest pupil sizes. None otherwise


    if rpsfile != None:
        with open(rpsfile, 'r') as f:
            lines = f.readlines()
        rpsdic = {}
        import re
        scenelist = re.findall('\w+', lines[0])
        for line in lines[1:]:
            linelist = re.findall('\w+', line)
            pid = cast_int(linelist[0])
            if pid == None: #if casting didn't work
                pid = linelist[0]
            rpsdic[pid] = {}
            for scene, rpsvalue in zip(scenelist[1:], linelist[1:]):
                rpsdic[pid][scene] = cast_int(rpsvalue)

        return rpsdic
    else:
        return None
"""


def plot_pupil_dilation_all(participants, outdir, scene):
    """
    Plots adjusted pupil dilations to

    Args:
        participants: collection of Participant objects

        outdir: directory where files should be exported

        scene: name of scene to be exported

    Returns:

    """
    lines = []
    for participant in participants:
        lines = export_pupil_dilation_from_scene(participant, scene, separator = "\t")
        with open(outdir + "pupildata" + "_" + str(participant.pid) + "_" + str(scene) + ".tsv", "w") as fout:
            if lines is not None:
                for line in lines:
                    fout.write(line)
            else:
                fout.write("There is no scene " + str(scene) + " in the participant " + str(participant.pid) + " record ")


def export_pupil_dilation_from_scene(participant, scene, separator = "\t"):
    """
    Exports pupil dilation information from  pupilinfo_for_export for a scene of a participant

    Args:
        participant: a Participant object

        scene: name of scene to be exported

    Returns:
        a collection of lines to be written in the file
    """
    lines = []
    for sc in participant.scenes:
        if sc.scid == scene:
            lines.append("timestamp\tpupil size\tadjusted pupil size\n")
            for el in sc.pupilinfo_for_export:
                lines.append(list_to_string(el, "\t"))
            return lines

    return None

def list_to_string(list, separator = "\t"):
    """
    Converts a list of values to a string using SEPARATOR for joints

    Args:
        list: a list of values to be converted to a string

        separator:  a separator to be used for joints

    Returns:
        a string

    """
    return separator.join(map(str, list))+ "\n"


# participants = list of all participants returned by "read_participants_Basic()"
# filename = file to export the validity information
# example: prop_valid_fix_per_segs(ps, "infor_valid_participants.txt")
def prop_valid_fix_per_segs(participants, filename):  # modified
    count_high = 0
    count_low = 0
    mean_high = 0
    mean_low = 0
    std_high = 0
    std_low = 0
    mean_p = []
    std_p = []
    count_p = []
    fout = open(filename, "w")

    print "======== Segments ==============="
    for p in participants:  # for all participants
        mean = 0
        std = 0

        for s in p.scenes:  # for all scenes, compute total & mean valid fixations per participants
            print str(p.pid) + '\t' + str(s.scid) + '\t' + str(s.proportion_valid)
            fout.write(str(p.pid) + '\t' + str(s.scid) + '\t' + str(s.proportion_valid) + '\n')
            if not str(s.scid).startswith('P'):
                mean = mean + s.proportion_valid
        mean = mean / (len(p.scenes))

        for s in p.scenes:  # std dev per participants
            if not str(s.scid).startswith('P'):
                std = std + abs(mean - s.proportion_valid)
        std = std / (len(p.scenes) - 1)
        mean_p.append(mean)
        std_p.append(std)
        count_p.append(len(p.scenes) - 1)

    print "======== Participants ==============="
    for i in range(0, len(mean_p)):
        print str(participants[i].pid) + " MEAN=" + str(mean_p[i]) + "; STDDEV=" + str(std_p[i]) + "; COUNT=" + str(
            count_p[i])

    fout.close()
