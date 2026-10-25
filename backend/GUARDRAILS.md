# RAG safety guardrails

Every RAG question is checked before retrieval and every generated answer is
checked before it is saved or streamed.

The implementation combines NVIDIA NeMo Guardrails with:

- **NemoGuard JailbreakDetect** on input, to block prompt injection and jailbreak attempts.
- **Nemotron Content Safety** on input and output, to block harmful content.
- A small local fallback policy for direct jailbreak and dangerous operational requests. It remains active if the NVIDIA service is unavailable.

## Enable NVIDIA checks

1. Install the backend requirements.
2. Create an NVIDIA API key at [build.nvidia.com](https://build.nvidia.com/).
3. Add `NVIDIA_API_KEY` to `backend/.env` and keep `NEMO_GUARDRAILS_ENABLED=true`.

The shipped NeMo configuration is in `app/guardrails`. Set
`NEMO_GUARDRAILS_CONFIG_PATH` only when deploying a customized configuration.

For a local NIM deployment, update the NIM URLs in `app/guardrails/config.yml`
to point to your service instead of `https://ai.api.nvidia.com`.
