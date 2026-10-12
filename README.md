# NosChat - 复古 AI 聊天应用

Vue 3 前端 + FastAPI 后端 + PostgreSQL 的 AI 聊天应用：真实的 OpenAI 兼容模型调用、SSE 流式输出、邮箱验证码注册登录、按用户持久化会话与消息，并提供容器化部署（容器只包含后端与数据库，**不含前端**）。

> 前端界面布局、配色与交互保持不变，本次改动集中在**数据/API 层**，并按需为认证表单补充「邮箱 / 验证码」输入项。

## 功能特性

### 前端
- 🎨 **现代化聊天界面**：渐变背景、毛玻璃效果与流畅动画（保持原有设计）
- 💬 **多对话管理**：会话列表来自后端并持久化，支持新建、重命名、删除
- 🧠 **深度思考展示**：推理模型先输出思考链，可逐条展开/折叠（由后端真实 `reasoning` 增量驱动）
- 🧩 **多模型切换**：模型清单由后端下发，含厂商、上下文、能力条、**介绍**与**发布日期**，支持按发布时间排序与搜索
- 🔐 **多种登录方式**：邮箱 + 密码登录、邮箱验证码登录（免密码）
- 😊 **昵称设置**：自动注册后弹出昵称设置；顶部昵称可随时点击修改
- ✉️ **注册 / 找回密码**：邮箱验证码注册；忘记密码可通过邮箱验证码重置
- 🆕 **验证码登录自动注册**：邮箱未注册时直接创建账号（昵称默认使用邮箱）
- 📱 **响应式设计**：桌面端内联侧栏、窄屏抽屉（原样保留）

### 后端
- 🚀 **FastAPI**（默认 `9135` 端口）+ PostgreSQL（SQLAlchemy 2.x 异步 + psycopg3）
- 🤖 **真实模型调用**：一个 `OPENAI_BASE_URL` + 一个 `OPENAI_API_KEY` + 多个 model（OpenAI 标准接口）
- 🌊 **SSE 流式转发**：思考内容与正式回答分别流式下发，前端逐字渲染
- ✉️ **SMTP 邮件验证码**：按用途（注册 / 登录 / 重置）分别校验与限流（哈希存储、有效期、重发间隔、错误次数限制）
- 🔑 **密码与令牌**：bcrypt 密码哈希 + JWT 访问令牌，重置密码后旧令牌立即失效
- 🗂️ **会话与消息持久化**：按用户隔离，自动生成标题与预览
- ⚙️ **环境变量驱动**：数据库、密钥、邮件、模型、CORS 等全部可配置
- 🐳 **容器化部署**：`docker compose` 一键起后端 + PostgreSQL（不含前端）

## 架构

```
┌────────────────────┐   /api/models        ┌──────────────────────────┐
│  Vue 3 前端 (web/) │   /api/auth/*        │  FastAPI 后端 (server/)  │
│  仅数据/API 层改造 │ ───────────────────► │  9135                    │
│  Vite dev: 3000    │   /api/conversations │                          │
│                    │ ◄══ SSE 流式 ◄══════ │  ┌────────────────────┐  │
└────────────────────┘   /api/chat/stream   │  │ OpenAI 兼容接口    │  │
                                            │  │ base_url + key     │  │
                                            │  └────────────────────┘  │
                                            │  ┌────────────────────┐  │
                                            │  │ SMTP 邮件服务      │  │
                                            │  └────────────────────┘  │
                                            └───────────┬──────────────┘
                                                        │
                                              ┌─────────▼─────────┐
                                              │   PostgreSQL 16   │
                                              │  用户/验证码/会话 │
                                              │  /消息            │
                                              └───────────────────┘
```

## 项目结构

