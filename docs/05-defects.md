# 真实缺陷记录

本文件只记录在本地测试过程中实际复现的两个缺陷，不虚构缺陷数量。两者均已完成修复和回归。

## BUG-001：工单更新显式传 null 返回 500

| 字段 | 内容 |
|---|---|
| 严重程度 | High |
| 发现阶段 | 边界/异常探索测试 |
| 状态 | Closed |
| 复现概率 | 必现 |
| 影响接口 | `PATCH /tickets/{ticket_id}` |

### 前置条件

- employee 已登录。
- 已创建一张 open 工单。

### 复现步骤

```bash
curl -X PATCH http://localhost:8000/tickets/1 \
  -H "Authorization: Bearer <employee-token>" \
  -H "Content-Type: application/json" \
  -d '{"title": null}'
```

对 `title`、`description`、`priority` 三个字段分别执行。

### 期望

显式 null 是非法输入，返回 422，数据库保持不变。

### 实际

三个字段均返回 500。原因：

1. Pydantic 将字段声明为 optional，允许 JSON null。
2. `model_dump(exclude_unset=True)` 会保留“客户端显式传入 null”。
3. 路由把 None 写入数据库非空列。
4. `IntegrityError` 未转换为客户端错误，最终返回 500。

### 修复

在 `TicketUpdate` 的 before model validator 中检查原始请求：

```python
for field in ("title", "description", "priority"):
    if field in data and data[field] is None:
        raise ValueError(f"{field} must not be null")
```

### 回归

`test_update_rejects_explicit_null_fields` 参数化执行：

```text
3 passed
```

## BUG-002：管理员可以降级自己

| 字段 | 内容 |
|---|---|
| 严重程度 | High |
| 发现阶段 | 权限/业务约束探索测试 |
| 状态 | Closed |
| 复现概率 | 必现 |
| 影响接口 | `PATCH /users/{user_id}/role` |

### 前置条件

- 使用一个 admin 账号登录。
- 目标 user_id 与当前账号相同。

### 复现步骤

```bash
curl -X PATCH http://localhost:8000/users/<own-id>/role \
  -H "Authorization: Bearer <admin-token>" \
  -H "Content-Type: application/json" \
  -d '{"role":"employee"}'
```

### 期望

管理员不应降级自己，返回 409，数据库角色保持 admin。

### 实际

返回 200，数据库角色变成 employee。此后该账号无法再访问管理员接口，单管理员部署会形成锁死。

### 修复

在角色更新接口中增加当前账号保护：

```python
if current_user.id == user.id and payload.role != UserRole.admin:
    raise HTTPException(status_code=409, detail="An admin cannot demote the current account")
```

### 回归

`test_admin_cannot_demote_current_account`：

```text
1 passed
```

同时用 SQL 断言角色仍为 admin。

## 缺陷闭环总结

```text
探索测试 -> 最小复现 -> 收集响应与日志 -> 定位校验/权限缺口
-> 提交修复 -> 针对性回归 -> 完整套件回归 -> 三次稳定执行
```
