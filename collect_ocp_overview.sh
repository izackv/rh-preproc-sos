#!/usr/bin/env bash
#
# collect-ocp-overview.sh
# Read-only OCP architecture-overview collector. Run once per cluster.
# Produces a timestamped, per-domain bundle for cross-cluster comparison.
#
# Safety: this script ONLY runs `oc get` / `oc adm top` / `oc auth can-i` /
# `oc whoami` / `oc version` / `oc adm upgrade`. It performs no writes.
#
# Usage:
#   export KUBECONFIG=/path/to/cluster-kubeconfig
#   ./collect-ocp-overview.sh [cluster-label]
#
set -uo pipefail

CLUSTER_LABEL="${1:-$(oc whoami --show-server 2>/dev/null | sed 's|https\?://||; s|[:/].*||' || echo cluster)}"
TS="$(date +%Y%m%d-%H%M%S)"
OUT="ocp-overview_${CLUSTER_LABEL}_${TS}"
mkdir -p "$OUT"

log()  { printf '  [+] %s\n' "$1"; }
warn() { printf '  [!] %s\n' "$1" >&2; }

# run <outfile> <oc args...>  — never fails the script; records missing/denied
run() {
  local f="$OUT/$1"; shift
  if oc "$@" > "$f" 2>"$f.err"; then
    [ -s "$f" ] || echo "(empty result)" > "$f"
    rm -f "$f.err"
  else
    echo "(command failed or resource absent — see $1.err)" > "$f"
  fi
}

echo "=== OCP Architecture Overview collection: $CLUSTER_LABEL ==="
echo "    Output dir: $OUT"

# ---- 0. Access sanity ------------------------------------------------------
log "Access & identity"
{
  echo "## whoami";        oc whoami 2>&1
  echo "## server";        oc whoami --show-server 2>&1
  echo "## can-i get nodes";              oc auth can-i get nodes 2>&1
  echo "## can-i list clusteroperators";  oc auth can-i list clusteroperators 2>&1
  echo "## can-i create clusterrolebindings (expect no for read-only)"
  oc auth can-i create clusterrolebindings 2>&1
} > "$OUT/00-access.txt"

# ---- 1. Identity, version & lifecycle -------------------------------------
log "Version & cluster operators"
run "01-version.txt"            version
run "01-clusterversion.yaml"    get clusterversion -o yaml
run "01-upgrade.txt"            adm upgrade
run "01-clusteroperators.txt"   get clusteroperators
run "01-infrastructure.yaml"    get infrastructure cluster -o yaml
run "01-proxy.yaml"             get proxy cluster -o yaml
run "01-dns.yaml"               get dns.config cluster -o yaml
run "01-featuregate.yaml"       get featuregate cluster -o yaml

# ---- 2. Topology & compute -------------------------------------------------
log "Nodes, machinesets, MCPs"
run "02-nodes-wide.txt"         get nodes -o wide
run "02-nodes-roles.txt"        get nodes -L node-role.kubernetes.io/master -L node-role.kubernetes.io/worker -L node-role.kubernetes.io/infra
run "02-nodes-capacity.txt"     get nodes -o custom-columns=NAME:.metadata.name,CPU:.status.capacity.cpu,MEM:.status.capacity.memory,KERNEL:.status.nodeInfo.kernelVersion,RUNTIME:.status.nodeInfo.containerRuntimeVersion
run "02-mcp.txt"                get machineconfigpool
run "02-machinesets.txt"        get machineset -n openshift-machine-api
run "02-machines.txt"           get machines -n openshift-machine-api -o wide
run "02-autoscalers.txt"        get clusterautoscaler,machineautoscaler -A
run "02-top-nodes.txt"          adm top nodes
run "02-gpu-nodes.txt"          get nodes -L nvidia.com/gpu.present
run "02-clusterpolicy.txt"      get clusterpolicy -A
run "02-nicclusterpolicy.txt"   get nicclusterpolicy -A

# ---- 3. Networking ---------------------------------------------------------
log "Networking"
run "03-network-config.yaml"    get network.config cluster -o yaml
run "03-network-operator.yaml"  get network.operator cluster -o yaml
run "03-ingresscontroller.yaml" get ingresscontroller -n openshift-ingress-operator -o yaml
run "03-ingress-svc.txt"        get svc -n openshift-ingress
run "03-routes.txt"             get routes -A
run "03-networkpolicy.txt"      get networkpolicy -A
run "03-egressips.txt"          get egressips
run "03-egressfirewall.txt"     get egressfirewall -A
run "03-metallb.txt"            get ipaddresspools,l2advertisements,bgpadvertisements -A
run "03-net-attach-def.txt"     get network-attachment-definitions -A
run "03-sriov.txt"              get sriovnetworknodepolicy,sriovnetwork -A