```
NosChat/
├── server/                                   # 后端（容器内运行）
│   ├── app/
│   │   ├── main.py                           # 应用入口：CORS、路由挂载、启动建表、/health
│   │   ├── config.py                         # 环境变量（pydantic-settings）
│   │   ├── database.py                       # 异步 engine / session / 建表
│   │   ├── models.py                         # ORM：User / EmailVerification / Conversation / Message
│   │   ├── schemas.py                        # 请求响应模型（对外 camelCase）
│   │   ├── security.py                       # bcrypt 密码哈希、JWT、验证码哈希
│   │   ├── deps.py                           # get_db / get_current_user
│   │   ├── mailer.py                         # aiosmtplib 发送验证码邮件
│   │   ├── llm.py                            # AsyncOpenAI 流式调用（含友好错误映射）
│   │   ├── model_registry.py                 # 模型清单加载与兜底
│   │   └── routers/{auth,catalog,chat}.py    # 认证 / 模型清单 / 会话与流式对话
│   ├── config/models.json                    # 模型清单备用来源（介绍、发布日期、标签等）
│   ├── scripts/export_models_env.py          # 把 models.json 导出为 .env 的 MODEL_* 写法
│   ├── tests/{smoke_api.py,mock_llm.py}      # 接口冒烟测试、本地 Mock 模型服务
│   ├── requirements.txt
│   ├── Dockerfile
│   ├── .env.example
│   └── run.py                                # 启动入口（Windows 事件循环兼容）
├── web/                                      # 前端（不进入容器）
│   └── src/
│       ├── api/{client,auth,chat}.js         # 新增：接口客户端、认证、模型/会话/SSE
│       ├── utils/time.js                     # 新增：时间展示格式化
│       ├── stores/userStore.js               # 改造：对接后端鉴权（保留原暴露字段）
│       ├── data/models.js                    # 改造：模型清单运行时注册表
│       ├── components/AuthPage.vue           # 增补：密码/验证码登录、注册、找回密码
│       ├── components/ModelSelector.vue      # 微调：清单为空时的兜底，避免渲染报错
│       ├── App.vue                           # 改造：真实模型清单 / SSE / 会话持久化（模板不变）
│       └── ...                               # 其余组件未改动
├── .github/workflows/                        # GitHub Actions（云端构建 + 传输部署）
│   ├── deploy-web.yml                        #   前端 → 1Panel 站点 index/dist
│   └── deploy-api.yml                        #   后端 → /opt/noschat（镜像 + compose）
├── docker-compose.yml                        # 后端 + PostgreSQL（不含前端）
└── check-project-structure.js                # 项目结构自检
```

> 环境变量只有一处：`server/.env`（从 `server/.env.example` 复制）。compose 与本地运行都读它，根目录不再需要 `.env`。

## 快速开始

### 方式一：容器化（后端 + PostgreSQL）

```bash
# 1) 准备环境变量（Windows PowerShell：Copy-Item server\.env.example server\.env）
cp server/.env.example server/.env
# 必填：JWT_SECRET、OPENAI_*、SMTP_*、MODEL_*（模型清单与介绍也在这里维护）

# 2) 构建并启动
docker compose up -d --build

# 3) 健康检查（容器只监听本机 127.0.0.1:9135，由反向代理对外提供服务）
curl http://localhost:9135/health
# {"status":"ok","version":"1.0.0","models":9}

# 4) 前端仍单独运行（容器不含前端）
cd web && npm install && npm run dev     # http://localhost:3000
```

### 方式二：本地开发

```bash
# 后端
cd server
python -m venv .venv
.venv/Scripts/pip install -r requirements.txt     # Linux/macOS: .venv/bin/pip
cp .env.example .env                              # 填写 POSTGRES_* / OPENAI_* / SMTP_* / MODEL_*
python run.py                                     # http://localhost:9135

# 前端（另开终端）
cd web
npm install
npm run dev                                       # http://localhost:3000
```

> **Windows 提示**：请使用 `python run.py` 启动后端。psycopg 的异步模式不支持 Windows 默认的 `ProactorEventLoop`，`run.py` 会自动切换到 `SelectorEventLoop`；直接执行 `python -m uvicorn app.main:app` 会报 `Psycopg cannot use the 'ProactorEventLoop'`。

### 接口冒烟测试

```bash
cd server
python tests/smoke_api.py            # 覆盖注册/登录/模型/会话/SSE/错误路径
```

本地没有真实模型服务时，可用自带 Mock：

```bash
cd server
python tests/mock_llm.py             # 127.0.0.1:9901
# server/.env 中设置 OPENAI_BASE_URL=http://127.0.0.1:9901/v1
```

