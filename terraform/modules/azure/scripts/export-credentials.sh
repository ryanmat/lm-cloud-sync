#!/bin/bash
# Export Azure credentials from Terraform output for lm-cloud-sync
#
# Usage:
#   source scripts/export-credentials.sh
#   # Or:
#   eval $(./scripts/export-credentials.sh)

set -e

# Check if we're in a Terraform directory
if [ ! -f "terraform.tfstate" ] && [ ! -d ".terraform" ]; then
    echo "Error: Not in a Terraform directory. Run 'terraform init' first." >&2
    exit 1
fi

# Get credentials from Terraform output
TENANT_ID=$(terraform output -raw tenant_id 2>/dev/null)
CLIENT_ID=$(terraform output -raw client_id 2>/dev/null)
CLIENT_SECRET=$(terraform output -raw client_secret 2>/dev/null)

if [ -z "$TENANT_ID" ] || [ -z "$CLIENT_ID" ] || [ -z "$CLIENT_SECRET" ]; then
    echo "Error: Could not retrieve Azure credentials from Terraform output." >&2
    echo "Make sure 'terraform apply' has been run successfully." >&2
    exit 1
fi

# Export for current shell (when sourced)
export AZURE_TENANT_ID="$TENANT_ID"
export AZURE_CLIENT_ID="$CLIENT_ID"
export AZURE_CLIENT_SECRET="$CLIENT_SECRET"

# Print export commands (when run directly)
if [ "$0" = "${BASH_SOURCE[0]}" ]; then
    echo "export AZURE_TENANT_ID=\"$TENANT_ID\""
    echo "export AZURE_CLIENT_ID=\"$CLIENT_ID\""
    echo "export AZURE_CLIENT_SECRET=\"$CLIENT_SECRET\""
else
    echo "Azure credentials exported successfully!" >&2
    echo "  AZURE_TENANT_ID: $TENANT_ID" >&2
    echo "  AZURE_CLIENT_ID: $CLIENT_ID" >&2
    echo "  AZURE_CLIENT_SECRET: <set>" >&2
fi
