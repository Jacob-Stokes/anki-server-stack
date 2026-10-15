# Optional: the Anki desktop app in a web page (KasmVNC), on the same Anki
# version as the rest of the stack, signed in to the stack's sync server. The
# real AnkiConnect add-on is installed in the image and turned on at start
# when DESKTOP_ANKICONNECT=true.
FROM lscr.io/linuxserver/baseimage-kasmvnc:ubuntunoble

ARG ANKI_VERSION=26.9.3
# AnkiConnect (github.com/FooSoft/anki-connect, archived; the last commit)
ARG ANKICONNECT_REF=4064fa142785975255457abd6a496015f5b71f38

# The app is the pinned version from PyPI, in a venv, with Qt bundled; these
# are the system libraries that Qt build needs, plus audio for card sounds.
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
      python3-venv wget unzip mpv lame \
      libegl1 libgl1 libnss3 libxkbcommon0 libxkbcommon-x11-0 libxcomposite1 libxdamage1 \
      libxrandr2 libxtst6 libxkbfile1 libasound2t64 libdbus-1-3 libfontconfig1 libxshmfence1 \
      libxcb-cursor0 libxcb-icccm4 libxcb-image0 libxcb-keysyms1 libxcb-randr0 libxcb-render-util0 \
      libxcb-shape0 libxcb-xinerama0 libxcb-xkb1 fonts-noto-core fonts-noto-cjk \
 && python3 -m venv /opt/anki \
 && /opt/anki/bin/pip install --no-cache-dir "aqt[qt6]==${ANKI_VERSION}" \
 && mkdir -p /defaults/ankiconnect \
 && wget -q "https://github.com/FooSoft/anki-connect/archive/${ANKICONNECT_REF}.zip" -O /tmp/ac.zip \
 && unzip -q /tmp/ac.zip -d /tmp \
 && cp -r /tmp/anki-connect-*/plugin/. /defaults/ankiconnect/ \
 && rm -rf /tmp/ac.zip /tmp/anki-connect-* /var/lib/apt/lists/*

COPY root/ /

EXPOSE 3000 8765
