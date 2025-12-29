#!/bin/bash
# Power control script - runs on host, listens for commands from container

FIFO_PATH="/tmp/jife-power-control"

# Create FIFO if it doesn't exist
if [ ! -p "$FIFO_PATH" ]; then
    mkfifo "$FIFO_PATH"
    chmod 666 "$FIFO_PATH"
fi

echo "Power control listener started. Waiting for commands..."

while true; do
    if read cmd < "$FIFO_PATH"; then
        case "$cmd" in
            shutdown)
                echo "Shutdown command received"
                sync
                sleep 1
                sudo shutdown -h now
                ;;
            reboot)
                echo "Reboot command received"
                sync
                sleep 1
                sudo reboot
                ;;
            *)
                echo "Unknown command: $cmd"
                ;;
        esac
    fi
done
