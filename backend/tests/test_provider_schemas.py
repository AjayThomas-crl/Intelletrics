import json
from unittest.mock import AsyncMock, Mock

from ai_insights import GeminiClient, InsightsResult, _compact_schema, build_insights_prompt
from query_planner import QueryPlan


def test_compact_schema_preserves_title_property():
    schema = json.loads(_compact_schema(InsightsResult))
    insight = schema['$defs']['DatasetInsight']
    assert 'title' in insight['properties']
    assert 'title' in insight['required']
    assert 'title' not in schema


def test_insights_context_is_bounded():
    profiles = [{'name': f'col_{i}', 'type': 'numeric', 'missing': {'count': i}, 'uniqueness': {'count': i}} for i in range(200)]
    prompt = build_insights_prompt(profiles, 'file.csv', 1000, 200)
    context = json.loads(prompt.split('\n')[-1])
    assert len(context['profiles']) == 16
    assert context['columns'] == 200
    assert context['profiles'][0]['column'] == 'col_199'


async def test_gemini_uses_json_schema_and_minimal_thinking():
    client = object.__new__(GeminiClient)
    client.model = 'gemini-3.5-flash-lite'
    generate = AsyncMock(return_value=Mock(parsed=None, text='{"sql":"SELECT count(*) FROM data"}'))
    client._client = Mock(aio=Mock(models=Mock(generate_content=generate)))
    plan = await client.generate_structured('prompt', QueryPlan, max_tokens=768)
    config = generate.call_args.kwargs['config']
    assert config.response_json_schema['properties']['sql']
    assert config.response_schema is None
    assert config.max_output_tokens == 768
    assert config.thinking_config.thinking_level.value.upper() == 'MINIMAL'
    assert plan.sql == 'SELECT count(*) FROM data'
