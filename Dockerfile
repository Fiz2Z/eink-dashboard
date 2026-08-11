# Static Web Bluetooth host for EPD-nRF5 compatible e-ink panels.
# Localhost is a secure context → Chrome/Edge can use Web Bluetooth.

FROM nginx:1.27-alpine

LABEL org.opencontainers.image.title="eink-dashboard"
LABEL org.opencontainers.image.description="Template-based Web Bluetooth host for EPD-nRF5 e-ink displays"
LABEL org.opencontainers.image.source="https://github.com/Fiz2Z/eink-dashboard"
LABEL org.opencontainers.image.licenses="MIT"

# Drop default site content
RUN rm -rf /usr/share/nginx/html/*

COPY docker/nginx.conf /etc/nginx/conf.d/default.conf
COPY index.html /usr/share/nginx/html/index.html
COPY css/ /usr/share/nginx/html/css/
COPY js/ /usr/share/nginx/html/js/
COPY README.md README.en.md LICENSE NOTICE.md /usr/share/nginx/html/

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD wget -qO- http://127.0.0.1/ >/dev/null || exit 1
