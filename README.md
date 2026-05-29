# ArgoCdApp

Sample **Python FastAPI** service packaged for **Kubernetes**, deployed with **Argo CD** (GitOps), and built via **GitHub Actions**.

## Stack

| Layer | Technology |
|-------|------------|
| App | FastAPI + Uvicorn |
| Container | Docker (multi-stage) |
| Orchestration | Kubernetes (Kustomize) |
| GitOps | Argo CD |
| CI/CD | GitHub Actions → GHCR |

## Project layout

```
app/                 # FastAPI application
tests/               # Pytest suite
k8s/base/            # Kustomize manifests (Argo CD source path)
argocd/              # Argo CD Application CR
.github/workflows/   # CI and CD pipelines
Dockerfile
```

## Local development

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -r requirements-dev.txt
uvicorn app.main:app --reload --port 8000
```

Endpoints:

- `GET /` — welcome message
- `GET /health` — liveness
- `GET /ready` — readiness
- `GET /docs` — OpenAPI UI

```bash
pytest
```

## Docker

```bash
docker build -t argocd-app:local .
docker run --rm -p 8000:8000 argocd-app:local
```

## GitHub setup

1. Push this repo to GitHub.
2. In **Settings → Actions → General**, allow workflows to write to the repository (required for CD to update `k8s/base/kustomization.yaml`).
3. After the first `main` push, the **CD** workflow builds the image to `ghcr.io/<owner>/<repo>` and commits the new image digest/tag to Git.

## Deploy on EC2 with Kind

If Kubernetes is **Kind on an EC2 instance**, use the Kind overlay and port mapping:

1. Create cluster: `kind create cluster --config kind/cluster-config.yaml`
2. Install Argo CD and apply `argocd/application-kind.yaml` (path: `k8s/overlays/kind`)
3. Open EC2 security group port **30080**; access app at `http://<EC2_IP>:30080`

Full step-by-step guide: **[docs/deploy-ec2-kind.md](docs/deploy-ec2-kind.md)**

## Argo CD setup

1. Install [Argo CD](https://argo-cd.readthedocs.io/) on your cluster.
2. Edit `argocd/application.yaml`:
   - Set `spec.source.repoURL` to your GitHub repo URL.
   - Confirm `spec.source.path` is `k8s/base`.
3. If the cluster is private, configure a repository credential in Argo CD.
4. For **GHCR**, create an image pull secret in namespace `argocd-app` and reference it in the Deployment if the package is private:

   ```bash
   kubectl create namespace argocd-app
   kubectl create secret docker-registry ghcr-credentials \
     --docker-server=ghcr.io \
     --docker-username=<github-user> \
     --docker-password=<pat> \
     -n argocd-app
   ```

   Then add `imagePullSecrets: [{ name: ghcr-credentials }]` to the pod spec in `k8s/base/deployment.yaml`.

5. Apply the Application:

   ```bash
   # Cloud / generic cluster
   kubectl apply -f argocd/application.yaml

   # Kind on EC2 (NodePort 30080)
   kubectl apply -f argocd/application-kind.yaml
   ```

Argo CD will sync manifests to namespace `argocd-app` with automated sync and self-heal.

## Workflows

| Workflow | Trigger | Purpose |
|----------|---------|---------|
| `ci.yml` | Push/PR to `main` | Run tests; validate Kustomize build |
| `cd.yml` | Push to `main` | Test, build/push image to GHCR, update GitOps manifests |

## Verify in the cluster

```bash
kubectl get pods -n argocd-app
kubectl port-forward svc/argocd-app 8080:80 -n argocd-app
curl http://localhost:8080/health
```

## ImagePullBackOff on EC2 / Kind

GHCR images from GitHub Actions are **private** by default. Either:

- Make the package **public**: [GitHub Packages](https://github.com/shuvojithalder?tab=packages) → **argocdapp** → Change visibility, **or**
- Create pull secret on the cluster: **[docs/fix-imagepullbackoff.md](docs/fix-imagepullbackoff.md)**

## Customize

- Change `replicas`, resources, or probes in `k8s/base/deployment.yaml`.
- Point `k8s/base/kustomization.yaml` `images[].newName` at your registry path before the first CD run, or let CD overwrite it on each deploy.
