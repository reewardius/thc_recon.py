#!/usr/bin/env python3
"""
Subdomain Collector for ip.thc.org API
Based on best practices from thc_recon.py by Tommy DeVoss
Improved version with better parsing and rate limiting
"""

import requests
import argparse
import sys
import time
import re
import os
from typing import Set, Optional, Tuple, List

# ANSI colors
class Colors:
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    WHITE = '\033[97m'
    GRAY = '\033[90m'
    BOLD = '\033[1m'
    RED = '\033[91m'
    END = '\033[0m'

def aggressive_strip_ansi(s: str) -> Optional[str]:
    """
    Strip all ANSI escape codes from string (both real and text-based)
    (copied from thc_recon.py - proven to work)
    """
    if not s:
        return None
    
    # Remove real ANSI escape codes (ESC character = \x1B)
    # Remove CSI sequences
    s = re.sub(r'\x1B\[[0-?]*[ -/]*[@-~]', '', s)
    # Remove other escape sequences
    s = re.sub(r'\x1B[@-Z\\-_][0-?]*[ -/]*[@-~]', '', s)
    # Remove charset selection sequences
    s = re.sub(r'\x1B\([AB0-2]', '', s)
    
    # Remove text-based ANSI codes like [0;36m, [0m, etc.
    # Pattern: [digits;digits...m or [digits...m
    s = re.sub(r'\[\d+(?:;\d+)*m', '', s)
    
    return s.strip()

def parse_response(text: str) -> Tuple[Optional[int], Optional[int], Optional[str], list]:
    """
    Parse API response (improved version from thc_recon.py)
    
    Returns:
        tuple: (total_entries, rate_limit, next_page_url, results_list)
    """
    total_entries = None
    rate_limit = None
    next_page_candidate = None
    results = []

    for raw_line in text.splitlines():
        line = aggressive_strip_ansi(raw_line)

        if not line:
            continue

        # Parse total entries
        if line.startswith(";;Entries:"):
            parts = line.split("/")
            if len(parts) >= 2:
                try:
                    total_entries = int(parts[1].split()[0])
                except:
                    pass
        
        # Parse rate limit
        elif line.startswith(";;Rate Limit:"):
            match = re.search(r'You can make (\d+)', line)
            if match:
                rate_limit = int(match.group(1))
        
        # Parse next page URL
        elif line.startswith(";;Next Page:"):
            candidate = line.split(":", 1)[1] if ":" in line else line
            next_page_candidate = aggressive_strip_ansi(candidate)
        
        # Collect subdomains (non-comment lines)
        elif not line.startswith(";;"):
            clean_result = aggressive_strip_ansi(raw_line).strip()
            if clean_result:
                results.append(clean_result)

    # Validate next page URL
    next_page = None
    if next_page_candidate and next_page_candidate.startswith("https://ip.thc.org/"):
        next_page = next_page_candidate

    return total_entries, rate_limit, next_page, results

def get_sleep_time(rate_limit_remaining: Optional[int]) -> float:
    """
    Calculate sleep time based on remaining rate limit
    (from thc_recon.py - intelligent rate limiting)
    """
    if rate_limit_remaining is None:
        return 2.1
    
    rl = int(rate_limit_remaining)
    if rl >= 50:
        return 0.1
    elif rl >= 20:
        return 0.5
    elif rl >= 10:
        return 1.0
    else:
        return 2.2 - (rl * 0.1)

