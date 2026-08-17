#!/bin/bash
# Cloudflare 隧道看门狗：检测到 Cloudflare 不可达时重启 cloudflared
CODE=$(curl -s -o /dev/null -w '%{http_code}' -m 8 https://api.cloudflare.com/client/v4/zones 2>/dev/null)
if [ "$CODE" != "401" ] && [ "$CODE" != "200" ]; then
    echo "$(date): Cloudflare 不可达 (code=$CODE)，重启 cloudflared"
    systemctl restart cloudflared
fi
