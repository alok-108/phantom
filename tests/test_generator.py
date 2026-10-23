"""Tests for the generator workflow, planner, transformer and providers."""

from __future__ import annotations

import ast
import json

import pytest

from phantom.generator import GenerationRequest, StaticProvider, generate
from phantom.generator.diff import host_layer_diff, strip_phantom_layer, unified_diff
from phantom.generator.planner import parse_plan, validate_plan
from phantom.generator.prompts import build_prompt
from phantom.generator.provider import (
    GeminiProvider,
    OpenAICompatibleProvider,
    ProviderError,
    RetryingProvider,
    redact,
)
from phantom.generator.transformer import (
    TransformError,
    apply_plan,
    resolve_placement,
    unsafe_insertion_lines,
)
from phantom.ir import EncodingMode
from phantom.parser import parse

PROGRAM = '''import sys


def greet(name):
    return "hi " + name


def main():
    print(greet("x"))


main()
'''


def _plan(*instructions, encoding="comment"):
    return json.dumps(
        {
            "request_summary": "test",
            "encoding": encoding,
            "instructions": [
                {
                    "instruction_type": t,
                    "arguments": [
                        {"type": "integer" if isinstance(v, int) else "string", "value": v}
                        for v in args
                    ],
                    "placement_line": 1,
                    "rationale": "because",
                }
                for t, *args in instructions
            ],
        }
    )


def _request(source=PROGRAM, **kw):
    return GenerationRequest(source_code=source, intent="annotate", **kw)


class TestPlanner:
    def test_parses_fenced_json(self):
        text = "Here you go:\n```json\n" + _plan(("meta.author", "A")) + "\n```"
        plan = parse_plan(text)
        assert plan.valid and plan.instructions[0].instruction_type == "meta.author"

    def test_rejects_non_json(self):
        with pytest.raises(ValueError):
            parse_plan("I cannot do that")

    @pytest.mark.parametrize(
        "instruction,fragment",
        [
            (("os.system", "rm -rf"), "unknown instruction"),
            (("counter.create", "c", "ten"), "must be integer"),
            (("meta.author",), "expected 1 argument"),
        ],
    )
    def test_invalid_instructions(self, instruction, fragment):
        plan = parse_plan(_plan(instruction))
        assert not plan.valid
        assert any(fragment in e for e in plan.validation_errors)

    def test_empty_plan_invalid(self):
        assert not parse_plan(_plan()).valid

    def test_bool_is_not_integer(self):
        plan = parse_plan(_plan(("meta.author", "a")))
        plan.instructions[0].placement_line = True
        assert not validate_plan(plan).valid


class TestTransformer:
    def test_inserts_without_touching_host(self):
        plan = parse_plan(_plan(("meta.author", "Alice")))
        out = apply_plan(PROGRAM, plan)
        assert out.splitlines()[0].startswith("#: phantom:0.1.0 meta.author")
        assert ast.dump(ast.parse(out)) == ast.dump(ast.parse(PROGRAM))
        assert strip_phantom_layer(out) == PROGRAM

    @pytest.mark.parametrize("enc", ["whitespace", "unicode"])
    def test_stego_candidates_stay_valid_python(self, enc):
        plan = parse_plan(_plan(("diagnostic.note", "hidden"), encoding=enc))
        out = apply_plan(PROGRAM, plan)
        ast.parse(out)
        prog = parse(out)
        assert not prog.errors
        assert prog.instructions[0].get_string_arg(0) == "hidden"

    def test_refuses_insertion_inside_string(self):
        src = 'x = """a\nb\nc"""\n'
        plan = parse_plan(_plan(("meta.author", "A")))
        plan.instructions[0].placement_line = 2
        with pytest.raises(TransformError):
            apply_plan(src, plan)
        assert 2 in unsafe_insertion_lines(src)

    def test_refuses_insertion_inside_brackets(self):
        src = "x = [\n    1,\n    2,\n]\n"
        plan = parse_plan(_plan(("meta.author", "A")))
        plan.instructions[0].placement_line = 3
        with pytest.raises(TransformError):
            apply_plan(src, plan)

    def test_refuses_invalid_plan(self):
        with pytest.raises(TransformError):
            apply_plan(PROGRAM, parse_plan(_plan(("nope.nope", "x"))))

    def test_preserves_crlf(self):
        plan = parse_plan(_plan(("meta.author", "A")))
        out = apply_plan("print(1)\r\n", plan)
        assert out.count("\r\n") == 2 and "\n" not in out.replace("\r\n", "")


