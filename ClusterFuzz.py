import docker
import sys
import paramiko as pm
import time
import os
import shutil

def clean_fuzzing_data(ip_addrs):
    ssh = pm.SSHClient()
    ssh.set_missing_host_key_policy(pm.AutoAddPolicy())
    
    for ip_addr in ip_addrs:
        try:
            ssh.connect(ip_addr, 22, username, password)
            ssh.exec_command("rm queue.tar.gz && rm corpus.tar.gz && rm fuzzer_stats.tar.gz")
        except:
            pass
    
    try:
        if os.path.isdir("fuzzer_queues"):
            for i in range(0, len(ip_addrs)):
                os.remove("fuzzer_queues/" + str(i) + ".tar.gz")
            shutil.rmtree("fuzzer_queues/queue")
    except:
        pass

def try_create_dir(dir_name):
    try:
        os.mkdir(dir_name)
    except:
        pass    

def get_tars(ip_addrs, username, password):
    print("Fetching Corpuses From Fuzzers")
    try_create_dir("fuzzer_queues")
    try_create_dir("fuzzer_queues/queue")
    path = os.path.abspath(os.getcwd()) + "/fuzzer_queues/"
    
    i = 0
    ssh = pm.SSHClient()
    ssh.set_missing_host_key_policy(pm.AutoAddPolicy())
    
    for ip_index in range(0, len(ip_addrs)):
        try:
            ssh.connect(ip_addrs[ip_index], 22, username, password)
            ftp = ssh.open_sftp()
            stdin, stdout, stderr = ssh.exec_command("tar -czf queue.tar.gz --mode 'a+rwX' -C /fuzz/output/ queue/")
            stdout.channel.recv_exit_status()
            ftp.get("queue.tar.gz", path + str(i) + ".tar.gz")
            os.system('tar -xzf ' + path + str(i) + ".tar.gz --skip-old-files " + "-C " + path) 
            ftp.close()
            ssh.close()
        except:
            print("Error occured when downloading corpus in: {}".format(ip_addrs[ip_index]))
            pass
        i += 1

def create_and_send_combined_corpus(ip_addrs, username, password):
    print("Sending Combined Corpus to Fuzzers")
    os.system("tar -czf fuzzer_queues/corpus.tar.gz --mode 'a+rwX' -C fuzzer_queues/ queue/")
    path = os.path.abspath(os.getcwd()) + "/fuzzer_queues/"

    i = 0
    ssh = pm.SSHClient()
    ssh.set_missing_host_key_policy(pm.AutoAddPolicy())
    
    for ip_index in range(0, len(ip_addrs)):
        try:
            ssh.connect(ip_addrs[ip_index], 22, username, password)
            ftp = ssh.open_sftp()
            ftp.put(path + "corpus.tar.gz", "corpus.tar.gz")
            stdin, stdout, stderr = ssh.exec_command("tar -xzf corpus.tar.gz --skip-old-files -C /fuzz/output/")
            ftp.close()
            ssh.close()
        except:
            print("Error occured when sending corpus in: {}".format(ip_addrs[ip_index]))
            pass
        i += 1

def get_fuzzer_stats(ip_addrs, username, password):
    print("Fetching Statistics From Fuzzers")
    try_create_dir("fuzzer_stats")
    
    i = 0
    ssh = pm.SSHClient()
    ssh.set_missing_host_key_policy(pm.AutoAddPolicy())
    
    for ip_index in range(0, len(ip_addrs)):
        try:
            ssh.connect(ip_addrs[ip_index], 22, username, password)
            ftp = ssh.open_sftp()
            stdin, stdout, stderr = ssh.exec_command("tar -czf fuzzer_stats.tar.gz --mode 'a+rwX' -C /fuzz/output/ fuzzer_stats/")
            stdout.channel.recv_exit_status()
            ftp.get("fuzzer_stats.tar.gz", os.path.abspath(os.getcwd()) + "/fuzzer_stats/" + str(i) + ".tar.gz")
            ftp.close()
            ssh.close()
        except:
            print("Error occured when downloading fuzzer status in: {}".format(ip_addrs[ip_index]))
            pass
        i += 1

def synthesize(ip_addrs, username, password):
    clean_fuzzing_data(ip_addrs)
    get_tars(ip_addrs, username, password)
    create_and_send_combined_corpus(ip_addrs, username, password)    
    get_fuzzer_stats(ip_addrs, username, password)
    
def create_containers(client, containers, ip_addrs, count):
    print("Creating {} containers.".format(count))
    for i in range(count):
        client.containers.run("raspberry", privileged=True, detach=True)

    for container in client.containers.list():
        if container.image.attrs["RepoTags"][0] == "raspberry:latest":
            containers.append(container)
            ip_addrs.append(container.attrs["NetworkSettings"]["IPAddress"])

def fuzz(ip_addrs, username, password):
    clean_fuzzing_data(ip_addrs)
    timer = 0
    print_info = True
    synthetization_time = 3600

    while True:
        try:
            if print_info:
                print("{:.2f} Minutes Until Next Synthetization, Use Ctrl+C to Exit!".format((synthetization_time - timer) / 60))
                print_info = False

            if timer == synthetization_time:
                synthesize(ip_addrs, username, password)
                print_info = True
                timer = 0

            if timer > 0 and timer % 10 == 0:
                print_info = True 
            time.sleep(1)
            timer += 1
        except:
            break

def cleanup(client, containers):
    print("Cleaning up..")
    for i in range(0, len(containers)):
        containers[i].stop()

    client.containers.prune()

def run(count, username, password):
    client = docker.from_env()
    containers = list()
    ip_addrs = list()    
    
    create_containers(client, containers, ip_addrs, count)
    fuzz(ip_addrs, username, password)
    get_fuzzer_stats(ip_addrs, username, password)
    cleanup(client, containers)

if __name__ == "__main__":
    count = 1

    if len(sys.argv) > 1:
        try:
            count = int(sys.argv[1])
        except ValueError:
            print("Invalid value: {}".format(count))
            sys.exit(-1)

    run(count, "root", "afldocker")
