# thc_recon.py

A powerful subdomain enumeration tool using the ip.thc.org API with automatic change detection and intelligent rate limiting.

## Installation

```bash
git clone https://github.com/yourusername/subdomain-collector.git
cd subdomain-collector
pip install requests
```

## Requirements

- Python 3.7+
- requests library

## Recommended Tools for Full Recon Pipeline

While this script works standalone, integrating with these tools provides comprehensive reconnaissance:

### httpx - HTTP probe and analysis
```bash
go install -v github.com/projectdiscovery/httpx/cmd/httpx@latest
```
Features: Probe live hosts, detect technologies, take screenshots

### naabu - Fast port scanner
```bash
go install -v github.com/projectdiscovery/naabu/v2/cmd/naabu@latest
```
Features: Fast SYN scanning, port discovery, service detection

### nuclei - Vulnerability scanner
```bash
go install -v github.com/projectdiscovery/nuclei/v3/cmd/nuclei@latest
# Update templates
nuclei -update-templates
```
Features: CVE detection, misconfigurations, exposures

### Optional tools
- **subfinder**: Additional subdomain enumeration
- **dnsx**: DNS toolkit for validation
- **notify**: Send results to Slack/Discord/Telegram

## Usage

### Basic Usage

```bash
# Single domain
python3 thc_recon.py -t example.com -o subs.txt

# Multiple domains (comma-separated)
python3 thc_recon.py -t example.com,another.com,test.com -o subs.txt

# Multiple domains (space-separated)
python3 thc_recon.py -t example.com another.com test.com -o subs.txt

# Load domains from file
python3 thc_recon.py -f domains.txt -o output.txt

# Verbose mode (detailed progress)
python3 thc_recon.py -t example.com -o subs.txt -v
```

### Input File Format

Create a text file with one domain per line:

```
example.com
test.com
another.com
# Comments are supported
demo.org
```

Then use it:

```bash
python3 thc_recon.py -f domains.txt -o results.txt
```

## How It Works

The script operates in the following sequence:

1. **Load existing data** - Reads previous results from output file (if exists)
2. **Collect new results** - Fetches all subdomains from ip.thc.org API
3. **Save all results** - Overwrites output file with complete current results
4. **Save new only** - Creates `new_subs.txt` with only newly discovered subdomains

### Example Workflow

```bash
# First run - found 100 subdomains
python3 thc_recon.py -t example.com -o subs.txt
# Result: 
#   subs.txt = 100 subdomains
#   new_subs.txt = 100 subdomains (all are new)

# Second run (later) - found 105 subdomains (5 new)
python3 thc_recon.py -t example.com -o subs.txt
# Result:
#   subs.txt = 105 subdomains (complete current list)
#   new_subs.txt = 5 subdomains (only the new ones)

# Third run - no changes, still 105
python3 thc_recon.py -t example.com -o subs.txt
# Result:
#   subs.txt = 105 subdomains
#   Output: "No new subdomains found (all 105 were already known)"
```

## Command Line Options

```
usage: thc_recon.py [-h] -o FILE [-t DOMAIN [DOMAIN ...]] [-f FILE] [-v]

options:
  -h, --help            Show this help message and exit
  
  -t DOMAIN [DOMAIN ...], --target DOMAIN [DOMAIN ...]
                        Target domain(s) to scan (comma-separated or space-separated)
  
  -f FILE, --file FILE  File containing list of target domains (one per line)
  
  -o FILE, --output FILE
                        Output file for collected subdomains (required)
  
  -v, --verbose         Verbose mode (show detailed progress)
```

## Output Files

### subs.txt (or your specified output file)
Contains **ALL** subdomains found in the current run (sorted alphabetically).

### new_subs.txt
Contains **ONLY** newly discovered subdomains that weren't in the previous run.
- Created only if new subdomains are found
- Overwritten on each run
- Useful for tracking changes over time

## Rate Limiting

The script automatically adjusts request speed based on API rate limits:

- **50+ requests remaining**: 0.1s delay
- **20-49 requests remaining**: 0.5s delay  
- **10-19 requests remaining**: 1.0s delay
- **<10 requests remaining**: 2.2s delay (adaptive)