class TestPlacement:
    def test_keywords(self):
        assert resolve_placement(PROGRAM, "beginning") == 1
        assert resolve_placement(PROGRAM, "end") == len(PROGRAM.splitlines()) + 1
        assert resolve_placement(PROGRAM, "line:4") == 4

    def test_near_function(self):
        assert resolve_placement(PROGRAM, "near:main") == 8

    def test_ambiguous_and_missing(self):
        dup = "def f():\n    pass\n\n\nclass A:\n    def f(self):\n        pass\n"
        with pytest.raises(TransformError, match="ambiguous"):
            resolve_placement(dup, "near:f")
        with pytest.raises(TransformError, match="No function"):
            resolve_placement(PROGRAM, "near:nothing")

    @pytest.mark.parametrize("bad", ["line:0", "line:999", "line:x", "middle"])
    def test_bad_specs(self, bad):
        with pytest.raises(TransformError):
            resolve_placement(PROGRAM, bad)


class TestWorkflow:
    def test_success(self):
        res = generate(
            _request(), StaticProvider(_plan(("meta.author", "A"), ("event.declare", "e")))
        )
        assert res.success and res.validation_passed
        assert "+#: phantom:0.1.0 meta.author" in res.diff
        assert strip_phantom_layer(res.candidate_source) == PROGRAM

    def test_model_line_numbers_are_ignored(self):
        plan = json.loads(_plan(("meta.author", "A")))
        plan["instructions"][0]["placement_line"] = 7
        res = generate(_request(placement="end"), StaticProvider(json.dumps(plan)))
        assert res.success
        assert res.candidate_source.splitlines()[-1].startswith("#: phantom")

    def test_invalid_input_python(self):
        res = generate(_request("def :\n"), StaticProvider("{}"))
        assert not res.success and "not valid Python" in res.errors[0]

    def test_ambiguous_placement_is_reported_not_guessed(self):
        calls = []
        res = generate(
            _request("def f(): pass\ndef f(): pass\n", placement="near:f"),
            StaticProvider(lambda p: calls.append(p) or "{}"),
        )
        assert not res.success and "ambiguous" in res.errors[0]
        assert calls == []

    def test_provider_failure(self):
        class Boom(StaticProvider):
            def complete(self, prompt):
                raise ProviderError("offline")

        res = generate(_request(), Boom(""))
        assert not res.success and res.errors == ["offline"]

    def test_malformed_response(self):
        res = generate(_request(), StaticProvider("sorry"))
        assert not res.success and "Unusable" in res.errors[0]

    def test_unsupported_instruction_rejected(self):
        res = generate(_request(), StaticProvider(_plan(("system.exec", "calc"))))
        assert not res.success and res.candidate_source is None

    def test_semantic_phantom_error_fails_validation(self):
        res = generate(_request(), StaticProvider(_plan(("event.on", "ghost", "a.b"))))
        assert not res.success and not res.phantom_valid
        assert res.candidate_source is not None  # shown for review, not accepted

    def test_oversized_source(self):
        res = generate(_request("x = 1\n" * 30000), StaticProvider("{}"))
        assert not res.success and "limit" in res.errors[0]

    def test_generation_never_executes_candidate(self, tmp_path):
        marker = tmp_path / "ran.txt"
        src = f"open({str(marker)!r}, 'w').write('x')\n"
        res = generate(_request(src), StaticProvider(_plan(("meta.author", "A"))))
        assert res.success and not marker.exists()


