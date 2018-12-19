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

# This is the main python file. Start the experiment by running this.

import os
import argparse
import random
import string
from multiprocessing.pool import ThreadPool
from time import sleep
import yaml

import numpy as np

import ga
from cloud_wrapper import Cloud

os.environ['REDIS_PW'] = "".join([random.choice(string.ascii_letters + string.digits) for _ in range(20)])
print(os.environ['REDIS_PW'])

import rq_worker  # It will read the password files

# Load settings yaml
with open('settings.yaml', 'rt') as f:
    settings = yaml.load(f)


def main():
    parser = argparse.ArgumentParser()
    required_args = parser.add_argument_group('required arguments')
    required_args.add_argument('-n', '--hostname-prefix', dest='hostname', type=str, required=True,
                               help="Choose a hostname prefix for the machines. "
                                    "If those already exist, they will be used without requesting new ones")
    parser.add_argument('--keep-vms', dest='keep_vms', action='store_true',
                        help="Do not delete the instantiated VMs at the end of the experiment.")
    parser.add_argument('--datacenter', dest='datacenter', type=str, required=True,
                        help="Datacenter to choose.")
    args, _ = parser.parse_known_args()

    # Ask for hostname prefix for the VMs
    hostname = args.hostname
    for i in range(settings['experiment']['count']):
        os.makedirs("out_"+str(i), exist_ok=False)

    cloud_mgr = Cloud(cpus=settings['vm']['cpus'],
                      mem=settings['vm']['mem'],
                      hostname=hostname,
                      count=settings['vm']['count'],
                      datacenter=args.datacenter)

    with ThreadPool(processes=settings['experiment']['count']) as pool:
        pool.map(run_experiment, range(settings['experiment']['count']))

    # Delete all the VMs
    if not args.keep_vms:
        cloud_mgr.cancel_all()


def run_experiment(id_: int):
    # Starting genetic algorithm
    gene_pool = ga.GA(popu_size=settings['experiment']['population'],
                      n_survivors=settings['experiment']['survivors'],
                      n_champions=settings['experiment']['champions'])

    for i in range(settings['experiment']['generations']):
        worker_async_results = [rq_worker.run.delay(seeds) for seeds in gene_pool.genomes]

        scores = wait_for_results(worker_async_results)

        survivors_scores, survivors_genomes = gene_pool.step(scores)

        np.savez("out_" + str(id_) + "/" + str(i) + ".npz", scores=survivors_scores, genomes=survivors_genomes)

        print("=== ID", id_, "Generation", i, "===\n",
              "Best scores:", list(reversed(survivors_scores)), "\n")


def wait_for_results(async_results: [], polling_sleep=2):
    # Get results (non-blocking)
    # If a result is not yet available, we get `None`
    results = [r.result for r in async_results]

    # While `results` contains `None` elements
    while any(e is None for e in results):
        sleep(polling_sleep)
        # Try to get the result for each `None` element
        for j, (r, ar) in enumerate(zip(results, async_results)):
            if r is None:
                results[j] = ar.result

    return results


if __name__ == '__main__':
    main()
