"""
this programs takes a file containing all Python programs to run as input, and 
put these programs into a workqueue, and at every instance we make sure only 
n Python programs are running

===========================
input: 

- file containing Python programs to run
- number of programs allowed to run concurrently
- time interval of checking the number of running programs
"""

import argparse, subprocess, time

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("cmdfile", type=str, help="file containing Python programs to run")
    parser.add_argument("file_finished", type=str, help="file containing the programs finished")
    parser.add_argument("--num", type=int, default=20, help="number of programs allowed to run concurrently")
    parser.add_argument("--interval", type=int, default=10, help="time interval of checking the number of running programs")

    args = parser.parse_args()

    command_file = args.cmdfile
    num_of_programs_allowed = args.num
    interval = args.interval

    with open(command_file, 'r') as cmdf:
        command_list = cmdf.read().strip().split('\n')

    command_list = [x for x in command_list if x.strip() != "" and x.strip()[0] != "#"]  # remove empty commands

    total_num_jobs = len(command_list)
    next_job_index = 0

    previous_running_python_jobs = []

    while next_job_index < total_num_jobs:
        time.sleep(interval)
        current_running_python_jobs = [x for x in subprocess.check_output(['ps', 'aux']).decode("utf-8").split('\n') if ' python ' in x and not 'python workqueue.py' in x]
        current_running_python_jobs = [' '.join(x.split()[10:]) for x in current_running_python_jobs]      # 11th column is command
        # print "current_running_jobs = %s" % str(current_running_python_jobs)

        # save finished programs into this file
        with open(args.file_finished, 'a') as file_containing_programs_finished:
            for item in previous_running_python_jobs:
                if not item in current_running_python_jobs:
                    file_containing_programs_finished.write(item)
                    file_containing_programs_finished.write('\n')

        previous_running_python_jobs = current_running_python_jobs

        num_of_running_jobs = len(current_running_python_jobs)
        if num_of_running_jobs < num_of_programs_allowed:
            if num_of_programs_allowed - num_of_running_jobs > total_num_jobs - next_job_index:
                run_programs(command_list, next_job_index, total_num_jobs)
                next_job_index = total_num_jobs
            else:
                run_programs(command_list, next_job_index, next_job_index + num_of_programs_allowed - num_of_running_jobs)
                next_job_index += num_of_programs_allowed - num_of_running_jobs

    print("Done all programs in " + args.cmdfile)
    return


def run_programs(command_list, start_index, end_index, shell=True):
    """
    run programs with index [start_index, end_index - 1]
    """
    for item in range(start_index, end_index):
        command_arg = command_list[item].strip()
        if command_arg != "":
            if command_arg[-1] == "&":
                command_arg = command_arg[:-1]

            print("running command: " + command_arg)
            if not shell: command_arg = command_arg.split()
            subprocess.Popen(command_arg, shell=shell)

    return
    

if __name__ == '__main__':
    main()
    
