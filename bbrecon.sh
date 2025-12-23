#!/bin/bash
# bbrecon.sh - Full subdomain recon

TARGET=$1

echo "[+] Starting recon for $TARGET"

# 1. Subdomain enumeration
echo "[*] Running subfinder..."
subfinder -d $TARGET -all -silent -o subs_subfinder.txt

echo "[*] Running THC Recon..."
python3 thc_recon.py -t $TARGET -o subs_thc.txt

echo "[*] Running assetfinder..."
assetfinder --subs-only $TARGET > subs_assetfinder.txt

# 2. Merge & dedupe
cat subs_*.txt | sort -u > all_subs.txt
echo "[+] Found $(wc -l < all_subs.txt) unique subdomains"

# 3. Scan active ports
echo "[*] Probing active ports..."
naabu -l all_subs.txt -tp 100 -ec -s s -o ports.txt
echo "[+] Found $(wc -l < ports.txt.txt) active ports"

# 4. Probe alive hosts
echo "[*] Probing alive hosts..."
httpx -l ports.txt -o alive.txt

# 5. Nuclei scan
echo "[*] Running nuclei..."
nuclei -l alive.txt -es unknown -rl 1000 -silent -o vulnerabilities.txt

echo "[+] Recon complete! Check vulnerabilities.txt"
