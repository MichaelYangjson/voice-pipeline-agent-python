#!/bin/bash

if [ -f logs/agent.pid ]; then
    pid=$(cat logs/agent.pid)
    kill $pid
    rm logs/agent.pid
    echo "Agent stopped (PID: $pid)"
else
    echo "Agent PID file not found"
fi