## 自动部署（GitHub Actions）

两个工作流都在 **GitHub 云端构建**，构建完成后通过 SSH 把产物传到服务器（服务器上不做构建）：

| 工作流 | 触发条件 | 云端构建 | 服务器上的结果 |
| --- | --- | --- | --- |
| `deploy-web.yml` | `web/**` 变更推送 main | `npm ci && npm run build` 后打包 | 解压到 `/opt/1panel/www/sites/noschat.vodyanitsa.top/index/dist` |
| `deploy-api.yml` | `server/**`、`docker-compose.yml` 变更推送 main | `docker build` 后端镜像并 `docker save \| gzip` | `docker load` → `docker compose up -d`（同时同步 compose 与 `server/` 源码） |

两者都支持在 Actions 页面手动触发（`workflow_dispatch`）。

### 仓库 Secrets（Settings → Secrets and variables → Actions）

| 名称 | 说明 |
| --- | --- |
| `SERVER_HOST` | 服务器 IP 或域名 |
| `SERVER_USER` | SSH 用户名（需对部署目录有写权限，或直接用 root） |
| `SERVER_SSH_KEY` | 该用户的**私钥**全文（`-----BEGIN ... PRIVATE KEY-----` 起止都要，建议 ed25519） |

可选 Repository **Variable**：`VITE_API_BASE_URL` —— 留空时前端请求同源 `/api`（由 Nginx 反代到后端，推荐）；若要前端直连其它域名再填。

### 服务器一次性准备

```bash
# 后端目录（CI 会把 docker-compose.yml 与 server/ 源码同步过来，但不会覆盖 .env）
mkdir -p /opt/noschat/server
cd /opt/noschat
cp server/.env.example server/.env     # CI 首次同步后该文件才存在；也可手动创建
vi server/.env                         # 填 OPENAI_* / JWT_SECRET / SMTP_* / POSTGRES_* / MODEL_*
# 容器内的 POSTGRES_HOST 由 compose 覆盖为 db，这里保持 localhost 即可

# 前端目录（1Panel 站点目录）
mkdir -p /opt/1panel/www/sites/noschat.vodyanitsa.top/index/dist
```

> 服务器上需要已安装 Docker（含 compose 插件）；`/opt/noschat/server/.env` 不会被 CI 覆盖，首次部署前必须先准备好。

### 反向代理（1Panel 面板创建）

推荐直接在 1Panel 面板配置，站点保持「**静态网站**」（不要建成「反向代理」类型，否则前端也会被转发到后端）：

1. 网站 → 选择站点 → **网站目录 → 运行目录** 选 `/dist`（即 `.../index/dist`）；
2. 网站 → 选择站点 → **反向代理 → 添加**：
   - 名称：`api`
   - 路径 / 匹配路径：`/api`
   - 代理地址：`http://127.0.0.1:9135`
3. 在该代理的**自定义配置 / 高级设置**里补上（面板默认不会开，缺了会导致流式回答卡住或一次性吐出）：

```nginx
proxy_http_version 1.1;
proxy_set_header Connection "";
proxy_buffering off;
proxy_cache off;
proxy_request_buffering off;
proxy_read_timeout 3600s;
proxy_send_timeout 3600s;
```

要点：

- 静态根目录指向 `/opt/1panel/www/sites/noschat.vodyanitsa.top/index/dist`，并保证有 `try_files $uri $uri/ /index.html`（单页应用回落）；
- **代理地址末尾不要加斜杠**：写 `http://127.0.0.1:9135`，不要写 `http://127.0.0.1:9135/`，否则会丢掉 `/api` 前缀导致全部 404；
- compose 只把 9135 绑定在 `127.0.0.1`，不直接对外暴露；
- 若面板不支持自定义路径（只允许 `/`），改用「配置文件」方式，在 `server` 块里加：

```nginx
location /api/ {
    proxy_pass http://127.0.0.1:9135;   # 末尾不要加斜杠，否则会丢掉 /api 前缀
    proxy_http_version 1.1;
    proxy_set_header Host              $host;
    proxy_set_header X-Real-IP         $remote_addr;
    proxy_set_header X-Forwarded-For   $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_set_header Connection        "";
    proxy_buffering         off;
    proxy_cache             off;
    proxy_request_buffering off;
    proxy_read_timeout      3600s;
    proxy_send_timeout      3600s;
}
```

