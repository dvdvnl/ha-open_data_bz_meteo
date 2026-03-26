FROM dvdvnl/devcontainer:python-3.14

# Install necessary packages for Home Assistant and development
RUN apt-get update && apt-get install -y --no-install-recommends \
  python3-pip python3-dev python3-venv autoconf \
  libssl-dev libxml2-dev libxslt1-dev libjpeg-dev libffi-dev \
  libudev-dev zlib1g-dev pkg-config libavformat-dev libavcodec-dev \
  libavdevice-dev libavutil-dev libswscale-dev libswresample-dev \
  libavfilter-dev ffmpeg libgammu-dev build-essential

# Setup workdir
WORKDIR /config

# Install Python dependencies
RUN pip install homeassistant open-data-bz-meteo==1.0.0a1 pytest-cov pytest

# Keep the container running
CMD ["sleep", "infinity"]
