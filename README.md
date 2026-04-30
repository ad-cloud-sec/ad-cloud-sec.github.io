# AD · Cloud Security Research

Security research, detection engineering, and incident analysis from a practitioner with 10 years in cloud security.

## Writing

- [How to Stream Claude Compliance Logs into Microsoft Sentinel](https://ad-cloud-sec.github.io/posts/claude-compliance-sentinel.html) - No built-in Sentinel connector exists for Claude Enterprise. Full Logic App pipeline, permissive JSON schema that survives spec updates, and five KQL detection queries covering roles, API keys, org settings, and compliance API self-monitoring. Built from the API spec, Rev J.

- [Privileged Accounts and the Claude M365 Connector: Why "User-Scoped" Has Limits Anthropic Didn't Document](https://ad-cloud-sec.github.io/posts/privileged-accounts-claude-m365-connector.html) - Under Microsoft's intersection model, a SharePoint Admin authenticating the Claude connector gets access through administrative override paths covering the full tenant. Anthropic's Security Guide doesn't document this. Includes per-scope breakdown, audit trail degradation analysis, Sentinel KQL detection query, and five deployment controls.

- [Securing the Claude Enterprise M365 Connector: What the Permission Model Doesn't Tell You](https://ad-cloud-sec.github.io/posts/claude-m365-secure-integration-controls.html) - The connector is read-only and delegated. That framing is accurate and insufficient. Analysis of token persistence, OAuth consent attack surfaces, tenant-wide search scope, and the DM surface most security reviews never look at. Ten security controls derived from a live pre-deployment assessment.

- [Building an Insider Threat Detection Program for Employee Offboarding in Microsoft Sentinel](https://ad-cloud-sec.github.io/posts/insider-threat-detection-sentinel.html) - Dynamic watchlist, ten KQL analytics rules covering every exfiltration and persistence path, alert fusion, monitoring workbook, and RBAC isolation.

- [Two Look-Alike Domains. One Email Man-in-the-Middle.](https://ad-cloud-sec.github.io/posts/email-mitm-investigation.html) - A real-world BEC investigation: double domain impersonation, email MitM, and why every authentication check returned green.

## Focus Areas

- AI Security and LLM Risk
- Cloud Security Posture Management (CSPM / CNAPP)
- Detection Engineering and SIEM
- Identity and Access (CIEM, Entra ID, Zero Trust)
- Incident Response and Forensics
- Email Security
- Kubernetes Security
- AWS · Azure · GCP

## Intel Dashboard

Daily cybersecurity intelligence: CVEs, threat intel, cloud security, AI/LLM threats, curated and updated every morning at 09:00 IST.

[ad-cloud-sec.github.io/dashboard.html](https://ad-cloud-sec.github.io/dashboard.html)

## Site

[ad-cloud-sec.github.io](https://ad-cloud-sec.github.io)
