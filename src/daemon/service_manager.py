#!/usr/bin/env python3
"""
Cross-platform service management for codex-dreams daemon.
Handles installation, uninstallation, and management of system services.
"""

import logging
import os
import platform
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional

from .config import DaemonConfig, get_default_config_path, load_config


@dataclass
class ServiceManager:
    """Cross-platform service manager"""

    config: DaemonConfig

    def __post_init__(self):
        self.platform = platform.system().lower()
        self.logger = logging.getLogger("codex_dreams_service")

    @property
    def is_admin(self) -> bool:
        """Check if running with administrative privileges"""
        if self.platform == "windows":
            try:
                import ctypes

                return ctypes.windll.shell32.IsUserAnAdmin() != 0
            except:
                return False
        else:
            return os.geteuid() == 0

    def install(self, user_mode: bool = False) -> bool:
        """Install the daemon as a system service"""
        try:
            if self.platform == "windows":
                return self._install_windows_service(user_mode)
            elif self.platform == "darwin":
                return self._install_macos_service(user_mode)
            elif self.platform == "linux":
                return self._install_linux_service(user_mode)
            else:
                self.logger.error(f"Unsupported platform: {self.platform}")
                return False
        except Exception as e:
            self.logger.error(f"Failed to install service: {e}")
            return False

    def uninstall(self) -> bool:
        """Uninstall the daemon service"""
        try:
            if self.platform == "windows":
                return self._uninstall_windows_service()
            elif self.platform == "darwin":
                return self._uninstall_macos_service()
            elif self.platform == "linux":
                return self._uninstall_linux_service()
            else:
                self.logger.error(f"Unsupported platform: {self.platform}")
                return False
        except Exception as e:
            self.logger.error(f"Failed to uninstall service: {e}")
            return False

    def start(self) -> bool:
        """Start the daemon service"""
        try:
            if self.platform == "windows":
                return self._windows_service_action("start")
            elif self.platform == "darwin":
                return self._macos_service_action("load")
            elif self.platform == "linux":
                return self._linux_service_action("start")
            else:
                return False
        except Exception as e:
            self.logger.error(f"Failed to start service: {e}")
            return False

    def stop(self) -> bool:
        """Stop the daemon service"""
        try:
            if self.platform == "windows":
                return self._windows_service_action("stop")
            elif self.platform == "darwin":
                return self._macos_service_action("unload")
            elif self.platform == "linux":
                return self._linux_service_action("stop")
            else:
                return False
        except Exception as e:
            self.logger.error(f"Failed to stop service: {e}")
            return False

    def status(self) -> Dict[str, Any]:
        """Get service status information"""
        status_info = {
            "platform": self.platform,
            "service_name": self.config.service_name,
            "installed": False,
            "running": False,
            "enabled": False,
        }

        try:
            if self.platform == "windows":
                status_info.update(self._get_windows_status())
            elif self.platform == "darwin":
                status_info.update(self._get_macos_status())
            elif self.platform == "linux":
                status_info.update(self._get_linux_status())
        except Exception as e:
            self.logger.error(f"Failed to get service status: {e}")
            status_info["error"] = str(e)

        return status_info

    def _install_windows_service(self, user_mode: bool = False) -> bool:
        """Install Windows service using NSSM or PowerShell"""
        service_name = self.config.service_name

        # Try to use NSSM first (Non-Sucking Service Manager)
        if shutil.which("nssm"):
            return self._install_nssm_service(user_mode)
        else:
            # Fallback to PowerShell New-Service
            return self._install_powershell_service(user_mode)

    def _install_nssm_service(self, user_mode: bool) -> bool:
        """Install Windows service using NSSM"""
        service_name = self.config.service_name

        # Get the Python executable and script path
        python_exe = sys.executable
        script_path = Path(__file__).parent / "scheduler.py"

        commands = [
            ["nssm", "install", service_name, python_exe, str(script_path)],
            ["nssm", "set", service_name, "Description", self.config.service_description],
            ["nssm", "set", service_name, "Start", "SERVICE_AUTO_START"],
        ]

        # Add working directory if specified
        if self.config.working_directory:
            commands.append(
                ["nssm", "set", service_name, "AppDirectory", self.config.working_directory]
            )

        # Add environment file if specified
        if self.config.environment_file:
            commands.append(
                [
                    "nssm",
                    "set",
                    service_name,
                    "AppEnvironment",
                    f"CODEX_ENV_FILE={self.config.environment_file}",
                ]
            )

        for cmd in commands:
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                self.logger.error(f"NSSM command failed: {' '.join(cmd)}")
                self.logger.error(f"Error: {result.stderr}")
                return False

        self.logger.info(f"Successfully installed Windows service '{service_name}' using NSSM")
        return True

    def _install_powershell_service(self, user_mode: bool) -> bool:
        """Install Windows service using PowerShell"""
        service_name = self.config.service_name
        python_exe = sys.executable
        script_path = Path(__file__).parent / "scheduler.py"

        # PowerShell command to create service
        ps_cmd = f"""
        New-Service -Name "{service_name}" `
                   -BinaryPathName '"{python_exe}" "{script_path}" --daemon' `
                   -DisplayName "{service_name}" `
                   -Description "{self.config.service_description}" `
                   -StartupType Automatic
        """

        result = subprocess.run(["powershell", "-Command", ps_cmd], capture_output=True, text=True)

        if result.returncode == 0:
            self.logger.info(
                f"Successfully installed Windows service '{service_name}' using PowerShell"
            )
            return True
        else:
            self.logger.error(f"PowerShell service installation failed: {result.stderr}")
            return False

    def _install_macos_service(self, user_mode: bool) -> bool:
        """Install macOS service using launchd"""
        service_name = self.config.service_name

        # Choose appropriate directory
        if user_mode:
            plist_dir = Path.home() / "Library" / "LaunchAgents"
        else:
            plist_dir = Path("/Library/LaunchDaemons")

        plist_dir.mkdir(parents=True, exist_ok=True)
        plist_file = plist_dir / f"com.codex-dreams.{service_name}.plist"

        # Create launchd plist
        python_exe = sys.executable
        script_path = Path(__file__).parent / "scheduler.py"

        plist_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.codex-dreams.{service_name}</string>
    <key>ProgramArguments</key>
    <array>
        <string>{python_exe}</string>
        <string>{script_path}</string>
        <string>--daemon</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>{self.config.log_file or '/tmp/codex-dreams-daemon.log'}</string>
    <key>StandardErrorPath</key>
    <string>{self.config.log_file or '/tmp/codex-dreams-daemon.log'}</string>"""

        if self.config.working_directory:
            plist_content += f"""
    <key>WorkingDirectory</key>
    <string>{self.config.working_directory}</string>"""

        if self.config.environment_file:
            plist_content += f"""
    <key>EnvironmentVariables</key>
    <dict>
        <key>CODEX_ENV_FILE</key>
        <string>{self.config.environment_file}</string>
    </dict>"""

        plist_content += """
