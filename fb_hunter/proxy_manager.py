import os, platform, subprocess, requests
from typing import Tuple
from .config import ProxyConfig

class ProxyManager:
    @staticmethod
    def read_system_proxy() -> ProxyConfig:
        # env first
        for key in ("HTTPS_PROXY","https_proxy","HTTP_PROXY","http_proxy"):
            val = os.environ.get(key)
            if val and "://" in val and ":" in val.split("://",1)[1]:
                scheme, rest = val.split("://",1)
                host, port = rest.split(":")
                mode = "http" if scheme.startswith("http") else "socks5"
                return ProxyConfig(mode, host.strip("/"), int(port.strip("/")))
        sysname = platform.system().lower()
        try:
            if sysname == "windows":
                import winreg
                path = r"Software\Microsoft\Windows\CurrentVersion\Internet Settings"
                with winreg.OpenKey(winreg.HKEY_CURRENT_USER, path) as k:
                    enabled,_ = winreg.QueryValueEx(k, "ProxyEnable")
                    server,_ = winreg.QueryValueEx(k, "ProxyServer")
                    if enabled and server:
                        parts = dict(s.split("=",1) if "=" in s else ("http",s) for s in server.split(";") if s)
                        target = parts.get("https") or parts.get("http")
                        if target and ":" in target:
                            host, port = target.split(":",1)
                            return ProxyConfig("http", host, int(port))
            elif sysname == "darwin":
                out = subprocess.check_output(
                    ["sh","-lc","networksetup -listallnetworkservices | tail -n +2 | while read s; do networksetup -getsecurewebproxy \"$s\"; done"],
                    stderr=subprocess.DEVNULL, text=True
                )
                blocks = out.strip().split("\n\n")
                for b in blocks:
                    if "Enabled: Yes" in b:
                        lines = dict(l.split(": ",1) for l in b.splitlines() if ": " in l)
                        host = lines.get("Server") or ""
                        port = int(lines.get("Port") or 0)
                        if host and port:
                            return ProxyConfig("http", host, port)
        except Exception:
            pass
        return ProxyConfig("none","",0)

    @staticmethod
    def test_connectivity(proxy: ProxyConfig, test_url: str = "https://httpbin.org/ip", timeout: int = 6) -> Tuple[bool,str]:
        try:
            proxies = {"http": proxy.server(), "https": proxy.server()} if proxy.server() else None
            r = requests.get(test_url, timeout=timeout, proxies=proxies)
            return (r.status_code == 200, f"HTTP {r.status_code}")
        except Exception as e:
            return (False, str(e))