This ensures optimal speed while respecting API limits.

## Verbose Mode

Enable with `-v` flag to see:

- Real-time progress for each domain
- Number of subdomains fetched vs total
- Remaining subdomains to fetch
- Current rate limit status
- Number of new subdomains found
- Request count

Example output:
```
Target: example.com  |  Fetched: 245/500  (Remaining: 255)  |  New: 12  |  Rate Limit: 45  |  Requests: 3
```

## Quiet Mode (Default)

Without `-v` flag, shows only:
- Error messages (if any)
- Final statistics
- File save confirmations

Perfect for automation and batch processing.

## Examples

### Daily subdomain monitoring

```bash
#!/bin/bash
# Run daily to track new subdomains

python3 thc_recon.py -t yourcompany.com -o company_subs.txt

# Check if new subdomains were found
if [ -f new_subs.txt ]; then
    echo "New subdomains discovered!"
    cat new_subs.txt
    # Send notification, update database, etc.
fi
```

### Multiple domain scanning

```bash
# Using comma-separated list
python3 thc_recon.py -t \
  primary.com,backup.com,test.com,dev.com \
  -o all_domains.txt -v

# Using file input
echo "primary.com" > targets.txt
echo "backup.com" >> targets.txt
echo "test.com" >> targets.txt
python3 thc_recon.py -f targets.txt -o all_domains.txt
```

### Integration with other tools

```bash
# Collect subdomains and feed to other tools
python3 thc_recon.py -t example.com -o subs.txt

# Use with httpx (probe for live web servers)
cat subs.txt | httpx -o alive_http.txt
cat subs.txt | httpx -sc -title -tech-detect -o httpx_results.txt

# Use with httpx - advanced options
cat subs.txt | httpx -ports 80,443,8080,8443 -threads 50 -o web_servers.txt
cat subs.txt | httpx -screenshot -o screenshots/

# Use with naabu (fast port scanning)
cat subs.txt | naabu -p - -o open_ports.txt
cat subs.txt | naabu -top-ports 1000 -o top_ports.txt

# Naabu with specific ports
cat subs.txt | naabu -p 80,443,8080,8443,3000,8000 -o common_web_ports.txt

# Use with nuclei (vulnerability scanning)
# After httpx probing
cat alive_http.txt | nuclei -t ~/nuclei-templates/ -o vulnerabilities.txt

# After port scanning - nuclei reads from file
nuclei -l open_ports.txt -t cves/ -o cve_results.txt

# Nuclei with specific templates
nuclei -l web_servers.txt -t exposures/ -t technologies/ -o nuclei_scan.txt

# Complete recon pipeline
python3 thc_recon.py -t example.com -o subs.txt -v
cat subs.txt | httpx -silent -o alive.txt
nuclei -l alive.txt -t ~/nuclei-templates/ -o vulns.txt

# Check only new subdomains with full pipeline
if [ -f new_subs.txt ]; then
    echo "[+] Scanning new subdomains..."
    
    # Probe HTTP
    cat new_subs.txt | httpx -o new_alive.txt
    
    # Port scanning
    cat new_subs.txt | naabu -top-ports 100 -o new_ports.txt
    
    # Vulnerability scanning on probed hosts
    nuclei -l new_alive.txt -o new_vulns.txt
    
    # Or scan directly the port scan results
    nuclei -l new_ports.txt -t cves/ -severity critical,high -o critical_vulns.txt
fi

# Advanced workflow: full recon on new subdomains
if [ -f new_subs.txt ]; then
    echo "[+] New subdomains found! Running full recon..."
    
    # Find live hosts
    cat new_subs.txt | httpx -sc -cl -title -tech-detect -o new_httpx.txt
    
    # Port scanning
    cat new_subs.txt | naabu -p - -rate 1000 -o new_naabu.txt
    
    # Vulnerability scanning on port scan results
    nuclei -l new_naabu.txt \
        -t cves/ \
        -t vulnerabilities/ \
        -t exposures/ \
        -severity critical,high,medium \
        -o new_nuclei.txt
    
    echo "[+] Recon complete! Check new_*.txt files"
fi

# Use with nmap (detailed scanning)
nmap -iL subs.txt -oA scan_results
nmap -iL alive.txt -sV -sC -oA detailed_scan
```

