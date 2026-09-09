"""Run with python -m unittest -v. No models or network required."""
import ast
import itertools
import unittest
from types import SimpleNamespace as Chunk
from evaluation import (parse_chunk, anchor_match, ranked_metrics,
                        validate_questions, verify_citations, decide)


def chunk(symbol, line, end=None):
    return Chunk(file_path='a.py', symbol_name=symbol, start_line=line,
                 end_line=end or line + 2)


def gold(symbol, line):
    return {'file': 'a.py', 'symbol': symbol, 'start_line': line}


class EvaluationTests(unittest.TestCase):
    def test_indented_method_keeps_calls(self):
        source = '    def send(self):\n        return self.prepare()\n'
        tree = parse_chunk(source)
        self.assertTrue(any(isinstance(n, ast.Call) for n in ast.walk(tree)))
        self.assertTrue(source.startswith('    '))
        with self.assertRaises(SyntaxError):
            parse_chunk('    def broken(')

    def test_same_name_other_method_is_not_gold(self):
        self.assertFalse(anchor_match(chunk('send', 100), gold('send', 900)))
        self.assertTrue(anchor_match(chunk('send', 100), gold('send', 100)))

    def test_enclosing_class_does_not_replace_method(self):
        self.assertFalse(anchor_match(chunk('Client', 1, 200), gold('send', 100)))

    def test_gold_order_and_duplicates_do_not_inflate_score(self):
        by_id = {'class': chunk('Client', 1, 200), 'a': chunk('a', 10), 'b': chunk('b', 20)}
        values = [ranked_metrics(['class', 'a', 'a', 'b'], list(g), by_id)
                  for g in itertools.permutations([gold('a', 10), gold('b', 20)])]
        self.assertEqual(values[0], values[1])
        self.assertEqual(values[0]['recall@5'], 1)
        self.assertEqual(values[0]['mrr@5'], .5)
        self.assertLess(values[0]['ndcg@5'], 1)
        self.assertEqual(ranked_metrics(['a'], [gold('a', 10)], by_id)['ndcg@5'], 1)

    def test_unknown_empty_and_cutoff(self):
        by_id = {'a': chunk('a', 10)}
        for ids in ([], ['missing'], ['missing'] * 5 + ['a']):
            self.assertEqual(ranked_metrics(ids, [gold('a', 10)], by_id),
                             {'recall@5': 0, 'mrr@5': 0, 'ndcg@5': 0})

    def test_gold_validation(self):
        q = {'id': 'q1', 'taxonomy': 'L2', 'gt_targets': [gold('a', 10)]}
        validate_questions([q], [chunk('a', 10)])
        for qs, chunks in (([], []), ([q, q], [chunk('a', 10)]), ([q], []),
                           ([q], [chunk('a', 10), chunk('a', 10)])):
            with self.assertRaises(ValueError):
                validate_questions(qs, chunks)

    def test_citation_denominator_and_observed_scope(self):
        by_id = {'a.py#1': chunk('a', 10), 'a.py#2': chunk('b', 20)}
        r = verify_citations('[a.py#1] [a.py#1] [a.py#2] [bad#oops]', by_id, {'a.py#1'})
        self.assertEqual(r['citation_id_validity'], 1 / 3)
        self.assertEqual(r['verified'], ['a.py#1'])
        self.assertNotIn('[a.py#2]', r['answer'])
        self.assertEqual(verify_citations('No citations', by_id)['citation_id_validity'], 0)
        self.assertNotIn('groundedness', r)

    def test_decision_uses_unrounded_values(self):
        rule = {'treatment': 'B4', 'controls': ['B3'], 'strata': ['L2'], 'min_margin': .05}
        checks, verdict = decide({'L2': {'B4': .049999, 'B3': 0}}, rule)
        self.assertEqual(verdict, 'unsupported')
        self.assertEqual(decide({'L2': {'B4': .05, 'B3': 0}}, rule)[1], 'supported')
        with self.assertRaises(KeyError):
            decide({}, rule)


class AgentAdapterTests(unittest.TestCase):
    def test_framework_prompt_and_four_tool_round_trip(self):
        import contextlib
        import io
        from agent_demo import build_agent

        calls = []
        names = ['search_code', 'file_outline', 'read_symbol', 'find_callers']

        class ScriptedLLM:
            def __init__(self):
                self.responses = iter([f'Thought: inspect\nAction: {name}[sample]' for name in names]
                                      + ['Thought: done\nAction: Finish[Answer [auth.py#2]]'])
                self.prompts = []

            def invoke(self, messages, **kwargs):
                self.prompts.append(messages[0]['content'])
                return next(self.responses)

        llm = ScriptedLLM()
        functions = {name: lambda text, name=name: calls.append((name, text)) or '[auth.py#2] source'
                     for name in names}
        agent = build_agent(llm, functions)
        with contextlib.redirect_stdout(io.StringIO()):
            answer = agent.run('Where is auth?')
        self.assertEqual([name for name, _ in calls], names)
        self.assertIn('[auth.py#2]', answer)
        self.assertTrue(all('Every factual claim' in prompt for prompt in llm.prompts))
        self.assertIn('Observation:', llm.prompts[-1])


class LiveParameterTests(unittest.TestCase):
    def test_serialized_completion_parameters(self):
        import json
        import os
        from unittest.mock import patch
        import httpx
        from openai import OpenAI
        from agent_demo import configured_llm

        for model in ('gpt-5.4-mini', 'gpt-4o-mini'):
            with self.subTest(model=model):
                payloads = []

                def respond(request):
                    payloads.append(json.loads(request.content))
                    return httpx.Response(200, json={
                        'id': 'test', 'object': 'chat.completion', 'created': 0,
                        'model': model, 'choices': [{'index': 0, 'finish_reason': 'stop',
                            'message': {'role': 'assistant', 'content': 'ok'}}]})

                with patch.dict(os.environ, {'LLM_MODEL_ID': model, 'LLM_API_KEY': 'test',
                                             'LLM_BASE_URL': 'https://example.invalid/v1'}):
                    llm = configured_llm()
                with httpx.Client(transport=httpx.MockTransport(respond)) as client:
                    llm._client = OpenAI(api_key='test', http_client=client)
                    self.assertEqual(llm.invoke([{'role': 'user', 'content': 'test'}]), 'ok')
                if model.startswith('gpt-5'):
                    self.assertEqual(payloads[0]['max_completion_tokens'], 4096)
                    self.assertNotIn('max_tokens', payloads[0])
                    self.assertNotIn('temperature', payloads[0])
                else:
                    self.assertEqual(payloads[0]['max_tokens'], 4096)
                    self.assertNotIn('max_completion_tokens', payloads[0])


if __name__ == '__main__':
    unittest.main()
