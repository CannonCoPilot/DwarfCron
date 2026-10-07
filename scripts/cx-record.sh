#!/bin/bash
# ===========================================================================
# cx-record.sh — record the Dwarf Fortress window as video, GIF and frames
# ===========================================================================
# Records the DF window itself (ScreenCaptureKit via cx-wincap.swift, so a
# terminal over it is never recorded) into ffmpeg, so animations and real-time anomalies (a band
# left by a pan, a fish drawn twice) can be watched frame by frame instead of
# guessed from screenshot bursts.
#
#   cx-record.sh SECONDS [NAME] [options]
#     --fps N          capture rate (default 30)
#     --crop X,Y,W,H   only this part of the window (window pixels)
#     --scale W        output width for the GIF (default 960; -1 keeps it)
#     --gif            also write NAME.gif (palette-optimised)
#     --frames N       also write PNG frames at N per second into frames/
#     --out DIR        output folder (default data/recordings/<time>-NAME)
#
# Prints the output folder. Needs ffmpeg (brew install ffmpeg) and Screen
# Recording permission for the terminal (the same one screencapture uses).
# The window must be on screen (any Space); covered by other windows is fine.
# Read-only toward the game: it never sends DF a key or an RPC.
# ===========================================================================
set -euo pipefail
here="$(cd "$(dirname "$0")/.." && pwd)"
secs="${1:?usage: cx-record.sh SECONDS [NAME] [--fps N] [--crop X,Y,W,H] [--scale W] [--gif] [--frames N] [--out DIR]}"
shift
name="clip"
if [ $# -gt 0 ] && [ "${1#--}" = "$1" ]; then name="$1"; shift; fi
fps=30 crop="" scale=960 gif=0 frames=0 out=""
while [ $# -gt 0 ]; do
    case "$1" in
        --fps) fps="$2"; shift 2 ;;
        --crop) crop="$2"; shift 2 ;;
        --scale) scale="$2"; shift 2 ;;
        --gif) gif=1; shift ;;
        --frames) frames="$2"; shift 2 ;;
        --out) out="$2"; shift 2 ;;
        *) echo "cx-record: unknown option $1" >&2; exit 2 ;;
    esac
done
command -v ffmpeg >/dev/null || { echo "cx-record: ffmpeg not found (brew install ffmpeg)" >&2; exit 3; }

# the DF window: id|pid|onscreen|owner|title|x,y,WxH (points)
win=$(swift "$here/scripts/cx-winid.swift" 2>/dev/null | grep "onscreen=true" | grep "|Dwarf Fortress|" | head -1 || true)
[ -n "$win" ] || { echo "cx-record: no on-screen Dwarf Fortress window" >&2; exit 4; }
wid="${win%%|*}"; geo="${win##*|}"; wh="${geo#*,}"; wh="${wh#*,}"; ww="${wh%x*}"; whh="${wh#*x}"
# ScreenCaptureKit captures the window itself (covered or not); built once
bin="$here/scripts/.bin/cx-wincap"
if [ ! -x "$bin" ] || [ "$here/scripts/cx-wincap.swift" -nt "$bin" ]; then
    mkdir -p "$here/scripts/.bin"
    swiftc -O -o "$bin" "$here/scripts/cx-wincap.swift" 2>&1 | grep -v "^$" >&2 || true
    [ -x "$bin" ] || { echo "cx-record: could not build cx-wincap" >&2; exit 5; }
fi
sc=$(swift -e 'import AppKit; print(Int(NSScreen.main?.backingScaleFactor ?? 1))' 2>/dev/null || echo 1)
pw=$((ww * sc)) ph=$((whh * sc)) # the frames' size, as cx-wincap asks for it
vf="null"
if [ -n "$crop" ]; then
    IFS=, read -r ox oy ow oh <<<"$crop"
    vf="crop=$(( ow * sc / 2 * 2 )):$(( oh * sc / 2 * 2 )):$((ox * sc)):$((oy * sc))"
else
    vf="crop=$((pw / 2 * 2)):$((ph / 2 * 2)):0:0" # h264 wants even sizes
fi

[ -n "$out" ] || out="$here/data/recordings/$(date +%Y%m%d-%H%M%S)-$name"
mkdir -p "$out"
mp4="$out/$name.mp4"
"$bin" "$wid" "$secs" "$fps" 2>"$out/capture.log" |
    ffmpeg -hide_banner -loglevel error -y -f rawvideo -pix_fmt bgra -s "${pw}x${ph}" -framerate "$fps" -i - \
        -vf "$vf" -c:v libx264 -preset veryfast -crf 18 -pix_fmt yuv420p "$mp4"
if [ "$gif" = 1 ]; then
    ffmpeg -hide_banner -loglevel error -y -i "$mp4" \
        -vf "fps=$((fps > 15 ? 15 : fps)),scale=$scale:-1:flags=lanczos,split[a][b];[a]palettegen=stats_mode=diff[p];[b][p]paletteuse=dither=bayer:bayer_scale=4" \
        "$out/$name.gif"
fi
if [ "$frames" != 0 ]; then
    mkdir -p "$out/frames"
    ffmpeg -hide_banner -loglevel error -y -i "$mp4" -vf "fps=$frames" "$out/frames/%04d.png"
fi
n=$(ffprobe -v error -count_frames -select_streams v:0 -show_entries stream=nb_read_frames -of csv=p=0 "$mp4" 2>/dev/null || echo "?")
echo "cx-record: $out ($n frames over ${secs}s; window $wid ${pw}x${ph}; $(tail -1 "$out/capture.log"))"
