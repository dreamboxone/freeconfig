import urllib.request
import base64
import json
import re

# منابعی که توسط بات‌های داخل ایران تست شده‌اند (به ترتیب اولویت)
SOURCES = [
    "https://raw.githubusercontent.com/0xRadikal/Free-v2ray-Configs/main/top100.txt",
    "https://raw.githubusercontent.com/yebekhe/TelegramV2rayCollector/main/sub/normal/mix",
    "https://raw.githubusercontent.com/mahdibland/ShadowsocksAggregator/master/Eternity"
]

def decode_base64(data):
    data = data.strip()
    missing_padding = len(data) % 4
    if missing_padding:
        data += '=' * (4 - missing_padding)
    try: return base64.b64decode(data).decode('utf-8')
    except: return ""

def get_configs():
    configs = []
    seen = set()
    for url in SOURCES:
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=10) as response:
                text = response.read().decode('utf-8')
                if "://" not in text[:100]: text = decode_base64(text)
                for line in text.splitlines():
                    line = line.strip()
                    if line.startswith(("vmess://", "vless://", "trojan://", "ss://", "hysteria2://", "tuic://")):
                        # استخراج بخش اصلی کانفیگ برای جلوگیری از تکراری بودن با نام‌های مختلف
                        core_config = line.split('#')[0] if '#' in line else line
                        if core_config not in seen:
                            seen.add(core_config)
                            configs.append(line)
        except Exception as e: print(f"Error fetching {url}: {e}")
    return configs

def main():
    print("Fetching pre-tested configs for Iran...")
    configs = get_configs()
    print(f"Found {len(configs)} unique configs.")

    # از آنجا که منابع از قبل بر اساس کیفیت در ایران مرتب شده‌اند، 
    # ما مستقیما 30 تای اول را که بهترین‌ها هستند انتخاب می‌کنیم.
    top_30 = configs[:30]
    
    print(f"Saving top {len(top_30)} configs.")
    plain_text = "\n".join(top_30)
    
    with open("sub.txt", "w", encoding="utf-8") as f: f.write(plain_text)
    
    base64_text = base64.b64encode(plain_text.encode('utf-8')).decode('utf-8')
    with open("sub_base64.txt", "w", encoding="utf-8") as f: f.write(base64_text)
    print("Update Complete!")

if __name__ == "__main__": main()
