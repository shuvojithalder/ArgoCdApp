# Deploy on EC2 with Kind

Use this guide when **Kind** runs on an **EC2** instance (Docker-in-Docker Kubernetes). Argo CD runs inside the same cluster and syncs this repo.

## Architecture

```
GitHub (manifests + GHCR image)
        │
        ▼
   Argo CD (namespace: argocd)  ──sync──►  App (namespace: argocd-app)
        │
        ▼
   Kind cluster on EC2  ──NodePort 30080──►  EC2 public IP
```

## 1. EC2 prerequisites

| Item | Notes |
|------|--------|
| OS | Amazon Linux 2023 or Ubuntu 22.04+ |
| Instance | `t3.medium` or larger recommended |
| Software | Docker, `kubectl`, `kind` |
| Security group | Inbound **22** (SSH), **30080** (app), **30443** or **8080** (Argo CD UI if exposed) |

Install tools (Amazon Linux example):

```bash
sudo yum update -y
sudo yum install -y docker git
sudo systemctl enable --now docker
sudo usermod -aG docker $USER
# log out and back in so docker group applies

curl -Lo ./kind https://kind.sigs.k8s.io/dl/v0.27.0/kind-linux-amd64
chmod +x ./kind && sudo mv ./kind /usr/local/bin/kind

curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
chmod +x kubectl && sudo mv kubectl /usr/local/bin/
```

## 2. Create Kind cluster (with app port mapping)

Clone the repo on EC2, then:

```bash
cd ArgoCdApp
kind create cluster --config kind/cluster-config.yaml
kubectl cluster-info --context kind-argocd
```

`kind/cluster-config.yaml` maps **host port 30080** → Service **NodePort 30080** (used by `k8s/overlays/kind`).

## 3. Install Argo CD

```bash
kubectl create namespace argocd
kubectl apply -n argocd --server-side -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml

kubectl wait --for=condition=available deployment/argocd-server -n argocd --timeout=300s

# Initial admin password
kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath="{.data.password}" | base64 -d && echo
```

Access UI from your laptop (SSH tunnel):

```bash
ssh -i your-key.pem ec2-user@<EC2_PUBLIC_IP> -L 8080:127.0.0.1:8080
# on EC2:
kubectl port-forward svc/argocd-server -n argocd 8080:443
```

Open https://localhost:8080 (user: `admin`, password from above).

## 4. Connect GitHub repo to Argo CD

1. Push `ArgoCdApp` to GitHub and run the **CD** workflow once (image on GHCR).
2. In Argo CD UI: **Settings → Repositories → Connect repo** (HTTPS + PAT if private).
3. On EC2, edit manifest and apply:

```bash
# Set your real repo URL
sed -i 's|https://github.com/OWNER/ArgoCdApp.git|https://github.com/YOUR_USER/ArgoCdApp.git|' argocd/application-kind.yaml
kubectl apply -f argocd/application-kind.yaml
```

Or use CLI:

```bash
argocd app create argocd-app \
  --repo https://github.com/YOUR_USER/ArgoCdApp.git \
  --path k8s/overlays/kind \
  --dest-server https://kubernetes.default.svc \
  --dest-namespace argocd-app \
  --sync-policy automated --auto-prune --self-heal
```

## 5. Pull images from GHCR

**Public package:** no extra steps.

**Private package** — on EC2:

```bash
kubectl create secret docker-registry ghcr-credentials \
  --docker-server=ghcr.io \
  --docker-username=YOUR_GITHUB_USER \
  --docker-password=YOUR_GITHUB_PAT \
  -n argocd-app \
  --dry-run=client -o yaml | kubectl apply -f -
```

Add to `k8s/base/deployment.yaml` under `spec.template.spec`:

```yaml
imagePullSecrets:
  - name: ghcr-credentials
```

Commit and let Argo CD sync.

## 6. Verify deployment

```bash
kubectl get applications -n argocd
kubectl get pods -n argocd-app
curl http://<EC2_PUBLIC_IP>:30080/health
curl http://<EC2_PUBLIC_IP>:30080/
```

## 7. Optional: load image without GHCR (local test)

Build on EC2 and load into Kind (bypasses registry):

```bash
docker build -t argocd-app:local .
kind load docker-image argocd-app:local --name argocd

cd k8s/base
kustomize edit set image argocd-app=argocd-app:local
kubectl apply -k ../overlays/kind
```

Revert `kustomization.yaml` before using Argo CD + GHCR again.

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `ImagePullBackOff` | Check GHCR visibility, `imagePullSecrets`, and `k8s/base/kustomization.yaml` image name/tag |
| Argo CD **OutOfSync** loop | Ensure CD workflow committed image tag; run `argocd app sync argocd-app` |
| Cannot reach app on :30080 | Open SG port 30080; confirm Kind created with `kind/cluster-config.yaml` |
| Argo CD cannot clone repo | Add repo credentials in Argo CD for private GitHub repos |

## Paths in this repo

| Path | Use on EC2 Kind |
|------|-----------------|
| `k8s/overlays/kind` | **Yes** — NodePort + 1 replica |
| `k8s/base` | Generic / cloud clusters |
| `argocd/application-kind.yaml` | Argo CD app for Kind overlay |
