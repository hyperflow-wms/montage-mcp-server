FROM debian:bookworm-slim

# Install Python 3 and system dependencies
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    wget \
    gcc \
    g++ \
    make \
    git \
    curl \
    libnsl-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Montage toolkit v6.0 - patch Makefiles to add -fcommon to CFLAGS
WORKDIR /tmp
RUN wget http://montage.ipac.caltech.edu/download/Montage_v6.0.tar.gz && \
    tar -xzf Montage_v6.0.tar.gz && \
    cd Montage && \
    echo "Patching Makefiles to add -fcommon flag..." && \
    sed -i '51s/-std=c99$/-std=c99 -fcommon/' Montage/Makefile.LINUX && \
    sed -i '3s/$/ -fcommon/' lib/src/coord/Makefile && \
    echo "Building Montage v6.0..." && \
    make && \
    echo "Copying binaries..." && \
    cp -v bin/* /usr/local/bin/ && \
    cd .. && \
    rm -rf Montage Montage_v6.0.tar.gz

# Install Python dependencies
# Upgrade pip first to get access to latest packages
RUN python3 -m pip install --upgrade --break-system-packages pip setuptools wheel

# Copy requirements and install dependencies
COPY mcp-server/requirements.txt /tmp/requirements.txt
RUN pip3 install --no-cache-dir --break-system-packages -r /tmp/requirements.txt

# Set up application directory
WORKDIR /app

# Copy MCP server files
COPY mcp-server/server.py /app/

# Copy workflow generator scripts to root
COPY montage-workflow-yaml.py /
COPY yaml2hyperflow.py /
COPY validate-workflow.py /
COPY workflow-stats.py /

# Make scripts executable
RUN chmod +x /*.py /app/*.py

# Set environment
ENV MONTAGE_HOME=/usr/local
ENV PATH="/usr/local/bin:${PATH}"

# Expose MCP server (stdio - no port needed)
ENTRYPOINT ["python3", "/app/server.py"]
