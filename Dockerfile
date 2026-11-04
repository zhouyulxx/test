# Reproducible Ada SM89 / RTX 4090 Hy-Nomas StreetView experimental image.
# The upstream image contains PyTorch/CUDA; this Dockerfile DOES NOT bundle weights.
FROM hynomasoss/hynomasoss:cu130
ARG UPSTREAM_COMMIT=a31c0fe0bcc493be188fd37ddba4ce2f674becb4
ENV NOMAS_ROOT=/Hy-Nomas \
    CUTLASS_PATH=/opt/cutlass \
    NOMAS_MODELS_DIR=/workspace/models \
    HF_HOME=/workspace/hf_cache \
    NOMAS_HTTP_PROXY_PORT=8081 \
    PORT=18084 \
    STREETVIEW_EXPORT_FRAMES=1 \
    STREETVIEW_FRAME_STRIDE=4 \
    PYTHONUNBUFFERED=1
WORKDIR /Hy-Nomas
RUN git init -q /Hy-Nomas \
    && git -C /Hy-Nomas remote add origin https://github.com/Tencent-Hunyuan/Hy-Nomas.git \
    && git -C /Hy-Nomas fetch --depth 1 origin ${UPSTREAM_COMMIT} \
    && git -C /Hy-Nomas checkout --force FETCH_HEAD \
    && if [ -d /opt/cutlass ] && [ -n "$(ls -A /opt/cutlass 2>/dev/null)" ]; then \
         echo "Reusing CUTLASS bundled with base image"; \
       else \
         rm -rf /opt/cutlass; \
         git clone --depth 1 https://github.com/NVIDIA/cutlass.git /opt/cutlass; \
       fi
COPY deploy /opt/streetview/deploy
COPY streetview /opt/streetview/streetview
COPY viewer /opt/streetview/viewer
COPY streetview /Hy-Nomas/streetview
RUN python /opt/streetview/deploy/patch_upstream.py /Hy-Nomas \
    && npm --prefix /Hy-Nomas/apps/frontend ci \
    && npm --prefix /Hy-Nomas/apps/frontend run build \
    && mkdir -p /Hy-Nomas/apps/frontend/dist/streetview \
    && chmod +x /opt/streetview/deploy/*.sh
# Re-copy after npm build: vite overwrites dist on build.
COPY viewer/ /Hy-Nomas/apps/frontend/dist/streetview/
EXPOSE 8081
HEALTHCHECK --interval=90s --timeout=10s --start-period=15m --retries=3 \
  CMD python /opt/streetview/deploy/check-health.py || exit 1
CMD ["/bin/bash", "/opt/streetview/deploy/entrypoint.sh"]
