# Service Desk API QA

一个面向入门级软件测试/测试开发岗位的完整接口自动化项目。被测对象是一个小型 IT 工单 REST API，测试项目使用 Python、pytest、requests、PostgreSQL 和 Docker Compose，覆盖鉴权、角色权限、分页筛选、业务状态机、异常输入和数据库一致性。

> 边界说明：被测 API 是为测试工程展示而自建的本地靶场，不是生产系统。项目重点是需求分析、测试设计、自动化框架、数据库校验、缺陷闭环和 CI，而不是包装接口的业务复杂度。

## 已验证结果

- 自动化用例：95 个
- 连续执行：3 次
- 执行结果：3 次均为 `95 passed`
- 执行耗时：5.62s、5.47s、5.84s
- 最终锁文件冷重建：`95 passed in 5.02s`
- 当前提交版本最终重建：`95 passed in 7.74s`
- JUnit：`tests=95 failures=0 errors=0 skipped=0`
- 测试后数据库：`users=1`（bootstrap admin）、`tickets=0`、`ticket_events=0`

报告文件：[reports/junit.xml](reports/junit.xml)

## 技术栈

- 被测服务：Python 3.12、FastAPI、SQLAlchemy、PostgreSQL 16
- 测试框架：pytest、requests、fixture、parametrize、测试数据工厂
- 数据库校验：SQLAlchemy Engine + 原生 SQL
- 环境编排：Docker、Docker Compose
- CI：GitHub Actions
- 报告：JUnit XML

## 架构

```text
┌──────────────────────────── test container ────────────────────────────┐
│                                                                        │
│  pytest                                                                │
│    ├── config       环境、账号、数据库连接                             │
│    ├── ApiClient    requests.Session、token、统一日志                  │
│    ├── DataFactory  唯一用户/工单创建、依赖顺序 teardown               │
│    ├── Database     原生 SQL 查询与数据清理                             │
│    └── assertions   HTTP 错误、分页、数据库字段断言                     │
│                                                                        │
└───────────────────────────────┬────────────────────────────────────────┘
                                │ HTTP / JSON
                                ▼
┌────────────────────────────── API container ───────────────────────────┐
│ FastAPI                                                                 │
│  ├── /auth       JWT 登录、当前用户                                     │
│  ├── /users      用户与角色管理                                          │
│  └── /tickets    工单 CRUD、分页筛选、分配、状态机                       │
│                                                                        │
│ SQLAlchemy                                                              │
└───────────────────────────────┬────────────────────────────────────────┘
                                │ SQL
                                ▼
┌────────────────────────────── Database ─────────────────────────────────┐
│ PostgreSQL 16                                                           │
│  ├── users                                                              │
│  ├── tickets                                                            │
│  └── ticket_events                                                      │
└─────────────────────────────────────────────────────────────────────────┘

CI: GitHub Actions -> Docker Compose -> pytest -> reports/junit.xml artifact
```

## 目录

```text
.
├── app/
│   ├── routers/            # auth、users、tickets 接口
│   ├── database.py         # 引擎、Session、初始化
│   ├── dependencies.py     # Bearer token 与角色依赖
│   ├── models.py           # 数据库模型和约束
│   ├── schemas.py          # 请求响应模型与参数校验
│   └── security.py         # PBKDF2 密码哈希与 JWT
├── tests/
│   ├── framework/
│   │   ├── api_client.py   # HTTP 客户端层
│   │   ├── config.py       # 配置层
│   │   ├── db_client.py    # SQL 查询与清理
│   │   ├── factories.py    # 测试数据工厂
│   │   └── assertions.py   # 公共断言
│   ├── conftest.py         # fixture 与生命周期
│   └── test_*.py           # 95 个测试用例
├── docs/                   # 需求、测试计划、缺陷、面试、简历、演示
├── .github/workflows/      # GitHub Actions
├── Dockerfile
├── docker-compose.yml
├── requirements.lock       # 已验证的锁定依赖
├── pytest.ini
└── reports/junit.xml
```

## 快速开始

前置条件：

- Docker Desktop 正常工作
- 本机 `8000` 和 `5432` 端口空闲

启动 API 和 PostgreSQL：

```bash
docker compose up -d --build db api
docker compose ps
```

打开接口文档：

```text
http://localhost:8000/docs
```

执行完整测试：

```bash
docker compose --profile test run --rm tests
```

查看报告：

```bash
open reports/junit.xml
```

执行单个模块：

```bash
docker compose --profile test run --rm tests pytest tests/test_ticket_workflow.py
```

