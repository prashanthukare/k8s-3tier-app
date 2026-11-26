# 3-Tier App on Kubernetes with Autoscaling and CI/CD

A simple 3-tier web application running on Kubernetes:

- **Frontend:** Nginx serving a web page
- **Backend:** Python Flask API that counts page visits
- **Database:** MySQL storing the visit count

The backend scales automatically from 2 to 6 pods based on CPU load (Horizontal
Pod Autoscaler), and a GitHub Actions workflow builds and pushes both Docker
images on every commit.

## Architecture

```text
                Browser
                   |
              [ Ingress ]          <- one entry point, routes by URL path
              |         |
        path: /    path: /api
              |         |
     [frontend svc]  [backend svc]  <- stable internal addresses
              |         |
        2 frontend    2-6 backend   <- HPA scales the backend pods
          pods          pods
                          |
                   [mysql-service]  <- headless service
                          |
                    1 MySQL pod     <- StatefulSet
                          |
                    PVC (1Gi)       <- data survives pod restarts
```

## What each piece does (in simple words)

| Piece | File | What it does |
|---|---|---|
| Namespace | `k8s/namespace.yaml` | A separate "room" in the cluster for this app, so its parts are grouped together. |
| Deployment | `k8s/frontend-deployment.yaml`, `k8s/backend-deployment.yaml` | Keeps a set number of identical pods running. If a pod dies, it is replaced. |
| Service | `k8s/frontend-service.yaml`, `k8s/backend-service.yaml` | A stable internal address for a group of pods, so other pods can reach them by name. |
| StatefulSet | `k8s/mysql-statefulset.yaml` | Like a Deployment, but for apps that keep data. The database pod gets a stable name and its own disk. |
| PVC | inside the StatefulSet | A piece of disk storage that belongs to the database. Data survives even if the pod is deleted and recreated. |
| Secret | `k8s/mysql-secret.yaml` | Stores passwords so they are not written into the app code or plain config files. |
| ConfigMap | `k8s/backend-configmap.yaml` | Stores normal (non-secret) settings, like the database host and name, in one place. |
| Probes | inside the Deployments | Health checks. Readiness: "is the pod ready for traffic?" Liveness: "is the pod still healthy, or should it be restarted?" |
| HPA | `k8s/backend-hpa.yaml` | Watches CPU usage and adds or removes backend pods automatically (2 minimum, 6 maximum). |
| Ingress | `k8s/ingress.yaml` | The single public entry point. Sends `/` to the frontend and `/api` to the backend. |
| GitHub Actions | `.github/workflows/build-and-push.yaml` | On every push to `main`: builds both Docker images and pushes them to Docker Hub. |

## Project structure

```text
k8s-3tier-app/
├── app/
│   ├── frontend/          # Nginx image: one static page
│   │   ├── Dockerfile
│   │   └── index.html
│   └── backend/           # Flask API image
│       ├── Dockerfile
│       ├── app.py
│       └── requirements.txt
├── k8s/                   # all Kubernetes manifests
│   ├── namespace.yaml
│   ├── mysql-secret.yaml
│   ├── mysql-statefulset.yaml
│   ├── mysql-service.yaml
│   ├── backend-configmap.yaml
│   ├── backend-deployment.yaml
│   ├── backend-service.yaml
│   ├── backend-hpa.yaml
│   ├── frontend-deployment.yaml
│   ├── frontend-service.yaml
│   └── ingress.yaml
└── .github/workflows/
    └── build-and-push.yaml
```

## Run it locally (minikube)

### One-time setup

1. Install [minikube](https://minikube.sigs.k8s.io/docs/start/) and kubectl.
2. Start the cluster and enable the add-ons this project needs:

```bash
minikube start
minikube addons enable ingress
minikube addons enable metrics-server   # needed by the HPA
```

### Get the Docker images

Pick ONE of these two options.

**Option A: let GitHub Actions build and push the images (recommended)**

1. On Docker Hub, create an access token: hub.docker.com -> Account Settings -> Security -> New Access Token.
2. In this repo on GitHub: Settings -> Secrets and variables -> Actions -> New repository secret. Add:
   - `DOCKER_USERNAME` = `prashanthukare`
   - `DOCKER_PASSWORD` = the Docker Hub access token
3. Push any commit (or run the workflow manually from the Actions tab).
   The images `prashanthukare/k8s-3tier-backend:latest` and
   `prashanthukare/k8s-3tier-frontend:latest` appear on Docker Hub.
   Kubernetes will pull them from there.

**Option B: build the images inside minikube yourself**

```bash
eval $(minikube docker-env)
docker build -t prashanthukare/k8s-3tier-backend:latest ./app/backend
docker build -t prashanthukare/k8s-3tier-frontend:latest ./app/frontend
```

### Deploy the app

```bash
kubectl apply -f k8s/
kubectl -n three-tier get pods -w     # wait until everything is Running
```

### Open the app in your browser

```bash
echo "$(minikube ip) three-tier.local" | sudo tee -a /etc/hosts
```

Now open <http://three-tier.local> in your browser. Every refresh increases
the visit counter stored in MySQL.

## Load test: watch the HPA scale (run this yourself)

In one terminal, watch the autoscaler:

```bash
kubectl -n three-tier get hpa -w
```

In a second terminal, create load (keep it running):

```bash
while true; do curl -s http://three-tier.local/api/visits > /dev/null; done
```

For heavier load, open a few more terminals and run the same loop in each.
Watch the HPA add backend pods (up to 6). Stop the loops with Ctrl+C and
watch it scale back down after a few minutes.

**My results (fill in after running it):**

- Date and machine (CPU/RAM): ___
- Number of load loops running: ___
- Backend pods before the test: ___
- Backend pods at the peak: ___
- Time from starting load to first new pod: ___
- CPU % shown by `kubectl -n three-tier top pods` at the peak: ___
- Time to scale back to 2 pods after stopping the load: ___

## Clean up

```bash
kubectl delete namespace three-tier
```

## What I learned

- Splitting an app into frontend, backend and database tiers, and connecting
  them with Kubernetes Services.
- Why a database uses a StatefulSet with a PVC instead of a plain Deployment.
- Keeping passwords in Secrets and settings in ConfigMaps.
- Health-checking pods with readiness and liveness probes.
- Autoscaling with an HPA driven by CPU usage.
- Automating Docker builds and pushes with GitHub Actions.

## Author

Prashant Hukare - Aspiring Cloud & DevOps Engineer, Nagpur
