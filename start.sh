#!/bin/bash

# 设置颜色输出
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# 错误处理函数
error_exit() {
    echo -e "${RED}Error: $1${NC}" >&2
    exit 1
}

# 检查 Python 是否安装
command -v python3 >/dev/null 2>&1 || error_exit "Python3 is required but not installed."

# 检查虚拟环境是否存在
if [ ! -d "voice" ]; then
    echo -e "${GREEN}Creating virtual environment...${NC}"
    python3 -m venv venv || error_exit "Failed to create virtual environment"
fi

# 激活虚拟环境
echo -e "${GREEN}Activating virtual environment...${NC}"
source venv/bin/activate || error_exit "Failed to activate virtual environment"

# 检查并安装依赖
if [ -f "requirements.txt" ]; then
    echo -e "${GREEN}Installing dependencies...${NC}"
    pip install -r requirements.txt || error_exit "Failed to install dependencies"
else
    error_exit "requirements.txt not found!"
fi

# 检查环境变量文件
if [ ! -f ".env.local" ]; then
    error_exit ".env.local file not found! Please create .env.local file with necessary environment variables."
fi

# 检查日志目录
if [ ! -d "logs" ]; then
    mkdir logs
fi

# 运行应用
echo -e "${GREEN}Starting the agent...${NC}"
python agent.py 2>&1 | tee logs/agent_$(date +%Y%m%d_%H%M%S).log

# 捕获退出信号
cleanup() {
    echo -e "${GREEN}Shutting down...${NC}"
    deactivate
}

trap cleanup EXIT