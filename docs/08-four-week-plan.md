# 四周执行清单

当前仓库已经是完成版。下面四行用于按周复现、学习和验收，而不是把同一份代码拆成四段重新生成。

## 第 1 周：环境和测试设计

实际完成：

- 检查 macOS、Docker、Python、端口和 Docker daemon。
- 固定 Python 3.12 容器运行。
- 写下角色、接口、业务规则、输入边界和不测试范围。
- 完成鉴权、用户、工单、列表、状态机、数据库用例矩阵。

验收：

```bash
docker compose config
```

标准：

- Compose 配置可解析。
- 能口头说明三个角色和五状态链路。
- 能说明为什么自建 API 是测试靶场。

未解决问题：无；性能、前端和安全渗透明确不在本轮范围。

## 第 2 周：API 与 pytest 基础框架

实际完成：

- FastAPI、SQLAlchemy、PostgreSQL 模型和路由。
- JWT 登录与当前用户接口。
- 用户管理和工单 CRUD。
- ApiClient、配置、fixture、DataFactory、公共断言。
- 鉴权、用户、CRUD 和边界用例。

验收：

```bash
docker compose up -d --build db api
docker compose --profile test run --rm tests pytest tests/test_auth.py tests/test_users.py tests/test_tickets_crud.py
```

标准：

- 健康检查正常。
- 基础 CRUD 和边界用例通过。
- token 按用户隔离。

未解决问题：无。

## 第 3 周：SQL、权限、状态机和 Docker 稳定性

实际完成：

- 工单分配和五状态状态机。
- 垂直/水平权限测试。
- SQL 字段验证、外键、审计事件、失败回滚和级联删除。
- 唯一测试数据和依赖顺序 teardown。
- Docker healthcheck。

验收：

```bash
docker compose --profile test run --rm tests
docker compose exec -T db psql -U service_desk -d service_desk \
  -c "SELECT (SELECT COUNT(*) FROM users), (SELECT COUNT(*) FROM tickets), (SELECT COUNT(*) FROM ticket_events);"
```

标准：

- 全量用例通过。
- 测试后基线为 `1 / 0 / 0`。
- 非法状态请求后 tickets 和 events 不变。

未解决问题：无。

## 第 4 周：缺陷、CI、报告和面试

实际完成：

- 探索测试发现 2 个真实缺陷。
- 修复并做针对性回归和完整回归。
- 全量连续执行 3 次。
- 生成 JUnit 报告。
- 提交 GitHub Actions。
- 完成 README、测试报告、缺陷记录、面试问答和演示流程。

验收：

```bash
docker compose --profile test run --rm tests
sed -n '1,2p' reports/junit.xml
```

标准：

- 三次 `95 passed`，最终锁文件冷重建再次通过。
- JUnit `failures=0 errors=0 skipped=0`。
- 能解释两个缺陷的复现、根因、修复和回归。
- 能在 5—8 分钟内完成演示。

未解决问题：

- 当前环境没有做服务端代码覆盖率插桩，不能写覆盖率百分比。
- 并发、性能和专业安全测试不在本项目范围。

GitHub Actions 首次运行发现 BuildKit `network.host` 权限问题，修复后第二次运行成功，JUnit artifact 已上传。
