# /startcycle Workflow

When the user runs /startcycle [idea]:

1. @pm — Write a technical spec for [idea]. Save it to
   production_artifacts/spec.md. Wait for user approval.

2. @engineer — Read production_artifacts/spec.md. Build the app in app_build/.
   Follow GEMINI.md rules. Save a build summary to
   production_artifacts/build_log.md.

3. @qa — Review app_build/ against the spec. Fix issues.
   Save a QA report to production_artifacts/qa_report.md.

4. @docs — Write a README.md in app_build/ based on the final code.

Report to the user when the cycle is complete with a summary and next steps.