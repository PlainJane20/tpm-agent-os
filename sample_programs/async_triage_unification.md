# Program Brief: Unified Async Triage

Leadership wants members to be able to start an async visit from either the
mobile app or the clinician web console and have triage state follow them
across both -- symptom intake, risk score, and escalation status should be
identical no matter which surface they're on. Target is "sometime in Q4."

What we know:
- Mobile team owns the existing symptom-intake flow.
- Clinician-console team owns an escalation queue that assumes intake always
  happens on mobile -- there's no contract for web-originated intake today.
- A third team (Risk Scoring) maintains the model that assigns triage
  urgency; two other teams have started calling it directly instead of
  through the shared service, for reasons nobody has fully explained.
- Compliance flagged in a hallway conversation that "symptom + risk score"
  data crossing from the consumer app into the clinician console needs a
  clear PHI handling boundary, but no one has written that down yet.
- No single team currently believes they own the end-to-end triage state
  machine. Each team believes another team owns the parts they don't.

Ask: turn this into something a program review board can act on, and tell us
whether this is a build (a real shared triage-state service) or a buy/borrow
(lean on the existing escalation queue and patch the gaps) -- and whether it's
even the right thing to be spending Q4 on given everything else in flight.
