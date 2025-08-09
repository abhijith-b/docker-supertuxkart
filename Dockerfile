# -----------
# Build stage
# -----------
    FROM debian:bookworm-slim AS build
    LABEL maintainer="jwestp"
    WORKDIR /stk
    
    # Build arguments for version control
    ARG STK_VERSION=master
    ARG BUILD_DATE
    ARG VCS_REF
    
    # Install build dependencies (following official STK build guide)
    ARG DEBIAN_FRONTEND=noninteractive
    RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
        --mount=type=cache,target=/var/lib/apt,sharing=locked \
        apt-get update && \
        apt-get install --no-install-recommends -y \
            # Build tools
            build-essential \
            cmake \
            git \
            subversion \
            pkg-config \
            ca-certificates \
            # Core STK dependencies (exact match from official docs)
            libbluetooth-dev \
            libsdl2-dev \
            libcurl4-openssl-dev \
            libenet-dev \
            libfreetype6-dev \
            libharfbuzz-dev \
            libjpeg62-turbo-dev \
            libogg-dev \
            libopenal-dev \
            libpng-dev \
            libssl-dev \
            libvorbis-dev \
            libmbedtls-dev \
            zlib1g-dev \
            # Additional dependencies for server build
            libsqlite3-dev
    
    # Clone source code with specific versions for reproducibility
    RUN git clone --depth=1 --branch=${STK_VERSION} https://github.com/supertuxkart/stk-code stk-code || \
        git clone --depth=1 https://github.com/supertuxkart/stk-code stk-code
    RUN svn co https://svn.code.sf.net/p/supertuxkart/code/stk-assets stk-assets
    
    # Build server (following official cmake options)
    RUN --mount=type=cache,target=/stk/stk-code/cmake_build,sharing=locked \
        mkdir -p stk-code/cmake_build && \
        cd stk-code/cmake_build && \
        cmake .. \
            -DSERVER_ONLY=ON \
            -DUSE_SQLITE3=ON \
            -DUSE_SYSTEM_ENET=ON \
            -DCMAKE_BUILD_TYPE=Release \
            -DBUILD_RECORDER=OFF \
            -DNO_SHADERC=ON \
            -DCMAKE_CXX_FLAGS="-O3" && \
        make -j$(nproc) && \
        make install
    
    # -----------
    # Final stage
    # -----------
    FROM debian:bookworm-slim
    
    # Import build arguments
    ARG STK_VERSION=${STK_VERSION}
    ARG BUILD_DATE
    ARG VCS_REF
    
    # Metadata labels following OCI standards
    LABEL maintainer="jwestp" \
          org.label-schema.name="SuperTuxKart Server" \
          org.label-schema.description="Containerized SuperTuxKart dedicated server with SQLite support" \
          org.label-schema.version="${STK_VERSION}" \
          org.label-schema.build-date="${BUILD_DATE}" \
          org.label-schema.vcs-ref="${VCS_REF}" \
          org.label-schema.vcs-url="https://github.com/supertuxkart/stk-code" \
          org.label-schema.schema-version="1.0"
    
    # Create non-root user for security
    RUN useradd -r -s /bin/false stk
    WORKDIR /stk
    
    # Install runtime dependencies (minimal set for STK server)
    RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
        --mount=type=cache,target=/var/lib/apt,sharing=locked \
        apt-get update && \
        apt-get install --no-install-recommends -y \
            # Core runtime libraries (matching STK build dependencies)
            libcurl4 \
            libssl3 \
            libsqlite3-0 \
            libenet7 \
            libfreetype6 \
            libharfbuzz0b \
            libjpeg62-turbo \
            libogg0 \
            libopenal1 \
            libpng16-16 \
            libvorbis0a \
            zlib1g \
            libbluetooth3 \
            libsdl2-2.0-0 \
            # System utilities
            netcat-openbsd \
            sqlite3 \
            tzdata \
            # Optional utilities (can be removed for smaller image)
            curl \
            dnsutils \
            unzip \
            wget
    
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
    EXPOSE 2759/udp
    
    ENTRYPOINT ["/stk/start.sh"]

