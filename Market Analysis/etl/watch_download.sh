#!/bin/zsh
# Live progress for the Denton 2025 certified JSON download (refreshes every 10 s; Ctrl-C to stop).
DIR="/Users/user2/PTP/CAD Website/Denton/Data/denton_prior_download/json_2025"
PARTS="$DIR/Denton_JSON_ALL_CERTIFIED_2025.zip.parts"
TOTAL=2293795469
prev=0
while true; do
  clear
  echo "Denton 2025 certified JSON export  (dentoncad.net, 2,294 MB)"
  echo
  if [ -d "$PARTS" ]; then
    kb=$(du -sk "$PARTS" | cut -f1)
  elif [ -f "$DIR/Denton_JSON_ALL_CERTIFIED_2025.zip" ]; then
    kb=$(( TOTAL / 1024 ))
  else
    kb=0
  fi
  b=$(( kb * 1024 )); [ $b -gt $TOTAL ] && b=$TOTAL
  pct=$(( b * 100 / TOTAL ))
  fill=$(( pct / 5 ))
  bar=""; for i in $(seq 1 20); do [ $i -le $fill ] && bar="${bar}#" || bar="${bar}-"; done
  speed=0; [ $prev -gt 0 ] && speed=$(( (kb - prev) / 10 ))
  prev=$kb
  left=$(( (TOTAL - b) / 1024 ))
  eta="--"; [ $speed -gt 0 ] && eta="$(( left / speed / 60 )) min"
  echo "[$bar] $pct%   $(( b / 1048576 )) MB of $(( TOTAL / 1048576 )) MB"
  echo "speed: ${speed} KB/s    time left: $eta"
  echo "active connections: $(pgrep -f 'Denton_JSON_ALL_CERTIFIED_2025' | wc -l | tr -d ' ')"
  if ! pgrep -f par_download.py >/dev/null && [ ! -d "$PARTS" ]; then
    echo; echo "Download finished."; break
  fi
  sleep 10
done