## Error Handling

- **404 errors**: Gracefully handled (domain has no records)
- **Network errors**: Automatic retry with 10s delay
- **Rate limit exceeded**: Intelligent slowdown
- **Interrupted scans**: Progress not saved on Ctrl+C

## Complete Automation Workflow

### Daily Subdomain Monitoring Script

```bash
#!/bin/bash
# daily_recon.sh - Automated subdomain discovery and security scanning

DOMAIN="example.com"
OUTPUT_DIR="./recon_$(date +%Y%m%d)"
mkdir -p "$OUTPUT_DIR"

echo "[*] Starting subdomain enumeration for $DOMAIN..."
python3 thc_recon.py -t "$DOMAIN" -o "$OUTPUT_DIR/all_subs.txt"

# Check if new subdomains were discovered
if [ -f new_subs.txt ]; then
    echo "[+] New subdomains found! Running security scans..."
    mv new_subs.txt "$OUTPUT_DIR/"
    
    # HTTP probing
    echo "[*] Probing for live web servers..."
    cat "$OUTPUT_DIR/new_subs.txt" | httpx \
        -sc -cl -title -tech-detect -server -ip \
        -o "$OUTPUT_DIR/httpx_results.txt"
    
    # Port scanning
    echo "[*] Scanning for open ports..."
    cat "$OUTPUT_DIR/new_subs.txt" | naabu \
        -top-ports 1000 \
        -rate 1000 \
        -o "$OUTPUT_DIR/naabu_ports.txt"
    
    # Vulnerability scanning with nuclei using port scan results
    echo "[*] Running vulnerability scans..."
    nuclei -l "$OUTPUT_DIR/naabu_ports.txt" \
        -t ~/nuclei-templates/cves/ \
        -t ~/nuclei-templates/vulnerabilities/ \
        -t ~/nuclei-templates/exposures/ \
        -t ~/nuclei-templates/misconfiguration/ \
        -severity critical,high,medium \
        -o "$OUTPUT_DIR/nuclei_vulnerabilities.txt"
    
    # Alternative: scan httpx results if you prefer
    # nuclei -l "$OUTPUT_DIR/httpx_results.txt" \
    #     -t ~/nuclei-templates/ \
    #     -severity critical,high,medium \
    #     -o "$OUTPUT_DIR/nuclei_from_httpx.txt"
    
    # Send notification (optional)
    echo "[+] Scan complete! Results in $OUTPUT_DIR"
    echo "New subdomains: $(wc -l < $OUTPUT_DIR/new_subs.txt)"
    
    # Send Slack/Discord notification
    # curl -X POST -H 'Content-type: application/json' \
    #   --data "{\"text\":\"Found $(wc -l < $OUTPUT_DIR/new_subs.txt) new subdomains for $DOMAIN\"}" \
    #   YOUR_WEBHOOK_URL
    
else
    echo "[-] No new subdomains found"
fi

echo "[*] Recon completed at $(date)"
```

### Continuous Monitoring with Cron

```bash
# Add to crontab for daily execution at 2 AM
# crontab -e

0 2 * * * /path/to/daily_recon.sh >> /var/log/subdomain_recon.log 2>&1
```

### Multi-Domain Monitoring

