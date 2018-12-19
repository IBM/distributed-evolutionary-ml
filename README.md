# distributed-evolutionary-ml
A tool for experimenting with evolutionary optimization methods for machine learning algorithms, by distributing the workload over a large number of compute nodes on the IBM Cloud. For now, it only includes an implementation of [Deep Neuroevolution: Genetic Algorithms Are a Competitive Alternative for Training Deep Neural Networks for Reinforcement Learning](https://arxiv.org/abs/1712.06567).

This code is designed to work on
- The [IBM Cloud](https://www.ibm.com/cloud/).

You have to run all of this on a Master server (that you create manually on the IBM Cloud). It will instantiate VMs for the workers automatically.

## Dependencies

On an Ubuntu 16.04 master node, you can get *the following dependencies installed by runnning `master_setup.sh`* as a regular user.
Note that the script will ask you for `sudo` access, as it will set-up some things as root.

### System dependencies

- python3.6, through Anaconda / Miniconda
- docker

### Python dependencies

- numpy
- spur
- softlayer
- netifaces
- rq

### IBM Cloud set up

The python softlayer API will look for `~/.softlayer` for your IBM Cloud account credentials. To generate that file, after having installed the softlayer python module (in `master_setup.sh`), run in a terminal: 
```sh
slcli config setup
```

To be able to communicate with the worker VMs, be sure to [enable VLAN spanning](https://console.bluemix.net/docs/infrastructure/vlans/getting-started.html#getting-started-with-vlans) on your account.

### Firewall set up for *redis* (master node)

First step is to ensure that docker will not bypass UFW rules by opening ports in iptables. Do this only once on the master node:
- Add the line `DOCKER_OPTS="--iptables=false"` at the end of the file `/etc/default/docker`
- Restart docker:
  ```bash
  sudo systemctl restart docker*
  ```
- Open the redis port (6379) only to the private LAN (where our worker nodes will be):
  ```bash
  sudo ufw allow from 10.0.0.0/8 to any port 6379 comment 'redis server'
  ```


## How to set up the experiment

- Edit the experiment's settings in the `settings.yaml` file (self documented).

- Start the master node script.
    On the master server, run:
    ```bash
     python3 master.py -n [server hostname prefix] --datacenter ibm_cloud_datacenter_code
    ```
    This will request VMs on the Cloud named `[server hostname prefix]-0`, `[server hostname prefix]-1`, etc.
    It is recommended that you choose the same datacenter as your master node.

  The results of the experiment will be stored in the `out/` folder, in numpy `.npz` files named after the number of generations.
  Each file contains the scores of the survivors as well as their genes.

- The instances will be destroyed at the end of the experiment. However, if you `ctrl-c` to stop the experiment, or you run with the `--keep-vms` that will not be the case. That can save you the waiting time of requesting the servers again if you know that you'll run something again soon using the same *hostname prefix* for the workers.

  - If you want to keep those machines for a subsequent run, just ask for the same *hostname prefix* and the same servers will be used.
  
  - If you want to destroy the machines manually:
    ```python
    import SoftLayer
    from SoftLayer.managers.vs import VSManager

    # Instantiate IBM cloud API objects
    sl_client = SoftLayer.create_client_from_env()
    sl_vsi_mgr = VSManager(sl_client)

    # This gets the IDs of all your account's VMs matching the [hostname] prefix
    # Replace [hostname] by the actual hostname prefix you chose for the worker nodes
    ids = [e['id'] for e in sl_vsi_mgr.list_instances(hostname='[hostname]*')]

    for i in ids:
      sl_vsi_mgr.cancel_instance(i)
    ```

## How to read the output files

Each experiment create a single Numpy `.npz` file per generation. It contains the scores of the survivors as well as their genes.
To load the results, here's a simple example in python:
```python
import numpy as np

d = np.load("something.npz")
# d[scores] and d[genes] contain a list of #survivors scores and genes, repectively
best_survivor_score = d[scores][-1]  # Outputs a single integer
best_survivor_genes = d[genes][-1]  # Outputs a list of integers
```

# License

Copyright (C) IBM Corporation 2018

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

     http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.