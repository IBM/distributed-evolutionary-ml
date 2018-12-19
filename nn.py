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

# This file contains the description of the neural network the will process the game frames and return player actions.

import numpy as np
import torch
import torch.nn.functional as F
torch.set_num_threads(1)


class NN:
    def __init__(self, sigma: float, seeds: [int]):
        self.sigma = sigma

        # Setting the initialization seed
        torch.manual_seed(seeds[0])

        self.conv1_w = F.normalize(torch.randn((32, 3, 8, 8)), p=2, dim=1)
        self.conv1_b = torch.zeros(32)

        self.conv2_w = F.normalize(torch.randn((32, 32, 6, 6)), p=2, dim=1)
        self.conv2_b = torch.zeros(32)

        self.conv3_w = F.normalize(torch.randn((64, 32, 4, 4)), p=2, dim=1)
        self.conv3_b = torch.zeros(64)

        self.conv4_w = F.normalize(torch.randn((64, 64, 3, 3)), p=2, dim=1)
        self.conv4_b = torch.zeros(64)

        self.fc1_w = F.normalize(torch.randn((128, 960)), p=2, dim=1)
        self.fc1_b = torch.zeros(128)

        self.fc2_w = F.normalize(torch.randn((4, 128)), p=2, dim=1)
        self.fc2_b = torch.zeros(4)

        # Applying all the seeds to get to the final genotype
        for i, seed in enumerate(seeds[1:]):
            torch.manual_seed(seed)

            self.conv1_w += self.sigma * torch.randn(self.conv1_w.shape)
            self.conv1_b += self.sigma * torch.randn(self.conv1_b.shape)

            self.conv2_w += self.sigma * torch.randn(self.conv2_w.shape)
            self.conv2_b += self.sigma * torch.randn(self.conv2_b.shape)

            self.conv3_w += self.sigma * torch.randn(self.conv3_w.shape)
            self.conv3_b += self.sigma * torch.randn(self.conv3_b.shape)

            self.conv4_w += self.sigma * torch.randn(self.conv4_w.shape)
            self.conv4_b += self.sigma * torch.randn(self.conv4_b.shape)

            self.fc1_w += self.sigma * torch.randn(self.fc1_w.shape)
            self.fc1_b += self.sigma * torch.randn(self.fc1_b.shape)

            self.fc2_w += self.sigma * torch.randn(self.fc2_w.shape)
            self.fc2_b += self.sigma * torch.randn(self.fc2_b.shape)

    def forward(self, inputs: np.array):
        m = inputs[np.newaxis, ...].astype(np.float32)
        m = np.swapaxes(m, 1, 3)
        m = torch.from_numpy(m)
        m /= 255
        m = F.relu(F.conv2d(m, self.conv1_w, self.conv1_b, 4))
        m = F.relu(F.conv2d(m, self.conv2_w, self.conv2_b, 3))
        m = F.relu(F.conv2d(m, self.conv3_w, self.conv3_b, 2))
        m = F.relu(F.conv2d(m, self.conv4_w, self.conv4_b, 1))
        m = F.relu(F.linear(m.reshape(-1), self.fc1_w, self.fc1_b))
        m = F.linear(m, self.fc2_w, self.fc2_b)
        return np.argmax(m.numpy())
