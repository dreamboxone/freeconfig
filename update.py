import urllib.request
import urllib.parse
import base64
import json
import os
import subprocess
import time
import queue
from concurrent.futures import ThreadPoolExecutor

SOURCES = [
    "https://raw.githubusercontent.com/0xRadikal/Free-v2ray-Configs/main/top100.txt",
    "https://raw.githubusercontent.com/mahdibland/ShadowsocksAggregator/master/Eternity",
    "https://raw.githubusercontent.com/pawelmalak/v2ray-configs/main/configs_base64.txt"
]

def decode_base64(data):
    data = data.strip()
    missing_padding = len(data) % 4
    if missing_padding:
        data += '=' * (4 - missing_padding)
    try: return base64.b64decode(data).decode('utf-8')
    except: return ""

def get_configs():
    configs = set()
    for url in SOURCES:
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=10) as response:
                text = response.read().decode('utf-8')
                if "://" not in text[:100]: text = decode_base64(text)
                for line in text.splitlines():
                    line = line.strip()
                    if line.startswith(("vmess://", "vless://", "trojan://")):
                        configs.add(line)
        except Exception as e: print(f"Error fetching {url}: {e}")
    return list(configs)

def parse_vmess(uri, local_port):
    try:
        data = json.loads(decode_base64(uri[8:]))
        outbound = {
            "protocol": "vmess",
            "settings": {
                "vnext": [{
                    "address": data.get("add", ""),
                    "port": int(data.get("port", 443)),
                    "users": [{"id": data.get("id", ""), "alterId": int(data.get("aid", 0)), "security": data.get("scy", "auto")}]
                }]
            },
            "streamSettings": {
                "network": data.get("net", "tcp"),
                "security": data.get("tls", "none")
            }
        }
        if data.get("net") == "ws":
            outbound["streamSettings"]["wsSettings"] = {"path": data.get("path", "/"), "headers": {"Host": data.get("host", "")}}
        elif data.get("net") == "grpc":
            outbound["streamSettings"]["grpcSettings"] = {"serviceName": data.get("path", ""), "multiMode": True}
        if data.get("tls") == "tls":
            outbound["streamSettings"]["tlsSettings"] = {"serverName": data.get("sni", data.get("host", "")), "allowInsecure": True}
        return create_full_json(outbound, local_port)
    except: return None

def parse_vless(uri, local_port):
    try:
        parsed = urllib.parse.urlparse(uri)
        params = urllib.parse.parse_qs(parsed.query)
        address = parsed.hostname
        outbound = {
            "protocol": "vless",
            "settings": {
                "vnext": [{
                    "address": address,
                    "port": parsed.port,
                    "users": [{"id": parsed.username, "encryption": params.get("encryption", ["none"])[0]}]
                }]
            },
            "streamSettings": {
                "network": params.get("type", ["tcp"])[0],
                "security": params.get("security", ["none"])[0]
            }
        }
        sec = params.get("security", ["none"])[0]
        if sec == "tls":
            outbound["streamSettings"]["tlsSettings"] = {"serverName": params.get("sni", [address])[0], "allowInsecure": True}
        elif sec == "reality":
            outbound["streamSettings"]["realitySettings"] = {
                "serverName": params.get("sni", [address])[0],
                "publicKey": params.get("pbk", [""])[0],
                "shortId": params.get("sid", [""])[0],
                "fingerprint": params.get("fp", ["chrome"])[0],
                "spiderX": params.get("spx", ["/"])[0]
            }
        net = params.get("type", ["tcp"])[0]
        if net == "ws":
            outbound["streamSettings"]["wsSettings"] = {"path": params.get("path", ["/"])[0], "headers": {"Host": params.get("host", [address])[0]}}
        elif net == "grpc":
            outbound["streamSettings"]["grpcSettings"] = {"serviceName": params.get("serviceName", [""])[0], "multiMode": True}
        return create_full_json(outbound, local_port)
    except: return None

