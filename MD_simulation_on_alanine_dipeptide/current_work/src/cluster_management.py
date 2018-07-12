import copy, pickle, re, os, time, subprocess, datetime, itertools, hashlib, glob

class cluster_management(object):
    def __init__(self):
        return

    @staticmethod
    def get_server_and_user():
        server = subprocess.check_output(['uname', '-n']).strip()
        user = subprocess.check_output('echo $HOME', shell=True).strip().split('/')[-1]
        return server, user

    @staticmethod
    def get_sge_file_content(command_in_sge_file, gpu, max_time, node=-1):
        command_in_sge_file = command_in_sge_file.strip()
        if command_in_sge_file[-1] == '&':  # need to remove & otherwise it will not work in the cluster
            command_in_sge_file = command_in_sge_file[:-1]
        server_name, _ = cluster_management.get_server_and_user()
        if 'alf' in server_name:
            gpu_option_string = '#$ -l gpu=1' if gpu else ''
            node_string = "" if node == -1 else "#$ -l hostname=compute-0-%d" % node

            content_for_sge_file = '''#!/bin/bash
#$ -S /bin/bash           # use bash shell
#$ -V                     # inherit the submission environment 
#$ -cwd                   # start job in submission directory
#$ -m ae                 # email on abort, begin, and end
#$ -M wei.herbert.chen@gmail.com         # email address
#$ -q all.q               # queue name
#$ -l h_rt=%s       # run time (hh:mm:ss)
%s
%s
%s
echo "This job is DONE!"
exit 0
''' % (max_time, gpu_option_string, node_string, command_in_sge_file)
        elif "golubh" in server_name:  # campus cluster
            content_for_sge_file = '''#!/bin/bash
#PBS -l walltime=%s
#PBS -l nodes=1:ppn=2
#PBS -l naccesspolicy=singleuser
#PBS -q alf
#PBS -V
#PBS -m ae                 # email on abort, begin, and end
#PBS -M wei.herbert.chen@gmail.com         # email address

cd $PBS_O_WORKDIR         # go to current directory
source /home/weichen9/.bashrc
%s
echo "This job is DONE!"
exit 0
''' % (max_time, command_in_sge_file)
        elif "h2ologin" in server_name or 'nid' in server_name:  # Blue Waters
            node_type = ':xk' if gpu else ''
            if not command_in_sge_file.startswith('aprun'):
                command_in_sge_file = 'aprun -n1 ' + command_in_sge_file
            command_in_sge_file = command_in_sge_file.replace('OMP_NUM_THREADS=6 ', '').replace('--device 1', '')
            content_for_sge_file = '''#!/usr/bin/zsh
#PBS -l walltime=%s
#PBS -l nodes=1:ppn=2%s
#PBS -m ae   
#PBS -M wei.herbert.chen@gmail.com    
#PBS -A batp

. /etc/zsh.zshrc.local
source /u/sciteam/chen21/.zshrc
cd $PBS_O_WORKDIR
# source /u/sciteam/chen21/.bashrc
%s
echo "This job is DONE!"
exit 0
''' % (max_time, node_type, command_in_sge_file)
        else:
            raise Exception('server error: %s does not exist' % server_name)
        return content_for_sge_file

    @staticmethod
    def generate_sge_filename_for_a_command(command):
        sge_filename = command.split('>')[0].replace('"','').replace(' ', '_').replace('..', '_').replace('/','_')\
                .replace('&', '').replace('--', '_').replace('\\','').replace(':', '_').strip() + '.sge'
        sge_filename = re.sub('_+', '_', sge_filename)
        if len(sge_filename) > 255:  # max length of file names in Linux
            temp = hashlib.md5()
            temp.update(sge_filename)
            sge_filename = "h_" + temp.hexdigest() + sge_filename[-200:]
        return sge_filename

    @staticmethod
    def create_sge_files_from_a_file_containing_commands(command_file, folder_to_store_sge_files='../sge_files/', run_on_gpu = False):
        with open(command_file, 'r') as commmand_file:
            commands_to_run = commmand_file.readlines()
            commands_to_run = map(lambda x: x.strip(), commands_to_run)
            commands_to_run = filter(lambda x: x != "", commands_to_run)
            cluster_management.create_sge_files_for_commands(commands_to_run, folder_to_store_sge_files, run_on_gpu)

        return commands_to_run

    @staticmethod
    def create_sge_files_for_commands(list_of_commands_to_run, folder_to_store_sge_files = '../sge_files/', run_on_gpu = False):
        sge_file_list = []
        for item in list_of_commands_to_run:
            if folder_to_store_sge_files[-1] != '/':
                folder_to_store_sge_files += '/'

            if not os.path.exists(folder_to_store_sge_files):
                subprocess.check_output(['mkdir', folder_to_store_sge_files])

            sge_filename = cluster_management.generate_sge_filename_for_a_command(item)
            sge_filename = folder_to_store_sge_files + sge_filename
            sge_file_list.append(sge_filename)

            content_for_sge_files = cluster_management.get_sge_file_content(
                item, gpu=run_on_gpu, max_time='24:00:00')
            with open(sge_filename, 'w') as f_out:
                f_out.write(content_for_sge_files)
                f_out.write("\n")
        return sge_file_list

    @staticmethod
    def get_num_of_running_jobs():
        _, user = cluster_management.get_server_and_user()
        output = subprocess.check_output(['qstat', '-u', user])
        all_entries = output.strip().split('\n')[2:]   # remove header
        all_entries = [item for item in all_entries if user in item]        # remove unrelated lines
        all_entries = [item for item in all_entries if (not item.strip().split()[4] == 'dr')]   # remove job in "dr" state
        num_of_running_jobs = len(all_entries)
        # print('checking number of running jobs = %d\n' % num_of_running_jobs)
        return num_of_running_jobs

    @staticmethod
    def submit_sge_jobs_and_archive_files(job_file_lists,
                                          num  # num is the max number of jobs submitted each time
                                          ):
        dir_to_archive_files = '../sge_files/archive/'

        if not os.path.exists(dir_to_archive_files):
            os.makedirs(dir_to_archive_files)

        assert(os.path.exists(dir_to_archive_files))
        sge_job_id_list = []
        for item in job_file_lists[0:num]:
            output_info = subprocess.check_output(['qsub', item]).strip()
            sge_job_id_list.append(cluster_management.get_job_id_from_qsub_output(output_info))
            print('submitting ' + str(item))
            subprocess.check_output(['mv', item, dir_to_archive_files]) # archive files
        return sge_job_id_list

    @staticmethod
    def get_job_id_from_qsub_output(output_info):
        server, _ = cluster_management.get_server_and_user()
        if 'alf' in server:
            result = output_info.strip().split(' ')[2]
        elif "h2ologin" in server or 'nid' in server:
            result = output_info.strip().split('\n')[-1]
            assert (result[-3:] == '.bw')
            result = result[:-3]
            assert (len(result) == 7)
        else: raise Exception('unknown server')
        return result

    @staticmethod
    def submit_a_single_job_and_wait_until_it_finishes(job_sge_file):
        job_id = cluster_management.submit_sge_jobs_and_archive_files([job_sge_file], num=1)[0]
        print "job = %s, job_id = %s" % (job_sge_file, job_id)
        while cluster_management.is_job_on_cluster(job_id):
            time.sleep(10)
        print "job (id = %s) done!" % job_id
        return job_id

    @staticmethod
    def run_a_command_and_wait_on_cluster(command):
        print 'running %s on cluster' % command
        sge_file = cluster_management.create_sge_files_for_commands([command])[0]
        id = cluster_management.submit_a_single_job_and_wait_until_it_finishes(sge_file)
        return id

    @staticmethod
    def get_output_and_err_with_job_id(job_id):
        temp_file_list = subprocess.check_output(['ls']).strip().split('\n')
        out_file = list(filter(lambda x: '.sge.o' + job_id in x, temp_file_list))[0]
        err_file = list(filter(lambda x: '.sge.e' + job_id in x, temp_file_list))[0]
        return out_file, err_file

    @staticmethod
    def get_sge_files_list():
        result = filter(lambda x: x[-3:] == "sge",subprocess.check_output(['ls', '../sge_files']).split('\n'))
        result = map(lambda x: '../sge_files/' + x, result)
        return result

    @staticmethod
    def submit_new_jobs_if_there_are_too_few_jobs(num):
        if cluster_management.get_num_of_running_jobs() < num:
            job_list = cluster_management.get_sge_files_list()
            job_id_list = cluster_management.submit_sge_jobs_and_archive_files(job_list,
                                    num - cluster_management.get_num_of_running_jobs())
        else:
            job_id_list = []
        return job_id_list

    @staticmethod
    def monitor_status_and_submit_periodically(num,
                                               num_of_running_jobs_when_allowed_to_stop = 0,
                                               monitor_mode = 'normal',  # monitor_mode determines whether it can go out of first while loop
                                               check_error_for_submitted_jobs=True):
        if monitor_mode == 'normal':
            min_num_of_unsubmitted_jobs = 0
        elif monitor_mode == 'always_wait_for_submit':
            min_num_of_unsubmitted_jobs = -1
        else:
            raise Exception('monitor_mode not defined')

        submitted_job_id = []
        num_of_unsubmitted_jobs = len(cluster_management.get_sge_files_list())
        # first check if there are unsubmitted jobs
        while len(submitted_job_id) > 0 or num_of_unsubmitted_jobs > min_num_of_unsubmitted_jobs:
            time.sleep(10)
            if check_error_for_submitted_jobs:
                cluster_management.get_sge_dot_e_files_in_current_folder_and_handle_jobs_not_finished_successfully()
            try:
                temp_submitted_job_id = cluster_management.submit_new_jobs_if_there_are_too_few_jobs(num)
                submitted_job_id += temp_submitted_job_id
                submitted_job_id = list(filter(lambda x: cluster_management.is_job_on_cluster(x),
                                               submitted_job_id))   # remove finished id of finished jobs
                print "submitted_job_id = %s" % str(submitted_job_id)
                num_of_unsubmitted_jobs = len(cluster_management.get_sge_files_list())
            except:
                print("not able to submit jobs!\n")

        # then check if all jobs are done (not really, since there could be multiple cluster_management running)
        while cluster_management.get_num_of_running_jobs() > num_of_running_jobs_when_allowed_to_stop:
            time.sleep(10)
        return

    @staticmethod
    def is_job_on_cluster(job_sgefile_name):    # input could be sge file name or job id
        server, user = cluster_management.get_server_and_user()
        if 'alf' in server:
            output = subprocess.check_output(['qstat', '-r'])
            result = job_sgefile_name in output
        elif "h2ologin" in server or 'nid' in server:
            output = subprocess.check_output(['qstat', '-u', user, '-f', '-x'])   # output in xml format, make sure long file name is displayed in one line
            result = False
            for item in output.split('<Job>')[1:]:
                if (job_sgefile_name in item) and (not '<job_state>C</job_state>' in item):  # ignore completed jobs
                    result = True
        else: raise Exception('unknown server')
        return result

    @staticmethod
    def check_whether_job_finishes_successfully(job_sgefile_name, latest_version = True):
        """
        return value:
        0: finishes successfully
        3: not finished
        1: finishes with exception
        2: aborted due to time limit or other reason
        -1: job does not exist
        """
        job_finished_message = 'This job is DONE!'
        # first we check whether the job finishes
        if cluster_management.is_job_on_cluster(job_sgefile_name):
            return 3  # not finished
        else:
            all_files_in_this_dir = sorted(glob.glob('*'))
            out_file_list = filter(lambda x: job_sgefile_name + ".o" in x, all_files_in_this_dir)
            err_file_list = filter(lambda x: job_sgefile_name + ".e" in x, all_files_in_this_dir)

            if len(out_file_list) == 0 or len(err_file_list) == 0:
                print "%s does not exist" % job_sgefile_name
                return -1  

            if latest_version:   # check output/error information for the latest version, since a job could be submitted multiple times
                job_serial_number_list = map(lambda x: int(x.split('.sge.o')[1]), out_file_list)
                job_serial_number_of_latest_version = max(job_serial_number_list)
                latest_out_file = filter(lambda x: str(job_serial_number_of_latest_version) in x, out_file_list)[0]
                latest_err_file = filter(lambda x: str(job_serial_number_of_latest_version) in x, err_file_list)[0]
                with open(latest_out_file, 'r') as out_f:
                    out_content = [item.strip() for item in out_f.readlines()]

                with open(latest_err_file, 'r') as err_f:
                    err_content = [item.strip() for item in err_f.readlines()]
                    err_content = filter(lambda x: "Traceback (most recent call last)" in x, err_content)

                if (job_finished_message in out_content) and (len(err_content) != 0):
                    print "%s ends with exception" % job_sgefile_name
                    return 1  
                elif not job_finished_message in out_content:
                    print "%s aborted due to time limit or other reason" % job_sgefile_name
                    return 2  
                else:
                    print "%s finishes successfully" % job_sgefile_name
                    return 0  
            else: return

    @staticmethod
    def handle_jobs_not_finished_successfully_and_archive(job_sgefile_name_list, latest_version=True):
        dir_to_archive_files = '../sge_files/archive/'
        folder_to_store_sge_files='../sge_files/'
        if not os.path.exists(dir_to_archive_files):
            subprocess.check_output(['mkdir', dir_to_archive_files])

        if not os.path.exists(folder_to_store_sge_files):
            subprocess.check_output(['mkdir', folder_to_store_sge_files])
            
        for item in job_sgefile_name_list:
            status_code = cluster_management.check_whether_job_finishes_successfully(item, latest_version)
            if status_code in (1, 2):
                if os.path.isfile(dir_to_archive_files + item):
                    print "restore sge_file: %s" % item
                    subprocess.check_output(['cp', dir_to_archive_files + item, folder_to_store_sge_files])
                    assert (os.path.exists(folder_to_store_sge_files + item))
                else:
                    print "%s not exists in %s" % (item, dir_to_archive_files)
            
            if status_code in (0, 1, 2):  # archive .o/.e files for finished jobs
                print "archive .o/.e files for %s" % item
                all_files_in_this_dir = sorted(glob.glob('*'))
                temp_dot_o_e_files_for_this_item = filter(lambda x: (item + '.o' in x) or (item + '.e' in x), 
                                                          all_files_in_this_dir)
                for temp_item_o_e_file in temp_dot_o_e_files_for_this_item:
                    subprocess.check_output(['mv', temp_item_o_e_file, dir_to_archive_files])
        return

    @staticmethod
    def get_sge_dot_e_files_in_current_folder_and_handle_jobs_not_finished_successfully(latest_version=True):
        sge_e_files = glob.glob('*.sge.e*')
        sge_files = [item.split('.sge')[0] + '.sge' for item in sge_e_files]
        sge_files = list(set(sge_files))
        # print "sge_files = %s" % str(sge_files)
        cluster_management.handle_jobs_not_finished_successfully_and_archive(sge_files, latest_version)
        return
