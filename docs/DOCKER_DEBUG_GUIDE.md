# OpenFinance Docker 调试指南

> 版本: 1.0.0  
> 更新日期: 2026-02-13

---

## 目录

1. [环境准备](#一环境准备)
2. [容器启动与管理](#二容器启动与管理)
3. [调试配置](#三调试配置)
4. [日志收集与分析](#四日志收集与分析)
5. [常见问题排查](#五常见问题排查)
6. [性能调优](#六性能调优)

---

## 一、环境准备

### 1.1 系统要求

| 组件 | 最低版本 | 推荐版本 |
|------|----------|----------|
| Docker | 24.0+ | 25.0+ |
| Docker Compose | 2.20+ | 2.23+ |
| VS Code | 1.85+ | 最新版 |
| Python | 3.11+ | 3.12 |
| Node.js | 18+ | 20 LTS |

### 1.2 安装 VS Code 扩展

```bash
# 必需扩展
code --install-extension ms-python.python
code --install-extension ms-python.vscode-pylance
code --install-extension ms-azuretools.vscode-docker
code --install-extension dbaeumer.vscode-eslint

# 推荐扩展
code --install-extension charliermarsh.ruff
code --install-extension esbenp.prettier-vscode
code --install-extension eamodio.gitlens
```

### 1.3 环境变量配置

创建 `.env` 文件：

```bash
# 复制示例配置
cp .env.example .env

# 编辑配置
vim .env
```

关键配置项：

```env
# LLM API Keys
OPENAI_API_KEY=sk-xxx
ANTHROPIC_API_KEY=sk-ant-xxx

# Database
DATABASE_URL=postgresql://openfinance:openfinance@postgres:5432/openfinance

# Redis
REDIS_URL=redis://redis:6379/0

# Debug
DEBUG=1
LOG_LEVEL=DEBUG
```

---

## 二、容器启动与管理

### 2.1 开发环境启动

```bash
# 启动所有服务（开发模式）
docker-compose up -d --build

# 查看服务状态
docker-compose ps

# 查看日志
docker-compose logs -f

# 查看特定服务日志
docker-compose logs -f backend
docker-compose logs -f frontend
```

### 2.2 生产环境启动

```bash
# 使用生产配置启动
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
```

### 2.3 监控栈启动

```bash
# 启动包含监控组件的完整栈
docker-compose --profile monitoring up -d

# 访问监控界面
# Grafana: http://localhost:3001 (admin/admin)
# Prometheus: http://localhost:9090
# Loki: http://localhost:3100
```

### 2.4 服务端口映射

| 服务 | 容器端口 | 主机端口 | 用途 |
|------|----------|----------|------|
| Frontend | 3000 | 3000 | Next.js 开发服务器 |
| Frontend Debug | 9229 | 9229 | Node.js 调试器 |
| Backend | 19100 | 19100 | FastAPI 应用 |
| Backend Debug | 5678 | 5678 | Debugpy 调试器 |
| PostgreSQL | 5432 | 5432 | 数据库 |
| Redis | 6379 | 6379 | 缓存 |
| Prometheus | 9090 | 9090 | 监控 |
| Grafana | 3000 | 3001 | 可视化 |
| Loki | 3100 | 3100 | 日志聚合 |

### 2.5 常用管理命令

```bash
# 停止所有服务
docker-compose down

# 停止并删除数据卷
docker-compose down -v

# 重启特定服务
docker-compose restart backend

# 进入容器
docker exec -it openfinance-backend bash
docker exec -it openfinance-frontend sh

# 查看容器资源使用
docker stats

# 清理未使用的资源
docker system prune -a
```

---

## 三、调试配置

### 3.1 后端调试 (Python/FastAPI)

#### 方式一：VS Code 调试器附加

1. **启动容器**

```bash
docker-compose up -d backend
```

2. **在 VS Code 中设置断点**

在代码行左侧点击设置断点（红点）

3. **启动调试**

- 按 `F5` 或点击"运行和调试"
- 选择 **"Backend: Attach to Docker (Debugpy)"**

4. **触发断点**

发送请求到 API 端点，断点会自动触发

#### 方式二：命令行调试

```bash
# 进入容器
docker exec -it openfinance-backend bash

# 使用 ipdb 调试
python -m ipdb -m pytest tests/test_api.py

# 使用 debugpy 等待连接
python -m debugpy --listen 0.0.0.0:5678 --wait-for-client \
    -m uvicorn openfinance.api.main:app --host 0.0.0.0 --port 19100
```

#### 方式三：远程调试配置

在 `.vscode/launch.json` 中：

```json
{
  "name": "Backend: Attach to Docker (Debugpy)",
  "type": "python",
  "request": "attach",
  "connect": {
    "host": "localhost",
    "port": 5678
  },
  "pathMappings": [
    {
      "localRoot": "${workspaceFolder}/backend",
      "remoteRoot": "/app"
    }
  ],
  "justMyCode": false
}
```

### 3.2 前端调试 (Next.js/React)

#### 方式一：Chrome DevTools

1. **启动前端容器**

```bash
docker-compose up -d frontend
```

2. **打开 Chrome DevTools**

- 访问 `chrome://inspect`
- 点击 "Configure" 添加 `localhost:9229`
- 点击 "Inspect" 连接调试

#### 方式二：VS Code 调试器

1. **配置 launch.json**

```json
{
  "name": "Frontend: Attach to Docker (Node)",
  "type": "node",
  "request": "attach",
  "port": 9229,
  "address": "localhost",
  "localRoot": "${workspaceFolder}/frontend",
  "remoteRoot": "/app",
  "skipFiles": ["<node_internals>/**"]
}
```

2. **启动调试**

- 按 `F5` 启动调试会话
- 在代码中设置断点

#### 方式三：React DevTools

```bash
# 安装 React DevTools 浏览器扩展
# 然后访问 http://localhost:3000
# 使用 Components 和 Profiler 标签页调试
```

### 3.3 数据库调试

```bash
# 连接 PostgreSQL
docker exec -it openfinance-postgres psql -U openfinance -d openfinance

# 常用查询
\dt                    # 列出所有表
\d+ table_name         # 查看表结构
SELECT * FROM users LIMIT 10;

# 查看活动连接
SELECT * FROM pg_stat_activity;

# 查看锁
SELECT * FROM pg_locks;
```

### 3.4 Redis 调试

```bash
# 连接 Redis
docker exec -it openfinance-redis redis-cli

# 常用命令
KEYS *                 # 列出所有键
GET key_name           # 获取值
MONITOR                # 实时监控命令
INFO                   # 查看信息
```

---

## 四、日志收集与分析

### 4.1 日志级别配置

```env
# .env
LOG_LEVEL=DEBUG        # DEBUG, INFO, WARNING, ERROR, CRITICAL
LOG_FORMAT=json        # json 或 text
```

### 4.2 查看容器日志

```bash
# 实时查看所有日志
docker-compose logs -f

# 查看最近100行
docker-compose logs --tail=100

# 查看特定服务
docker-compose logs -f backend --tail=50

# 过滤日志
docker-compose logs backend | grep ERROR
docker-compose logs backend | grep "trace_id"
```

### 4.3 使用 Loki 查询日志

访问 Grafana (`http://localhost:3001`)，使用 Explore 功能：

```logql
# 查看后端所有日志
{job="backend"}

# 按级别过滤
{job="backend"} |= "ERROR"

# 按trace_id查询
{job="backend"} |= "trace_id_123"

# JSON字段过滤
{job="backend"} | json | level = "ERROR"

# 统计错误数量
count_over_time({job="backend"} |= "ERROR" [1h])
```

### 4.4 日志分析脚本

```python
# scripts/analyze_logs.py
import json
from collections import Counter
from datetime import datetime

def analyze_logs(log_file: str):
    errors = []
    trace_ids = set()
    
    with open(log_file) as f:
        for line in f:
            try:
                log = json.loads(line)
                if log.get('level') == 'ERROR':
                    errors.append(log)
                if trace_id := log.get('trace_id'):
                    trace_ids.add(trace_id)
            except:
                continue
    
    print(f"Total errors: {len(errors)}")
    print(f"Unique trace IDs: {len(trace_ids)}")
    
    # 按错误类型统计
    error_types = Counter(e.get('message', 'Unknown') for e in errors)
    for msg, count in error_types.most_common(10):
        print(f"  {count}x: {msg[:100]}")

if __name__ == "__main__":
    analyze_logs("/app/logs/app.log")
```

---

## 五、常见问题排查

### 5.1 容器无法启动

```bash
# 检查容器状态
docker-compose ps

# 查看容器日志
docker-compose logs backend

# 检查容器配置
docker inspect openfinance-backend

# 检查端口占用
lsof -i :19100
netstat -tlnp | grep 19100
```

**常见原因：**

1. **端口被占用**
```bash
# 查找占用进程
lsof -i :19100
# 终止进程
kill -9 <PID>
```

2. **数据卷权限问题**
```bash
# 修复权限
sudo chown -R $USER:$USER ./docker
```

3. **内存不足**
```bash
# 检查 Docker 资源
docker info | grep Memory

# 增加 Docker 内存限制（Docker Desktop 设置）
```

### 5.2 调试器无法连接

```bash
# 检查调试端口
docker exec openfinance-backend netstat -tlnp | grep 5678

# 检查防火墙
sudo ufw status

# 测试端口连接
nc -zv localhost 5678
```

**解决方案：**

1. 确保容器启动时暴露了调试端口
2. 检查 VS Code launch.json 配置
3. 重启 VS Code 和 Docker

### 5.3 数据库连接失败

```bash
# 检查 PostgreSQL 状态
docker-compose ps postgres
docker-compose logs postgres

# 测试连接
docker exec openfinance-backend python -c "
import psycopg2
conn = psycopg2.connect('postgresql://openfinance:openfinance@postgres:5432/openfinance')
print('Connected!')
conn.close()
"
```

**常见原因：**

1. **PostgreSQL 未启动**
```bash
docker-compose up -d postgres
```

2. **网络问题**
```bash
# 检查网络
docker network inspect openfinance-network
```

3. **认证失败**
```bash
# 检查用户名密码
docker exec -it openfinance-postgres psql -U openfinance -d openfinance
```

### 5.4 API 请求超时

```bash
# 检查后端日志
docker-compose logs backend | grep timeout

# 检查响应时间
curl -w "Time: %{time_total}s\n" http://localhost:19100/api/health

# 检查进程状态
docker exec openfinance-backend ps aux
```

### 5.5 热重载不工作

**后端：**
```bash
# 确保使用 --reload 参数
# 检查文件挂载
docker exec openfinance-backend ls -la /app

# 重启容器
docker-compose restart backend
```

**前端：**
```bash
# 清除 .next 缓存
docker exec openfinance-frontend rm -rf /app/.next

# 重启容器
docker-compose restart frontend
```

---

## 六、性能调优

### 6.1 容器资源限制

```yaml
# docker-compose.yml
services:
  backend:
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 2G
        reservations:
          cpus: '1'
          memory: 1G
```

### 6.2 数据库优化

```sql
-- 查看慢查询
SELECT * FROM pg_stat_statements 
ORDER BY total_time DESC LIMIT 10;

-- 创建索引
CREATE INDEX CONCURRENTLY idx_chat_messages_trace_id 
ON openfinance.chat_messages(trace_id);

-- 分析表
ANALYZE openfinance.chat_messages;
```

### 6.3 Redis 优化

```bash
# 查看内存使用
docker exec openfinance-redis redis-cli INFO memory

# 设置最大内存
docker exec openfinance-redis redis-cli CONFIG SET maxmemory 256mb

# 设置淘汰策略
docker exec openfinance-redis redis-cli CONFIG SET maxmemory-policy allkeys-lru
```

### 6.4 监控指标

访问 Prometheus (`http://localhost:9090`) 查询：

```promql
# 请求速率
rate(http_requests_total[5m])

# 错误率
rate(http_requests_total{status=~"5.."}[5m])

# 响应时间
histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))

# 内存使用
process_resident_memory_bytes{job="backend"}

# CPU 使用
rate(process_cpu_seconds_total{job="backend"}[5m])
```

---

## 附录

### A. 快速参考命令

```bash
# 启动开发环境
docker-compose up -d

# 查看日志
docker-compose logs -f

# 进入后端容器
docker exec -it openfinance-backend bash

# 进入前端容器
docker exec -it openfinance-frontend sh

# 连接数据库
docker exec -it openfinance-postgres psql -U openfinance

# 连接 Redis
docker exec -it openfinance-redis redis-cli

# 重启服务
docker-compose restart

# 完全清理
docker-compose down -v --rmi all
```

### B. 调试端口速查

| 端口 | 服务 | 协议 | 用途 |
|------|------|------|------|
| 5678 | Backend | debugpy | Python 远程调试 |
| 9229 | Frontend | V8 Inspector | Node.js 调试 |
| 9230 | Frontend | V8 Inspector | Node.js 备用 |
| 9001 | Backend | Prometheus | 指标暴露 |

### C. 有用的链接

- [Docker 官方文档](https://docs.docker.com/)
- [VS Code 调试文档](https://code.visualstudio.com/docs/editor/debugging)
- [Debugpy 文档](https://github.com/microsoft/debugpy)
- [Node.js 调试指南](https://nodejs.org/en/docs/guides/debugging-getting-started/)
- [Prometheus 查询语法](https://prometheus.io/docs/prometheus/latest/querying/basics/)
- [Loki LogQL](https://grafana.com/docs/loki/latest/query/)