# ---- 4. Storage ------------------------------------------------------------
log "Storage"
run "04-storageclasses.txt"     get sc -o custom-columns=NAME:.metadata.name,PROVISIONER:.provisioner,RECLAIM:.reclaimPolicy,BINDMODE:.volumeBindingMode,DEFAULT:.metadata.annotations.storageclass\\.kubernetes\\.io/is-default-class
run "04-csidrivers.txt"         get csidrivers
run "04-volumesnapshotclass.txt" get volumesnapshotclass
run "04-pv.txt"                 get pv
run "04-pvc.txt"                get pvc -A
run "04-storagecluster.txt"     get storagecluster -n openshift-storage
run "04-cephcluster.txt"        get cephcluster -n openshift-storage
run "04-trident.txt"            get tridentbackendconfig -A

# ---- 5. Operators & OLM ----------------------------------------------------
log "Operators & OLM"
run "05-catalogsource.txt"      get catalogsource -A
run "05-operatorgroup.txt"      get operatorgroup -A
run "05-subscriptions.txt"      get subscription -A -o custom-columns=NS:.metadata.namespace,NAME:.metadata.name,CHANNEL:.spec.channel,APPROVAL:.spec.installPlanApproval,CSV:.status.installedCSV
run "05-csv.txt"                get csv -A
run "05-installplan.txt"        get installplan -A

# ---- 6. Workloads & tenancy ------------------------------------------------
log "Workloads & tenancy"
run "06-projects.txt"           get projects
run "06-resourcequota.txt"      get resourcequota -A
run "06-limitrange.txt"         get limitrange -A
run "06-pods-all.txt"           get pods -A -o wide
run "06-workloads.txt"          get deploy,statefulset,daemonset -A

# ---- 7. Security & access --------------------------------------------------
log "Security & access"
run "07-oauth.yaml"             get oauth cluster -o yaml
run "07-users.txt"              get user
run "07-identities.txt"         get identity
run "07-clusterrolebindings.txt" get clusterrolebinding -o wide
run "07-scc.txt"                get scc
run "07-etcd-encryption.txt"    get apiserver cluster -o jsonpath={.spec.encryption.type}
run "07-imageregistry.yaml"     get configs.imageregistry.operator.openshift.io cluster -o yaml
run "07-registry-route.txt"     get route -n openshift-image-registry
run "07-certificates.txt"       get certificates -A
run "07-acs-central.txt"        get central -A
run "07-acs-secured.txt"        get securedcluster -A

# ---- 8. Observability ------------------------------------------------------
log "Observability"
run "08-cluster-monitoring.yaml" get configmap cluster-monitoring-config -n openshift-monitoring -o yaml
run "08-uwm.yaml"               get configmap user-workload-monitoring-config -n openshift-user-workload-monitoring -o yaml
run "08-prom-am.txt"            get prometheus,alertmanager -n openshift-monitoring
run "08-clusterlogging.txt"     get clusterlogging,clusterlogforwarder -n openshift-logging
run "08-lokistack.txt"          get lokistack -A
run "08-prometheusrules.txt"    get prometheusrule -A

# ---- 9. GitOps / CD --------------------------------------------------------
log "GitOps / CD"
run "09-argocd.txt"             get argocd -A
run "09-applications.txt"       get applications -A
run "09-appprojects.txt"        get appprojects -A
run "09-tektonconfig.txt"       get tektonconfig

# ---- 10. Backup & DR -------------------------------------------------------
log "Backup & DR"
run "10-cronjobs.txt"           get cronjob -A
run "10-oadp-dpa.txt"           get dataprotectionapplication -A
run "10-backup-locations.txt"   get backupstoragelocation,volumesnapshotlocation -A
run "10-velero-crs.txt"         get backup,restore,schedule -A

# ---- Summary ---------------------------------------------------------------
{
  echo "# Collection summary: $CLUSTER_LABEL ($TS)"
  echo
  echo "## Degraded ClusterOperators"
  grep -iE 'True\s+True|Degraded' "$OUT/01-clusteroperators.txt" 2>/dev/null || echo "  (none flagged in plain listing — verify 01-clusteroperators.txt)"
  echo
  echo "## Non-running pods"
  grep -Ev 'Running|Completed|NAME' "$OUT/06-pods-all.txt" 2>/dev/null | head -50 || true
  echo
  echo "## etcd encryption type (empty = NOT enabled)"
  cat "$OUT/07-etcd-encryption.txt" 2>/dev/null; echo
  echo
  echo "## Default StorageClass"
  cat "$OUT/04-storageclasses.txt" 2>/dev/null
} > "$OUT/SUMMARY.txt"

echo
echo "=== Done. Bundle: $OUT ==="
echo "    Review $OUT/SUMMARY.txt first, then per-domain files."
echo "    Optional next step (connected): oc adm must-gather --dest-dir=$OUT/mustgather"
