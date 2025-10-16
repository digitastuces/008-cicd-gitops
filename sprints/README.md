# 🚀 Sprint 1 — CI/CD Avancé & GitOps Propre (EKS + Argo CD + GitHub Actions)

![Terraform](https://img.shields.io/badge/Terraform-v1.5+-purple?logo=terraform)
![AWS EKS](https://img.shields.io/badge/AWS-EKS-orange?logo=amazonaws)
![GitHub Actions](https://img.shields.io/badge/GitHub-Actions-blue?logo=githubactions)
![Argo CD](https://img.shields.io/badge/Argo-CD-red?logo=argo)
![Status](https://img.shields.io/badge/Sprint-1-success-green)

---

## 🎯 Objectif

Mettre en place une chaîne **CI/CD GitOps industrielle**, connectée à ton cluster EKS et Argo CD :

- Build et push des images Docker (backend & frontend) dans **ECR**
- Validation automatique (lint / Kubeval / scan)
- Déploiement automatisé via **Argo CD**
- Gestion multi-environnements : `dev`, `staging`, `prod`
- Préparation à la signature Cosign et scan Trivy (Sprint 2 : DevSecOps)

---

## 🧱 Structure du projet

```
008-cicd-gitops/
├── .github/workflows/
│   ├── build-push-ecr.yml           # CI: build & push Docker images vers ECR
│   └── lint-test.yml                # Lint YAML & validation K8s
│
├── manifests/                       # Manifests Kubernetes + Kustomize
│   ├── base/
│   │   ├── backend-deployment.yaml
│   │   ├── backend-service.yaml
│   │   ├── frontend-deployment.yaml
│   │   ├── frontend-service.yaml
│   │   └── namespace.yaml
│   └── overlays/
│       ├── dev/kustomization.yaml
│       ├── staging/kustomization.yaml
│       └── prod/kustomization.yaml
│
├── argocd/                          # Déclarations Argo CD (GitOps)
│   ├── project.yaml
│   ├── app-of-apps.yaml
│   ├── app-backend-dev.yaml
│   ├── app-frontend-dev.yaml
│   ├── app-backend-staging.yaml
│   └── app-frontend-staging.yaml
│
└── README.md                        # Ce fichier
```

---

## ⚙️ Pré-requis

- ✅ **Cluster EKS** opérationnel (`eks-devsecops`)
- ✅ **Argo CD** déployé (`argocd` namespace)
- ✅ **Amazon ECR** configuré dans `eu-west-3`
- ✅ GitHub Actions avec **OIDC → IAM Role**
  - Secret GitHub : `AWS_OIDC_ROLE_ARN`

---

## 🧰 Variables principales

| Variable | Description | Valeur exemple |
|-----------|--------------|----------------|
| `AWS_REGION` | Région AWS | `eu-west-3` |
| `ECR_REGISTRY` | Registre ECR cible | `065967698083.dkr.ecr.eu-west-3.amazonaws.com` |
| `IMAGE_BACKEND` | Nom image backend | `gitops-demo-backend` |
| `IMAGE_FRONTEND` | Nom image frontend | `gitops-demo-frontend` |

---

## 🪄 Étape 1 : Initialiser le projet Argo CD

Déployer le projet et les applications racines :

```bash
kubectl apply -n argocd -f argocd/project.yaml
kubectl apply -n argocd -f argocd/app-of-apps.yaml
```

Puis les applications “enfant” (pour `dev`) :

```bash
kubectl apply -n argocd -f argocd/app-backend-dev.yaml
kubectl apply -n argocd -f argocd/app-frontend-dev.yaml
```

> 🔸 Argo CD détectera automatiquement les changements sur le repo et synchronisera les environnements.

---

## ⚙️ Étape 2 : CI/CD GitHub Actions

### 📄 Workflow : `.github/workflows/build-push-ecr.yml`

- Build & Push des images Docker dans ECR
- Utilise GitHub OIDC pour s’authentifier (pas de clé AWS statique)
- Déclenché à chaque `push` sur `main`

Exécution manuelle :
```bash
# Depuis ton poste local
docker build -t gitops-demo-backend backend
docker tag gitops-demo-backend:latest 065967698083.dkr.ecr.eu-west-3.amazonaws.com/gitops-demo-backend:latest

aws sso login --profile formation
export AWS_PROFILE=formation AWS_REGION=eu-west-3 AWS_SDK_LOAD_CONFIG=1

aws ecr get-login-password --region eu-west-3 | docker login --username AWS --password-stdin 065967698083.dkr.ecr.eu-west-3.amazonaws.com
docker push 065967698083.dkr.ecr.eu-west-3.amazonaws.com/gitops-demo-backend:latest
```

---

## 🧪 Étape 3 : Validation avant merge

### 📄 Workflow : `.github/workflows/lint-test.yml`

Vérifie chaque PR sur `main` :
- Lint YAML (`yamllint`)
- Validation syntaxe K8s (`kubeval`)
- Éventuellement tests unitaires backend/frontend (ajout possible)

---

## 🧩 Étape 4 : Structure Kustomize

- `base/` : définition commune (Deployments/Services)
- `overlays/dev|staging|prod` : images + namespaces spécifiques

Exemple `overlays/dev/kustomization.yaml` :
```yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization
namespace: dev
resources:
  - ../../base
images:
  - name: 065967698083.dkr.ecr.eu-west-3.amazonaws.com/gitops-demo-backend
    newTag: latest
```

---

## 🕹️ Étape 5 : Vérifications rapides

```bash
kubectl -n dev get all
kubectl -n dev get ingress
kubectl -n dev get pods
kubectl -n dev port-forward svc/backend 8080:80 &
curl -s http://localhost:8080
```

---

## 🔒 Étape 6 : Sécurité et conformité (pré-Sprint 2)

Prépare le pipeline pour la partie **DevSecOps :**

| Outil | Rôle | Intégration |
|--------|------|-------------|
| **Trivy** | Scan vulnérabilités d’image | Étape `scan image` dans CI |
| **Cosign** | Signature d’images ECR | Étape `cosign sign` |
| **Kyverno** | Policy cluster (no `:latest`, images signées) | Namespace `argocd` |
| **Syft** | Génération SBOM | Étape de build |

Exemple Trivy + Cosign :

```yaml
      - name: Scan image
        run: trivy image --exit-code 1 --severity CRITICAL,HIGH $ECR_REGISTRY/$IMAGE_BACKEND:latest

      - name: Sign image
        env:
          COSIGN_EXPERIMENTAL: 1
        run: cosign sign --yes $ECR_REGISTRY/$IMAGE_BACKEND:latest
```

---

## 🧭 Étape 7 : Promotion Dev → Staging → Prod

1. Commit sur `main` → déploiement `dev` automatique  
2. Merge vers `staging` → Argo CD déploie sur env. staging  
3. Merge vers `prod` → déploiement production

> Chaque overlay/branche reflète un environnement.  
> L’approche suit la logique **GitOps branch-based promotion**.

---

## 🧠 Étape suivante (Sprint 2)

> **Objectif :** renforcer la chaîne CI/CD avec Tekton, Cosign, Kyverno et Trivy.

- Migration du pipeline GitHub Actions → **Tekton Pipelines**
- Scan & signature automatique via Cosign
- Enforcement de politiques de sécurité via Kyverno
- Génération de SBOM (Syft + Dependency-Track)

---

## 👤 Auteur

**Adama DIENG**  
📧 [formation@digitastuces.com](mailto:formation@digitastuces.com)  
🌐 [digitastuces.com](https://digitastuces.com)
