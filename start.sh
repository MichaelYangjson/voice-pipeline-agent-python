#!/bin/bash

# 设置颜色输出
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

# 创建日志目录
echo "创建日志目录..."
if mkdir -p logs; then
    echo -e "${GREEN}✓ 日志目录创建成功${NC}"
else
    echo -e "${RED}✗ 创建日志目录失败${NC}"
    exit 1
fi

# 检查并激活 conda 环境
echo -e "\n检查 conda 环境..."
if ! command -v conda &> /dev/null; then
    echo -e "${RED}✗ conda 未安装或未添加到 PATH${NC}"
    exit 1
fi

eval "$(conda shell.bash hook)"
if conda activate voice 2>/dev/null; then
    echo -e "${GREEN}✓ Conda 环境 'voice' 已激活${NC}"
    echo -e "${YELLOW}Python 路径: $(which python)${NC}"
    echo -e "${YELLOW}Python 版本: $(python --version)${NC}"
else
    echo -e "${RED}✗ 无法激活 Conda 环境 'voice'${NC}"
    exit 1
fi

# 检查必要的 Python 包
echo -e "\n检查 Python 依赖..."
if ! python -c "import livekit" 2>/dev/null; then
    echo -e "${RED}✗ 缺少必要的 Python 包: livekit${NC}"
    exit 1
fi

# 检查是否已有实例在运行
if [ -f logs/agent.pid ]; then
    OLD_PID=$(cat logs/agent.pid)
    if ps -p $OLD_PID > /dev/null 2>&1; then
        echo -e "${RED}✗ Agent 服务已在运行 (PID: $OLD_PID)${NC}"
        exit 1
    else
        rm logs/agent.pid
    fi
fi

# 启动 agent
echo -e "\n启动 Agent 服务..."
nohup python agent.py > logs/agent.log 2>&1 &
PID=$!

# 保存进程 ID
echo $PID > logs/agent.pid

# 实时显示日志并检查启动状态
echo -e "\n等待服务启动..."
attempt=0
max_attempts=30

(tail -f logs/agent.log) &
TAIL_PID=$!

while [ $attempt -lt $max_attempts ]; do
    if ! ps -p $PID > /dev/null; then
        echo -e "${RED}✗ Agent 进程已终止${NC}"
        kill $TAIL_PID
        echo -e "${YELLOW}错误日志:${NC}"
        tail -n 20 logs/agent.log
        exit 1
    fi

    if grep -q "VAD model loaded successfully" logs/agent.log; then
        echo -e "\n${GREEN}✓ Agent 服务已成功启动${NC}"
        echo -e "${GREEN}✓ PID: $PID${NC}"
        echo -e "${YELLOW}完整日志请查看: logs/agent.log${NC}"
        kill $TAIL_PID
        exit 0
    fi

    attempt=$((attempt + 1))
    sleep 1
done

# 如果超时
kill $TAIL_PID
echo -e "${RED}✗ 服务启动超时${NC}"
echo -e "${YELLOW}最后 20 行日志:${NC}"
tail -n 20 logs/agent.log
exit 1