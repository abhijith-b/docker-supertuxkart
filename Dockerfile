# -----------
# Build stage
# -----------
    FROM ubuntu:24.04 AS build
    LABEL maintainer="jwestp"
    WORKDIR /stk
    
    # Set stk version to build
    ENV VERSION=1.4
    
    # Install build dependencies
    ARG DEBIAN_FRONTEND=noninteractive
    RUN apt-get update && \
        apt-get install --no-install-recommends -y \
            build-essential \
            cmake \
            git \
            libcurl4-openssl-dev \
            libenet-dev \
            libssl-dev \
            pkg-config \
            subversion \
            zlib1g-dev \
            ca-certificates && \
        rm -rf /var/lib/apt/lists/*
    
    # Clone source code
    RUN git clone --branch ${VERSION} --depth=1 https://github.com/supertuxkart/stk-code.git
    RUN svn checkout https://svn.code.sf.net/p/supertuxkart/code/stk-assets-release/1.1/ stk-assets
    
    # Build server
    RUN mkdir stk-code/cmake_build && \
        cd stk-code/cmake_build && \
        cmake .. \
            -DSERVER_ONLY=ON \
            -DUSE_SYSTEM_ENET=ON \
            -DCMAKE_BUILD_TYPE=Release \
            -DCMAKE_CXX_FLAGS="-O3 -march=native" && \
        make -j$(nproc) && \
        make install
    
    # -----------
    # Final stage
    # -----------
    FROM ubuntu:24.04
    LABEL maintainer="jwestp"
    
    # Create non-root user for security
    RUN useradd -r -s /bin/false stk
    WORKDIR /stk
    
    # Install runtime dependencies
    RUN apt-get update && \
        apt-get install --no-install-recommends -y \
            libcurl4-openssl-dev \
            libssl3 && \
        rm -rf /var/lib/apt/lists/*
    
    # Copy artifacts from build stage
    COPY --from=build /usr/local/bin/supertuxkart /usr/local/bin/
    COPY --from=build /usr/local/share/supertuxkart /usr/local/share/supertuxkart/
    COPY start.sh /stk/
    
    # Set permissions and switch user
    RUN chown -R stk:stk /stk && \
        chmod +x /stk/start.sh
    
    USER stk
    
    # Expose the ports used to find and connect to the server
    EXPOSE 2757/udp
    EXPOSE 2759/tcp
    
    ENTRYPOINT ["/stk/start.sh"]
