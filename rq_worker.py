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

import subprocess as sp
import os

from rq.decorators import job
from redis import Redis

redis_pw = os.environ['REDIS_PW']

redis_conn = Redis(host="localhost", port=6379, db=0, password=redis_pw)


@job('default', connection=redis_conn, timeout='1h')
def run(seeds: [int]):
    seeds_str = ' '.join([str(s) for s in seeds]).encode('utf-8')

    result = sp.run(["python", "worker.py"], input=seeds_str, stdout=sp.PIPE)

    result = result.stdout.decode('utf-8')
    score = int(result)
    return score
