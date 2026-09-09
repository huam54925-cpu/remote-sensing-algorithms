# 构建时必须指定经过验证的官方 Python slim 镜像及 sha256 digest。
ARG PYTHON_BASE=python:3.13-slim-trixie@sha256:9d2e5553305c7c7b0097999bb17187c69b921ccd6bc9d40e4bb5ebe652c00285
FROM ${PYTHON_BASE} AS build
WORKDIR /build
COPY src/ /build/src/
COPY requirements.lock /build/requirements.lock
RUN python -m pip install --no-cache-dir --prefix=/install -r /build/requirements.lock && \
    PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/build/src:/install/lib/python3.13/site-packages \
    python -m rs_container --healthcheck

COPY deps/python-transitive.lock /build/python-transitive.lock
RUN python -m pip install --no-cache-dir --no-deps --prefix=/install -r /build/python-transitive.lock

FROM ${PYTHON_BASE} AS runtime
ARG VERSION=0.3.0
ARG BUILD_ID
LABEL org.opencontainers.image.title="Remote sensing MNDWI and KMeans batch examples" \
      org.opencontainers.image.version="${VERSION}" \
      org.opencontainers.image.revision="${BUILD_ID}" \
      org.opencontainers.image.description="MNDWI and KMeans GeoTIFF batch examples"
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/app/src HOME=/tmp OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
WORKDIR /app
COPY deps/debs/ /tmp/system-debs/
# Official Debian packages downloaded with apt signature verification; versions
# and checksums are retained so rebuilding does not select mutable apt versions.
RUN cd /tmp/system-debs && sha256sum -c SHA256SUMS && \
    dpkg -i ./*.deb && apt-get purge -y mount && \
    rm -rf /tmp/system-debs /var/lib/apt/lists/*
COPY --from=build /build/src/ /app/src/
COPY --from=build /install/ /usr/local/
RUN python -c 'import rasterio, numpy, sklearn, ssl, sqlite3; print(rasterio.__version__)' && \
    python -m pip uninstall -y pip
COPY scripts/healthcheck.sh /app/healthcheck.sh
COPY scripts/check-host.py /app/check-host.py
RUN test -x /bin/sh && mkdir -p /data/input /data/output /data/work && chmod 755 /app/healthcheck.sh
USER 10001:10001
# 批处理无监听端口。只读根文件系统必须由运行配置实施。
ENTRYPOINT ["python", "-m", "rs_container"]
CMD ["--help"]
