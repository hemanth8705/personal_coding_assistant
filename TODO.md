# AI Engineering Learning TODO

Based on: TypeScript Pi (`packages/agent/`) vs Python Pi gap analysis.

These are engineering patterns to understand and implement — not feature additions.

---

## Level 2 — Agent Runtime Patterns

- [ ] **Parallel Tool Execution**
  - When LLM returns multiple tool calls in one response, run them concurrently
  - Use `asyncio.gather()` for IO-bound tools (file reads, bash)
  - Concept: concurrent task execution with a shared result barrier

- [ ] **Hook System — `before_tool_call` / `after_tool_call`**
  - `before_tool_call`: intercept before execution — block dangerous tools, permission prompts, logging
  - `after_tool_call`: intercept after execution — override result, sanitize huge outputs, force error flag
  - Concept: middleware / interceptor pattern applied to tool execution

- [ ] **`terminate` Flag on Tool Results**
  - A tool can signal "stop the agent loop after this batch"
  - Agent stops only when ALL tools in a batch return `terminate=True`
  - Concept: cooperative termination signaling from within tools

- [ ] **Mid-Run Steering**
  - `get_steering_messages()`: inject user messages mid-run while agent is working
  - `get_follow_up_messages()`: queue next messages after agent would otherwise stop
  - Concept: decoupling the input source from the agent loop

- [ ] **`transform_context` — Context Pipeline**
  - A hook that runs before every LLM call to transform message history
  - Use for: pruning old messages, injecting dynamic context, summarizing old tool results
  - Concept: context window management as a pluggable pipeline stage

- [ ] **Event System**
  - Emit structured lifecycle events: `agent_start`, `agent_end`, `turn_start`, `turn_end`, `tool_execution_start`, `tool_execution_end`
  - UI (terminal, Telegram, web) subscribes to events — fully decoupled from agent logic
  - Concept: event-driven architecture

- [ ] **Tool Streaming Updates (`on_update` callback)**
  - Tools call `on_update(partial_result)` while still running
  - Stream bash output line-by-line while command executes
  - Concept: progressive result streaming from long-running tools

- [ ] **Extensible Message Types**
  - Agent's internal message history holds non-LLM messages (notifications, artifacts, UI state)
  - `convert_to_llm()` filters these out before sending to LLM
  - Concept: internal representation vs LLM representation

---

## Level 3 — Production Patterns (from free-claude-code + leaked code)

- [ ] **Protocol Conversion (Anthropic ↔ OpenAI)**
  - Convert between Anthropic Messages format and OpenAI Chat format transparently
  - Understand SSE (Server-Sent Events) streaming protocol
  - Concept: wire protocol abstraction

- [ ] **Thinking / Reasoning Tokens**
  - Enable extended thinking, set token budget, handle thinking blocks in streaming
  - Concept: reasoning budget management

- [ ] **MCP (Model Context Protocol)**
  - Build an MCP server so your tools work with any client (Claude, Cursor, etc.)
  - Concept: standardized tool protocol

---

## Order of Attack

1. Parallel tool execution — biggest impact, relatively simple with `asyncio`
2. Event system — unlocks clean UI decoupling
3. Hook system — adds safety and observability
4. terminate flag — cleaner loop control
5. transform_context — proper context management
6. Mid-run steering — advanced agent control
7. Tool streaming updates — polish
8. Extensible message types — architecture cleanup
9. Protocol conversion — Level 3
10. Thinking tokens — Level 3
11. MCP server — Level 3
