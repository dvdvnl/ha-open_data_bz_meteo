FROM dvdvnl/devcontainer:python-3.12

# Install necessary packages for Home Assistant and development
RUN apt-get update && apt-get install -y --no-install-recommends \
  python3-pip python3-dev python3-venv autoconf \
  libssl-dev libxml2-dev libxslt1-dev libjpeg-dev libffi-dev \
  libudev-dev zlib1g-dev pkg-config libavformat-dev libavcodec-dev \
  libavdevice-dev libavutil-dev libswscale-dev libswresample-dev \
  libavfilter-dev ffmpeg libgammu-dev build-essential bash-completion

# Setup workdir
WORKDIR /config

# Install Python dependencies
RUN pip install homeassistant==2025.1.4 open-data-bz-meteo==1.0.0a2 pytest-cov>=7.0 pytest>=7.0

# Keep the container running
CMD ["sleep", "infinity"]
