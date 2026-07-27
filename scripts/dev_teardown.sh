#!/usr/bin/env bash
set -euo pipefail

SLUG=""
PROJECT=""
DELETE_PROJECT=0
YES_FLAG=0

while [ $# -gt 0 ]; do
  case "$1" in
    --slug)
      SLUG="$2"
      shift 2
      ;;
    --project)
      PROJECT="$2"
      shift 2
      ;;
    --delete-project)
      DELETE_PROJECT=1
      shift
      ;;
    --yes)
      YES_FLAG=1
      shift
      ;;
    *)
      echo "Unknown argument: $1"
      exit 1
      ;;
  esac
done

if [ -z "$SLUG" ] || [ -z "$PROJECT" ]; then
  echo "Error: --slug and --project are required."
  echo "Usage: $0 --slug <slug> --project <project-id> [--delete-project] [--yes]"
  exit 1
fi

echo "The following resources will be deleted in project: $PROJECT"
echo " - VM Instance: hermes-vm-$SLUG"
echo " - Firewall Rule: allow-iap-ssh-$SLUG"
echo " - Firewall Rule: allow-public-ssh-$SLUG"
echo " - Service Account: hermes-vm-$SLUG@$PROJECT.iam.gserviceaccount.com"
echo " - Secret: hermes-agent-key-$SLUG"
if [ "$DELETE_PROJECT" -eq 1 ]; then
  echo " - GCP Project: $PROJECT"
fi
echo ""

if [ "$YES_FLAG" -eq 0 ]; then
  printf "Type 'yes' to confirm deletion: "
  read -r CONFIRM
  if [ "$CONFIRM" != "yes" ]; then
    echo "Aborting teardown."
    exit 0
  fi
fi

echo "Deleting VM Instance..."
gcloud compute instances delete "hermes-vm-$SLUG" --project="$PROJECT" --quiet || true

echo "Deleting Firewall Rule (allow-iap-ssh)..."
gcloud compute firewall-rules delete "allow-iap-ssh-$SLUG" --project="$PROJECT" --quiet || true

echo "Deleting Firewall Rule (allow-public-ssh)..."
gcloud compute firewall-rules delete "allow-public-ssh-$SLUG" --project="$PROJECT" --quiet || true

echo "Deleting Service Account..."
gcloud iam service-accounts delete "hermes-vm-$SLUG@$PROJECT.iam.gserviceaccount.com" --project="$PROJECT" --quiet || true

echo "Deleting Secret..."
gcloud secrets delete "hermes-agent-key-$SLUG" --project="$PROJECT" --quiet || true

if [ "$DELETE_PROJECT" -eq 1 ]; then
  echo "Deleting GCP Project..."
  gcloud projects delete "$PROJECT" --quiet || true
fi

echo "Teardown complete."
