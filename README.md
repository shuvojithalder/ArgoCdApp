# ArgoCdApp

Simple **FastAPI** app deployed to **Kind on EC2** with **Argo CD**.

## Flow

```
Push to main → GitHub Actions builds image → ghcr.io → Argo CD syncs k8s/ → Kind
```

## Project layout

```
app/                    Python API
k8s/                    Plain Kubernetes YAML (no Kustomize)
argocd/application.yaml Argo CD app (path: k8s)
.github/workflows/      CI tests + CD build/push
```

## Local run

```bash
pip install -r requirements-dev.txt
uvicorn app.main:app --reload --port 9000
pytest
```

## Deploy on EC2 (Kind + Argo CD already installed)

### 1. Push code to GitHub

Wait for **Actions → CD** to finish (builds image, makes GHCR package public).

### 2. Apply Argo CD application (once)

```bash
kubectl apply -f argocd/application.yaml
```

### 3. Open port 30080 on EC2 security group

### 4. Test

```bash
kubectl get pods -n argocd-app
curl http://<EC2_PUBLIC_IP>:30080/health
```

## Kind port mapping (first-time cluster setup)

If NodePort 30080 is not reachable, create Kind with:

```bash
kind create cluster --config kind/cluster-config.yaml
```

## Image location

```text
ghcr.io/shuvojithalder/argocdapp:latest
```

CD workflow builds, pushes, and updates `k8s/deployment.yaml` automatically.

## Troubleshooting ImagePullBackOff

1. Confirm CD workflow succeeded on GitHub Actions.
2. Make package public: GitHub → **Packages** → **argocdapp** → **Public**.
3. Restart pods: `kubectl delete pods -n argocd-app --all`

## Argo CD UI

```bash
kubectl port-forward svc/argocd-server -n argocd 8080:443
```

Open https://localhost:8080 (user: `admin`).