class SubdomainCollector:
    def __init__(self, output_file: str, verbose: bool = False):
        """
        Initialize the subdomain collector
        
        Args:
            output_file: Path to output file for collected subdomains
            verbose: Show detailed progress
        """
        self.output_file = output_file
        self.verbose = verbose
        self.old_subdomains = set()
        self.new_subdomains_found = set()
        
        # Load old subdomains if file exists (for comparison)
        if os.path.exists(self.output_file):
            with open(self.output_file, 'r') as f:
                self.old_subdomains = {aggressive_strip_ansi(line).strip() for line in f if line.strip()}
            if self.verbose:
                print(f"{Colors.CYAN}Loaded {len(self.old_subdomains)} existing subdomains from {self.output_file}{Colors.END}")
        
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36'
        })
        
    def print_status(self, target: str, fetched: int, total: Optional[int], 
                    rate_limit: Optional[int], requests_made: int, new_count: int = 0):
        """
        Print live status update on same line
        """
        if not self.verbose:
            return
            
        remaining = total - fetched if total else 0
        total_str = total if total else "?"
        remaining_str = remaining if total else "?"
        
        new_info = f"  |  {Colors.GRAY}New:{Colors.END} {Colors.GREEN}{new_count}{Colors.END}"
        
        status = (
            f"{Colors.CYAN}{Colors.BOLD}Target:{Colors.END} {Colors.WHITE}{target}{Colors.END}  |  "
            f"{Colors.GRAY}Fetched:{Colors.END} {Colors.GREEN}{fetched}{Colors.END}/{Colors.GREEN}{total_str}{Colors.END}  "
            f"({Colors.GRAY}Remaining:{Colors.END} {Colors.GREEN}{remaining_str}{Colors.END}){new_info}  |  "
            f"{Colors.GRAY}Rate Limit:{Colors.END} {Colors.YELLOW}{rate_limit if rate_limit else '?'}{Colors.END}  |  "
            f"{Colors.GRAY}Requests:{Colors.END} {Colors.WHITE}{requests_made}{Colors.END}"
        )
        # Carriage return + clear to end of line
        print(f"\r\033[K{status}", end="", flush=True)
    
    def collect_subdomains(self, domain: str) -> Set[str]:
        """
        Collect all subdomains for a given domain with pagination
        
        Args:
            domain: Target domain
            
        Returns:
            Set of unique subdomains
        """
        all_subdomains = set()
        url = f"https://ip.thc.org/{domain}?l=100"
        page_num = 1
        total_requests = 0
        total_entries = None
        rate_limit = None
        
        if self.verbose:
            print(f"{Colors.WHITE}Starting collection for domain: {domain}{Colors.END}\n")
        
        while url:
            total_requests += 1
            
            try:
                response = self.session.get(url, timeout=30)
                
                # Handle 404 gracefully
                if response.status_code == 404:
                    if self.verbose:
                        print(f"\n{Colors.GRAY}No records found (404){Colors.END}")
                    break
                
                response.raise_for_status()
                
            except requests.exceptions.HTTPError as e:
                if e.response and e.response.status_code == 404:
                    if self.verbose:
                        print(f"\n{Colors.GRAY}No records found (404){Colors.END}")
                    break
                else:
                    print(f"\n{Colors.RED}HTTP error: {e}{Colors.END}", file=sys.stderr)
                    time.sleep(10)
                    continue
                    
            except requests.exceptions.RequestException as e:
                print(f"\n{Colors.RED}Request failed: {e}{Colors.END}", file=sys.stderr)
                time.sleep(10)
                continue
            
            # Parse response using proven parser
            total_entries_new, rate_limit_new, next_page, results = parse_response(response.text)
            
            if total_entries_new is not None:
                total_entries = total_entries_new
            if rate_limit_new is not None:
                rate_limit = rate_limit_new
            
            # Add subdomains and track new ones
            for subdomain in results:
                if subdomain not in all_subdomains:
                    all_subdomains.add(subdomain)
                    
                    # Track if this is a new subdomain (not in old file)
                    if subdomain not in self.old_subdomains:
                        self.new_subdomains_found.add(subdomain)
            
            # Update status
            new_count = len(self.new_subdomains_found)
            self.print_status(domain, len(all_subdomains), total_entries, rate_limit, total_requests, new_count)
            
            # Check if there's a next page
            if next_page:
                url = next_page
                page_num += 1
                
                # Intelligent sleep based on rate limit
                sleep_time = get_sleep_time(rate_limit)
                time.sleep(sleep_time)
            else:
                if self.verbose:
                    print(f"\n{Colors.GREEN}Collection complete!{Colors.END}")
                break
        
        return all_subdomains
    
    def process_targets(self, targets: List[str]):
        """
        Process multiple target domains
        
        Args:
            targets: List of target domains
        """
        if self.verbose:
            print(f"\n{Colors.CYAN}{Colors.BOLD}{'='*80}{Colors.END}")
            print(f"{Colors.CYAN}{Colors.BOLD}Subdomain Collector - ip.thc.org API{Colors.END}")
            print(f"{Colors.CYAN}{Colors.BOLD}{'='*80}{Colors.END}\n")
        
        all_results = set()
        
        for i, domain in enumerate(targets, 1):
            if self.verbose:
                print(f"{Colors.WHITE}Processing target {i}/{len(targets)}: {domain}{Colors.END}")
            
            try:
                subdomains = self.collect_subdomains(domain)
                all_results.update(subdomains)
                
                if self.verbose:
                    print(f"\n{Colors.GREEN}Collected {len(subdomains)} subdomains for {domain}{Colors.END}\n")
                
            except KeyboardInterrupt:
                print(f"\n\n{Colors.YELLOW}Interrupted by user (Ctrl+C){Colors.END}")
                print(f"{Colors.WHITE}Progress saved{Colors.END}")
                sys.exit(0)
        
        # Save all results to main output file
        with open(self.output_file, 'w') as f:
            for subdomain in sorted(all_results):
                f.write(f"{subdomain}\n")
        
        # Save new subdomains to new_subs.txt
        if self.new_subdomains_found:
            new_file = "new_subs.txt"
            with open(new_file, 'w') as f:
                for subdomain in sorted(self.new_subdomains_found):
                    f.write(f"{subdomain}\n")
            
            print(f"{Colors.GREEN}New subdomains found: {len(self.new_subdomains_found)}{Colors.END}")
            print(f"{Colors.WHITE}New subdomains saved to: {new_file}{Colors.END}")
        else:
            print(f"{Colors.YELLOW}No new subdomains found (all {len(all_results)} were already known){Colors.END}")
        
        # Final summary
        if self.verbose:
            print(f"\n{Colors.CYAN}{Colors.BOLD}{'='*80}{Colors.END}")
            print(f"{Colors.BOLD}SUMMARY{Colors.END}")
            print(f"{Colors.CYAN}{'='*80}{Colors.END}")
        
        print(f"{Colors.GREEN}Total unique subdomains: {len(all_results)}{Colors.END}")
        print(f"{Colors.WHITE}Saved to: {self.output_file}{Colors.END}")
        
        if self.verbose:
            print(f"{Colors.CYAN}{'='*80}{Colors.END}")