## 环境变量

### 后端（`server/.env`，compose 与本地运行共用同一份）

| 变量 | 默认值 | 说明 |
| --- | --- | --- |
| `PORT` | `9135` | 后端监听端口 |
| `DEBUG` | `false` | 调试日志 |
| `CORS_ORIGINS` | `http://localhost:3000,http://127.0.0.1:3000` | 允许的前端来源，逗号分隔 |
| `POSTGRES_HOST` / `POSTGRES_PORT` | `localhost` / `5432` | 数据库地址；容器部署时 compose 会把 host 覆盖为服务名 `db` |
| `POSTGRES_USER` / `POSTGRES_PASSWORD` / `POSTGRES_DB` | `noschat` | 数据库账号与库名（同时供 postgres 容器初始化使用） |
| `DATABASE_URL` | 空 | 可选：直接给完整连接串（设置后优先于上面的 `POSTGRES_*`） |
| `OPENAI_BASE_URL` | `https://api.openai.com/v1` | OpenAI 兼容接口地址（**一个**） |
| `OPENAI_API_KEY` | 空 | 接口密钥（**一个**，必填） |
| `OPENAI_TIMEOUT` | `120` | 上游请求超时（秒） |
| `OPENAI_TRUST_ENV` | `false` | 是否走系统代理；默认关闭，避免代理拦截内网/本地模型服务 |
| `JWT_SECRET` | — | 令牌签名密钥（**生产必填**） |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `20160` | 令牌有效期（分钟，默认 14 天） |
| `SMTP_HOST` / `SMTP_PORT` | 空 / `587` | SMTP 服务器 |
| `SMTP_USER` / `SMTP_PASS` | 空 | SMTP 账号与密码（也可写作 `SMTP_USERNAME` / `SMTP_PASSWORD`；多数服务需用授权码） |
| `SMTP_FROM` / `SMTP_FROM_NAME` | 空 / `NosChat` | 发件地址与显示名，`SMTP_FROM` 支持 `显示名 <地址>` 形式 |
| `SMTP_STARTTLS` / `SMTP_SSL` | `true` / `false` | 587 用 STARTTLS；465 请设 `SMTP_SSL=true` 且 `SMTP_STARTTLS=false`（QQ、163 等） |
| `AUTH_DEV_ECHO_CODE` | `false` | 未配置 SMTP 时是否把验证码回传前端（**仅本地开发**） |
| `CODE_TTL_SECONDS` | `300` | 验证码有效期 |
| `CODE_RESEND_INTERVAL_SECONDS` | `60` | 同邮箱重发间隔（限流） |
| `CODE_MAX_ATTEMPTS` | `5` | 单个验证码最大校验次数 |
| `MODEL_1`、`MODEL_2`… | 空 | 在 `.env` 里声明模型清单（`id=xx;name=yy;desc=zz…`），定义了即优先生效 |
| `MODELS_CONFIG_PATH` | `config/models.json` | 未定义任何 `MODEL_*` 时使用的模型清单文件路径 |

### 前端（`web/.env`）

| 变量 | 默认值 | 说明 |
| --- | --- | --- |
| `VITE_API_BASE_URL` | `http://127.0.0.1:9135` | 后端地址；设为空字符串时走 Vite 的 `/api` 代理（同源） |

## 模型清单（`.env` 或 `server/config/models.json`）

模型清单支持两种维护方式，**二选一**（只要定义了任意 `MODEL_*` 就以环境变量为准，`models.json` 会被忽略）：

**方式一（推荐）：直接写在 `.env` 里**，每个模型一行，字段用 `;` 分隔、`key=value` 形式：

```env
# 字段：id(必填) model name provider icon badge color desc tags context released
#       speed(1-5) intelligence(1-5) temp reasoning latency base_url
MODEL_1=id=deepseek-v3;model=deepseek-chat;name=DeepSeek-V3;provider=深度求索;icon=🐋;badge=推荐;color=#4d6bfe;desc=通用对话能力强，中文理解自然，响应速度快。;tags=通用,中文,性价比;context=64K;released=2024-12-27;speed=5;intelligence=4;temp=0.7;reasoning=false;latency=600-1200
```

