# Fix ImagePullBackOff (GHCR private package)

**Cause:** `ghcr.io/shuvojithalder/argocdapp` is **private** (GitHub returns `401` without login). Kind on EC2 cannot pull the image.

**Image name is correct** — you only need auth or a public package.

---

## Option A — Make package public (recommended, ~2 minutes)

1. Open https://github.com/users/shuvojithalder/packages/container/package/argocdapp  
   (or **Your profile → Packages → argocdapp**)
2. **Package settings** → **Change package visibility** → **Public**
3. On EC2:

   ```bash
   kubectl delete pods -n argocd-app --all
   kubectl get pods -n argocd-app -w
   ```

Pods should go to `Running`. No secrets required.

---

## Option B — Keep private: GitHub PAT + pull secret

### 1. Create a PAT

GitHub → **Settings** → **Developer settings** → **Personal access tokens** → **Tokens (classic)**

- Scope: **`read:packages`**
- Note the token (used once below)

### 2. Create secret on EC2

```bash
kubectl create namespace argocd-app --dry-run=client -o yaml | kubectl apply -f -

kubectl create secret docker-registry ghcr-credentials \
  --docker-server=ghcr.io \
  --docker-username=shuvojithalder \
  --docker-password=YOUR_GITHUB_PAT \
  -n argocd-app
```

### 3. Enable pull secret in manifests

Edit `k8s/overlays/kind/kustomization.yaml` — uncomment the ghcr patch line:

```yaml
patches:
  - path: service-nodeport.yaml
  - path: deployment-replicas.yaml
  - path: patches/ghcr-pull-secret.yaml   # uncomment this line
```

Commit, push, then:

```bash
argocd app sync argocd-app --force
```

**Quick test without Git commit:**

```bash
kubectl patch deployment argocd-app -n argocd-app --type=json -p='[
  {"op":"add","path":"/spec/template/spec/imagePullSecrets","value":[{"name":"ghcr-credentials"}]}
]'
kubectl rollout restart deployment/argocd-app -n argocd-app
```

### 4. Verify

```bash
kubectl describe pod -n argocd-app -l app.kubernetes.io/name=argocd-app | tail -20
kubectl get pods -n argocd-app
```

---

## Check image reference

```bash
kubectl get deploy argocd-app -n argocd-app -o jsonpath='{.spec.template.spec.containers[0].image}'; echo
```

Must be lowercase:

```text
ghcr.io/shuvojithalder/argocdapp:<tag>
```

---

## Test from EC2 with Docker

```bash
echo YOUR_GITHUB_PAT | docker login ghcr.io -u shuvojithalder --password-stdin
docker pull ghcr.io/shuvojithalder/argocdapp:latest
```

If this fails, fix PAT or package name before debugging Kubernetes again.
