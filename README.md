# 项目：原油价格监控

## 元信息
- 项目ID: 3
- 状态: open
- 基础Agent: main
- 会话Agent: main@prj-8e2585b4
- Session: main-prj-8e2585b4
- 创建时间: 2026-03-07T22:11:45+00:00
- 默认技能: web-architecture-master

## 目标
- 每隔 10 分钟自动采集国际原油价格（WTI、Brent）
- 生成趋势折线图网站，支持 24h/72h/7d/14d 时间窗口
- 完成部署并输出可访问网址

## 验收标准
- 采集器自动运行，数据库持续写入价格数据
- 网站接口 `/api/v1/prices` 可正常返回序列数据
- 前端折线图可显示趋势并刷新最新价格
- 提供数据库备份与恢复命令
- 完成部署并给出可访问地址

## 本地运行
```bash
cd /Users/macmini_dong/.openclaw/workspace/projects/openclaw-telegram-agent/projects/20260308-prj-8e2585b4-project
bash scripts/deploy_local.sh
```

启动后访问：`http://127.0.0.1:18080/`

## 已部署地址（本次交付）
- 网站：`http://127.0.0.1:18080/`
- 健康检查：`http://127.0.0.1:18080/healthz`
- 数据接口：`http://127.0.0.1:18080/api/v1/prices?hours=336`

## VPS 公网地址（已上线）
- 网站：`http://43.167.189.158:18080/`
- 健康检查：`http://43.167.189.158:18080/healthz`
- 数据接口：`http://43.167.189.158:18080/api/v1/prices?hours=336`

## 管理命令
```bash
# 状态检查
bash scripts/status_local.sh

# 停止服务
bash scripts/stop_local.sh

# 手动数据库备份
bash scripts/backup_db.sh

# 从备份恢复（恢复前建议先停止服务）
bash scripts/restore_db.sh data/backups/oil_prices-YYYYMMDD-HHMMSS.db
```

## API
- `GET /healthz`：健康检查
- `GET /api/v1/prices?hours=72`：获取趋势序列与最新价格
- `POST /api/v1/admin/collect`：立即触发一次采集（可选 token）
- `POST /api/v1/admin/backup`：立即创建备份（可选 token）
- `GET /api/v1/backups`：查看备份文件列表（可选 token）

## 数据源说明
- WTI: FRED `DCOILWTICO`
- Brent: FRED `DCOILBRENTEU`
- 采集周期：每 10 分钟触发一次；若源站暂无更高频更新，数据库会自动去重保留有效新点。

## 部署说明（VPS 路径）
已提供 Dockerfile 与 docker-compose，可直接接入 `vps-deploy` 流程（Nginx + systemd + webhook）：
- Web 服务端口：`8080`（容器内）
- 对外映射默认：`18080`
- 数据卷：`./data`

一键发布到当前 VPS：
```bash
cd /Users/macmini_dong/.openclaw/workspace/projects/openclaw-telegram-agent/projects/20260308-prj-8e2585b4-project
bash scripts/deploy_vps.sh
```
