# ArgoCdApp

Sample **Python FastAPI** app deployed to **Kind on EC2** using **Argo CD** (GitOps) and **GitHub Actions**.

## Stack

| Layer | Technology |
|-------|------------|
| App | FastAPI + Uvicorn (port **9000**) |
| Container | Docker → **GHCR** |
| Cluster | Kind on EC2 |
| GitOps | Argo CD |
| CI/CD | GitHub Actions |

## How it works

```
Push to main → CD workflow builds image → ghcr.io/shuvojithalder/argocdapp:latest
            → updates k8s/deployment.yaml → Argo CD syncs → Kind runs the app
```

## Project layout

```
app/                    FastAPI application
k8s/                    Kubernetes manifests (namespace, deployment, service)
argocd/application.yaml Argo CD Application (watches path: k8s)
kind/cluster-config.yaml  Kind cluster config (maps NodePort to EC2)
.github/workflows/      ci.yml (tests) + cd.yml (build, push, deploy)
Dockerfile
```

## Ports

| Where | Port | Purpose |
|-------|------|---------|
| App (container) | **9000** | Uvicorn listens here |
| Service (cluster) | **80** → 9000 | Internal cluster access |
| NodePort (EC2) | **30090** | Browser access from outside |

Open in browser:

```text
http://<EC2_PUBLIC_IP>:30090/
http://<EC2_PUBLIC_IP>:30090/docs
http://<EC2_PUBLIC_IP>:30090/health
```

Port-forward is **not required** if NodePort **30090** is open in the EC2 security group.

## Local development

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -r requirements-dev.txt
uvicorn app.main:app --reload --port 9000
pytest
```

Local URLs:

- http://localhost:9000/
- http://localhost:9000/docs
- http://localhost:9000/health

## Docker (local test)

```bash
docker build -t argocd-app:local .
docker run --rm -p 9000:9000 argocd-app:local
```

## GitHub setup

1. Push this repo to https://github.com/shuvojithalder/ArgoCdApp
2. **Settings → Actions → General** → allow workflows to read and write (for CD manifest updates)
3. Push to `main` and wait for **Actions → CD** to complete

Image published to:

```text
ghcr.io/shuvojithalder/argocdapp:latest
```

## Deploy on EC2 (Kind + Argo CD already installed)

### 1. Create Kind cluster (first time only)

```bash
kind create cluster --config kind/cluster-config.yaml
```

This maps NodePort **30090** on the Kind node to the EC2 host.

### 2. Install Argo CD (first time only)

```bash
kubectl create namespace argocd
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml
```

### 3. Register the Argo CD application (once)

```bash
kubectl apply -f argocd/application.yaml
```

### 4. Open EC2 security group

Allow inbound **TCP 30090** (and **22** for SSH).

### 5. Verify

```bash
kubectl get application -n argocd
kubectl get pods -n argocd-app
curl http://localhost:30090/health
```

## GitHub Actions

| Workflow | Trigger | What it does |
|----------|---------|--------------|
| `ci.yml` | Push / PR to `main` | Runs pytest |
| `cd.yml` | Push to `main` | Tests, builds Docker image, pushes to GHCR, makes package public, updates `k8s/deployment.yaml` |

## Argo CD UI

On EC2:

```bash
kubectl port-forward svc/argocd-server -n argocd 8080:443
```

Open https://localhost:8080 (user: `admin`).

Get initial password:

```bash
kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath="{.data.password}" | base64 -d && echo
```

From your PC (SSH tunnel):

```bash
ssh -i your-key.pem ec2-user@<EC2_PUBLIC_IP> -L 8080:127.0.0.1:8080
```

## Optional: port-forward the app

Use this if NodePort is not reachable:

```bash
kubectl port-forward svc/argocd-app 9000:80 -n argocd-app
```

Then open http://localhost:9000/

## Troubleshooting

### ImagePullBackOff

1. Confirm **Actions → CD** succeeded on GitHub.
2. Make GHCR package public: GitHub → **Packages** → **argocdapp** → **Public**.
3. Restart pods:

   ```bash
   kubectl delete pods -n argocd-app --all
   ```

### App not reachable on :30090

1. Confirm Kind was created with `kind/cluster-config.yaml`.
2. Confirm EC2 security group allows **TCP 30090**.
3. Check pods: `kubectl get pods -n argocd-app`

### Argo CD not syncing

```bash
argocd app sync argocd-app --force
kubectl get application argocd-app -n argocd
```

## API endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | Welcome message |
| GET | `/health` | Liveness probe |
| GET | `/ready` | Readiness probe |
| GET | `/api/info` | App info |
| GET | `/docs` | Swagger UI |
