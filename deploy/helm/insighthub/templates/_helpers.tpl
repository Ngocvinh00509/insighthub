{{- define "insighthub.name" -}}insighthub{{- end -}}
{{- define "insighthub.labels" -}}app.kubernetes.io/name: {{ include "insighthub.name" . }}
app.kubernetes.io/part-of: insighthub
app.kubernetes.io/managed-by: Helm
app.kubernetes.io/environment: {{ .Values.global.environment }}{{- end -}}
