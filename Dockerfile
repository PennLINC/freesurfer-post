# Parts copied from fMRIPrep Docker Container Image distribution
#
# MIT License
#
# Copyright (c) The NiPreps Developers
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

# Ubuntu 22.04 LTS - Jammy
ARG BASE_IMAGE=ubuntu:jammy-20240125

#
# Build wheel
#
FROM ghcr.io/astral-sh/uv:python3.12-alpine AS src
RUN apk add git
COPY . /src
RUN uvx --from build pyproject-build --installer uv -w /src

#
# Download stages
#

# Utilities for downloading packages
FROM ${BASE_IMAGE} AS downloader
# Bump the date to current to refresh curl/certificates/etc
RUN echo "2023.07.20"
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
                    binutils \
                    bzip2 \
                    ca-certificates \
                    curl \
                    unzip && \
    apt-get clean && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# FreeSurfer 7.3.2
FROM downloader AS freesurfer
COPY docker/files/freesurfer7.3.2-exclude.txt /usr/local/etc/freesurfer7.3.2-exclude.txt
RUN curl -sSL https://surfer.nmr.mgh.harvard.edu/pub/dist/freesurfer/7.3.2/freesurfer-linux-ubuntu22_amd64-7.3.2.tar.gz \
     | tar zxv --no-same-owner -C /opt --exclude-from=/usr/local/etc/freesurfer7.3.2-exclude.txt

# Micromamba
FROM downloader AS micromamba

# Install a C compiler to build extensions when needed.
# traits<6.4 wheels are not available for Python 3.11+, but build easily.
RUN apt-get update && \
    apt-get install -y --no-install-recommends build-essential && \
    apt-get clean && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

WORKDIR /
# Bump the date to current to force update micromamba
RUN echo "2024.02.06"
RUN curl -Ls https://micro.mamba.pm/api/micromamba/linux-64/latest | tar -xvj bin/micromamba

ENV MAMBA_ROOT_PREFIX="/opt/conda"
COPY env.yml /tmp/env.yml
WORKDIR /tmp
RUN micromamba create -y -f /tmp/env.yml && \
    micromamba clean -y -a

#
# Main stage
#
FROM ${BASE_IMAGE} AS fspost

# Configure apt
ENV DEBIAN_FRONTEND="noninteractive" \
    LANG="en_US.UTF-8" \
    LC_ALL="en_US.UTF-8"

# Some baseline tools; bc is needed for FreeSurfer, so don't drop it
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
                    bc \
                    ca-certificates \
                    curl \
                    git \
                    gnupg \
                    lsb-release \
                    netbase \
                    xvfb && \
    apt-get clean && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# Install files from stages
COPY --from=freesurfer /opt/freesurfer /opt/freesurfer

# Simulate SetUpFreeSurfer.sh
ENV OS="Linux" \
    FS_OVERRIDE=0 \
    FIX_VERTEX_AREA="" \
    FSF_OUTPUT_FORMAT="nii.gz" \
    FREESURFER_HOME="/opt/freesurfer"
ENV SUBJECTS_DIR="$FREESURFER_HOME/subjects" \
    FUNCTIONALS_DIR="$FREESURFER_HOME/sessions" \
    MNI_DIR="$FREESURFER_HOME/mni" \
    LOCAL_DIR="$FREESURFER_HOME/local" \
    MINC_BIN_DIR="$FREESURFER_HOME/mni/bin" \
    MINC_LIB_DIR="$FREESURFER_HOME/mni/lib" \
    MNI_DATAPATH="$FREESURFER_HOME/mni/data"
ENV PERL5LIB="$MINC_LIB_DIR/perl5/5.8.5" \
    MNI_PERL5LIB="$MINC_LIB_DIR/perl5/5.8.5" \
    PATH="$FREESURFER_HOME/bin:$FREESURFER_HOME/tktools:$MINC_BIN_DIR:$PATH"

# AFNI config
ENV PATH="/opt/afni-latest:$PATH" \
    AFNI_IMSAVE_WARNINGS="NO" \
    AFNI_PLUGINPATH="/opt/afni-latest"

# Create a shared $HOME directory
RUN useradd -m -s /bin/bash -G users freesurfer-post
WORKDIR /home/freesurfer-post
ENV HOME="/home/freesurfer-post" \
    LD_LIBRARY_PATH="/usr/lib/x86_64-linux-gnu:$LD_LIBRARY_PATH"

COPY --from=micromamba /bin/micromamba /bin/micromamba
COPY --from=micromamba /opt/conda/envs/freesurfer-post /opt/conda/envs/freesurfer-post

ENV MAMBA_ROOT_PREFIX="/opt/conda"
RUN micromamba shell init -s bash && \
    echo "micromamba activate freesurfer-post" >> $HOME/.bashrc
ENV PATH="/opt/conda/envs/freesurfer-post/bin:$PATH" \
    CPATH="/opt/conda/envs/freesurfer-post/include:$CPATH" \
    LD_LIBRARY_PATH="/opt/conda/envs/freesurfer-post/lib:$LD_LIBRARY_PATH"

# FSL environment
ENV LANG="C.UTF-8" \
    LC_ALL="C.UTF-8" \
    PYTHONNOUSERSITE=1 \
    FSLDIR="/opt/conda/envs/freesurfer-post" \
    FSLOUTPUTTYPE="NIFTI_GZ" \
    FSLMULTIFILEQUIT="TRUE" \
    FSLLOCKDIR="" \
    FSLMACHINELIST="" \
    FSLREMOTECALL="" \
    FSLGECUDAQ="cuda.q"

# Unless otherwise specified each process should only use one thread - nipype
# will handle parallelization
ENV MKL_NUM_THREADS=1 \
    OMP_NUM_THREADS=1

# Installing FMRIPREP
COPY --from=src /src/dist/*.whl .
RUN pip install --no-cache-dir $( ls *.whl )[container,test]

RUN find $HOME -type d -exec chmod go=u {} + && \
    find $HOME -type f -exec chmod go=u {} + && \
    rm -rf  $HOME/.conda $HOME/.empty

# Get the annots from the original freesurfer_tabulate
RUN git clone https://github.com/pennlinc/freesurfer_tabulate.git /opt/freesurfer_tabulate

# For detecting the container
ENV IS_DOCKER_8395080871=1

RUN ldconfig
WORKDIR /tmp
ENTRYPOINT ["/opt/conda/envs/freesurfer-post/bin/freesurfer-post"]

ARG BUILD_DATE
ARG VCS_REF
ARG VERSION
LABEL org.label-schema.build-date=$BUILD_DATE \
      org.label-schema.name="freesurfer-post" \
      org.label-schema.description="FreeSurfer Post-processing tool" \
      org.label-schema.url="https://freesurfer-post.readthedocs.io" \
      org.label-schema.vcs-ref=$VCS_REF \
      org.label-schema.version=$VERSION \
      org.label-schema.schema-version="1.0"