class TestPromptAndProviders:
    def test_prompt_lists_real_registry_and_line(self):
        prompt = build_prompt(_request(), 5)
        assert "counter.create(name: string, limit: integer)" in prompt
        assert "before line 5" in prompt
        assert "   1 | import sys" in prompt

    def test_redaction(self):
        text = "failed key=AIzaSyA1234567890abcdefghijklmnop and sk-abcdefghijklmnopqrstuv"
        out = redact(text, ("hunter2hunter2",))
        assert "AIza" not in out and "sk-abc" not in out
        assert redact("pw hunter2hunter2", ("hunter2hunter2",)) == "pw [REDACTED]"

    def test_gemini_requires_key(self, monkeypatch):
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        with pytest.raises(ProviderError, match="GEMINI_API_KEY"):
            GeminiProvider()

    def test_retries_are_bounded(self):
        calls = []

        class Flaky(StaticProvider):
            def complete(self, prompt):
                calls.append(1)
                raise ProviderError("rate limited")

        sleeps = []
        provider = RetryingProvider(Flaky(""), retries=2, backoff=1.0, sleep=sleeps.append)
        with pytest.raises(ProviderError):
            provider.complete("x")
        assert len(calls) == 3 and sleeps == [1.0, 2.0]

    def test_retry_recovers(self):
        state = {"n": 0}

        class Once(StaticProvider):
            def complete(self, prompt):
                state["n"] += 1
                if state["n"] == 1:
                    raise ProviderError("blip")
                return "ok"

        assert RetryingProvider(Once(""), sleep=lambda s: None).complete("x") == "ok"


class TestOpenAICompatibleWiring:
    """Exercise OpenAICompatibleProvider against a fake SDK (no network or SDK needed)."""

    def _install_fake(self, monkeypatch, behavior):
        import sys
        import types

        calls = {}

        class Completions:
            def create(self, model, messages):
                calls["model"], calls["messages"] = model, messages
                return behavior()

        class OpenAI:
            def __init__(self, **kwargs):
                calls.update(kwargs)
                self.chat = types.SimpleNamespace(
                    completions=Completions()
                )

        sdk = types.ModuleType("openai")
        sdk.OpenAI = OpenAI
        monkeypatch.setitem(sys.modules, "openai", sdk)
        return calls

    def test_success_uses_configured_endpoint_model_and_timeout(self, monkeypatch):
        response = types_ns(
            choices=[types_ns(message=types_ns(content="PLAN"))]
        )
        calls = self._install_fake(monkeypatch, lambda: response)
        provider = OpenAICompatibleProvider(
            api_key="k", model="configured-model", base_url="https://llm.example/v1", timeout=7
        )
        assert provider.complete("hello") == "PLAN"
        assert calls == {
            "api_key": "k",
            "base_url": "https://llm.example/v1",
            "timeout": 7,
            "max_retries": 0,
            "model": "configured-model",
            "messages": [{"role": "user", "content": "hello"}],
        }

    def test_reads_configuration_from_environment(self, monkeypatch):
        from phantom.generator.provider import get_provider

        monkeypatch.setenv("OPENAI_API_KEY", "secret")
        monkeypatch.setenv("PHANTOM_OPENAI_MODEL", "endpoint-model")
        monkeypatch.setenv("PHANTOM_OPENAI_BASE_URL", "https://llm.example/v1")
        provider = get_provider("openai")
        assert isinstance(provider, OpenAICompatibleProvider)
        assert provider.api_key == "secret"
        assert provider.model == "endpoint-model"
        assert provider.base_url == "https://llm.example/v1"

    def test_requires_key_and_model(self, monkeypatch):
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        monkeypatch.delenv("PHANTOM_OPENAI_MODEL", raising=False)
        with pytest.raises(ProviderError, match="OPENAI_API_KEY"):
            OpenAICompatibleProvider()
        monkeypatch.setenv("OPENAI_API_KEY", "k")
        with pytest.raises(ProviderError, match="PHANTOM_OPENAI_MODEL"):
            OpenAICompatibleProvider()

    def test_failure_is_redacted(self, monkeypatch):
        def boom():
            raise RuntimeError("401 for key secret-key-123456")

        self._install_fake(monkeypatch, boom)
        with pytest.raises(ProviderError) as info:
            OpenAICompatibleProvider(
                api_key="secret-key-123456", model="configured-model"
            ).complete("x")
        assert "secret-key-123456" not in str(info.value)
        assert info.value.__cause__ is None

    def test_empty_choices_return_empty_text(self, monkeypatch):
        self._install_fake(monkeypatch, lambda: types_ns(choices=[]))
        provider = OpenAICompatibleProvider(api_key="k", model="configured-model")
        assert provider.complete("hello") == ""

    def test_missing_sdk_message(self, monkeypatch):
        import sys

        monkeypatch.setitem(sys.modules, "openai", None)
        with pytest.raises(ProviderError, match="openai is not installed"):
            OpenAICompatibleProvider(api_key="k", model="configured-model").complete("x")


