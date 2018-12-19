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

import sys
import os
os.environ["MKL_NUM_THREADS"] = '1'
os.environ["OMP_NUM_THREADS"] = '1'
from nn import NN
import gym


def run(seeds: [int]):
    # Create neural net instance
    nn = NN(sigma=0.005, seeds=seeds)

    env = gym.make('SpaceInvadersDeterministic-v4')
    env.reset()
    done = False
    score = 0

    observation, reward, done, info = env.step(0)
    action = nn.forward(observation)

    while not done:
        # observation dim is (210, 160, 3)
        observation, reward, done, info = env.step(action)
        score += reward
        action = nn.forward(observation)
        if info['ale.lives'] < 3:
            done = True

    return int(score)


if __name__ == '__main__':
    seeds = sys.stdin.read().split(' ')
    seeds = [int(e) for e in seeds]
    print(run(seeds))