- 编号只用于排序，可增删、可跳号；`desc` 就是界面上的「介绍」，`released` 是发布日期（`YYYY-MM-DD`）。
- 未写的字段自动兜底（`icon=🤖`、`color=#667eea`、`speed/intelligence=3`、`temp=0.7`、`latency=600-1400`、`context=—`）。
- 别名可用：`description`=`desc`、`date`=`released`、`upstream`/`model_name`=`model`、`temperature`=`temp`；标签支持 `,`、`|`、`、` 分隔；`latency` 支持 `600-1200`、`600,1200`、`600~1200`。
- 字段拼错会记录 warning 并忽略该字段；`id` 缺失的条目会被跳过。

**方式二：使用 `server/config/models.json`**（未定义任何 `MODEL_*` 时生效）。

两种方式里，每个模型包含以下字段（前端启动后通过 `GET /api/models` 拉取，增删模型无需改前端代码）：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `id` | string | 前端使用的唯一标识（必填） |
| `model` | string | 上游真实模型名，缺省回落到 `id` |
| `name` / `provider` | string | 展示名 / 厂商 |
| `icon` / `color` / `badge` | string | 头像、主题色、角标 |
| `desc` / `tags` | string / string[] | **介绍**与能力标签 |
| `context` | string | 上下文窗口（展示用） |
| `released` | string | **发布日期** `YYYY-MM-DD`，用于展示、相对时间与排序 |
| `speed` / `intelligence` | 1–5 | 能力条数值 |
| `temp` | number | 温度参数 |
| `reasoning` | boolean | 是否为推理模型（决定思考链展示） |
| `latency` | [min, max] | 响应耗时估算（毫秒，前端信息条展示） |
| `base_url` | string | 可选：为单个模型覆盖全局 `OPENAI_BASE_URL` |

修改后重启后端即可生效：

```bash
docker compose up -d api          # 改了 .env 需要重建容器（会重新注入环境变量）
# 或本地开发：重跑 python run.py
```

`server/config/models.json` 的改动不需要重建镜像（compose 已把 `server/config` 挂载进容器），`docker compose restart api` 即可。

从 JSON 生成 `.env` 写法（便于从方式二迁移到方式一）：

```bash
cd server
python scripts/export_models_env.py                # 打印 MODEL_* 行
python scripts/export_models_env.py -o models.env  # 写入文件
```

## 接口一览

| 方法 | 路径 | 说明 | 鉴权 |
| --- | --- | --- | --- |
| GET | `/health` | 健康检查（含已加载模型数） | 否 |
| POST | `/api/auth/send-code` | 发送验证码，`purpose` 取 `register`/`login`/`reset`（同邮箱同用途 60s 限流） | 否 |
| POST | `/api/auth/register` | 邮箱验证码注册（成功即返回令牌；昵称留空则用邮箱） | 否 |
| POST | `/api/auth/login` | 邮箱 + 密码登录 | 否 |
| POST | `/api/auth/login-code` | 邮箱验证码登录，**未注册的邮箱自动注册**（`isNewUser` 标识） | 否 |
| POST | `/api/auth/reset-password` | 找回密码：验证码校验后重置密码，旧令牌全部失效 | 否 |
| GET | `/api/auth/me` | 当前登录用户 | 是 |
| PATCH | `/api/auth/me` | 更新昵称（留空则回退为邮箱） | 是 |
| GET | `/api/models` | 模型清单（含介绍 / 发布日期等） | 否 |
| GET | `/api/conversations` | 会话列表（置顶优先、按更新时间倒序） | 是 |
| POST | `/api/conversations` | 新建会话（附带欢迎消息） | 是 |
| GET | `/api/conversations/{id}/messages` | 会话消息列表 | 是 |
| PATCH | `/api/conversations/{id}` | 更新标题 / 模型 / 置顶 / 未读 | 是 |
| DELETE | `/api/conversations/{id}` | 删除会话（级联删除消息） | 是 |
| POST | `/api/chat/stream` | 流式对话（`text/event-stream`） | 是 |

### 认证流程