</dict>
</plist>"""

        # Write plist file
        with open(plist_file, "w") as f:
            f.write(plist_content)

        # Set appropriate permissions
        os.chmod(plist_file, 0o644)

        self.logger.info(f"Successfully installed macOS service '{service_name}' at {plist_file}")
        return True

    def _install_linux_service(self, user_mode: bool) -> bool:
        """Install Linux service using systemd"""
        service_name = self.config.service_name

        # Choose appropriate directory
        if user_mode:
            service_dir = Path.home() / ".config" / "systemd" / "user"
            service_dir.mkdir(parents=True, exist_ok=True)
        else:
            service_dir = Path("/etc/systemd/system")

        service_file = service_dir / f"{service_name}.service"

        # Create systemd service file
        python_exe = sys.executable
        script_path = Path(__file__).parent / "scheduler.py"

        service_content = f"""[Unit]
Description={self.config.service_description}
After=network.target
Wants=network.target

[Service]
Type=simple
ExecStart={python_exe} {script_path} --daemon
Restart=always
RestartSec=10
User={os.getenv('USER', 'root') if user_mode else 'root'}"""

        if self.config.working_directory:
            service_content += f"\nWorkingDirectory={self.config.working_directory}"

        if self.config.environment_file:
            service_content += f"\nEnvironmentFile={self.config.environment_file}"

        service_content += """

