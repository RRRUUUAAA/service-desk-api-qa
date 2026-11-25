# 测试计划

## 1. 测试对象

- 被测服务：Service Desk API
- 服务地址：`http://localhost:8000`
- 数据库：PostgreSQL 16
- 测试类型：接口集成测试、数据库一致性测试、权限测试

## 2. 测试策略

测试从外部 HTTP 接口进入，通过真实 API 创建和修改数据，再用独立 SQL 连接验证数据库。测试不直接调用路由函数，也不 mock 数据库，因为目标是验证 HTTP、业务逻辑和持久化组合后的真实行为。

| 层级 | 验证内容 |
|---|---|
| HTTP 契约 | 方法、路径、状态码、JSON 结构、错误详情 |
| 鉴权 | Bearer token、过期、格式错误、停用账号 |
| 授权 | 角色级权限、对象级可见性、creator/assignee 权限 |
| 业务 | 工单状态机、分配规则、重复操作 |
| 数据 | 落库字段、外键、审计事件、失败回滚、级联删除 |
| 稳定性 | 连续执行、唯一数据、依赖顺序清理 |
| CI | Compose 启动、测试执行、JUnit artifact、日志收集 |

## 3. 测试环境

| 组件 | 版本/配置 |
|---|---|
| 主机 | macOS 26.5.2，Apple Silicon |
| Docker | 29.4.3 |
| Docker Compose | 5.1.3 |
| Python 容器 | 3.12-slim |
| PostgreSQL | 16-alpine |
| pytest | 9.2.0 |
| FastAPI | 0.165.0 |

所有实际版本见 [requirements.lock](../requirements.lock)，避免只写粗粒度版本范围。

## 4. 数据策略

### 4.1 为什么不用一个全局固定账号包打天下

固定账号会让测试之间共享 token、角色和资源，容易产生执行顺序依赖。例如修改角色后，后续测试可能突然从 200 变成 403。

### 4.2 当前方案

- admin 为 bootstrap 数据，只用于登录和创建隔离用户。
- 每个 function-scoped fixture 创建独立用户。
- `DataFactory.run_id` 标识本次测试数据。
- 用户名、邮箱、工单标题均带唯一标识。
- 测试结束后清理工单事件、工单和用户。
- 不假设全库总数，只对精确 ID 或本次唯一关键词统计。

### 4.3 为什么不用事务回滚

API 使用自己的数据库连接，测试进程开启的事务不会覆盖 API 写入。若强行让 API 共享测试事务，测试就不再是真实 HTTP 集成测试。当前使用“真实 API 写入 + teardown 清理”的方式。

## 5. fixture 设计

| fixture | 作用域 | 说明 |
|---|---|---|
| `test_config` | session | 从环境变量读取配置 |
| `db_client` | session | 复用一个 SQLAlchemy Engine |
| `admin_actor` | session | 登录 bootstrap admin |
| `anonymous_api` | function | 无 token 客户端 |
| `data_factory` | function | 创建并登记本次测试数据，结束后清理 |
| `employee` | function | 独立普通员工 |
| `technician` | function | 独立技术人员 |

token 按用户对象独立维护；不使用一个全局可变 token header。

## 6. 风险分析

| 风险 | 影响 | 措施 |
|---|---|---|
| 测试数据污染 | 顺序依赖、误报失败 | 唯一标识、依赖顺序清理、数据库基线检查 |
| token 失效/串用 | 鉴权用例互相影响 | 每个 Actor 使用独立 ApiClient |
| 非法操作产生部分写入 | 数据不一致 | 操作后 SQL 校验状态与事件数 |
| 容器启动慢 | CI 偶发连接失败 | DB/API healthcheck、测试前等待健康 |
| 依赖漂移 | 本机能跑 CI 失败 | Python 3.12 固定、requirements.lock |
| 网络环境差异 | 镜像安装失败 | `PIP_INDEX_URL` 可配置、CI 使用 PyPI |
| 并发写冲突 | 偶发重复数据 | 本轮不测试并发；使用唯一值和数据库约束 |
| 自建靶场可信度 | 面试质疑 | README 明确边界，强调测试工程产出而非生产业务 |

## 7. 用例设计方法

- 正常路径：成功创建、查询、更新、删除、完整状态闭环。
- 等价类：三个角色、三种优先级、五种状态。
- 边界值：字段长度和分页上下界。
- 错误猜测：显式 null、缺少字段、重复资源、不存在 ID。
- 权限矩阵：匿名、员工、技术员、管理员、对象 owner/assignee。
- 状态迁移：合法迁移和所有高风险非法迁移。
- 数据一致性：响应字段与 SQL 字段逐一比对。

## 8. 进入与退出标准

进入：

- Docker daemon 可用。
- `8000`、`5432` 端口空闲。
- Compose 配置可解析。

退出：

- 全量用例通过。
- 连续三次执行无偶发失败。
- 失败、错误、跳过数量明确。
- JUnit 报告可读取。
- 测试后数据库恢复基线。
- 缺陷有复现、根因、修复和回归结果。

## 9. 实际结果

| 执行 | 结果 | 耗时 |
|---|---|---:|
| 第一次 | 95 passed | 5.62s |
| 第二次 | 95 passed | 5.47s |
| 第三次 | 95 passed | 5.84s |

详细结果见 [测试报告](04-test-report.md)。
