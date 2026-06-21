# Task Checklist

## 1. Ingress Routing Fixes
- [x] Remove `appgw.ingress.kubernetes.io/backend-path-prefix: /` annotation in `admin-service/ingress.yaml`
- [x] Remove `appgw.ingress.kubernetes.io/backend-path-prefix: /` annotation in `analytics-service/ingress.yaml`
- [x] Remove `appgw.ingress.kubernetes.io/backend-path-prefix: /` annotation in `billing-service/ingress.yaml`
- [x] Remove `appgw.ingress.kubernetes.io/backend-path-prefix: /` annotation in `student-service/ingress.yaml`
- [x] Remove `appgw.ingress.kubernetes.io/backend-path-prefix: /` annotation in `trainer-service/ingress.yaml`

## 2. Frontend MSAL & SSO Adjustments
- [x] Modify `msal-config.ts` to request standard OIDC scopes `["openid", "profile", "email"]`
- [x] Update `use-api-client.ts` to acquire and return the MSAL `idToken` instead of `accessToken`
- [x] Update `/login/page.tsx`:
  - [x] Rename button to "Sign in with Microsoft"
  - [x] Hide credential form behind toggle link
  - [x] Auto-redirect to `/dashboard` when MSAL accounts exist
- [x] Update `/admin/page.tsx`:
  - [x] Add "Sign in with Microsoft" button
  - [x] Hide admin credential form behind toggle link
  - [x] Check if authenticated user has `Admin` role; redirect to `/dashboard` if yes, show error if no

## 3. Backend Token Audience Compatibility
- [x] Modify `admin-service/app/config.py` to accept list of audiences (client ID and `api://` format)
- [x] Modify `analytics-service/app/config.py` to accept list of audiences
- [x] Modify `auth-service/app/config.py` to accept list of audiences
- [x] Modify `billing-service/app/config.py` to accept list of audiences
- [x] Modify `student-service/app/config.py` to accept list of audiences
- [x] Modify `trainer-service/app/config.py` to accept list of audiences

## 4. Infrastructure (Workload Identity & PostgreSQL AD Auth)
- [x] Update root `main.tf` to provision `azurerm_user_assigned_identity` for workload
- [x] Create `azurerm_federated_identity_credential` linking workload identity to ServiceAccount `ctmp-workload-sa`
- [x] Grant workload identity `Key Vault Secrets User` role assignment
- [x] Update database module parameters to pass workload identity client and principal ID
- [x] Update `modules/database/main.tf` to enable `active_directory_auth_enabled = true` and create the active directory administrator resource

## 5. Kubernetes manifests (Workload Identity)
- [x] Create `gitops/manifests/service-account.yaml` ServiceAccount definition with workload client ID annotation
- [x] Update deployment manifests of all services to use `serviceAccountName: ctmp-workload-sa`, `azure.workload.identity/use: "true"` label, and set environment variables `USE_ENTRA_DB_AUTH` and `DB_USER`

## 6. Backend PostgreSQL Active Directory Code
- [x] Update dependencies in `requirements.txt` of all 4 database-connected services to include `azure-identity==1.16.1`
- [x] Implement dynamic Entra ID database token connection pool creator in `database.py` of all 4 database services when `USE_ENTRA_DB_AUTH=true`
