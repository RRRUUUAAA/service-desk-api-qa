# 简历表达与项目演示

## 1. 项目名称

**Service Desk API 接口自动化测试项目**

技术栈：Python、pytest、requests、PostgreSQL、Docker Compose、GitHub Actions

## 2. 简历写法

```text
Service Desk API 接口自动化测试项目
技术栈：Python、pytest、requests、PostgreSQL、Docker Compose、GitHub Actions

- 自建 FastAPI + PostgreSQL 工单 API 测试靶场，按角色、状态机、分页筛选和
  数据库一致性设计 95 个接口自动化用例。
- 搭建配置、ApiClient、DataFactory、DatabaseClient、公共断言分层框架；
  使用唯一测试数据与依赖顺序 teardown，连续 3 次执行均 95 passed，
  测试后数据库恢复为 1 个 bootstrap admin、0 工单、0 审计事件。
- 使用 SQL 校验创建、分配、状态变更、失败回滚和级联删除；定位并修复
  “显式 null 返回 500”“管理员自我降级导致锁死”两个缺陷并完成回归。
- 使用 Docker Compose 统一 API 与 PostgreSQL 环境，接入 GitHub Actions
  自动执行 pytest 并归档 JUnit 报告。
```

### 可以写

- 95 个实际执行用例。
- 3 次连续通过。
- 数据库恢复基线。
- 两个真实发现并修复的缺陷。
- Docker Compose 和 CI 配置。

### 不要写

- “支撑百万用户”或其他没有数据来源的规模。
- “发现上百个线上缺陷”。
- “覆盖率 95%”，除非通过服务端插桩实际测得。
- “企业级高并发框架”。
- 把自建靶场描述为真实生产业务系统。

## 3. 5—8 分钟演示流程

### 0:00—0:40 项目边界

说明这是一个自建本地工单 API，目标是证明测试工程能力，不是包装业务规模。

### 0:40—1:30 架构和分层

展示 README 架构图和目录：

```text
pytest -> ApiClient -> FastAPI -> PostgreSQL
          DataFactory
          DatabaseClient -> SQL
```

解释 session fixture 和 function fixture 的职责。

### 1:30—2:30 需求到测试设计

打开 `docs/01-requirements.md` 和 `docs/03-test-cases.md`：

- 三角色。
- open/assigned/in_progress/resolved/closed。
- 401/403/404/409/422。
- 边界值、越权、重复操作。

### 2:30—3:30 运行主套件

```bash
docker compose ps
docker compose --profile test run --rm tests
```

展示：

```text
95 passed
```

说明三次执行结果。

### 3:30—4:40 鉴权与权限用例

打开 `tests/test_ticket_workflow.py`：

- admin 分配。
- assignee 开始工作。
- 非 assignee 访问返回 404。
- creator 不能代替技术员处理。
- 非法状态迁移不产生事件。

### 4:40—5:45 数据库校验与缺陷

打开 `tests/test_db_consistency.py` 和 `docs/05-defects.md`：

- 响应断言之外，用 SQL 查 `users/tickets/ticket_events`。
- 失败操作后状态和事件数不变。
- explicit null 500 的定位和修复。
- 管理员自降级的风险与修复。

### 5:45—6:30 CI 和稳定性

打开 `.github/workflows/tests.yml`：

- Compose 启动。
- 健康检查。
- pytest。
- 上传 JUnit。
- 失败输出日志。
- 始终清理环境。

### 6:30—7:30 局限和反思

主动说明：

- 未测并发和性能。
- 自建靶场的边界。
- 如果继续做，会加 Alembic、契约检查、并发测试和服务端覆盖率插桩。

## 4. 演示前检查

```bash
docker compose config
docker compose up -d --build db api
docker compose ps
docker compose --profile test run --rm tests
```

演示时如果网络不可用，保留：

- `reports/junit.xml`
- `docs/04-test-report.md`
- `docs/05-defects.md`

不要现场首次拉镜像；提前构建好容器。

## 5. 面试官可能追问

- 为什么不用事务回滚？见 `docs/06-interview-qa.md` 第 4 题。
- 95 个用例是否注水？说明参数化和业务分组。
- 自建系统怎么证明测试有效？用实际缺陷、失败前后数据库和回归结果回答。
- 400、401、403、404、409、422 的区别是什么？
- CI 偶发失败怎么排查？
- 如何把当前框架迁移到公司接口？
