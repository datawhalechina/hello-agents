# 多平台聊天文件导入

进入数据源页面，填写来源标识，文件格式保持自动识别，选择原始导出文件，再执行检查并导入。原始时间没有时区时，采用页面所选时区，默认北京时间。格式、来源、时区或文件变更会使旧检查失效。

## 支持的导出结构

| 导出类型 | 文件格式 | 识别依据 |
|---|---|---|
| 飞书 API、CLI 历史消息 | JSON / JSONL | message_id、create_time、body.content 或 content，兼容原有 messages/items/data 容器 |
| 飞书活动或通用消息列表 | JSON / JSONL | id、time、chat、sender、content，保留 kind、source、link、attachments 等原字段 |
| ChatLab 多平台交换格式 | JSON / JSONL | chatlab/meta/members/messages，JSONL 的 header/member/message 类型，使用平台和成员表 |
| 多会话打包导出 | JSON | chats、conversations 或 sessions 容器内的消息列表，按各自会话继承明确的平台与标识 |
| 微信常见导出 | CSV / TSV / JSON | CreateTime、StrTime、StrContent、NickName、StrTalker、IsSender、MsgSvrID、localId 等列 |
| QQ 结构化记录 | JSON / JSONL | 群或私聊标识、发送人、原始时间、原生消息 ID、文本字段 |
| QQ OneBot / NapCat | JSON / JSONL | 账号、会话、发送人和消息段数组，保留文本、提及、媒体与回复引用 |
| QQ 或通用聊天文本 | TXT | 日期时间与发送人消息头，正文可跨多行，QQ 昵称与账号可一并保留 |
| 静态聊天导出网页 | HTML / HTM | 带字段表头的消息表格、可识别消息节点/data 属性或 application/json 消息数据 |

JSON 与 CSV 字段适配使用共同的别名规则。发送人、会话、时间、正文与标识的原始字段会记录在元数据中。同一条记录里的字段值发生实际矛盾时，检查器报告对应位置和字段。

ChatLab 的 JSON/JSONL 容器参考其公开格式规范。QQ 消息链参考 OneBot 与 NapCat 的公开消息结构。[ChatLab 格式规范](https://docs.chatlab.fun/standard/chatlab-format)、[OneBot 消息数据类型](https://github.com/botuniverse/onebot/blob/main/specs/interface/message/type.md)、[NapCat 事件结构](https://napneko.github.io/onebot/basic_event)

## 原文与标识

原消息保存在 metadata.raw。HTML 记录保留对应原始片段，TXT 记录保留原始消息段。图片、语音、文件等附件保留消息段、链接或路径元数据。导入过程只解析本地文件内容。

已有标准消息与原飞书历史消息沿用既有标识和规范化结构。微信、QQ 中仅在会话内唯一的标识加上账号/会话命名空间，原生值保留在元数据中。缺少原生标识的可识别导出生成 localimport 标识，其哈希依据和重复出现次序明确记录，界面显示提醒。同文件中的相同文本消息可保留各次出现，重新导入同文件能稳定去重。

导出头、会话资料和完整成员表按哈希单独保存一次。每条消息保存引用及当前发送人的必要资料。该上下文与消息在同一数据库事务中提交，任一写入失败会整体回滚。新的导出时间或新增无关成员可以生成另一份导出上下文，相同的原消息仍按重复处理，并保留最初存储的证据。删除来源时同步清理该来源的导出上下文。

## 编码与错误处理

支持 UTF-8、带 BOM 的 UTF-16/32，以及严格 GB18030/GBK 解码。没有原始时间、无法识别的文件结构或损坏的语法会出现在检查结果中。静态 HTML 的脚本内容作为原始资料保存，页面解析只提取可识别消息节点。二进制或加密备份需先导出为表中格式。

全部有效时完成导入。有异常时，可下载或复制完整问题记录，也可以确认只导入可识别消息。正式提交绑定原始文件内容、所选选项及检查指纹，已有数据发生冲突时需要重新检查。保留每文件10 MiB、最多10000条消息的现有限制。

## 本次验证

测试使用合成的多平台消息，覆盖检查、正式提交、重复导入、原始元数据、消息链、时区、编码和事务回滚。与用户提供的字段结构相同的134条合成消息已完成检查、导入和重复去重验证。用户完整的134条原文件尚未提供，本次验证范围为其样本字段和独立格式用例。

Main 最终运行553项 pytest 和37项连接器检查，均通过。严格前端构建通过。隔离浏览器验证了自动识别、格式覆盖、重复导入、显式部分导入、配置变化取消预检、问题报告和移动端显示。真实服务已更新，Main 用只读检查确认新入口默认自动识别，并核对原有数据与配置的数据库摘要。
