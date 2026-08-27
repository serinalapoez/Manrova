# AWS / Strands Provider

This is where the Agents for Humans (Strands Agents SDK) implementation
lives. It wraps the shared core in `core/`, `agents/`, and `oow/` -
it does not reimplement business logic.

## What's here

- `tools.py` - `@tool`-decorated functions wrapping each deterministic core
  agent, same responsibility split as `providers/google/adk/tools.py`.
- `agents.py` - four specialist Strands `Agent`s (one tool each), each
  wrapped as a `@tool` the Officer of the Watch can call ("agents as tools"
  pattern), plus `officer_of_the_watch`, the root orchestrating agent.
- `requirements-aws.txt` - `strands-agents` + `strands-agents-tools`.

## Run it locally

```bash
cd Manrova
pip install -r providers/aws/strands/requirements-aws.txt
```

By default Strands uses Amazon Bedrock with Claude as the model provider,
which needs AWS credentials configured (`aws configure`) with Bedrock model
access enabled in your region. If you'd rather not set up Bedrock access
for local testing, Strands also supports OpenAI, Gemini, Ollama, and
LiteLLM as drop-in model providers - see strandsagents.com/docs for the
one-line swap.

```bash
python providers/aws/strands/agents.py
```

This runs the MV Atlas smoke test scenario built into the bottom of
`agents.py` and prints the Officer of the Watch's full response.

## Plan

1. Wrap each specialist agent class (`agents/*/agent.py`) as a Strands Tool,
   keeping the deterministic `.analyze()` / `.assess()` methods as the tool
   function and adding a Strands `Agent` on top for the reasoning step.
2. Wrap `OfficerOfTheWatch` as the top-level Strands orchestrating agent.
3. Deploy via AWS AgentCore Runtime (optional but strengthens the
   Technological Implementation score per the judging criteria).
4. Swap `data/demo/fleet_data.py` for a real event source (e.g. an
   EventBridge rule or a simple ingestion Lambda) when moving past the demo.

## Status

- [x] Strands Agent wrapper for NavIntegrityAgent
- [x] Strands Agent wrapper for CrewReadinessAgent
- [x] Strands Agent wrapper for FleetPatternAgent
- [x] Strands Agent wrapper for ComplianceReadinessAgent
- [x] Strands orchestrating agent for Officer of the Watch (`officer_of_the_watch` in
      `agents.py`, using the "agents as tools" multi-agent pattern)
- [ ] Actually run this locally and confirm the model follows the
      "consult all four before fusing risk" instruction reliably
- [ ] AgentCore Runtime deployment (optional, strengthens Technical
      Implementation score per judging criteria)
- [ ] AWS Builder ID attached to submission
- [ ] Architecture diagram + demo video
