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

# This Dockerfile describes the Docker image that will contain the Python code of the worker nodes, as well as
# all the dependencies.

FROM ubuntu:16.04 AS build

ENV LANG=C.UTF-8 LC_ALL=C.UTF-8

RUN apt-get update --fix-missing && \
    apt-get install -y --no-install-recommends \
        bzip2 \
        git \
        wget \
        ca-certificates \
        supervisor && \
    apt-get clean

RUN wget --quiet https://repo.continuum.io/miniconda/Miniconda3-latest-Linux-x86_64.sh -O ~/miniconda.sh && \
    chmod +x ~/miniconda.sh && \
    ~/miniconda.sh -b -p /opt/conda && \
    rm ~/miniconda.sh

ENV PATH /opt/conda/bin:$PATH

# Setting specific versions of redis and rq because of https://github.com/rq/rq/issues/1014
RUN conda install python=3.6 && \
    conda install pytorch-cpu -c pytorch && \
    conda install cmake numpy setuptools pyyaml && \
    pip install --no-cache-dir gym[atari] redis==2.10.6 rq==0.12.0 && \
    conda clean -ya

COPY worker.py nn.py rq_worker.py supervisord_launch.sh supervisord.conf /root/worker/

WORKDIR /root/worker

# The script below expect [redis pw] and [redis ip] arguments to be given (when starting docker image)
ENTRYPOINT ["sh", "supervisord_launch.sh"]