[Install]
WantedBy=multi-user.target
"""

        # Write service file
        with open(service_file, "w") as f:
            f.write(service_content)

        # Reload systemd and enable service
        if user_mode:
            subprocess.run(["systemctl", "--user", "daemon-reload"])
            subprocess.run(["systemctl", "--user", "enable", f"{service_name}.service"])
        else:
            subprocess.run(["systemctl", "daemon-reload"])
            subprocess.run(["systemctl", "enable", f"{service_name}.service"])

        self.logger.info(f"Successfully installed Linux service '{service_name}' at {service_file}")
        return True

    def _uninstall_windows_service(self) -> bool:
        """Uninstall Windows service"""
        service_name = self.config.service_name

        # Try NSSM first
        if shutil.which("nssm"):
            result = subprocess.run(
                ["nssm", "remove", service_name, "confirm"], capture_output=True, text=True
            )
        else:
            # Fallback to PowerShell
            result = subprocess.run(
                ["powershell", "-Command", f"Remove-Service -Name '{service_name}'"],
                capture_output=True,
                text=True,
            )

        success = result.returncode == 0
        if success:
            self.logger.info(f"Successfully uninstalled Windows service '{service_name}'")
        else:
            self.logger.error(f"Failed to uninstall Windows service: {result.stderr}")

        return success

    def _uninstall_macos_service(self) -> bool:
        """Uninstall macOS service"""
        service_name = self.config.service_name
        plist_name = f"com.codex-dreams.{service_name}"

        # Try to unload first
        subprocess.run(["launchctl", "unload", plist_name], capture_output=True)

        # Remove plist files
        plist_locations = [
            Path.home() / "Library" / "LaunchAgents" / f"{plist_name}.plist",
            Path("/Library/LaunchDaemons") / f"{plist_name}.plist",
        ]

        removed = False
        for plist_file in plist_locations:
            if plist_file.exists():
                plist_file.unlink()
                removed = True
                self.logger.info(f"Removed {plist_file}")

        if removed:
            self.logger.info(f"Successfully uninstalled macOS service '{service_name}'")

        return removed

    def _uninstall_linux_service(self) -> bool:
        """Uninstall Linux service"""
        service_name = self.config.service_name
        service_file = f"{service_name}.service"

        # Stop and disable service
        subprocess.run(["systemctl", "stop", service_file], capture_output=True)
        subprocess.run(["systemctl", "disable", service_file], capture_output=True)

        # Remove service files
        service_locations = [
            Path("/etc/systemd/system") / service_file,
            Path.home() / ".config" / "systemd" / "user" / service_file,
        ]

        removed = False
        for service_path in service_locations:
            if service_path.exists():
                service_path.unlink()
                removed = True
                self.logger.info(f"Removed {service_path}")

        if removed:
            # Reload systemd
            subprocess.run(["systemctl", "daemon-reload"], capture_output=True)
            self.logger.info(f"Successfully uninstalled Linux service '{service_name}'")

        return removed

    def _windows_service_action(self, action: str) -> bool:
        """Perform Windows service action"""
        service_name = self.config.service_name

        if shutil.which("nssm"):
            cmd = ["nssm", action, service_name]
        else:
            cmd = ["sc", action, service_name]

        result = subprocess.run(cmd, capture_output=True, text=True)
        return result.returncode == 0

    def _macos_service_action(self, action: str) -> bool:
        """Perform macOS service action"""
        service_name = self.config.service_name
        plist_name = f"com.codex-dreams.{service_name}"

        result = subprocess.run(["launchctl", action, plist_name], capture_output=True, text=True)
        return result.returncode == 0

    def _linux_service_action(self, action: str) -> bool:
        """Perform Linux service action"""
        service_name = self.config.service_name

        result = subprocess.run(
            ["systemctl", action, f"{service_name}.service"], capture_output=True, text=True
        )
        return result.returncode == 0

    def _get_windows_status(self) -> Dict[str, Any]:
        """Get Windows service status"""
        service_name = self.config.service_name
        status = {"installed": False, "running": False, "enabled": False}

        # Check if service exists
        result = subprocess.run(["sc", "query", service_name], capture_output=True, text=True)

        if result.returncode == 0:
            status["installed"] = True
            output = result.stdout.lower()
            status["running"] = "running" in output
            status["enabled"] = "auto_start" in output

        return status

    def _get_macos_status(self) -> Dict[str, Any]:
        """Get macOS service status"""
        service_name = self.config.service_name
        plist_name = f"com.codex-dreams.{service_name}"
        status = {"installed": False, "running": False, "enabled": False}

        # Check if plist file exists
        plist_locations = [
            Path.home() / "Library" / "LaunchAgents" / f"{plist_name}.plist",
            Path("/Library/LaunchDaemons") / f"{plist_name}.plist",
        ]

        status["installed"] = any(p.exists() for p in plist_locations)

        if status["installed"]:
            # Check if service is loaded
            result = subprocess.run(
                ["launchctl", "list", plist_name], capture_output=True, text=True
            )
            status["running"] = result.returncode == 0
            status["enabled"] = status["running"]  # If loaded, it's enabled

        return status

    def _get_linux_status(self) -> Dict[str, Any]:
        """Get Linux service status"""
        service_name = self.config.service_name
        service_file = f"{service_name}.service"
        status = {"installed": False, "running": False, "enabled": False}

        # Check if service file exists
        service_locations = [
            Path("/etc/systemd/system") / service_file,
            Path.home() / ".config" / "systemd" / "user" / service_file,
        ]

        status["installed"] = any(p.exists() for p in service_locations)

        if status["installed"]:
            # Check if service is running
            result = subprocess.run(
                ["systemctl", "is-active", service_file], capture_output=True, text=True
            )
            status["running"] = result.stdout.strip() == "active"

            # Check if service is enabled
            result = subprocess.run(
                ["systemctl", "is-enabled", service_file], capture_output=True, text=True
            )
            status["enabled"] = result.stdout.strip() == "enabled"

        return status


def main():
    """Main entry point for service management"""
    import argparse

    parser = argparse.ArgumentParser(description="Codex Dreams Service Manager")
    parser.add_argument(
        "action",
        choices=["install", "uninstall", "start", "stop", "status"],
        help="Service management action",
    )
    parser.add_argument(
        "--config", type=Path, default=get_default_config_path(), help="Configuration file path"
    )
    parser.add_argument(
        "--user", action="store_true", help="Install as user service (not system-wide)"
    )

    args = parser.parse_args()

    # Setup logging
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    # Load configuration
    config = load_config(args.config)

    # Create service manager
    service_manager = ServiceManager(config)

    # Perform requested action
    if args.action == "install":
        success = service_manager.install(user_mode=args.user)
        sys.exit(0 if success else 1)
    elif args.action == "uninstall":
        success = service_manager.uninstall()
        sys.exit(0 if success else 1)
    elif args.action == "start":
        success = service_manager.start()
        sys.exit(0 if success else 1)
    elif args.action == "stop":
        success = service_manager.stop()
        sys.exit(0 if success else 1)
    elif args.action == "status":
        status = service_manager.status()
        print(f"Service Status for '{config.service_name}':")
        for key, value in status.items():
            print(f"  {key}: {value}")


if __name__ == "__main__":
    main()
