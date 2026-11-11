#!/usr/bin/env bash
# One-shot cluster setup. Run on the master VM from the project root,
# after editing ansible/inventory.ini and ansible/group_vars/all.yml.
set -euo pipefail
cd "$(dirname "$0")"
INV=ansible/inventory.ini

sudo apt-get update -qq
sudo apt-get install -y ansible
[ -f ~/.ssh/id_ed25519 ] || ssh-keygen -t ed25519 -N "" -f ~/.ssh/id_ed25519

user=$(awk -F= '/^ansible_user/ {print $2}' "$INV")
for ip in $(grep -oE 'ansible_host=[0-9.]+' "$INV" | cut -d= -f2); do
  ssh-copy-id -o StrictHostKeyChecking=no "$user@$ip"
done

(cd ansible && ansible all -m ping && ansible-playbook site.yml -K)
bash -lc "$(pwd)/apps/build.sh && /opt/bench/cluster.sh status"
