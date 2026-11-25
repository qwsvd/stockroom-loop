# 从 codex exec 的一次决策读懂公开客户端

本机报告 codex-cli 0.144.6。检出官方标记 rust-v0.144.6，其带注释标签指向提交 5d1fbf26c43abc65a203928b2e31561cb039e06d。以下链接固定到实际检查的源码。版本字符串相符无法证明本机二进制逐字节来自该源码。

| 顺序 | 在源码里跟踪什么 |
|---|---|
| 1. CLI 入口 | Rust CLI 的子命令分支合并覆盖参数并等待 codex_exec::run_main。这里还没有进行模型推理。[main.rs](https://github.com/openai/codex/blob/5d1fbf26c43abc65a203928b2e31561cb039e06d/codex-rs/cli/src/main.rs#L1002) |
| 2. 会话与请求 | run_main 启动进程内 App Server 客户端，构造 ThreadStartParams，再提交 TurnStartParams。thread 保存对话范围，turn 是其中一次工作请求。两者有不同处理入口。[exec](https://github.com/openai/codex/blob/5d1fbf26c43abc65a203928b2e31561cb039e06d/codex-rs/exec/src/lib.rs#L796) · [thread_start](https://github.com/openai/codex/blob/5d1fbf26c43abc65a203928b2e31561cb039e06d/codex-rs/app-server/src/request_processors/thread_processor.rs#L450) · [turn_start](https://github.com/openai/codex/blob/5d1fbf26c43abc65a203928b2e31561cb039e06d/codex-rs/app-server/src/request_processors/turn_processor.rs#L155) |
| 3. 外层循环 | 常规任务的 run 进入 run_turn。循环合并模型是否需要后续处理与是否有待处理输入，决定是否继续。工具结果可以触发下一轮。[regular.rs](https://github.com/openai/codex/blob/5d1fbf26c43abc65a203928b2e31561cb039e06d/codex-rs/core/src/tasks/regular.rs#L74) · [run_turn](https://github.com/openai/codex/blob/5d1fbf26c43abc65a203928b2e31561cb039e06d/codex-rs/core/src/session/turn.rs#L142) |
| 4. 请求、错误和重试 | run_sampling_request 读取流重试上限，调用 try_run_sampling_request，检查错误是否可重试；后者打开 client_session.stream。客户端实现区分 WebSocket 与 Responses API 路径。因此外部的一次策略决策不能换算成精确的服务端请求次数。[采样与重试](https://github.com/openai/codex/blob/5d1fbf26c43abc65a203928b2e31561cb039e06d/codex-rs/core/src/session/turn.rs#L1112) · [传输](https://github.com/openai/codex/blob/5d1fbf26c43abc65a203928b2e31561cb039e06d/codex-rs/core/src/client.rs#L1775) |
| 5. 响应与工具 | handle_output_item_done 调用 ToolRouter::build_tool_call。识别到工具后记录响应，构造 handle_tool_call 的异步任务，并设置 needs_follow_up。普通消息走完成消息的分支。[响应处理](https://github.com/openai/codex/blob/5d1fbf26c43abc65a203928b2e31561cb039e06d/codex-rs/core/src/stream_events_utils.rs#L318) · [工具调度](https://github.com/openai/codex/blob/5d1fbf26c43abc65a203928b2e31561cb039e06d/codex-rs/core/src/tools/parallel.rs#L75) |
| 6. 审批与隔离 | 对经过 ToolOrchestrator 的执行，run 评估审批需要、选择首次沙箱策略，再由 run_attempt 调用工具。SandboxManager::transform 按平台和策略构造执行参数。批准的意图与操作系统实际施加的约束是两层检查。[执行策略](https://github.com/openai/codex/blob/5d1fbf26c43abc65a203928b2e31561cb039e06d/codex-rs/core/src/tools/orchestrator.rs#L143) · [沙箱](https://github.com/openai/codex/blob/5d1fbf26c43abc65a203928b2e31561cb039e06d/codex-rs/sandboxing/src/manager.rs#L321) |
| 7. 上下文 | record_items 记录历史，for_prompt 为模型输入整理历史。run_turn 有压缩判断，run_inline_auto_compact_task 是公开的压缩入口之一。一个能继续工作的摘要仍可能丢失业务约束。[历史](https://github.com/openai/codex/blob/5d1fbf26c43abc65a203928b2e31561cb039e06d/codex-rs/core/src/context_manager/history.rs#L121) · [压缩](https://github.com/openai/codex/blob/5d1fbf26c43abc65a203928b2e31561cb039e06d/codex-rs/core/src/compact.rs#L91) |
| 8. 可观测性 | JSONL 处理器保存 ThreadTokenUsageUpdated 并在 turn.completed 发布 usage。缺数据时可返回默认值。ModelRerouted 与 ModelVerification 走不同分支，后者在此没有输出可验证的模型证明。[用量](https://github.com/openai/codex/blob/5d1fbf26c43abc65a203928b2e31561cb039e06d/codex-rs/exec/src/event_processor_with_jsonl_output.rs#L117) · [事件映射](https://github.com/openai/codex/blob/5d1fbf26c43abc65a203928b2e31561cb039e06d/codex-rs/exec/src/event_processor_with_jsonl_output.rs#L481) |

在 Stockroom Loop 中，Codex 返回动作文本，Python 校验后执行库存动作。我们用临时目录、只读沙箱并关闭几个工具功能。任务状态留在 Python 中，每次决策向新的 CLI 进程重发公开历史。CLI 内部的会话与我们的订单生命周期因此不同。

客户端源码能解释如何构造请求、处理流、执行工具以及发出使用量事件。推理权重、服务端调度、实际执行模型身份、账号计价和私有安全系统不在这条源码链内。本次没有对远端服务做逆向分析。
