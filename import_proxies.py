#!/usr/bin/env python3
"""
Script to import proxies from CSV file to ProxyManager
"""
import os
import sys
from proxy_manager import ProxyManager

def main():
    # Get CSV file path
    if len(sys.argv) > 1:
        csv_file = sys.argv[1]
    else:
        csv_file = os.path.join(os.path.dirname(__file__), 'proxy_ipv6.csv')

    if not os.path.exists(csv_file):
        print(f"❌ CSV file not found: {csv_file}")
        print(f"Usage: python import_proxies.py [csv_file_path]")
        sys.exit(1)

    print(f"📥 Importing proxies from: {csv_file}")

    # Create ProxyManager
    proxy_manager = ProxyManager()

    # Import from CSV
    success, error = proxy_manager.import_from_csv(csv_file)

    print(f"\n✅ Import completed:")
    print(f"   Success: {success} proxies")
    print(f"   Errors: {error}")
    print(f"   Total proxies: {proxy_manager.get_proxy_count()}")

    # Display sample proxies
    print(f"\n📋 Sample proxies:")
    for i in range(min(5, proxy_manager.get_proxy_count())):
        proxy = proxy_manager.get_proxy(i)
        if proxy:
            print(f"   {i+1}. {proxy.get_proxy_url()}")

    if proxy_manager.get_proxy_count() > 5:
        print(f"   ... and {proxy_manager.get_proxy_count() - 5} more")

    print(f"\n💾 Proxies saved to: {proxy_manager.proxy_file_path}")

if __name__ == "__main__":
    main()
