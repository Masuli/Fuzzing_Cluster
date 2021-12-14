FROM ubuntu:20.04 AS raspberry

RUN echo "Installing dependencies" && \
    apt-get update && apt-get -y install \
    build-essential \
    zlib1g-dev \
    git \
    subversion \
    nano

RUN echo "Downloading AFL" && \
    mkdir AFL && \
    cd AFL && \
    git clone https://github.com/google/AFL.git . && \
    make install

RUN echo "Downloading libpng" && \
    mkdir libpng && \
    cd libpng && \
    git clone git://git.code.sf.net/p/libpng/code . && \
    svn export https://github.com/google/AFL/trunk/experimental/libpng_no_checksum/libpng-nocrc.patch && \
    git apply libpng-nocrc.patch

RUN echo "Compiling libpng and fuzz target" && \
    cd libpng && \
    ./configure --disable-shared && \
    make CC=afl-gcc && \
    afl-gcc contrib/libtests/readpng.c .libs/libpng16.a -lm -lz -o readpng && \
    echo "Creating fuzz environment" && \
    cd .. && \
    mkdir fuzz && \
    cd fuzz && \
    mkdir output && \
    svn export https://github.com/mozillasecurity/fuzzdata.git/trunk/samples/png/common/

RUN echo "Downloading and enabling SSH" && \
    DEBIAN_FRONTEND=noninteractive apt-get -y install openssh-server && \
    mkdir /var/run/sshd && \
    echo 'root:afldocker' | chpasswd && \
    sed -i 's/#PermitRootLogin prohibit-password/PermitRootLogin yes/' /etc/ssh/sshd_config && \
    sed 's@session\s*required\s*pam_loginuid.so@session optional pam_loginuid.so@g' -i /etc/pam.d/sshd

EXPOSE 22
CMD service ssh start && echo core >/proc/sys/kernel/core_pattern && afl-fuzz -i fuzz/common/ -o fuzz/output/ ./libpng/readpng