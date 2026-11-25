# 需求说明与测试范围

## 1. 项目目标

为一个可控的本地 IT 工单 API 建立接口自动化测试项目，证明以下能力：

- 从需求和业务规则推导测试场景。
- 使用 pytest、requests 和 fixture 组织可重复执行的 HTTP 测试。
- 使用 SQL 验证响应之后的真实数据库状态。
- 验证 JWT 鉴权和角色/对象级权限。
- 使用 Docker Compose 管理被测服务和数据库。
- 使用 GitHub Actions 自动执行并保存 JUnit 报告。
- 形成缺陷发现、定位、修复和回归闭环。

## 2. 系统角色

| 角色 | 主要能力 |
|---|---|
| employee | 登录、创建工单、查看自己的工单、编辑处于 open 状态的自己的工单、关闭已解决的自己的工单 |
| technician | 登录、查看分配给自己的工单、开始处理、标记已解决 |
| admin | 管理用户和角色、查看全部工单、分配/重新分配工单、驱动合法状态流转、删除工单 |

## 3. 功能范围

### 3.1 鉴权

- `POST /auth/login`
- `GET /auth/me`
- 使用 Bearer JWT。
- 账号停用后，旧 token 也必须失效。

### 3.2 用户

- `POST /users`
- `GET /users`
- `GET /users/{id}`
- `PATCH /users/{id}/role`
- `PATCH /users/{id}/active`
- 用户列表支持分页、角色筛选、启用状态筛选、用户名/邮箱关键词筛选。

### 3.3 工单

- `POST /tickets`
- `GET /tickets`
- `GET /tickets/{id}`
- `PATCH /tickets/{id}`
- `DELETE /tickets/{id}`
- `POST /tickets/{id}/assign`
- `PATCH /tickets/{id}/status`
- 工单列表支持分页、状态、优先级、处理人和关键词筛选。

### 3.4 审计

- 创建、分配、重新分配、状态变更写入 `ticket_events`。
- 删除工单时审计事件级联删除。

## 4. 业务规则

1. 用户名和邮箱必须唯一。
2. 角色只能是 `employee`、`technician`、`admin`。
3. 只有 active technician 可以被分配工单。
4. 工单状态只能沿合法路径流转：
   - `open -> assigned`：通过分配接口
   - `assigned -> in_progress`：管理员或当前处理人
   - `in_progress -> resolved`：管理员或当前处理人
   - `resolved -> closed`：管理员或创建人
5. 不能跳过状态或重复提交当前状态。
6. 普通员工只能看到自己创建的工单。
7. 技术人员只能看到分配给自己的工单。
8. 管理员可以查看全部工单。
9. creator 只能在工单为 `open` 时编辑标题、描述和优先级。
10. 只有管理员可以删除工单。
11. 管理员不能停用或降级自己的账号，避免自锁。
12. 请求参数显式传 `null` 不能被当作“未提供该字段”。

## 5. 输入边界

| 字段 | 规则 |
|---|---|
| 用户名 | 3—32 字符，仅字母、数字、`_`、`.`、`-` |
| 密码 | 8—128 字符 |
| 工单标题 | 去除首尾空白后 1—120 字符 |
| 工单描述 | 0—2000 字符 |
| 分页 page | 最小 1 |
| 分页 page_size | 1—100 |
| 角色 | 三个固定枚举值 |
| 优先级 | `low`、`medium`、`high` |
| 状态 | 五个固定枚举值 |

## 6. 测试范围

### 包含

- HTTP 方法、路径、状态码、响应 JSON。
- JWT 正常、错误、过期和账号停用。
- 垂直越权和对象级越权。
- CRUD、分页、筛选、边界、重复操作。
- 状态机合法与非法流转。
- SQL 数据一致性、外键、审计事件和级联删除。
- 测试数据唯一性与 teardown。
- Docker Compose 启动和 CI 执行。
- JUnit 报告。

### 不包含

- UI、小程序和移动端。
- 性能、容量和并发压测。
- 真实短信、邮件、支付和第三方服务。
- 专业安全渗透测试。
- 生产部署、监控、告警和数据库迁移。
- 多副本、消息队列和分布式事务。

## 7. 验收标准

- `docker compose up -d --build db api` 后 API 与 PostgreSQL 健康。
- `docker compose --profile test run --rm tests` 可执行。
- 自动化用例不少于 40 个。
- 测试覆盖鉴权、用户、工单、筛选、权限、状态机和数据库。
- 每个测试可独立执行，连续运行无数据污染。
- 失败操作后数据库没有部分写入。
- JUnit 报告可生成并上传。
- README、测试报告、缺陷记录、面试材料齐全。