def parse_trojan(uri, local_port):
    try:
        parsed = urllib.parse.urlparse(uri)
        params = urllib.parse.parse_qs(parsed.query)
        address = parsed.hostname
        outbound = {
            "protocol": "trojan",
            "settings": {
                "servers": [{"address": address, "port": parsed.port, "password": parsed.username}]
            },
            "streamSettings": {
                "network": params.get("type", ["tcp"])[0],
                "security": params.get("security", ["tls"])[0]
            }
        }
        if outbound["streamSettings"]["security"] == "tls":
            outbound["streamSettings"]["tlsSettings"] = {"serverName": params.get("sni", [address])[0], "allowInsecure": True}
        net = params.get("type", ["tcp"])[0]
        if net == "ws":
            outbound["streamSettings"]["wsSettings"] = {"path": params.get("path", ["/"])[0], "headers": {"Host": params.get("host", [address])[0]}}
        elif net == "grpc":
            outbound["streamSettings"]["grpcSettings"] = {"serviceName": params.get("serviceName", [""])[0], "multiMode": True}
        return create_full_json(outbound, local_port)
    except: return None

def create_full_json(outbound, local_port):
    return {
        "log": {"loglevel": "none"},
        "inbounds": [{
            "port": local_port,
            "listen": "127.0.0.1",
            "protocol": "socks",
            "settings": {"udp": True}
        }],
        "outbounds": [outbound]
    }

def test_with_xray(uri, port):
    if uri.startswith("vmess://"): config_json = parse_vmess(uri, port)
    elif uri.startswith("vless://"): config_json = parse_vless(uri, port)
    elif uri.startswith("trojan://"): config_json = parse_trojan(uri, port)
    else: return uri, float('inf')
    
    if not config_json: return uri, float('inf')
    
    config_file = f"config_{port}.json"
    with open(config_file, 'w') as f: json.dump(config_json, f)
        
    proc = subprocess.Popen(["./xray", "-c", config_file], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(1.0) # Increased to 1.0s to ensure Xray core fully initializes on GitHub servers before curling
    
    curl_cmd = [
        "curl", "-x", f"socks5h://127.0.0.1:{port}",
        "-s", "-o", "/dev/null", "-w", "%{time_total}",
        "-m", "5", "http://cp.cloudflare.com/generate_204" # Increased curl timeout to 5s to be safe
    ]
    
    latency = float('inf')
    try:
        res = subprocess.run(curl_cmd, capture_output=True, text=True, timeout=7)
        if res.returncode == 0: latency = float(res.stdout.strip())
    except: pass
    
    proc.terminate()
    proc.wait()
    try: os.remove(config_file)
    except: pass
    
    return uri, latency

def main():
    if not os.path.exists("./xray"):
        print("Xray core not found! Make sure GitHub Actions downloaded it.")
        return

    print("Fetching configs...")
    configs = get_configs()
    configs = configs[:300] # Limit to prevent timeouts
    print(f"Found {len(configs)} raw configs to test.")

    workers = 15
    port_queue = queue.Queue()
    for i in range(10000, 10000 + workers): port_queue.put(i)

    def worker_task(uri):
        port = port_queue.get()
        try: return test_with_xray(uri, port)
        finally: port_queue.put(port)

    print("Running REAL URL tests using Xray-core...")
    tested_configs = []
    with ThreadPoolExecutor(max_workers=workers) as executor:
        results = executor.map(worker_task, configs)
        for config, ping_time in results:
            if ping_time != float('inf'):
                tested_configs.append((config, ping_time))
                print(f"Success: {ping_time}s")

    tested_configs.sort(key=lambda x: x[1])
    top_30 = [c[0] for c in tested_configs[:30]]
    
    print(f"Saving top {len(top_30)} configs.")
    plain_text = "\n".join(top_30)
    with open("sub.txt", "w", encoding="utf-8") as f: f.write(plain_text)
    
    base64_text = base64.b64encode(plain_text.encode('utf-8')).decode('utf-8')
    with open("sub_base64.txt", "w", encoding="utf-8") as f: f.write(base64_text)
    print("Update Complete!")

if __name__ == "__main__": main()
