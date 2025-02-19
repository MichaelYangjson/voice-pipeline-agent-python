#!/bin/bash

# 创建日志目录
mkdir -p logs

# 激活 conda 环境
eval "$(conda shell.bash hook)"
conda activate voice

# 启动 agent
nohup python agent.py > logs/agent.log 2>&1 &

# 保存进程 ID
echo $! > logs/agent.pid

echo "Agent is running in background. PID: $(cat logs/agent.pid)"
echo "Check logs/agent.log for output."