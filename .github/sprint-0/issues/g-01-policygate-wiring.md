# G-01 PolicyGate Wiring

## What & Why
The `PolicyGate` component is implemented but not yet integrated into our agent execution flow. We need to wire it into the `BaseAgent.send()` method to ensure all outgoing messages pass through content moderation, PII detection, and rate limiting checks.

This is a critical security and compliance feature that will prevent agents from sending inappropriate content, leaking sensitive information, or exceeding usage limits.

## Acceptance Criteria
- [ ] Hook `PolicyGate.enforce()` method into `BaseAgent.send()` method
- [ ] Add a simple "banned words" test that blocks messages containing specific strings
- [ ] Return binary success/failure (✓/✗) from the enforcement process
- [ ] Log all policy violations with appropriate severity levels
- [ ] Implement graceful handling when content is blocked (return explanation to caller)
- [ ] Add integration test that verifies:
  - [ ] Clean messages pass through
  - [ ] Messages with banned content are blocked
  - [ ] PII is properly redacted
  - [ ] Rate limits are enforced

## Implementation Notes
- The `PolicyGate` class is already implemented in `shared/guardrails/policy_gate.py`
- The check should be applied before the message is sent through any external channel
- Consider creating a `shared/guardrails/banned_words.py` file for the banned words list
- Ensure the integration doesn't significantly impact message latency
- Metrics should be emitted for blocked content (for monitoring)

## Example Integration
```python
from shared.guardrails.policy_gate import PolicyGate

# Initialize the gate
policy_gate = PolicyGate()

async def send(self, message, recipient, **kwargs):
    # Check message against policies
    enforcement_result = await policy_gate.enforce(
        content=message,
        metadata={
            "client_id": self.client_id,
            "direction": "outbound",
            "recipient": recipient
        }
    )
    
    # Check if allowed
    if enforcement_result["allowed"]:
        # Use filtered content (may have PII redacted)
        filtered_message = enforcement_result["filtered_content"]
        # Proceed with sending the filtered message
        return True, "Message sent"
    else:
        # Message was blocked by policy
        return False, enforcement_result["reasons"]
```

## Related Files
- Target integration point: `agents/base/sales_agent_base.py`
- PolicyGate implementation: `shared/guardrails/policy_gate.py`
- New file for banned words: `shared/guardrails/banned_words.py`
- Test file: `tests/policy_gate_integration_test.py`
