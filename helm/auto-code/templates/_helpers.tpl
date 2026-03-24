{{/*
Expand the name of the chart.
*/}}
{{- define "auto-code.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified app name.
*/}}
{{- define "auto-code.fullname" -}}
{{- if .Values.fullnameOverride }}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- $name := default .Chart.Name .Values.nameOverride }}
{{- if contains $name .Release.Name }}
{{- .Release.Name | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}
{{- end }}

{{/*
Create chart name and version as used by the chart label.
*/}}
{{- define "auto-code.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Common labels
*/}}
{{- define "auto-code.labels" -}}
helm.sh/chart: {{ include "auto-code.chart" . }}
{{ include "auto-code.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{/*
Selector labels
*/}}
{{- define "auto-code.selectorLabels" -}}
app.kubernetes.io/name: {{ include "auto-code.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/*
Backend labels
*/}}
{{- define "auto-code.backend.labels" -}}
{{ include "auto-code.labels" . }}
app: auto-claude
component: backend
tier: application
{{- end }}

{{/*
Backend selector labels
*/}}
{{- define "auto-code.backend.selectorLabels" -}}
{{ include "auto-code.selectorLabels" . }}
app: auto-claude
component: backend
{{- end }}

{{/*
Web backend labels
*/}}
{{- define "auto-code.webBackend.labels" -}}
{{ include "auto-code.labels" . }}
app: auto-claude
component: web-backend
tier: api
{{- end }}

{{/*
Web backend selector labels
*/}}
{{- define "auto-code.webBackend.selectorLabels" -}}
{{ include "auto-code.selectorLabels" . }}
app: auto-claude
component: web-backend
{{- end }}

{{/*
Web frontend labels
*/}}
{{- define "auto-code.webFrontend.labels" -}}
{{ include "auto-code.labels" . }}
app: auto-claude
component: web-frontend
tier: frontend
{{- end }}

{{/*
Web frontend selector labels
*/}}
{{- define "auto-code.webFrontend.selectorLabels" -}}
{{ include "auto-code.selectorLabels" . }}
app: auto-claude
component: web-frontend
{{- end }}

{{/*
Postgres labels
*/}}
{{- define "auto-code.postgres.labels" -}}
{{ include "auto-code.labels" . }}
app: auto-claude
component: postgres
tier: database
{{- end }}

{{/*
Postgres selector labels
*/}}
{{- define "auto-code.postgres.selectorLabels" -}}
{{ include "auto-code.selectorLabels" . }}
app: auto-claude
component: postgres
{{- end }}

{{/*
Redis labels
*/}}
{{- define "auto-code.redis.labels" -}}
{{ include "auto-code.labels" . }}
app: auto-claude
component: redis
tier: cache
{{- end }}

{{/*
Redis selector labels
*/}}
{{- define "auto-code.redis.selectorLabels" -}}
{{ include "auto-code.selectorLabels" . }}
app: auto-claude
component: redis
{{- end }}

{{/*
Create the name of the service account to use
*/}}
{{- define "auto-code.serviceAccountName" -}}
{{- if .Values.serviceAccount.create }}
{{- default (include "auto-code.fullname" .) .Values.serviceAccount.name }}
{{- else }}
{{- default "default" .Values.serviceAccount.name }}
{{- end }}
{{- end }}

{{/*
Namespace
*/}}
{{- define "auto-code.namespace" -}}
{{- default .Values.global.namespace .Release.Namespace }}
{{- end }}
