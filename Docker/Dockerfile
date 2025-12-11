FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1

# Install system packages and disk tools
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
        python3-pip \
        jq \
        && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Install Python dependencies (DB logging etc.)
# If you later add a requirements.txt, switch this to `-r requirements.txt`
RUN python3 -m pip install --no-cache-dir \
        psycopg2-binary

# App directory
WORKDIR /wiper

# copy the app package (matches your current structure)
COPY Docker/wiper /wiper

# make sure a logs dir exists (even if you also mount one from host)
RUN mkdir -p /wiper/logs

# copy entrypoint
COPY Docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