| 场景 | 接口步骤 | 说明 |
| --- | --- | --- |
| 注册 | `send-code(register)` → `register` | 邮箱必须未注册；需昵称与密码，成功即登录 |
| 验证码登录 | `send-code(login)` → `login-code` | 邮箱已注册则直接登录；**未注册则自动创建账号**（昵称默认使用邮箱，且该账号没有密码）。自动注册后前端会弹出昵称设置框，可填昵称或选择「用邮箱当昵称」 |
| 密码登录 | `login` | 验证码自动注册的账号可用「找回密码」设置密码后再用密码登录 |
| 找回密码 | `send-code(reset)` → `reset-password` | 邮箱必须已注册；重置成功即登录，此前签发的令牌全部失效 |

> 验证码按 `(邮箱, 用途)` 独立记录与限流：有效期 `CODE_TTL_SECONDS`（默认 300s）、重发间隔 `CODE_RESEND_INTERVAL_SECONDS`（默认 60s）、最大尝试次数 `CODE_MAX_ATTEMPTS`（默认 5 次）。

### SSE 事件格式

```
data: {"type":"start","conversationId":"...","userMessageId":"...","title":"...","preview":"..."}
data: {"type":"thinking","delta":"..."}    # 推理模型的思考增量（可能没有）
data: {"type":"content","delta":"..."}     # 回答增量
data: {"type":"done","conversationId":"...","messageId":"...","title":"...","preview":"..."}
data: {"type":"error","message":"..."}     # 上游失败等错误（不会写入空消息）
```

## 数据模型

| 表 | 关键字段 | 说明 |
| --- | --- | --- |
| `users` | `email`(唯一)、`nickname`、`hashed_password`、`is_active` | 以邮箱为登录账号，密码 bcrypt 存储 |
| `email_verifications` | `email`、`purpose`、`code_hash`、`expires_at`、`consumed_at`、`attempts` | 验证码只存哈希，含过期与次数限制 |
| `conversations` | `id`、`user_id`、`title`、`model_id`、`preview`、`pinned`、`unread` | 按 `user_id` + `pinned` + `updated_at` 建索引 |
| `messages` | `id`、`conversation_id`、`role`、`model_id`、`content`、`thinking`、`thinking_sec` | 按 `conversation_id` + `created_at` 建索引 |

表结构在服务启动时自动创建（幂等）。

## 安全说明

- 密码使用 bcrypt 哈希，验证码以 HMAC-SHA256 哈希入库，二者都不落明文。
- 访问令牌为 JWT（默认 14 天），所有会话/消息接口都校验令牌并校验资源归属。
- `JWT_SECRET` 必须替换为随机长字符串：`python -c "import secrets;print(secrets.token_urlsafe(48))"`。
- 生产环境请关闭 `AUTH_DEV_ECHO_CODE`，并只把数据库端口暴露在内网（compose 默认不映射 `db` 端口）。
- 后端镜像以非 root 用户运行，`.env` 已通过 `.dockerignore` 排除，不会打进镜像。

## 常见问题

1. **前端报「无法连接后端服务」**：确认后端已在 `9135` 启动（`GET /health`），并检查 `CORS_ORIGINS` 是否包含前端地址。
2. **发送验证码返回 503**：未配置 `SMTP_HOST`。配置真实 SMTP，或本地开发时设置 `AUTH_DEV_ECHO_CODE=true` 直接回传验证码。
3. **Windows 启动报 ProactorEventLoop**：请用 `python run.py` 启动（见上文提示）。
4. **模型调用报 502 / Connection error**：多为本机代理软件拦截，确认 `OPENAI_TRUST_ENV=false`，或把 `OPENAI_BASE_URL` 指向可达地址。
5. **切换模型后提示保存失败**：模型 id 必须在模型清单中（`.env` 的 `MODEL_*` 或 `server/config/models.json`）。
6. **模型清单没生效**：`server/.env` 里 `MODEL_*` 的字段拼写有误会被忽略并打 warning（`docker logs noschat-api | grep 模型`），`id` 缺失的条目会被跳过；改 `server/.env` 后需要 `docker compose up -d api` 重建容器重新注入变量。

## 许可证

MIT
