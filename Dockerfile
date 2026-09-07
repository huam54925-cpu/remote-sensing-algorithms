# 构建时必须指定经过验证的官方 Python slim 镜像及 sha256 digest。
ARG PYTHON_BASE
FROM ${PYTHON_BASE} AS build
WORKDIR /build
COPY src/ /build/src/
COPY requirements.lock /build/requirements.lock
RUN python -m pip install --no-cache-dir --prefix=/install -r /build/requirements.lock && \
    PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/build/src:/install/lib/python3.13/site-packages \
    python -m rs_container --healthcheck

FROM ${PYTHON_BASE} AS runtime
ARG VERSION=0.2.0
ARG BUILD_ID
LABEL org.opencontainers.image.title="Remote sensing MNDWI batch example" \
      org.opencontainers.image.version="${VERSION}" \
      org.opencontainers.image.revision="${BUILD_ID}" \
      org.opencontainers.image.description="MNDWI GeoTIFF batch example"
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/app/src HOME=/tmp
WORKDIR /app
COPY --from=build /build/src/ /app/src/
COPY --from=build /install/ /usr/local/
COPY scripts/healthcheck.sh /app/healthcheck.sh
RUN test -x /bin/sh && mkdir -p /data/input /data/output /data/work && chmod 755 /app/healthcheck.sh
USER 10001:10001
# 批处理无监听端口。只读根文件系统必须由运行配置实施。
ENTRYPOINT ["python", "-m", "rs_container"]
CMD ["--help"]