def read_targets_from_file(filename: str) -> List[str]:
    """
    Read target domains from file
    
    Args:
        filename: Path to file containing domains (one per line)
        
    Returns:
        List of domain names
    """
    try:
        with open(filename, 'r') as f:
            domains = [line.strip() for line in f if line.strip() and not line.startswith('#')]
        return domains
    except IOError as e:
        print(f"{Colors.RED}Error reading file {filename}: {e}{Colors.END}", file=sys.stderr)
        sys.exit(1)


def parse_comma_separated(targets: List[str]) -> List[str]:
    """
    Parse comma-separated targets into individual domains
    
    Args:
        targets: List of target strings (may contain commas)
        
    Returns:
        List of individual domain names
    """
    result = []
    for target in targets:
        # Split by comma and strip whitespace
        domains = [d.strip() for d in target.split(',') if d.strip()]
        result.extend(domains)
    return result


def main():
    parser = argparse.ArgumentParser(
        description=f'{Colors.CYAN}{Colors.BOLD}Subdomain Collector{Colors.END} - Fetch all subdomains from ip.thc.org API\n'
                    f'{Colors.GRAY}Based on thc_recon.py by Tommy DeVoss{Colors.END}',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f'''{Colors.CYAN}Examples:{Colors.END}
  # Collect subdomains (compares with existing subs.txt automatically)
  python3 %(prog)s -t example.com -o subs.txt
  python3 %(prog)s -t example.com,another.com,test.com -o subs.txt
  python3 %(prog)s -f domains.txt -o output.txt
  
  # Verbose mode with detailed progress
  python3 %(prog)s -t example.com -o subs.txt -v
  
{Colors.YELLOW}Features:{Colors.END}
  • Auto-comparison with existing file (new subdomains → new_subs.txt)
  • Intelligent rate limiting (faster when possible)
  • Real-time progress display (with -v flag)
  • Automatic ANSI code cleaning
  • Comma-separated targets support
  
{Colors.GRAY}How it works:{Colors.END}
  1. Loads existing subdomains from output file (if exists)
  2. Collects new results from API
  3. Saves ALL results to output file (overwrites)
  4. Saves ONLY NEW subdomains to new_subs.txt
        '''
    )
    
    parser.add_argument('-t', '--target', 
                        nargs='+',
                        metavar='DOMAIN',
                        help='Target domain(s) to scan (comma-separated or space-separated)')
    
    parser.add_argument('-f', '--file',
                        metavar='FILE',
                        help='File containing list of target domains (one per line)')
    
    parser.add_argument('-o', '--output',
                        metavar='FILE',
                        help='Output file for collected subdomains',
                        required=True)
    
    parser.add_argument('-v', '--verbose',
                        action='store_true',
                        help='Verbose mode (show detailed progress)')
    
    args = parser.parse_args()
    
    # Collect targets from both sources
    targets = []
    
    if args.target:
        # Parse comma-separated targets
        parsed_targets = parse_comma_separated(args.target)
        targets.extend(parsed_targets)
    
    if args.file:
        targets.extend(read_targets_from_file(args.file))
    
    if not targets:
        parser.error("No targets specified. Use -t or -f to specify targets.")
    
    # Remove duplicates while preserving order
    seen = set()
    unique_targets = []
    for target in targets:
        if target not in seen:
            seen.add(target)
            unique_targets.append(target)
    
    # Create collector and process targets
    collector = SubdomainCollector(args.output, verbose=args.verbose)
    
    try:
        collector.process_targets(unique_targets)
    except KeyboardInterrupt:
        print(f"\n\n{Colors.YELLOW}Interrupted by user{Colors.END}")
        sys.exit(0)


if __name__ == "__main__":
    main()
