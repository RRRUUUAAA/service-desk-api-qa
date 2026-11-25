# 测试报告

## 1. 概要

| 项目 | 内容 |
|---|---|
| 测试日期 | 2026-11-25 |
| 时区 | Asia/Shanghai |
| 被测系统 | Service Desk API |
| 测试类型 | 接口集成、权限、状态机、数据库一致性 |
| 最终结论 | 通过 |

## 2. 最终结果

| 指标 | 结果 |
|---|---:|
| 用例总数 | 95 |
| 通过 | 95 |
| 失败 | 0 |
| 错误 | 0 |
| 跳过 | 0 |
| 当前提交版本最终重建耗时 | 7.74s |

JUnit 文件：[reports/junit.xml](../reports/junit.xml)

```text
tests="95" failures="0" errors="0" skipped="0" time="7.743"
```

## 3. 稳定性

| 轮次 | 结果 | 耗时 |
|---|---|---:|
| 1 | 95 passed | 5.62s |
| 2 | 95 passed | 5.47s |
| 3 | 95 passed | 5.84s |
| 最终锁文件冷重建 | 95 passed | 5.02s |
| 当前提交版本最终重建 | 95 passed | 7.74s |

三次执行均使用同一数据库卷，没有重启或清空数据库，说明唯一数据与 teardown 可以支持重复执行。

## 4. 数据清理验证

全量测试完成后执行：

```sql
SELECT
  (SELECT COUNT(*) FROM users) AS users,
  (SELECT COUNT(*) FROM tickets) AS tickets,
  (SELECT COUNT(*) FROM ticket_events) AS ticket_events;
```

实际结果：

```text
 users | tickets | ticket_events
-------+---------+---------------
     1 |       0 |             0
```

唯一的用户是 bootstrap admin。测试用户、工单和审计事件均被清理。

## 5. 执行历史

### 第一轮：测试数据域名错误

结果：`22 passed, 10 failed, 59 errors`

原因：测试工厂使用 `@example.test`，`email-validator` 将其识别为保留域名并返回 422。大量 fixture 在创建用户阶段失败。

处理：测试数据改为合法的 `@example.com`；这不是被测系统缺陷。

### 第二轮：主套件通过

结果：`91 passed in 6.16s`

说明：鉴权、用户、工单、权限、状态机和数据库主流程均通过。

### 第三轮：探索性缺陷检查

新增 4 个参数化检查后：

结果：`0 passed, 4 failed`

发现：

- 显式 null 更新返回 500。
- 管理员可降级自己。

### 修复回归

缺陷修复后执行针对性测试：`4 passed`

最终完整套件：连续三次 `95 passed`；使用锁定依赖和固定镜像 digest 冷重建后再次 `95 passed in 5.02s`；EOF 规范化后的当前待提交版本再次执行 `95 passed in 7.74s`。

## 6. 覆盖矩阵

| 风险区域 | 覆盖 |
|---|---|
| 无 token / 错误 token / 过期 token | 已覆盖 |
| 角色级权限 | 已覆盖 |
| 对象级权限 | 已覆盖 |
| 用户唯一性和角色更新 | 已覆盖 |
| 工单 CRUD 和长度边界 | 已覆盖 |
| 显式 null 和非法枚举 | 已覆盖 |
| 状态机合法/非法迁移 | 已覆盖 |
| 分页上下界 | 已覆盖 |
| 数据库字段和审计事件 | 已覆盖 |
| 失败操作回滚 | 已覆盖 |
| 数据清理 | 已覆盖 |
| CI/JUnit | 已配置，本地报告已验证 |

## 7. 未覆盖与残余风险

- 未测试并发分配或并发状态更新。
- 未测试性能和容量。
- 未做真实第三方服务异常。
- GitHub Actions 工作流已提交，但本轮本地执行不等同于线上 CI 运行证明；首次 push 后仍需查看 Actions 结果。
- 自建靶场仅用于测试能力展示，不能表达真实生产流量。
