# 用例矩阵

## 1. 统计

| 模块 | 用例数 |
|---|---:|
| 健康检查与 OpenAPI | 2 |
| 鉴权与 token | 10 |
| 用户管理 | 21 |
| 工单 CRUD 与输入边界 | 24 |
| 工单列表、筛选与分页 | 14 |
| 分配与状态机 | 19 |
| 数据库一致性 | 5 |
| 合计 | **95** |

参数化用例会展开成多个 JUnit testcase，因此本文件按业务场景分组，`reports/junit.xml` 是最终执行清单。

## 2. 健康检查

| ID | 场景 | 期望 |
|---|---|---|
| HEALTH-001 | `GET /health` | 200，`{"status":"ok"}` |
| HEALTH-002 | 获取 OpenAPI | 200，核心资源路径存在 |

## 3. 鉴权与 token

| ID | 场景 | 期望 |
|---|---|---|
| AUTH-001 | admin 正确账号密码登录 | 200，返回 JWT 与用户信息 |
| AUTH-002 | 正确用户名、错误密码 | 401 |
| AUTH-003 | 不存在用户名 | 401，和错误密码使用通用错误 |
| AUTH-004 | 登录缺少 password | 422 |
| AUTH-005 | 有效 token 调用 `/auth/me` | 200，用户与 token 一致 |
| AUTH-006 | 不带 token 调用 `/auth/me` | 401 + `WWW-Authenticate: Bearer` |
| AUTH-007 | 非法 JWT | 401 |
| AUTH-008 | 过期 JWT | 401 |
| AUTH-009 | inactive 用户登录 | 403 |
| AUTH-010 | 登录后账号被停用，旧 token 继续访问 | 401 |

## 4. 用户管理

完整套件共 21 项，参数化覆盖非法角色和分页边界。

| ID | 场景 | 期望 |
|---|---|---|
| USER-001 | admin 创建 employee | 201，数据库存哈希密码 |
| USER-002 | 重复用户名 | 409，数据库仍只有 1 行 |
| USER-003 | 重复邮箱，大小写不同 | 409 |
| USER-004 | 非法角色 manager/root/空值 | 422 |
| USER-005 | 非法邮箱 | 422 |
| USER-006 | employee 创建用户 | 403 |
| USER-007 | 匿名创建用户 | 401 |
| USER-008 | 用户列表 page=1&page_size=2 | 200，分页元数据正确 |
| USER-009 | 按 role + keyword 筛选 | 200，只返回目标用户 |
| USER-010 | page=0、page_size=0、page_size=101 | 422 |
| USER-011 | 用户读取自己 | 200 |
| USER-012 | 用户读取他人 | 404，隐藏对象存在性 |
| USER-013 | employee 查看用户列表 | 403 |
| USER-014 | admin 修改角色 | 200，SQL 中角色同步变化 |
| USER-015 | employee 修改角色 | 403 |
| USER-016 | admin 停用他人 | 200，SQL 同步 |
| USER-017 | admin 停用自己 | 409 |
| USER-018 | admin 降级自己 | 409 |

## 5. 工单 CRUD 与边界

| ID | 场景 | 期望 |
|---|---|---|
| TICKET-001 | employee 创建合法工单 | 201，数据库字段和 created 事件正确 |
| TICKET-002 | 标题 1 字符 | 201 |
| TICKET-003 | 标题 120 字符 | 201 |
| TICKET-004 | 标题 121 字符 | 422 |
| TICKET-005 | 标题全为空格 | 422 |
| TICKET-006 | 缺少标题 | 422 |
| TICKET-007 | 描述 2000 字符 | 201 |
| TICKET-008 | 描述 2001 字符 | 422 |
| TICKET-009 | 非法优先级 | 422 |
| TICKET-010 | 匿名创建工单 | 401 |
| TICKET-011 | 读取自己的工单 | 200 |
| TICKET-012 | 读取他人工单 | 404 |
| TICKET-013 | admin 读取任意工单 | 200 |
| TICKET-014 | 查询不存在工单 | 404 |
| TICKET-015 | creator 更新 open 工单 | 200，SQL 字段同步 |
| TICKET-016 | 非 owner 更新 | 404，SQL 不变 |
| TICKET-017 | PATCH 空对象 | 422 |
| TICKET-018 | PATCH title/description/priority 为 null | 422，不允许 500 |
| TICKET-019 | 工单已分配后 creator 继续编辑 | 409 |
| TICKET-020 | employee 删除工单 | 403，SQL 仍存在 |
| TICKET-021 | admin 删除工单 | 204，工单及审计事件删除 |
| TICKET-022 | 删除不存在工单 | 404 |

## 6. 列表、筛选与分页

| ID | 场景 | 期望 |
|---|---|---|
| LIST-001 | employee 列表 | 只含自己创建的工单 |
| LIST-002 | admin 列表 | 可包含多个 creator 的工单 |
| LIST-003 | technician 列表 | 只含分配给自己的工单 |
| LIST-004 | status=assigned | 只返回 assigned |
| LIST-005 | priority=high | 只返回 high |
| LIST-006 | 关键词大小写不同 | 返回匹配结果 |
| LIST-007 | 三行数据 page_size=2 | 两页共 3 行，倒序稳定 |
| LIST-008 | page=0、page_size=0/101 | 422 |
| LIST-009 | 非法 status | 422 |
| LIST-010 | 无匹配关键词 | 200，空数组、total=0 |
| LIST-011 | 匿名查询列表 | 401 |
| LIST-012 | admin 按 assignee_id 筛选 | 只返回该处理人工单 |

## 7. 分配与状态机

| ID | 场景 | 期望 |
|---|---|---|
| FLOW-001 | admin 分配给 technician | 200，状态 assigned，SQL 与事件一致 |
| FLOW-002 | 重复分配给同一 technician | 409，事件数不增加 |
| FLOW-003 | 分配给 employee | 409 |
| FLOW-004 | 分配给不存在用户 | 404 |
| FLOW-005 | 分配给 inactive technician | 409 |
| FLOW-006 | employee 执行分配 | 403 |
| FLOW-007 | 重新分配给另一个 technician | 200，记录 reassigned |
| FLOW-008 | assignee 从 assigned -> in_progress | 200，SQL 同步 |
| FLOW-009 | 非 assignee technician 尝试开始 | 404 |
| FLOW-010 | creator 尝试开始 | 403 |
| FLOW-011 | assignee 从 in_progress -> resolved | 200 |
| FLOW-012 | assigned 直接 -> resolved | 409，SQL 和事件不变 |
| FLOW-013 | creator 从 resolved -> closed | 200 |
| FLOW-014 | 非 creator 关闭 | 403 |
| FLOW-015 | creator 从 open 直接关闭 | 409 |
| FLOW-016 | 重复提交当前状态 | 409 |
| FLOW-017 | 通过状态接口提交 assigned | 409，提示使用分配接口 |
| FLOW-018 | 工作已开始后重新分配 | 409 |
| FLOW-019 | admin 驱动完整状态链路 | 200 |

## 8. 数据库一致性

| ID | 场景 | 期望 |
|---|---|---|
| DB-001 | ticket.assignee_id JOIN users | 外键指向 active technician |
| DB-002 | 重复用户失败 | 数据库行数不增加 |
| DB-003 | employee 列表 total | 与 SQL 可见范围 COUNT 相等 |
| DB-004 | 非法状态流转 | tickets 状态、updated_at 和 events 数均不变 |
| DB-005 | 删除工单 | `ticket_events` 级联删除 |
