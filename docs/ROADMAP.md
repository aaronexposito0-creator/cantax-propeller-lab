# Roadmap

Version 1.0 demonstrates application integration and reproducible preliminary calculations. The following items are planned work, not delivered functionality or commitments to a release date.

## Physical model validation

1. Define an actual vessel, wake field and operating envelope, with permission to distribute any experimental data.
2. Add section polars with documented provenance, Reynolds range and transition/separation behavior.
3. Compare against open-water measurements and distinguish calibration cases from independent validation cases.
4. Quantify the effect of CAD trimming, skew and rake on the gap between nominal BEM geometry and real blade surface.
5. Develop a separately verified CFD workflow and establish mesh/time-step independence before claiming 3D validation.
6. Address cavitation, ventilation, hull interaction and scale effects with appropriate evidence.

## Structural credibility

Define the real hub and shaft connection, fillets, trailing-edge manufacturing requirements and material condition. Compare element order and refine displacement/stress solutions to convergence. Replace equivalent resultants with justified surface loading where needed. Introduce certified allowables and fatigue/corrosion/service criteria only when the necessary data are available. Apply those analyses to candidate designs before incorporating structural constraints in selection.

## Controls and system design

Replace the startup surrogate with a model valid across starting, windmilling and reverse-torque regimes. Characterize motor, controller, gearbox and shaft parameters. Verify torque/power availability across the envelope instead of treating the present 25 N·m scenario as a selected hardware system.

## Software and integration

- Extend portable path discovery and regression tests on clean Windows installations with licensed engines.
- Remove environment-specific authoring dependencies with a separately verified, permissibly licensed backend.
- Add explicit compatibility checks when application or output-format versions change.
- Review optional Inventor, ParaView and DWSIM connectors individually; none is represented as working in V1.0.
- Package distribution dependencies only after license and security review.
- Improve reproducible comparison, error handling and report QA for new operating points.

## Release criteria

Any claim stronger than preliminary numerical consistency should identify the supporting dataset, acceptance criteria and independent review. A commercial product would additionally require packaging, licensing, support, security maintenance and a defined intended use. The current release does not imply that these requirements have been met.
