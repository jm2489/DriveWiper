FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive

# Install wipe + disk tools
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        nwipe \
        hdparm \
        nvme-cli \
        smartmontools \
        lshw \
        pciutils \
        usbutils \
        util-linux \
        parted \
        python3 \
        jq \
        && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

WORKDIR /wiper
COPY wipe_drive.py /wiper/wipe_drive.py
COPY entrypoint.sh /wiper/entrypoint.sh
RUN chmod +x /wiper/wipe_drive.py

# keep your entrypoint or swap to Python tool later
ENTRYPOINT ["/wiper/entrypoint.sh"]