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


import random


class GA:
    """
    This class contains the Genetic Algorithm as described in:
        Such, et al. (2018). Deep Neuroevolution: Genetic Algorithms Are a Competitive Alternative for Training Deep
        Neural Networks for Reinforcement Learning
    """
    def __init__(self, popu_size: int, n_survivors: int, n_champions: int=1):
        assert n_champions < n_survivors < popu_size
        self.popu_size = popu_size
        self.n_survivors = n_survivors
        self.n_champions = n_champions
        self.genomes = [[random.randrange(2 ** 32)] for _ in range(popu_size)]
        self.genomes_champions = []
        self.scores_champions = []

    def step(self, scores):
        # Sort the population according to individual's score, from low to high
        # The sorted tuples list includes the champions from the previous iteration
        sorted_results_tup = sorted(zip(scores + self.scores_champions,
                                        self.genomes + self.genomes_champions))

        # Keep only the best n_survivors, while also unpacking the tuples
        survivors_scores, survivors_genomes = \
            (list(t) for t in zip(*sorted_results_tup[-self.n_survivors:]))

        # Save the champions, while also unpacking the tuples
        self.scores_champions, self.genomes_champions = \
            (list(t) for t in zip(*sorted_results_tup[-self.n_champions:]))

        # Zero-out the current population
        self.genomes = []

        # Select random survivors and append a new random seed to those
        while len(self.genomes) < self.popu_size:
            self.genomes.append(random.choice(survivors_genomes) + [random.randrange(2**32)])

        return survivors_scores, survivors_genomes
