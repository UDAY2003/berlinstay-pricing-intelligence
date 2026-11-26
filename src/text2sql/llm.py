"""Provider-agnostic LLM client (stdlib only). Configure with environment variables or Streamlit secrets:

  LLM_PROVIDER  anthropic | openai | none          (openai = any OpenAI-compatible /chat/completions endpoint)
  LLM_API_KEY   the key (also accepted: ANTHROPIC_API_KEY / OPENAI_API_KEY)
  LLM_MODEL     model id of your provider (required; no default is built in)
  LLM_BASE_URL  optional endpoint override (default: provider's public API)
  LLM_TIMEOUT   seconds (default 30)
The key is read at runtime and never logged, printed or stored.
"""
import json
import os
import urllib.error
import urllib.request


class ProviderError(Exception):
    """LLM call failed; message is safe to show (never contains the key)."""


class _Base:
    def __init__(self, key, model, base_url, timeout):
        self._key, self.model, self.base_url, self.timeout = key, model, base_url, timeout

    def _post(self, url, headers, payload):
        req = urllib.request.Request(url, data=json.dumps(payload).encode(), headers={"content-type": "application/json", **headers})
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            detail = ""
            try:                                   # providers return {"error": {"type"/"code": ...}}; never contains our key
                err = json.loads(e.read()).get("error", {})
                err = err if isinstance(err, dict) else {}
                detail = " (" + ", ".join(str(err[k]) for k in ("type", "code") if err.get(k)) + ")" if (err.get("type") or err.get("code")) else ""
            except Exception:
                pass
            raise ProviderError(f"LLM provider returned HTTP {e.code}{detail}.")
        except Exception as e:
            raise ProviderError(f"LLM provider unreachable ({type(e).__name__}).")


class AnthropicProvider(_Base):
    name = "anthropic"

    def complete(self, system: str, user: str, max_tokens: int = 700) -> str:
        r = self._post(f"{self.base_url.rstrip('/')}/v1/messages", {"x-api-key": self._key, "anthropic-version": "2023-06-01"},
                       {"model": self.model, "max_tokens": max_tokens, "temperature": 0, "system": system,
                        "messages": [{"role": "user", "content": user}]})
        try:
            return "".join(b.get("text", "") for b in r["content"])
        except Exception:
            raise ProviderError("Unexpected response format from provider.")


class OpenAICompatProvider(_Base):
    name = "openai"

    def complete(self, system: str, user: str, max_tokens: int = 700) -> str:
        r = self._post(f"{self.base_url.rstrip('/')}/chat/completions", {"authorization": f"Bearer {self._key}"},
                       {"model": self.model, "max_tokens": max_tokens, "temperature": 0,
                        "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]})
        try:
            return r["choices"][0]["message"]["content"]
        except Exception:
            raise ProviderError("Unexpected response format from provider.")


def _model(get) -> str:
    m = get("LLM_MODEL")
    if not m:
        raise ProviderError("LLM_MODEL is not set. Set it to the model id offered by your provider.")
    return m


def get_provider(secrets=None, env=None):
    """Return a provider or None (= demo mode). `secrets` may be Streamlit's st.secrets (mapping) or None."""
    env = os.environ if env is None else env
    get = lambda k, d=None: (secrets.get(k) if secrets is not None and k in secrets else None) or env.get(k) or d
    kind = (get("LLM_PROVIDER") or "").lower()
    if kind in ("", "none"):
        return None
    timeout = float(get("LLM_TIMEOUT", 30))
    if kind == "anthropic":
        key = get("LLM_API_KEY") or get("ANTHROPIC_API_KEY")
        return AnthropicProvider(key, _model(get), get("LLM_BASE_URL", "https://api.anthropic.com"), timeout) if key else None
    if kind == "openai":
        key = get("LLM_API_KEY") or get("OPENAI_API_KEY")
        return OpenAICompatProvider(key, _model(get), get("LLM_BASE_URL", "https://api.openai.com/v1"), timeout) if key else None
    raise ProviderError(f"Unknown LLM_PROVIDER '{kind}' (use anthropic, openai or none).")