查看日志：

```bash
docker compose logs --no-color api
docker compose logs --no-color db
```

停止环境：

```bash
docker compose down
```

彻底重建数据库：

```bash
docker compose down -v
docker compose up -d --build db api
```

## 测试设计

| 模块 | 用例数 | 主要验证点 |
|---|---:|---|
| 健康检查 | 2 | 服务可用、OpenAPI 核心路径 |
| 登录与 token | 10 | 正确/错误密码、非法/过期 token、停用账号 |
| 用户管理 | 21 | 创建、重复、角色、分页、水平/垂直权限、自我保护 |
| 工单 CRUD | 24 | 边界长度、非法输入、显式 null、对象级权限、删除级联 |
| 工单列表 | 14 | 角色可见范围、状态/优先级/关键词/处理人筛选、分页 |
| 分配与状态机 | 19 | 分配、重复分配、非法状态流转、角色限制、完整闭环 |
| 数据库一致性 | 5 | 外键、失败回滚、审计事件、列表总数与 SQL 对账 |

测试设计方法：

- 等价类：合法角色、优先级、状态。
- 边界值：标题 1/120/121 字符，描述 2000/2001 字符，分页 0/1/100/101。
- 异常输入：缺失字段、非法枚举、错误邮箱、显式 null、不存在 ID。
- 鉴权：无 token、格式错误 token、过期 token、账号停用后的旧 token。
- 权限：垂直越权（普通用户调用管理员接口）和水平越权（访问他人资源）。
- 状态转换：合法链路、跳过中间状态、重复状态、越权转换。
- 数据库：创建后字段落库、失败操作不产生部分写入、审计事件、级联删除。

## 数据隔离

每个测试使用一个独立 `DataFactory`：

1. 用随机 `run_id` 生成唯一用户名、邮箱和工单标记。
2. 通过 API 创建真实数据，而不是直接插入数据库绕过业务逻辑。
3. 记录本次创建的用户 ID 和工单 ID。
4. 测试结束后按 `ticket_events -> tickets -> users` 顺序清理。
5. 测试不依赖固定总行数，数据库计数均带本次唯一标记或精确 ID。
6. 清理后数据库应恢复到 `1 admin / 0 tickets / 0 events`。

这种方案适合黑盒接口测试。没有用数据库事务回滚，因为 API 使用独立数据库连接，测试事务无法自动控制服务端写入。

## CI

GitHub Actions 工作流位于 [.github/workflows/tests.yml](.github/workflows/tests.yml)：

1. 检出代码。
2. 校验 Compose 配置。
3. 启动 API 和 PostgreSQL。
4. 在测试容器中运行 pytest。
5. 上传 `reports/junit.xml`。
6. 失败时输出容器日志。
7. 无论成功失败都清理容器和测试数据卷。

## 覆盖率说明

项目没有使用 `pytest-cov` 给出虚假的服务端代码覆盖率。API 和测试运行在不同容器、不同进程中，普通 `pytest-cov` 只能统计测试容器本身，不能代表 FastAPI 服务代码覆盖率。

本项目采用可核验的覆盖方式：

- 需求覆盖：需求文档中的鉴权、用户、工单、权限、筛选、状态机均有对应用例。
- 接口覆盖：OpenAPI 核心路径有冒烟检查，关键接口均有正常/异常用例。
- 数据覆盖：关键写操作均通过 SQL 回查数据库状态。
- 风险覆盖：重复操作、越权、非法状态转换、测试数据污染均有专项用例。

## 已知限制

- 被测 API 是自建测试靶场，不宣称生产使用或真实用户量。
- 未测试前端、移动端、性能、压测、短信、邮件、文件上传。
- 未做专业安全渗透、限流、CSRF、SQL 注入专项扫描。
- JWT 密钥是本地演示配置，生产环境必须通过 Secret 管理。
- `create_all` 适合本地测试环境；生产级变更应使用数据库迁移工具。
- 数据库清理依赖测试进程正常执行 fixture teardown；进程被强杀时需运行 `docker compose down -v` 恢复基线。

## 文档

- [需求与范围](docs/01-requirements.md)
- [测试计划](docs/02-test-plan.md)
- [用例矩阵](docs/03-test-cases.md)
- [测试报告](docs/04-test-report.md)
- [真实缺陷记录](docs/05-defects.md)
- [面试问答](docs/06-interview-qa.md)
- [简历表达与演示流程](docs/07-resume-and-demo.md)
- [四周执行清单](docs/08-four-week-plan.md)
