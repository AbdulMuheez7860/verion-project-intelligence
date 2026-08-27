\# Verion



\### AI-Powered Software Repository Intelligence \& Evaluation Platform



Verion analyzes GitHub repositories and turns their source code, dependencies, security findings, code quality, and development activity into a single engineering intelligence dashboard.



It helps developers understand \*\*what is wrong, how risky the repository is, and what should be fixed first\*\*.



\---



\## ✨ Features



\- 🔗 \*\*GitHub Integration\*\* — Connect GitHub and analyze repositories.

\- 📊 \*\*Repository Intelligence\*\* — Health, security, quality, dependency, and risk scores.

\- 🔍 \*\*Code Analysis\*\* — Repository structure, LOC, language distribution, and code metrics.

\- 🛡️ \*\*Security Scanning\*\* — Semgrep, Bandit, and detect-secrets.

\- 📦 \*\*Dependency Analysis\*\* — Dependency inventory and vulnerability scanning where supported.

\- 🧹 \*\*Code Quality\*\* — Ruff and ESLint analysis.

\- 📈 \*\*Analysis History\*\* — Track repository health across multiple analyses.

\- 🔀 \*\*Pull Request Insights\*\* — Retrieve and analyze GitHub pull request information.

\- 📄 \*\*Reports\*\* — Generate PDF and JSON repository reports.

\- 🤖 \*\*AI Assistant\*\* — Ask evidence-based questions about repository findings.

\- ⚡ \*\*Asynchronous Analysis\*\* — Celery workers and Redis handle long-running analysis jobs.

\- 🔐 \*\*Security\*\* — OAuth state validation, encrypted GitHub tokens, JWT authentication, and environment-based secrets.



\---



\## 🏗️ Architecture



```text

&#x20;                   GitHub API

&#x20;                       │

&#x20;                       ▼

┌──────────────┐   ┌──────────────┐

│   React UI   │◄─►│   FastAPI    │

└──────────────┘   └──────┬───────┘

&#x20;                          │

&#x20;             ┌────────────┼────────────┐

&#x20;             │            │            │

&#x20;             ▼            ▼            ▼

&#x20;         MongoDB        Redis      GitHub API

&#x20;                          │

&#x20;                          ▼

&#x20;                       Celery

&#x20;                       Worker

&#x20;                          │

&#x20;                          ▼

&#x20;                  Analysis Engine

&#x20;                          │

&#x20;         ┌────────────────┼────────────────┐

&#x20;         ▼                ▼                ▼

&#x20;      Semgrep          Bandit       detect-secrets

&#x20;         │                │                │

&#x20;         └────────────────┼────────────────┘

&#x20;                          ▼

&#x20;                 Analysis Results

&#x20;                          │

&#x20;             ┌────────────┼────────────┐

&#x20;             ▼            ▼            ▼

&#x20;         Dashboard      Reports    AI Assistant

