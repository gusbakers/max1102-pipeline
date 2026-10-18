FROM mcr.microsoft.com/devcontainers/universal:2
USER root
RUN find /etc/apt/sources.list.d -name '*.list' -exec sed -i '/dl\.yarnpkg\.com/d' {} +
