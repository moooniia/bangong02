# bangong02.com → 腾讯云 109 迁移笔记

日期：2026-10-20（Asia/Singapore / CST）
状态：**已拷贝并可 IP 自测；DNS 未切换**

## 机器

| 角色 | 地址 | SSH |
|------|------|-----|
| 源（阿里云 OpenClaw） | 139.196.28.78 | `root` + box `~/.ssh/id_ed25519` |
| 目标（腾讯 109） | 43.142.98.170 | `ubuntu` 密码登录 |

## 目标路径

- 站点根：`/home/ubuntu/bangong02/`
  - `frontend/` 静态页（含备案号页脚）
  - `backend/` Flask API
  - `venv/` Python 3.12 虚拟环境
  - `toolbox.env` API 密钥（权限 600）
  - `uploads/` / `outputs/`
  - `umami/` 编排文件已拷，**未启动**
- nginx：`/etc/nginx/sites-available/bangong02.conf`（enabled）
- systemd：`toolbox.service` → venv 跑 `backend/app.py` :5000

## 已拷内容

- `/home/toolbox/` 除 `lab/`、旧 backups、旧 InvoiceToolbox 安装包、日志、空 uploads/outputs
- 保留 downloads：`InvoiceToolbox.WinUI_latest.msix`、`InvoiceToolboxInstaller-1.0.0.60.exe`
- **已迁**：`/home/toolbox/lab` → `/home/ubuntu/bangong02/lab`（2026-10-20 晚）

## 109 已装

- nginx、LibreOffice、poppler-utils、tesseract(+chi_sim)、ImageMagick
- Python venv + Flask / PyMuPDF / opencv / pdf2docx 等（见 `requirements-109.txt`）
- 停用占 80 端口的默认 **Caddy**（原先仅 “Caddy works!”）

## 自测

- 首页：http://43.142.98.170/ → 200，页脚有 `赣ICP备2026013721号-1` → https://beian.miit.gov.cn/
- 工具页：`/pdf-to-word.html` 等 200
- API：`POST /api/convert` 无文件返回 400 `没有文件`（说明 nginx→Flask 通）
- Host：`bangong02.com` / IP 均可（HTTP only）

## DNS / 源站（未改）

- 公网 DNS：`bangong02.com` / `www` → **仍是 139.196.28.78**
- 阿里云 `nginx` + `toolbox` 仍 active；`lab/` 未动

## 已知未做 / 阻塞点

1. **未切 DNS**（按计划）
2. **无 HTTPS**：证书仍在阿里云 Let’s Encrypt；切 DNS 后再在 109 申请
3. **Umami**（docker :3000）未部署 → `/script.js`、统计登录会 502
4. **OpenClaw `/claw`** 未配（原在阿里云反代 18789）
5. Flask 用开发服务器；正式可用 gunicorn
6. 旧版 InvoiceToolbox msix/zip 未拷（省约 800MB）；需要可再从源站补
7. `/home/ubuntu` 已 `chmod 755` 以便 nginx 读站点；勿再改回 750 除非改 root 到别处

## 切 DNS 前建议

1. 用 http://43.142.98.170/ 完整点几轮转换
2. 需要统计时再 `docker compose` 起 umami
3. 切 A 记录到 `43.142.98.170` → 申请证书 → 加 443
4. ~~与模型训练小白另约搬 `lab/`~~ → 已完成，见下文「lab 迁移」

## lab 迁移（2026-10-20 晚，Asia/Singapore）

- **源**：`root@139.196.28.78:/home/toolbox/lab`（约 1.3MB，主要为 `backend/`）
- **目标**：`ubuntu@43.142.98.170:/home/ubuntu/bangong02/lab`
- **方式**：live rsync（未停阿里云服务）；**DNS 未改**
- **未建** `toolbox` 系统用户（源站也无该 login 用户，目录属 root）；统一放在 `ubuntu` 家目录下站点树内

### 109 SSH 钥匙（ubuntu `~/.ssh/authorized_keys`）

从阿里云 `root` authorized_keys 同步（无单独「xiaomei/模型训练小白」注释的公钥）：

| 注释 | 指纹 (SHA256) |
|------|----------------|
| `paz@openclaw-tunnel` | `/gEg0IA3vnsQUldBEGVPiKvWPpYmJiYvpg8/NHeMUFg` |
| `openclaw-local-node-20260701` | `PlHOr/a4ksCVyJQsWCJNIAGvzal+y9bkzU6RyDAePl0` |
| `moooni-box` | `Jf1p0odV7LhvV5UNNQWvRqdqawwSTKYTiAUcobm1ihc` |
| `paz@DESKTOP-1C14212` | `oAGOz2aZrHRaz8v8FC8bO86yIJIne1SZoraX4sDGLYA` |

- 本机（box）用 `moooni-box` 私钥已 `BatchMode` 密钥登录验证通过
- 密码登录仍开着（备用）
- 若小白另有个人 `.pub`，需自行贴过来再追加

### 小白登录方式

```bash
ssh ubuntu@43.142.98.170
# 试验目录
cd /home/ubuntu/bangong02/lab/backend
```

持有上述四把私钥之一即可；否则用现有 ubuntu 密码，或把新 `.pub` 发来追加。
