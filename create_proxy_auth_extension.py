#!/usr/bin/env python3
"""
Create Chrome extension for proxy authentication
"""
import os
import zipfile
import json


def create_proxy_auth_extension(proxy_host: str, proxy_port: str,
                                proxy_username: str, proxy_password: str,
                                output_dir: str = None, protocol: str = 'http') -> str:
    """
    Create a Chrome extension to handle proxy authentication

    Args:
        proxy_host: Proxy hostname/IP
        proxy_port: Proxy port
        proxy_username: Proxy username
        proxy_password: Proxy password
        output_dir: Output directory (default: chrome_extensions)

    Returns:
        str: Path to the created extension zip file
    """
    if output_dir is None:
        output_dir = os.path.join(os.path.dirname(__file__), 'chrome_extensions')

    os.makedirs(output_dir, exist_ok=True)

    # Extension manifest
    manifest_json = {
        "version": "1.0.0",
        "manifest_version": 2,
        "name": "Proxy Auth Extension",
        "permissions": [
            "proxy",
            "tabs",
            "unlimitedStorage",
            "storage",
            "<all_urls>",
            "webRequest",
            "webRequestBlocking"
        ],
        "background": {
            "scripts": ["background.js"]
        },
        "minimum_chrome_version": "22.0.0"
    }

    # Determine proxy scheme based on protocol
    proxy_scheme = "socks5" if protocol.lower() in ['socks5', 'socks'] else "http"

    # Background script - Only handle authentication, don't set proxy
    background_js = f"""
// Log when extension starts
console.log("Proxy Auth Extension loaded");
console.log("Protocol: {proxy_scheme}");
console.log("Proxy: {proxy_host}:{proxy_port}");
console.log("Username: {proxy_username}");

// Only handle proxy authentication when requested
function callbackFn(details) {{
    console.log("Proxy auth requested for:", details.url);
    return {{
        authCredentials: {{
            username: "{proxy_username}",
            password: "{proxy_password}"
        }}
    }};
}}

chrome.webRequest.onAuthRequired.addListener(
    callbackFn,
    {{urls: ["<all_urls>"]}},
    ['blocking']
);
"""

    # Create extension directory
    extension_dir = os.path.join(output_dir, 'proxy_auth_extension')
    os.makedirs(extension_dir, exist_ok=True)

    # Write manifest.json
    manifest_path = os.path.join(extension_dir, 'manifest.json')
    with open(manifest_path, 'w') as f:
        json.dump(manifest_json, f, indent=2)

    # Write background.js
    background_path = os.path.join(extension_dir, 'background.js')
    with open(background_path, 'w') as f:
        f.write(background_js)

    # Create zip file
    zip_path = os.path.join(output_dir, 'proxy_auth_extension.zip')
    with zipfile.ZipFile(zip_path, 'w') as zipf:
        zipf.write(manifest_path, 'manifest.json')
        zipf.write(background_path, 'background.js')

    print(f"✅ Created proxy auth extension: {extension_dir}")
    print(f"✅ Created extension zip: {zip_path}")

    return extension_dir


if __name__ == "__main__":
    # Test
    extension_path = create_proxy_auth_extension(
        proxy_host="45.32.122.119",
        proxy_port="10000",
        proxy_username="proxy1",
        proxy_password="123"
    )
    print(f"Extension created at: {extension_path}")
