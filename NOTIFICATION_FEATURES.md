# 邮件通知和 WebSocket 实时通知功能说明

## 邮件通知功能

### 配置

在 `.env` 文件中配置邮件服务：

```env
MAIL_SERVER=smtp.example.com
MAIL_PORT=587
MAIL_USE_TLS=true
MAIL_USERNAME=your-email@example.com
MAIL_PASSWORD=your-password
MAIL_DEFAULT_SENDER=noreply@example.com
```

### API 端点

#### 1. 获取邮件通知设置
```
GET /api/email/settings
```
获取当前用户的邮件通知配置

#### 2. 更新邮件通知设置
```
PUT /api/email/settings
```
参数：
- `enable_email` (bool): 是否启用邮件通知
- `enable_workflow_email` (bool): 是否启用工作流邮件通知
- `enable_system_email` (bool): 是否启用系统邮件通知
- `quiet_start` (str): 免打扰开始时间
- `quiet_end` (str): 免打扰结束时间

#### 3. 发送测试邮件
```
POST /api/email/test
```

#### 4. 查看邮件发送记录
```
GET /api/email/logs?status=sent&skip=0&limit=50
```
（仅管理员可访问）

### 自动发送邮件场景

工作流审批流程中会自动发送邮件：

1. **工作流待办通知** - 当有新的审批节点时
2. **审批结果通知** - 当流程完成（通过/拒绝）时
3. **抄送通知** - 当被抄送时

---

## WebSocket 实时通知

### 连接 WebSocket

客户端通过 JWT token 认证后建立 WebSocket 连接：

```javascript
// 前端示例
const token = localStorage.getItem('token');
const ws = new WebSocket(`ws://localhost:8000/api/ws/ws/notifications?token=${token}`);

ws.onopen = () => {
    console.log('WebSocket 连接成功');
};

ws.onmessage = (event) => {
    const message = JSON.parse(event.data);
    if (message.type === 'notification') {
        console.log('收到通知:', message.data);
        // 显示通知提示
    } else if (message.type === 'pong') {
        console.log('心跳响应');
    }
};

// 发送心跳
setInterval(() => {
    ws.send(JSON.stringify({ type: 'heartbeat' }));
}, 30000);
```

### 消息格式

#### 服务端 -> 客户端

```json
{
    "type": "notification",
    "data": {
        "id": 123,
        "title": "待办审批：资源申请流程 - 部门负责人审批",
        "content": "您有一个待审批的流程节点"
    },
    "timestamp": "2026-03-24T10:30:00"
}
```

#### 客户端 -> 服务端

心跳消息：
```json
{
    "type": "heartbeat"
}
```

已读确认：
```json
{
    "type": "mark_read",
    "notification_id": 123
}
```

### 在线用户查询

```
GET /api/ws/online-users
```

返回当前通过 WebSocket 在线的用户列表。

---

## 工作流通知集成

### 通知发送点

| 场景 | 站内通知 | WebSocket | 邮件 |
|------|----------|-----------|------|
| 启动工作流 | ✓ | ✓ | ✓ |
| 普通审批节点 | ✓ | ✓ | ✓ |
| 并行审批节点 | ✓ | ✓ | ✓ |
| 条件分支节点 | ✓ | ✓ | ✓ |
| 抄送节点 | ✓ | ✓ | ✓ |
| 审批通过 | ✓ | ✓ | ✓ |
| 审批拒绝 | ✓ | ✓ | ✓ |

### 用户免打扰设置

用户可通过 `/api/email/settings` 设置免打扰时间段，在免打扰时间内不会发送邮件通知。

---

## 测试建议

1. **测试邮件发送**：先发送测试邮件确认配置正确
2. **测试 WebSocket 连接**：使用浏览器控制台或 Postman 测试 WebSocket 连接
3. **测试工作流通知**：创建一个简单的工作流，测试各节点的通知发送
