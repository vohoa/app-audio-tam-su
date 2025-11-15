#!/usr/bin/env python3
"""
Script to download proxy_ipv6.csv from remote server via SSH
Uses paramiko library for SSH/SCP connection
"""
import os
import sys
import getpass
from typing import Optional

try:
    import paramiko
    from scp import SCPClient
except ImportError:
    print("❌ Required libraries not installed!")
    print("Please install: pip install paramiko scp")
    sys.exit(1)


def download_file_via_ssh(
    host: str,
    username: str,
    password: str,
    remote_file_path: str,
    local_file_path: str,
    port: int = 22
) -> bool:
    """
    Download file from remote server via SSH/SCP

    Args:
        host: Server hostname or IP address
        username: SSH username
        password: SSH password
        remote_file_path: Path to file on remote server
        local_file_path: Path to save file locally
        port: SSH port (default: 22)

    Returns:
        bool: True if successful, False otherwise
    """
    ssh_client = None
    scp_client = None

    try:
        print(f"🔗 Connecting to {username}@{host}:{port}...")

        # Create SSH client
        ssh_client = paramiko.SSHClient()
        ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        # Connect to server
        ssh_client.connect(
            hostname=host,
            port=port,
            username=username,
            password=password,
            timeout=10
        )

        print(f"✅ Connected successfully!")

        # Check if remote file exists
        stdin, stdout, stderr = ssh_client.exec_command(f'test -f {remote_file_path} && echo "EXISTS"')
        result = stdout.read().decode().strip()

        if result != "EXISTS":
            print(f"❌ Remote file not found: {remote_file_path}")
            return False

        # Get file size
        stdin, stdout, stderr = ssh_client.exec_command(f'wc -c < {remote_file_path}')
        file_size = int(stdout.read().decode().strip())
        print(f"📁 File size: {file_size} bytes")

        # Create SCP client
        scp_client = SCPClient(ssh_client.get_transport())

        # Download file
        print(f"📥 Downloading {remote_file_path} -> {local_file_path}...")
        scp_client.get(remote_file_path, local_file_path)

        print(f"✅ Download completed!")

        # Verify local file
        if os.path.exists(local_file_path):
            local_size = os.path.getsize(local_file_path)
            print(f"✅ Local file created: {local_file_path} ({local_size} bytes)")

            # Count lines
            with open(local_file_path, 'r') as f:
                line_count = sum(1 for line in f)
            print(f"📊 Total proxies: {line_count}")

            return True
        else:
            print(f"❌ Local file not created")
            return False

    except paramiko.AuthenticationException:
        print(f"❌ Authentication failed! Invalid username or password")
        return False
    except paramiko.SSHException as e:
        print(f"❌ SSH error: {e}")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False
    finally:
        # Cleanup
        if scp_client:
            scp_client.close()
        if ssh_client:
            ssh_client.close()
        print(f"🔌 Connection closed")


def main():
    """Main function"""
    print("=" * 60)
    print("📡 Download Proxy List from Server")
    print("=" * 60)
    print()

    # Get server details
    print("Enter server details:")
    host = input("🖥️  Server IP/Hostname: ").strip()
    if not host:
        print("❌ Server hostname is required!")
        sys.exit(1)

    username = input("👤 Username: ").strip()
    if not username:
        print("❌ Username is required!")
        sys.exit(1)

    password = getpass.getpass("🔑 Password: ")
    if not password:
        print("❌ Password is required!")
        sys.exit(1)

    # SSH port
    port_input = input("🔌 SSH Port (default: 22): ").strip()
    port = int(port_input) if port_input else 22

    # Remote file path
    remote_file = input("📁 Remote file path (default: /root/proxy_ipv6.csv): ").strip()
    if not remote_file:
        remote_file = "/root/proxy_ipv6.csv"

    # Local file path
    current_dir = os.path.dirname(os.path.abspath(__file__))
    local_file = os.path.join(current_dir, "proxy_ipv6.csv")
    print(f"💾 Local save path: {local_file}")

    # Confirm
    print()
    print("📋 Configuration:")
    print(f"   Server: {username}@{host}:{port}")
    print(f"   Remote: {remote_file}")
    print(f"   Local:  {local_file}")
    print()

    confirm = input("Continue? (y/n): ").strip().lower()
    if confirm not in ['y', 'yes']:
        print("❌ Cancelled")
        sys.exit(0)

    print()
    print("=" * 60)

    # Download file
    success = download_file_via_ssh(
        host=host,
        username=username,
        password=password,
        remote_file_path=remote_file,
        local_file_path=local_file,
        port=port
    )

    print("=" * 60)

    if success:
        print("✅ SUCCESS! Proxy file downloaded")
        print()
        print("Next steps:")
        print("1. Run: python import_proxies.py proxy_ipv6.csv")
        print("2. Or use GUI: Menu -> 🌐 Proxy -> ⚙️ Quản Lý Proxy -> Import CSV")
        return 0
    else:
        print("❌ FAILED! Could not download file")
        return 1


if __name__ == "__main__":
    sys.exit(main())
