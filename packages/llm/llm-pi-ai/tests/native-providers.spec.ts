/** Native onboarding routes exercise their real SDK protocols against local SSE servers. */
import { afterEach, expect, it, vi } from 'vitest'
import { Context } from '@deepseek-ai/cordis'
import LlmRuntime, { createUserMessage, ToolCallId } from '@deepseek-ai/dsh-llm'
import * as LlmPiAi from '@deepseek-ai/dsh-llm-pi-ai'
import { assemble } from './assemble.ts'
import { closeMockServers, mockServer } from './mock-server.ts'

const contexts: Context[] = []
afterEach(async () => {
  await Promise.all(contexts.splice(0).map(ctx => ctx.fiber.dispose()))
  await closeMockServers()
  vi.unstubAllEnvs()
})

const claudeEvents = [
  { type: 'message_start', message: { id: 'msg_fixture', type: 'message', role: 'assistant', model: 'claude-haiku-4-5', content: [], stop_reason: null, usage: { input_tokens: 12, output_tokens: 0 } } },
  { type: 'content_block_start', index: 0, content_block: { type: 'tool_use', id: 'call_fixture', name: 'lookup', input: {} } },
  { type: 'content_block_delta', index: 0, delta: { type: 'input_json_delta', partial_json: '{"word":' } },
  { type: 'content_block_delta', index: 0, delta: { type: 'input_json_delta', partial_json: '"ことば"}' } },
  { type: 'content_block_stop', index: 0 },
  { type: 'message_delta', delta: { stop_reason: 'tool_use', stop_sequence: null }, usage: { output_tokens: 8 } },
  { type: 'message_stop' },
]
const response = { id: 'resp_fixture', object: 'response', model: 'gpt-4.1', status: 'completed', output: [
  { type: 'function_call', id: 'fc_fixture', call_id: 'call_fixture', name: 'lookup', arguments: '{"word":"ことば"}', status: 'completed' },
], usage: { input_tokens: 12, output_tokens: 8, total_tokens: 20 } }
const openaiEvents = [
  { type: 'response.created', response: { ...response, status: 'in_progress', output: [] } },
  { type: 'response.output_item.added', output_index: 0, item: { ...response.output[0], arguments: '', status: 'in_progress' } },
  { type: 'response.function_call_arguments.delta', item_id: 'fc_fixture', output_index: 0, delta: '{"word":' },
  { type: 'response.function_call_arguments.delta', item_id: 'fc_fixture', output_index: 0, delta: '"ことば"}' },
  { type: 'response.output_item.done', output_index: 0, item: response.output[0] },
  { type: 'response.completed', response },
]
const kimiEvents = [
  { choices: [{ index: 0, delta: { role: 'assistant', tool_calls: [{ index: 0, id: 'call_fixture', type: 'function', function: { name: 'lookup', arguments: '{"word":' } }] }, finish_reason: null }] },
  { choices: [{ index: 0, delta: { tool_calls: [{ index: 0, function: { arguments: '"ことば"}' } }] }, finish_reason: null }] },
  { choices: [{ index: 0, delta: {}, finish_reason: 'tool_calls' }], usage: { prompt_tokens: 12, completion_tokens: 8, total_tokens: 20 } },
]

const providerCases: { provider: string; model: string; path: string; events: Record<string, unknown>[] }[] = [
  { provider: 'openai', model: 'gpt-4.1', path: '/v1/responses', events: openaiEvents },
  { provider: 'anthropic', model: 'claude-haiku-4-5', path: '/v1/messages', events: claudeEvents },
  { provider: 'moonshotai', model: 'kimi-k2-0905-preview', path: '/v1/chat/completions', events: kimiEvents },
]

it.each(providerCases)('streams bilingual tool calls using the native $provider API', async ({ provider, model, path, events }) => {
  const script = {
    events: [...events.map(event => JSON.stringify(event)), ...(provider === 'moonshotai' ? ['[DONE]'] : [])],
    ...(provider === 'anthropic' ? { eventNames: claudeEvents.map(event => event.type) } : {}),
  }
  const server = await mockServer([script, script,
    { status: 401, body: JSON.stringify({ error: { type: 'authentication_error', message: 'Invalid fixture key' } }) },
  ])
  vi.stubEnv('KOTOBA_FIXTURE_KEY', 'fixture-key-only')
  const ctx = new Context()
  contexts.push(ctx)
  await ctx.plugin(LlmRuntime)
  await ctx.plugin(LlmPiAi, { providers: { [provider]: {
    apiKeyEnv: 'KOTOBA_FIXTURE_KEY', baseURL: provider === 'anthropic' ? server.url : `${server.url}/v1`,
  } } })
  const result = await assemble(ctx, {
    provider, model, messages: [createUserMessage({ content: [{ type: 'text', text: 'Translate ことば into English.' }], source: { kind: 'plugin', plugin: 'test' } })],
    tools: [{ name: 'lookup', description: 'Look up a Japanese word.', parameters: { type: 'object', properties: { word: { type: 'string' } }, required: ['word'] } }],
    maxTokens: 256,
  })
  expect(result.finish).toMatchObject({ kind: 'tool-calls' })
  expect(result.message.content).toContainEqual(expect.objectContaining({ type: 'tool-call', name: 'lookup', arguments: '{"word":"ことば"}' }))
  expect(server.paths.map(value => new URL(value, server.url).pathname)).toEqual([path])
  expect(server.headers[0]?.[provider === 'anthropic' ? 'x-api-key' : 'authorization'])
    .toBe(provider === 'anthropic' ? 'fixture-key-only' : 'Bearer fixture-key-only')
  expect(JSON.stringify(server.requests[0])).toContain('Translate ことば into English.')
  expect(result.usage).toBeDefined()
  expect({ content: result.message.content, finish: result.finish }).toMatchSnapshot()
  const call = result.message.content.find(block => block.type === 'tool-call')!
  const replay = await assemble(ctx, { provider, model, messages: [
    result.message,
    createUserMessage({ content: [{ type: 'tool-result', toolCallId: ToolCallId(call.id),
      content: [{ type: 'text', text: 'ことば means word or language.' }] }], source: { kind: 'plugin', plugin: 'test' } }),
  ], maxTokens: 256 })
  expect(replay.finish.kind).toBe('tool-calls')
  expect(JSON.stringify(server.requests[1])).toContain('ことば means word or language.')
  const rejected = await assemble(ctx, { provider, model, messages: [], maxTokens: 256 })
  expect(rejected.finish.kind).toBe('error')
  expect(server.paths.map(value => new URL(value, server.url).pathname)).toEqual([path, path, path])
})
