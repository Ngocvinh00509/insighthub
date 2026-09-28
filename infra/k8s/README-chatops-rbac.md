# ChatOps Kubernetes RBAC verification

`chatops-rbac.yaml` is a namespace-scoped identity for Day 5 read-only MCP
operations. It intentionally does not grant `create`, `update`, `patch`,
`delete`, `exec`, `pods/log`, Secret access, or any cluster-scoped permission.
No mutation ServiceAccount is supplied: Day 5 has no approved mutation executor.
If a later task introduces one, it must use a separate identity and a narrowly
scoped Role; it must not reuse `insighthub-chatops-readonly`.

Apply only to the disposable target namespace, then verify as the ServiceAccount:

```powershell
$namespace = "insighthub-dev"
$identity = "system:serviceaccount:$namespace:insighthub-chatops-readonly"
kubectl apply -f infra/k8s/chatops-rbac.yaml

kubectl auth can-i get pods --as=$identity -n $namespace
kubectl auth can-i list pods --as=$identity -n $namespace
kubectl auth can-i watch pods --as=$identity -n $namespace
kubectl auth can-i get deployments.apps --as=$identity -n $namespace
kubectl auth can-i list events --as=$identity -n $namespace

kubectl auth can-i delete pods --as=$identity -n $namespace
kubectl auth can-i create pods --as=$identity -n $namespace
kubectl auth can-i get secrets --as=$identity -n $namespace
kubectl auth can-i create deployments.apps --as=$identity -n $namespace
kubectl auth can-i get nodes --as=$identity
```

Expected results: the first five read checks return `yes`; every dangerous or
cluster-scoped check returns `no`. Save the actual command output in Day 5
evidence; source review alone is not runtime verification.
