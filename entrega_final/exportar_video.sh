#!/usr/bin/env bash
set -euo pipefail
export LC_ALL=C

if [[ $# != 2 ]]; then
    echo "Uso: $0 grabacion.mkv Video_Final_Simulacion.mp4" >&2
    exit 2
fi
duracion=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$1")
factor=$(awk -v d="$duracion" 'BEGIN {
    if (!(d > 0)) exit 1
    printf "%.8f", (d > 170 ? 170 / d : 1)
}')
ffmpeg -n -i "$1" -map 0:v:0 -an \
    -vf "setpts=$factor*(PTS-STARTPTS),fps=24,scale=trunc(iw/2)*2:trunc(ih/2)*2" \
    -c:v libx264 -crf 22 -pix_fmt yuv420p -movflags +faststart "$2"
ffprobe -v error -show_entries format=duration -of csv=p=0 "$2" |
    awk '{ if (!($1 > 0 && $1 <= 180)) exit 1; printf "Duración comprobada: %.2f s\n", $1 }'
