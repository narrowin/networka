Secure dev container

- Read-only workspace bind at /workspace
- Non-root user (vscode)
- All Linux capabilities dropped, no-new-privileges
- Persistent volumes:
  - networker-venv -> /opt/venv
  - networker-cache -> /home/vscode/.cache
  - networker-data -> /workdata (results, test_results, .env)

Common tasks

- Seed .env: Run task "Seed Environment"
- Install deps: Run task "Install Dependencies"
- Run tests: Run task "Run Tests"
- Export outputs back to host: Run task "Export Outputs" (optional)

Jupyter

- A kernel "Python (net-worker)" is created bound to /opt/venv.
