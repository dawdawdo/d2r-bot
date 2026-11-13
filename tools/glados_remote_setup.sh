#!/bin/bash
# One-time GLaDOS setup for running the bot without a local monitor/KVM (2026-11-13).
#   sudo bash tools/glados_remote_setup.sh
# - LightDM auto-logs stephen into Cinnamon on the real screen (:0), where D2R and /dev/uinput live.
# - x11vnc (started from ~/.config/autostart/x11vnc.desktop) shares :0 on port 5900, so a VNC viewer on
#   Singularity sees the same screen the bot plays on. xrdp's own sessions (:10) can't run the bot.
# - Restarts LightDM 20 s after the script ends: log out of the RDP session right away.
set -euo pipefail
[ "$(id -u)" = 0 ] || { echo "run with sudo"; exit 1; }
USER_NAME=stephen

apt-get update -qq
apt-get install -y x11vnc

cat > /etc/lightdm/lightdm.conf.d/80-autologin.conf <<EOF
[Seat:*]
autologin-user=$USER_NAME
autologin-user-timeout=0
autologin-session=cinnamon
EOF
echo "auto-login: /etc/lightdm/lightdm.conf.d/80-autologin.conf"

if [ ! -s /home/$USER_NAME/.vnc/passwd ]; then
  echo "Pick a VNC password (VNC uses only the first 8 characters):"
  sudo -u $USER_NAME mkdir -p /home/$USER_NAME/.vnc
  sudo -u $USER_NAME x11vnc -storepasswd /home/$USER_NAME/.vnc/passwd
fi

systemd-run --on-active=20 --unit=lightdm-restart-once systemctl restart lightdm
echo "LightDM restarts in 20 s. Log out of RDP now, then connect a VNC viewer to $(hostname -I | awk '{print $1}'):5900"