class TestDiff:
    def test_host_layer_diff_ignores_phantom_lines(self):
        cand = '#: phantom:0.1.0 meta.author("A")\n' + PROGRAM
        assert host_layer_diff(PROGRAM, cand) == ""
        assert unified_diff(PROGRAM, cand) != ""

    def test_host_layer_diff_detects_host_change(self):
        assert host_layer_diff(PROGRAM, PROGRAM.replace("hi ", "yo ")) != ""

    def test_encoding_mode_default(self):
        assert _request().encoding == EncodingMode.COMMENT


class TestGeminiWiring:
    """Exercise GeminiProvider against a fake `google.genai` (no network, no SDK needed)."""

    def _install_fake(self, monkeypatch, behavior):
        import sys
        import types

        calls = {}

        class HttpOptions:
            def __init__(self, timeout=None):
                calls["timeout"] = timeout

        class Models:
            def generate_content(self, model, contents):
                calls["model"], calls["contents"] = model, contents
                return behavior()

        class Client:
            def __init__(self, api_key=None, http_options=None):
                calls["api_key"] = api_key
                self.models = Models()

        genai = types.ModuleType("google.genai")
        genai.Client = Client
        genai.types = types.SimpleNamespace(HttpOptions=HttpOptions)
        google = types.ModuleType("google")
        google.genai = genai
        monkeypatch.setitem(sys.modules, "google", google)
        monkeypatch.setitem(sys.modules, "google.genai", genai)
        monkeypatch.setitem(sys.modules, "google.genai.types", genai.types)
        return calls

    def test_success_and_request_shape(self, monkeypatch):
        calls = self._install_fake(monkeypatch, lambda: types_ns(text="PLAN"))
        provider = GeminiProvider(api_key="k", model="m", timeout=7)
        assert provider.complete("hello") == "PLAN"
        assert calls == {"timeout": 7000, "api_key": "k", "model": "m", "contents": "hello"}

    def test_failure_is_redacted(self, monkeypatch):
        def boom():
            raise RuntimeError("401 for key secret-key-123456")

        self._install_fake(monkeypatch, boom)
        with pytest.raises(ProviderError) as info:
            GeminiProvider(api_key="secret-key-123456").complete("x")
        assert "secret-key-123456" not in str(info.value)
        assert info.value.__cause__ is None

    def test_missing_sdk_message(self, monkeypatch):
        import sys

        monkeypatch.setitem(sys.modules, "google", None)
        with pytest.raises(ProviderError, match="google-genai is not installed"):
            GeminiProvider(api_key="k").complete("x")


def types_ns(**kw):
    import types

    return types.SimpleNamespace(**kw)


class TestStalePatches:
    def test_anchor_matches(self):
        plan = parse_plan(_plan(("meta.author", "A")))
        plan.instructions[0].placement_line = 4
        plan.instructions[0].anchor = "def greet(name):"
        assert "def greet(name):" in apply_plan(PROGRAM, plan)

    def test_anchor_mismatch_is_rejected(self):
        plan = parse_plan(_plan(("meta.author", "A")))
        plan.instructions[0].placement_line = 4
        plan.instructions[0].anchor = "def something_else():"
        with pytest.raises(TransformError, match="Stale or mismatched"):
            apply_plan(PROGRAM, plan)

    def test_anchor_from_model_response_is_enforced_by_workflow(self):
        data = json.loads(_plan(("meta.author", "A")))
        data["instructions"][0]["anchor"] = "def not_here():"
        res = generate(_request(placement="near:greet"), StaticProvider(json.dumps(data)))
        assert not res.success and "Stale or mismatched" in res.errors[0]

    def test_result_records_source_digest(self):
        from phantom.generator.workflow import source_digest

        res = generate(_request(), StaticProvider(_plan(("meta.author", "A"))))
        assert res.source_sha256 == source_digest(PROGRAM)

    def test_cli_refuses_when_input_changes_during_generation(self, tmp_path, capsys):
        from phantom.cli import cmd_generate, create_parser

        path = tmp_path / "p.py"
        path.write_text("print(1)\n")
        out = tmp_path / "c.py"

        def mutate(prompt):
            path.write_text("print(2)\n")  # the file changes while the model is "thinking"
            return _plan(("meta.author", "A"))

        args = create_parser().parse_args(
            ["generate", str(path), "--intent", "x", "--output", str(out)]
        )
        assert cmd_generate(args, StaticProvider(mutate)) == 2
        assert not out.exists()
        assert "stale candidate" in capsys.readouterr().err