```bash
#!/bin/bash
# multi_domain_recon.sh - Monitor multiple domains

DOMAINS=("example.com" "test.com" "another.com")
OUTPUT_BASE="./recon_results"

for domain in "${DOMAINS[@]}"; do
    echo "[*] Processing $domain..."
    
    DOMAIN_DIR="$OUTPUT_BASE/$domain"
    mkdir -p "$DOMAIN_DIR"
    
    # Run subdomain collection
    python3 thc_recon.py -t "$domain" -o "$DOMAIN_DIR/subs.txt"
    
    # If new subdomains found, run scans
    if [ -f new_subs.txt ]; then
        mv new_subs.txt "$DOMAIN_DIR/"
        
        # Quick httpx check
        cat "$DOMAIN_DIR/new_subs.txt" | httpx -silent -o "$DOMAIN_DIR/alive.txt"
        
        # Fast port scan
        cat "$DOMAIN_DIR/new_subs.txt" | naabu -top-ports 100 -silent -o "$DOMAIN_DIR/ports.txt"
        
        # Critical vulnerability scan using port results
        nuclei -l "$DOMAIN_DIR/ports.txt" \
            -t cves/ \
            -severity critical,high \
            -silent \
            -o "$DOMAIN_DIR/critical.txt"
        
        echo "[+] $domain: Found $(wc -l < $DOMAIN_DIR/new_subs.txt) new subdomains"
    fi
done
```

### Advanced Pipeline with Parallel Processing

```bash
#!/bin/bash
# advanced_recon.sh - Full recon pipeline

DOMAIN="$1"
if [ -z "$DOMAIN" ]; then
    echo "Usage: $0 <domain>"
    exit 1
fi

OUTPUT_DIR="./recon_${DOMAIN}_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$OUTPUT_DIR"

echo "[*] Phase 1: Subdomain Enumeration"
python3 thc_recon.py -t "$DOMAIN" -o "$OUTPUT_DIR/all_subs.txt" -v

if [ ! -f new_subs.txt ]; then
    echo "[-] No new subdomains found. Exiting."
    exit 0
fi

mv new_subs.txt "$OUTPUT_DIR/"
NEW_COUNT=$(wc -l < "$OUTPUT_DIR/new_subs.txt")
echo "[+] Found $NEW_COUNT new subdomains"

echo "[*] Phase 2: HTTP Probing"
cat "$OUTPUT_DIR/new_subs.txt" | httpx \
    -sc -cl -ct -location -title -tech-detect \
    -threads 50 \
    -o "$OUTPUT_DIR/httpx.txt"

echo "[*] Phase 3: Port Scanning"
cat "$OUTPUT_DIR/new_subs.txt" | naabu \
    -p - \
    -rate 1000 \
    -stats \
    -o "$OUTPUT_DIR/ports.txt"

echo "[*] Phase 4: Vulnerability Scanning"

# Scan ports file with nuclei
nuclei -l "$OUTPUT_DIR/ports.txt" \
    -t ~/nuclei-templates/ \
    -severity critical,high,medium \
    -stats \
    -o "$OUTPUT_DIR/nuclei_all.txt"

# Separate scan for critical only
nuclei -l "$OUTPUT_DIR/ports.txt" \
    -t ~/nuclei-templates/cves/ \
    -severity critical \
    -o "$OUTPUT_DIR/nuclei_critical.txt"

echo "[*] Phase 5: Generating Report"
cat << EOF > "$OUTPUT_DIR/report.txt"
======================================
Reconnaissance Report for $DOMAIN
Date: $(date)
======================================

New Subdomains: $NEW_COUNT
Live HTTP Hosts: $(wc -l < "$OUTPUT_DIR/httpx.txt")
Open Ports Found: $(wc -l < "$OUTPUT_DIR/ports.txt")
Vulnerabilities: $(wc -l < "$OUTPUT_DIR/nuclei_all.txt")
Critical Issues: $(wc -l < "$OUTPUT_DIR/nuclei_critical.txt")

Results saved in: $OUTPUT_DIR/
======================================
EOF

cat "$OUTPUT_DIR/report.txt"
echo "[+] Recon complete!"
```

## Tips

1. **First run**: All results will be "new" since there's no comparison file
2. **Regular monitoring**: Run periodically to track subdomain changes
3. **Combine targets**: Mix `-t` and `-f` options for flexibility
4. **Automation**: Use quiet mode (default) in scripts and cron jobs
5. **Debug issues**: Use `-v` flag to see what's happening

## Troubleshooting

### No results returned
```bash
# Check if domain exists in database
curl https://ip.thc.org/example.com
```

### Rate limit issues
The script handles this automatically, but you can:
- Wait a few minutes between runs
- Reduce number of simultaneous targets

## License

MIT License - feel free to use and modify
