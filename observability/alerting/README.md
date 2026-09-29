# Alertmanager → Slack

The webhook is read from Secret `insighthub-alertmanager-slack`, key
`webhook_url`, in namespace `monitoring`; no secret value is stored in Git.

Create the Secret from an ignored protected env file containing only
`webhook_url=...`:

```powershell
kubectl -n monitoring create secret generic insighthub-alertmanager-slack `
  --from-env-file=$env:INSIGHTHUB_SLACK_SECRET_ENV
```

Apply `test-alert.yaml` only in a disposable lab, capture firing/resolved Slack
messages, then delete it immediately.
