# Copyright (C) IBM Corporation 2018
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
from multiprocessing.pool import ThreadPool
from time import sleep
import netifaces as ni
import SoftLayer
from SoftLayer.managers.vs import VSManager
import spur


class Cloud:
    """
    This class contains the methods needed to provision the worker VMs on the IBM Cloud.
    """

    def __init__(self, cpus: int,
                 mem: int,
                 hostname: str,
                 datacenter: str,
                 count: int,
                 transient=False):

        # Instantiate IBM cloud API object

        self._sl_client = SoftLayer.create_client_from_env()
        self.cloud_mgr = VSManager(self._sl_client)

        self._cpus = cpus
        self._mem = mem
        self._hostname = hostname
        self._count = count
        self._transient = transient

        # Load redis password
        self.redis_pw = os.environ['REDIS_PW']

        self.own_ip = ni.ifaddresses('eth0')[ni.AF_INET][0]['addr']
        print("Determined that own IP is", self.own_ip)

        # Restart redis server
        print("Starting local redis server")
        start_redis_script = """
        if [ "$(docker ps -aq -f name=redis)" ]; then \
            docker rm -f redis ; \
        fi ; \
        docker run -d -p 6379:6379 --name redis redis --requirepass {0}
        """.format(self.redis_pw)
        result = self._shell_run_script(spur.LocalShell(), start_redis_script)
        if result.return_code != 0:
            print("Error while starting local redis server")
            print(result.stderr_output.decode('utf-8'))
            exit(-1)

        # Build and save worker docker image
        print("Building worker docker image")
        build_docker_image = """
            docker build . -t invaders && \
            docker save invaders | pigz > invaders.tar.gz
        """
        result = self._shell_run_script(spur.LocalShell(), build_docker_image)
        if result.return_code != 0:
            print("Error while building worker docker image")
            print(result.stderr_output.decode('utf-8'))
            exit(-1)

        # Create all the hostnames
        hostnames = [self._hostname + '-' + str(i) for i in range(self._count)]
        # Keep aside only the ones that are not already instantiated on IBM Cloud
        instances_list = self.cloud_mgr.list_instances()
        hostnames_list = [e['hostname'] for e in instances_list]

        # List of the VMs to instantiate
        hostnames_nonexistant = [h for h in hostnames if h not in hostnames_list]

        datacenters = []
        for _ in range(len(hostnames_nonexistant)):
            datacenters.append(datacenter)

        if len(hostnames_nonexistant) > 0:
            print("Requesting the VMs...")
            vm_settings = [{
                'hostname': h,
                'domain': 'IBM.cloud',
                'datacenter': d,
                'dedicated': False,
                'private': True,
                'cpus': self._cpus,
                'os_code': 'CENTOS_7_64',
                'local_disk': False,
                'memory': self._mem * 1024,
                'tags': 'worker, ga',
                'nic_speed': 100
            }
                for h, d in zip(hostnames_nonexistant, datacenters)]

            # Request the machines 10 at a time
            vm_settings = [vm_settings[x:x + 10] for x in range(0, len(vm_settings), 10)]
            for s in vm_settings:
                self.cloud_mgr.create_instances(config_list=s)

        # Get the IDs of the VMs we'll use
        self._vm_ids = [e['id'] for e in self.cloud_mgr.list_instances() if e['hostname'] in hostnames]

        print("Waiting for the VMs to be available + set-up (in background thread)")
        self.pool = ThreadPool(processes=10)  # Limit to 10 to avoid hitting the API calls limit
        self._setup_results = self.pool.map_async(self._setup_vm, self._vm_ids)

    def _setup_vm(self, id_):
        self.cloud_mgr.wait_for_ready(id_)

        ip = None
        pw = None

        # Sometimes the OS password is not ready on time, so retry 30 times
        for i in range(30):
            try:
                vm_info = self.cloud_mgr.get_instance(id_)
                ip = vm_info['primaryBackendIpAddress']
                pw = vm_info['operatingSystem']['passwords'][0]['password']
            except KeyError:
                sleep(10)
            else:
                break

        assert ip is not None, "Could not retrieve IP address for " + str(id_)
        assert pw is not None, "Could not retrieve password for " + str(id_)

        local_shell = spur.LocalShell()
        shell = spur.SshShell(hostname=ip, username='root', password=pw,
                              missing_host_key=spur.ssh.MissingHostKey.accept,
                              load_system_host_keys=False)

        # Configure the VM
        vm_config_script = """
            ip route replace default via {0} ; \
            yum install -y epel-release && \
            yum install -y wget pxz lbzip2 pigz rsync && \

            wget -q https://get.docker.com/ -O docker_install.sh && \
            sh docker_install.sh && \
            
            sysctl -w net.ipv4.ip_forward=1 && \
            systemctl restart network && \
            
            systemctl enable docker && \
            systemctl restart docker
        """.format(self.own_ip)

        result = self._shell_run_script(shell, vm_config_script)
        if result.return_code != 0:
            print("Error while setting up the VM", id_)
            print(result.stderr_output.decode('utf-8'))
            exit(-1)

        # Uploading the docker image on the VMs
        docker_copy_script = """
            /usr/bin/rsync --verbose --inplace -r \
            --rsh="/usr/bin/sshpass -p {0} \
            ssh -Tx -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -o Compression=no -l root" \
            invaders.tar.gz \
            {1}:/root/ga/
        """.format(pw, ip)

        result = self._shell_run_script(local_shell, docker_copy_script)
        if result.return_code != 0:
            print("Error while uploading docker image on VM", id_)
            print(result.stderr_output.decode('utf-8'))
            exit(-1)

        # Decompressing the docker image, loading it
        # + changing sshd settings to allow for simultaneous connections

        docker_load_script = """
            cd /root/ga ; \
            docker rm -f invaders ; \
            docker rm -f /invaders ; \
            cat invaders.tar.gz | pigz -d  | docker load ; \
            docker run -d -p 6379:6379 -e \"REDIS_PW={0}\" -e \"REDIS_IP={1}\" --name invaders invaders
            """.format(self.redis_pw, self.own_ip)

        result = self._shell_run_script(shell, docker_load_script)
        if result.return_code != 0:
            print("Error while loading docker image on VM", id_)
            print(result.stderr_output.decode('utf-8'))
            exit(-1)

        return ip, pw

    def cancel_all(self):
        print("Deleting instances...")
        for i, id_ in enumerate(self._vm_ids):
            print('\r' + str(i) + '/' + str(len(self._vm_ids)), end='')
            self.cloud_mgr.cancel_instance(id_)
        print('\r' + str(len(self._vm_ids)) + '/' + str(len(self._vm_ids)))

    @staticmethod
    def _shell_run_script(shell, script, allow_error=True):
        return shell.run(["/bin/bash", "-c", script], allow_error=allow_error)
