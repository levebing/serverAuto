# 服务器巡检系统 - API 接口文档

---

## 目录

- [一、认证模块](#一认证模块)
- [二、服务器管理模块](#二服务器管理模块)
- [三、巡检模块](#三巡检模块)
- [四、分组管理模块](#四分组管理模块)
- [五、定时任务模块](#五定时任务模块)
- [六、报告管理模块](#六报告管理模块)
- [七、文件下载模块](#七文件下载模块)
- [八、通用说明](#八通用说明)

---

## 一、认证模块

### 1. 用户登录

| 属性 | 值 |
|------|-----|
| **接口地址** | `POST /login` |
| **请求方式** | POST |

**请求参数**（JSON）:

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| username | string | 是 | 用户名 |
| password | string | 是 | 密码 |

**成功响应**（JSON）:
```json
{
  "success": true,
  "token": "22745da1663c48613676d75c6a036480cd48e006f9299b294bf35810c9f8876e",
  "expires_at": "2026-06-16 16:35:27",
  "token_expires_in": 86400
}
```

**失败响应**（JSON）:
```json
{"success": false, "message": "用户名或密码错误"}
```

**返回字段说明**:

| 字段名 | 类型 | 说明 |
|--------|------|------|
| success | bool | 请求是否成功 |
| username | string | 用户名 |
| token | string | API Token（用于后续接口认证） |
| token_expires_in | int | Token有效期（秒），默认86400秒（24小时） |

---

### 2. 用户登出

| 属性 | 值 |
|------|-----|
| **接口地址** | `GET /logout` |
| **请求方式** | GET |

**说明**: 清除 session，重定向到登录页

---

### 3. 修改密码

| 属性 | 值 |
|------|-----|
| **接口地址** | `POST /change_password` |
| **请求方式** | POST |

**请求参数**（Form Data）:

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| old_password | string | 是 | 原密码 |
| new_password | string | 是 | 新密码 |
| confirm_password | string | 是 | 确认密码 |

---

## 二、服务器管理模块

### 1. 服务器列表

| 属性 | 值 |
|------|-----|
| **接口地址** | `GET /` |
| **请求方式** | GET |

**请求参数**（Query）:

| 参数名 | 类型 | 必填 | 默认值 | 说明 |
|--------|------|------|--------|------|
| group_id | string | 否 | all | 分组ID，all表示全部 |
| ip | string | 否 | - | IP搜索关键字 |
| page | int | 否 | 1 | 页码 |

---

### 2. 添加服务器

| 属性 | 值 |
|------|-----|
| **接口地址** | `POST /add` |
| **请求方式** | POST |
| **认证方式** | 在请求头中添加 `X-API-Token` |

**请求头**（Headers）:

| Header名 | 值 | 必填 | 说明 |
|----------|-----|------|------|
| X-API-Token | string | 是 | 登录时获取的API Token |

**请求参数**（Form Data）:

| 参数名 | 类型 | 必填 | 默认值 | 说明 |
|--------|------|------|--------|------|
| name | string | 是 | - | 服务器名称 |
| ip | string | 是 | - | IP地址 |
| port | int | 是 | - | SSH端口 |
| username | string | 是 | - | SSH用户名 |
| group_id | int | 否 | 1 | 分组ID |
| remark | string | 否 | - | 备注 |
| private_key | file | 否 | - | SSH密钥文件（与password二选一） |
| password | string | 否 | - | SSH密码（与private_key二选一） |
| os_type | string | 否 | linux | 操作系统类型（linux/windows） |

**成功响应**:
- HTTP状态码: 302（重定向到服务器列表页）

**失败响应**（JSON）:
```json
{"success": false, "message": "未授权访问，请提供有效的 API Token"}
```

**调用示例**:
```bash
curl -X POST http://localhost:5001/add \
  -H "X-API-Token: 22745da1663c48613676d75c6a036480cd48e006f9299b294bf35810c9f8876e" \
  -F "name=测试服务器" \
  -F "ip=192.168.1.100" \
  -F "port=22" \
  -F "username=root" \
  -F "password=123456"
```

---

### 3. 编辑服务器

| 属性 | 值 |
|------|-----|
| **接口地址** | `POST /edit/<server_id>` |
| **请求方式** | POST |

**路径参数**:

| 参数名 | 类型 | 说明 |
|--------|------|------|
| server_id | int | 服务器ID |

**请求参数**（Form Data）: 同添加服务器

---

### 4. 删除服务器

| 属性 | 值 |
|------|-----|
| **接口地址** | `GET /delete/<server_id>` |
| **请求方式** | GET |

**路径参数**:

| 参数名 | 类型 | 说明 |
|--------|------|------|
| server_id | int | 服务器ID |

---

## 三、巡检模块

### 1. 执行巡检（同步）

| 属性 | 值 |
|------|-----|
| **接口地址** | `GET /inspect/<server_id>` |
| **请求方式** | GET |

**路径参数**:

| 参数名 | 类型 | 说明 |
|--------|------|------|
| server_id | int | 服务器ID |

---

### 2. 异步巡检

| 属性 | 值 |
|------|-----|
| **接口地址** | `POST /api/inspect_async/<server_id>` |
| **请求方式** | POST |
| **认证方式** | 在请求头中添加 `X-API-Token` |

**请求头**（Headers）:

| Header名 | 值 | 必填 | 说明 |
|----------|-----|------|------|
| X-API-Token | string | 是 | 登录时获取的API Token |
| Content-Type | application/json | 是 | 固定值 |

**路径参数**:

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| server_id | int | 是 | 服务器ID |

**成功响应**（JSON）:
```json
{
  "success": true,
  "server_name": "服务器名称",
  "server_ip": "192.168.1.1",
  "inspection_result": "正常 | CPU 25%, 内存 60%",
  "inspection_time": "2024-01-01 12:00:00"
}
```

**成功响应字段说明**:

| 字段名 | 类型 | 说明 |
|--------|------|------|
| success | bool | 请求是否成功 |
| server_name | string | 服务器名称 |
| server_ip | string | 服务器IP地址 |
| inspection_result | string | 巡检结果摘要（正常/告警及具体指标） |
| inspection_time | string | 巡检时间 |

**失败响应**（JSON）:
```json
{"success": false, "message": "连接超时"}
```

**失败响应字段说明**:

| 字段名 | 类型 | 说明 |
|--------|------|------|
| success | bool | 请求是否失败 |
| message | string | 失败原因（连接超时/SSH认证失败/服务器不存在等） |

**调用示例**:
```bash
curl -X POST http://localhost:5001/api/inspect_async/1 \
  -H "X-API-Token: 22745da1663c48613676d75c6a036480cd48e006f9299b294bf35810c9f8876e" \
  -H "Content-Type: application/json"
```

---

### 3. 巡检记录列表

| 属性 | 值 |
|------|-----|
| **接口地址** | `GET /records` |
| **请求方式** | GET |

**请求参数**（Query）:

| 参数名 | 类型 | 必填 | 默认值 | 说明 |
|--------|------|------|--------|------|
| group_id | string | 否 | all | 分组ID |
| ip | string | 否 | - | IP搜索 |
| page | int | 否 | 1 | 页码 |

---

### 4. 获取巡检记录详情

| 属性 | 值 |
|------|-----|
| **接口地址** | `GET /api/get_record_detail/<record_id>` |
| **请求方式** | GET |

**路径参数**:

| 参数名 | 类型 | 说明 |
|--------|------|------|
| record_id | int | 记录ID |

**成功响应**（JSON）:
```json
{
  "success": true,
  "record": {
    "server_name": "服务器名称",
    "server_ip": "192.168.1.1",
    "group_name": "测试分组",
    "cpu_usage": "25%",
    "memory_usage": "60%",
    "disk_usage": "[{...}]",
    "system_time": "2024-01-01 12:00:00",
    "os_version": "CentOS 7",
    "alert_content": "无告警",
    "inspection_result": "正常",
    "inspection_time": "2024-01-01 12:00:00"
  }
}
```

---

### 5. 下载巡检报告

| 属性 | 值 |
|------|-----|
| **接口地址** | `GET /download_report/<record_id>` |
| **请求方式** | GET |

**路径参数**:

| 参数名 | 类型 | 说明 |
|--------|------|------|
| record_id | int | 记录ID |

**响应**: DOCX 文件流

---

### 6. 删除巡检记录

| 属性 | 值 |
|------|-----|
| **接口地址** | `GET /delete_record/<record_id>` |
| **请求方式** | GET |

**路径参数**:

| 参数名 | 类型 | 说明 |
|--------|------|------|
| record_id | int | 记录ID |

---

## 四、分组管理模块

### 1. 分组列表

| 属性 | 值 |
|------|-----|
| **接口地址** | `GET /groups` |
| **请求方式** | GET |

**请求参数**（Query）:

| 参数名 | 类型 | 必填 | 默认值 | 说明 |
|--------|------|------|--------|------|
| name | string | 否 | - | 分组名称搜索 |
| page | int | 否 | 1 | 页码 |
| per_page | int | 否 | 10 | 每页数量 |

---

### 2. 添加分组

| 属性 | 值 |
|------|-----|
| **接口地址** | `POST /api/add_group` |
| **请求方式** | POST |

**请求参数**（JSON）:

| 参数名 | 类型 | 必填 | 默认值 | 说明 |
|--------|------|------|--------|------|
| name | string | 是 | - | 分组名称 |
| sort_order | int | 否 | 0 | 排序序号 |
| parent_id | int | 否 | null | 父分组ID |

**成功响应**（JSON）:
```json
{"success": true, "group_id": 1, "name": "测试分组"}
```

---

### 3. 更新分组

| 属性 | 值 |
|------|-----|
| **接口地址** | `POST /api/update_group` |
| **请求方式** | POST |

**请求参数**（JSON）:

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| group_id | int | 是 | 分组ID |
| name | string | 是 | 分组名称 |
| sort_order | int | 否 | 排序序号 |
| parent_id | int | 否 | 父分组ID |

---

### 4. 删除分组

| 属性 | 值 |
|------|-----|
| **接口地址** | `GET /api/delete_group/<group_id>` |
| **请求方式** | GET |

**路径参数**:

| 参数名 | 类型 | 说明 |
|--------|------|------|
| group_id | int | 分组ID |

**失败响应**（JSON）:
```json
{"success": false, "message": "不能删除默认分组"}
```

---

### 5. 更新分组排序

| 属性 | 值 |
|------|-----|
| **接口地址** | `POST /api/update_group_sort` |
| **请求方式** | POST |

**请求参数**（JSON）:

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| group_id | int | 是 | 分组ID |
| sort_order | int | 是 | 新排序序号 |

---

### 6. 搜索分组

| 属性 | 值 |
|------|-----|
| **接口地址** | `GET /api/search_groups` |
| **请求方式** | GET |

**请求参数**（Query）:

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| name | string | 否 | 搜索关键字 |

---

## 五、定时任务模块

### 1. 定时任务列表

| 属性 | 值 |
|------|-----|
| **接口地址** | `GET /tasks` |
| **请求方式** | GET |

---

### 2. 添加定时任务

| 属性 | 值 |
|------|-----|
| **接口地址** | `POST /api/add_task` |
| **请求方式** | POST |

**请求参数**（JSON）:

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| server_id | int | 是 | 服务器ID |
| cron_expression | string | 是 | Cron表达式 |
| enabled | bool | 否 | true | 是否启用 |

---

### 3. 更新定时任务

| 属性 | 值 |
|------|-----|
| **接口地址** | `POST /api/update_task` |
| **请求方式** | POST |

**请求参数**（JSON）:

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| task_id | int | 是 | 任务ID |
| cron_expression | string | 是 | Cron表达式 |
| enabled | bool | 否 | 是否启用 |

---

### 4. 删除定时任务

| 属性 | 值 |
|------|-----|
| **接口地址** | `GET /api/delete_task/<server_id>` |
| **请求方式** | GET |

**路径参数**:

| 参数名 | 类型 | 说明 |
|--------|------|------|
| server_id | int | 服务器ID |

---

## 六、报告管理模块

### 1. 删除报告

| 属性 | 值 |
|------|-----|
| **接口地址** | `GET /api/delete_report/<report_id>` |
| **请求方式** | GET |

**路径参数**:

| 参数名 | 类型 | 说明 |
|--------|------|------|
| report_id | int | 报告ID |

---

## 七、文件下载模块

### 1. 文件下载

| 属性 | 值 |
|------|-----|
| **接口地址** | `GET /download` |
| **请求方式** | GET |

**请求参数**（Query）:

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| path | string | 是 | 文件路径（相对路径） |

---

## 八、通用说明

### 认证要求

- 除 `/login` 外，所有接口均需登录认证
- 使用 Flask Session 进行会话管理

### 响应格式

- 成功响应: `{"success": true, ...}`
- 失败响应: `{"success": false, "message": "错误信息"}`

### 错误码

| HTTP状态码 | 说明 |
|-----------|------|
| 400 | 请求参数错误 |
| 401 | 未登录或会话过期 |
| 403 | 权限不足或路径非法 |
| 404 | 资源不存在 |
| 500 | 服务器内部错误 |

---

> **注**: 所有接口均需要在登录状态下访问，未登录用户将被重定向到登录页。

---

**文档版本**: v1.0  
**生成时间**: 2024年  
**所属项目**: 服务器巡检系统
