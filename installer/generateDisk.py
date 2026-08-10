#!/usr/bin/env python3

import argparse
import json
import os
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path


# ============================================================================
# Exceptions
# ============================================================================


class ConfigurationError(Exception):
    pass


# ============================================================================
# Hardware model
# ============================================================================


@dataclass
class Disk:
    path: str
    name: str
    size: int
    model: str
    serial: str
    transport: str
    removable: bool
    by_id: str | None = None

    @property
    def size_gib(self) -> float:
        return self.size / (1024 ** 3)

    @property
    def description(self) -> str:
        parts = []

        if self.model:
            parts.append(self.model)

        if self.transport:
            parts.append(self.transport.upper())

        parts.append(f"{self.size_gib:.1f} GiB")

        return " — ".join(parts)


# ============================================================================
# Disk configuration model
# ============================================================================


@dataclass
class BootPartition:
    size: str = "1G"


@dataclass
class Mount:
    mountpoint: str
    mount_options: list[str] = field(default_factory=list)
    subvolume: str | None = None


@dataclass
class Filesystem:
    type: str
    mounts: list[Mount]


@dataclass
class DiskConfig:
    disk: Disk
    boot: BootPartition | None
    encrypted: bool
    filesystem: Filesystem
    luks_name: str | None = None


# ============================================================================
# Utilities
# ============================================================================


def run(*command: str) -> str:
    try:
        result = subprocess.run(
            command,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
    except FileNotFoundError as exc:
        raise ConfigurationError(
            f"Required command not found: {command[0]}"
        ) from exc

    return result.stdout


def nix_string(value: str) -> str:
    """
    Escape a Python string as a Nix double-quoted string.
    """

    return (
        '"'
        + value
        .replace("\\", "\\\\")
        .replace('"', '\\"')
        .replace("\n", "\\n")
        + '"'
    )


def format_options(options: list[str], indent: int) -> str:
    """
    Render a Nix list of strings.

    Example:

        mountOptions = [
          "noatime"
          "compress=zstd"
        ];
    """

    if not options:
        return ""

    spaces = " " * indent

    lines = [
        f"{spaces}mountOptions = [",
    ]

    for option in options:
        lines.append(
            f'{spaces}  {nix_string(option)}'
        )

    lines.append(f"{spaces}];")

    return "\n".join(lines)


def normalize_mountpoint(value: str) -> str:
    value = value.strip()

    if not value:
        raise ConfigurationError(
            "Mount point cannot be empty."
        )

    if not value.startswith("/"):
        raise ConfigurationError(
            f"Mount point must start with '/': {value}"
        )

    if value != "/" and value.endswith("/"):
        value = value.rstrip("/")

    return value


def parse_mount_options(value: str) -> list[str]:
    """
    Accept comma-separated mount options.

    Example:
        noatime,compress=zstd,ssd
    """

    if not value.strip():
        return []

    options = []

    for option in value.split(","):
        option = option.strip()

        if not option:
            continue

        if option not in options:
            options.append(option)

    return options


# ============================================================================
# Hardware discovery
# ============================================================================


def find_by_id(device: str) -> str | None:
    by_id = Path("/dev/disk/by-id")

    if not by_id.exists():
        return None

    real_device = os.path.realpath(device)

    candidates = []

    for path in sorted(by_id.iterdir()):
        if not path.is_symlink():
            continue

        try:
            if os.path.realpath(path) == real_device:
                candidates.append(str(path))
        except OSError:
            continue

    if not candidates:
        return None

    # Prefer IDs that are normally stable and human-readable.
    priorities = (
        "nvme-",
        "wwn-",
        "ata-",
        "scsi-",
        "usb-",
    )

    for prefix in priorities:
        for candidate in candidates:
            if f"/dev/disk/by-id/{prefix}" in candidate:
                return candidate

    return candidates[0]


def discover_disks() -> list[Disk]:
    output = run(
        "lsblk",
        "--json",
        "--bytes",
        "--paths",
        "-o",
        "NAME,PATH,TYPE,SIZE,MODEL,SERIAL,TRAN,RM",
    )

    try:
        data = json.loads(output)
    except json.JSONDecodeError as exc:
        raise ConfigurationError(
            "Could not parse lsblk output."
        ) from exc

    disks = []

    for item in data.get("blockdevices", []):
        if item.get("type") != "disk":
            continue

        path = item.get("path")

        if not path:
            continue

        try:
            size = int(item.get("size") or 0)
        except (TypeError, ValueError):
            size = 0

        disk = Disk(
            path=path,
            name=os.path.basename(path),
            size=size,
            model=(item.get("model") or "").strip(),
            serial=(item.get("serial") or "").strip(),
            transport=(item.get("tran") or "").strip(),
            removable=bool(item.get("rm")),
        )

        disk.by_id = find_by_id(path)

        disks.append(disk)

    return disks


# ============================================================================
# User interaction
# ============================================================================


def ask(
    prompt: str,
    default: str | None = None,
) -> str:
    suffix = f" [{default}]" if default is not None else ""

    while True:
        answer = input(f"{prompt}{suffix}: ").strip()

        if answer:
            return answer

        if default is not None:
            return default


def ask_yes_no(
    prompt: str,
    default: bool = False,
) -> bool:
    suffix = "[Y/n]" if default else "[y/N]"

    while True:
        answer = input(
            f"{prompt} {suffix}: "
        ).strip().lower()

        if not answer:
            return default

        if answer in ("y", "yes"):
            return True

        if answer in ("n", "no"):
            return False

        print("Please answer yes or no.")


def choose_from_list(
    title: str,
    choices: list[str],
    default: int | None = None,
) -> str:
    print()
    print(title)

    for index, choice in enumerate(choices, start=1):
        print(f"  {index}) {choice}")

    while True:
        suffix = (
            f" [{default}]"
            if default is not None
            else ""
        )

        answer = input(
            f"Select{suffix}: "
        ).strip()

        if not answer and default is not None:
            return choices[default - 1]

        try:
            index = int(answer)

            if 1 <= index <= len(choices):
                return choices[index - 1]

        except ValueError:
            pass

        print("Invalid selection.")


def choose_disk(
    disk: Disk,
    index: int,
    total: int,
) -> bool:
    print()
    print("────────────────────────────────────────")
    print(f"Disk {index}/{total}")
    print("────────────────────────────────────────")
    print(f"Device:     {disk.path}")
    print(f"Size:       {disk.size_gib:.1f} GiB")

    if disk.model:
        print(f"Model:      {disk.model}")

    if disk.serial:
        print(f"Serial:     {disk.serial}")

    if disk.transport:
        print(f"Transport:  {disk.transport.upper()}")

    if disk.removable:
        print("WARNING:    removable device")

    if disk.by_id:
        print(f"Stable ID:  {disk.by_id}")

    print()

    return ask_yes_no(
        "Include this disk in the configuration?",
        default=False,
    )


# ============================================================================
# Filesystem configuration
# ============================================================================


def configure_mount_options() -> list[str]:
    print()
    print(
        "Enter mount options separated by commas."
    )
    print(
        "Example: noatime,compress=zstd,ssd"
    )

    value = ask(
        "Mount options",
        "",
    )

    return parse_mount_options(value)


def configure_ext4_mount() -> Mount:
    print()
    print("Configure ext4 filesystem")

    mountpoint = normalize_mountpoint(
        ask("Mount point")
    )

    mount_options = configure_mount_options()

    return Mount(
        mountpoint=mountpoint,
        mount_options=mount_options,
    )


def configure_btrfs_subvolume() -> Mount:
    print()
    print("Configure btrfs subvolume")

    subvolume = ask(
        "Subvolume name",
        "@",
    )

    if not subvolume:
        raise ConfigurationError(
            "Subvolume name cannot be empty."
        )

    mountpoint = normalize_mountpoint(
        ask("Mount point")
    )

    mount_options = configure_mount_options()

    return Mount(
        mountpoint=mountpoint,
        mount_options=mount_options,
        subvolume=subvolume,
    )


def configure_btrfs_mounts() -> list[Mount]:
    mounts = []

    print()
    print("Configure btrfs subvolumes.")
    print(
        "Each subvolume can have its own mount point "
        "and mount options."
    )

    while True:
        mount = configure_btrfs_subvolume()

        if any(
            existing.mountpoint == mount.mountpoint
            for existing in mounts
        ):
            raise ConfigurationError(
                f"Duplicate mount point: "
                f"{mount.mountpoint}"
            )

        if any(
            existing.subvolume == mount.subvolume
            for existing in mounts
        ):
            raise ConfigurationError(
                f"Duplicate btrfs subvolume: "
                f"{mount.subvolume}"
            )

        mounts.append(mount)

        if not ask_yes_no(
            "Add another subvolume?",
            default=False,
        ):
            break

    return mounts


def configure_filesystem() -> Filesystem:
    filesystem_type = choose_from_list(
        "Filesystem type:",
        [
            "ext4",
            "btrfs",
        ],
        default=2,
    )

    if filesystem_type == "ext4":
        mounts = [
            configure_ext4_mount()
        ]
    else:
        mounts = configure_btrfs_mounts()

    return Filesystem(
        type=filesystem_type,
        mounts=mounts,
    )


# ============================================================================
# Disk configuration
# ============================================================================


def configure_disk(
    disk: Disk,
    boot_available: bool,
) -> tuple[DiskConfig, bool]:

    print()
    print("========================================")
    print(f"Configuring {disk.path}")
    print("========================================")

    boot = None

    if not boot_available:
        if ask_yes_no(
            "Create an EFI boot partition on this disk?",
            default=False,
        ):
            boot = BootPartition()
            boot_available = True

    encrypted = ask_yes_no(
        "Encrypt this disk's data partition with LUKS?",
        default=True,
    )

    filesystem = configure_filesystem()

    luks_name = None

    if encrypted:
        # Disko uses this name for the mapped LUKS device.
        # Make it unique per physical disk.
        safe_name = disk.name.replace("-", "_")
        luks_name = f"crypt_{safe_name}"

    return (
        DiskConfig(
            disk=disk,
            boot=boot,
            encrypted=encrypted,
            filesystem=filesystem,
            luks_name=luks_name,
        ),
        boot_available,
    )


# ============================================================================
# Validation
# ============================================================================


def validate_configuration(
    configs: list[DiskConfig],
) -> None:

    if not configs:
        raise ConfigurationError(
            "No disks were selected."
        )

    boot_count = sum(
        1 for config in configs
        if config.boot is not None
    )

    if boot_count == 0:
        raise ConfigurationError(
            "No EFI boot partition was configured."
        )

    if boot_count > 1:
        raise ConfigurationError(
            "Multiple EFI boot partitions are not "
            "currently supported by this generator."
        )

    mountpoints: dict[str, DiskConfig] = {}

    root_found = False

    for config in configs:
        filesystem = config.filesystem

        if not filesystem.mounts:
            raise ConfigurationError(
                f"{config.disk.path} has no mount points."
            )

        if filesystem.type == "ext4":
            if len(filesystem.mounts) != 1:
                raise ConfigurationError(
                    f"{config.disk.path}: ext4 supports "
                    "one mount point per filesystem."
                )

        for mount in filesystem.mounts:
            if mount.mountpoint in mountpoints:
                other = mountpoints[mount.mountpoint]

                raise ConfigurationError(
                    f"Duplicate mount point "
                    f"'{mount.mountpoint}' on "
                    f"{config.disk.path} and "
                    f"{other.disk.path}."
                )

            mountpoints[mount.mountpoint] = config

            if mount.mountpoint == "/":
                root_found = True

            if filesystem.type == "ext4":
                if mount.subvolume is not None:
                    raise ConfigurationError(
                        "ext4 mount cannot have a "
                        "subvolume."
                    )

            elif filesystem.type == "btrfs":
                if not mount.subvolume:
                    raise ConfigurationError(
                        f"Btrfs mount {mount.mountpoint} "
                        "has no subvolume name."
                    )

    if not root_found:
        raise ConfigurationError(
            "No root filesystem was configured. "
            "One mount point must be '/'."
        )

    boot_mountpoints = [
        mount.mountpoint
        for config in configs
        for mount in config.filesystem.mounts
    ]

    if "/boot" in boot_mountpoints:
        # /boot is allowed only when there is an ESP.
        boot_config = next(
            (
                config
                for config in configs
                if config.boot is not None
            ),
            None,
        )

        if boot_config is None:
            raise ConfigurationError(
                "/boot is configured but no EFI "
                "partition exists."
            )


# ============================================================================
# Nix rendering
# ============================================================================


def render_mount_options(
    options: list[str],
    indent: int,
) -> str:

    if not options:
        return ""

    return format_options(
        options,
        indent,
    )


def render_ext4(
    mount: Mount,
    indent: int,
) -> str:

    spaces = " " * indent

    lines = [
        f'{spaces}type = "filesystem";',
        f'{spaces}format = "ext4";',
        (
            f"{spaces}mountpoint = "
            f"{nix_string(mount.mountpoint)};"
        ),
    ]

    options = render_mount_options(
        mount.mount_options,
        indent,
    )

    if options:
        lines.append(options)

    return "\n".join(lines)


def render_btrfs(
    mounts: list[Mount],
    indent: int,
) -> str:

    spaces = " " * indent

    lines = [
        f'{spaces}type = "btrfs";',
        "",
        f"{spaces}subvolumes = {{",
    ]

    for mount in mounts:
        subvolume = mount.subvolume

        lines.extend(
            [
                f"{" " * (indent + 2)}"
                f"{nix_string(subvolume)} = {{",
                (
                    f"{" " * (indent + 4)}"
                    f"mountpoint = "
                    f"{nix_string(mount.mountpoint)};"
                ),
            ]
        )

        options = render_mount_options(
            mount.mount_options,
            indent + 4,
        )

        if options:
            lines.append(options)

        lines.append(
            f"{" " * (indent + 2)}}};"
        )

    lines.extend(
        [
            f"{spaces}}};",
        ]
    )

    return "\n".join(lines)


def render_filesystem_content(
    config: DiskConfig,
) -> str:

    filesystem = config.filesystem

    if filesystem.type == "ext4":
        content = render_ext4(
            filesystem.mounts[0],
            indent=16,
        )

    elif filesystem.type == "btrfs":
        content = render_btrfs(
            filesystem.mounts,
            indent=16,
        )

    else:
        raise ConfigurationError(
            f"Unsupported filesystem: "
            f"{filesystem.type}"
        )

    if not config.encrypted:
        return content

    spaces = " " * 16

    return "\n".join(
        [
            f'{spaces}type = "luks";',
            (
                f"{spaces}name = "
                f"{nix_string(config.luks_name)};"
            ),
            "",
            f"{spaces}settings = {{",
            f"{spaces}  allowDiscards = true;",
            f"{spaces}}};",
            "",
            f"{spaces}content = {{",
            content,
            f"{spaces}}};",
        ]
    )


def render_disk(
    config: DiskConfig,
) -> str:

    disk = config.disk

    device = disk.by_id or disk.path

    lines = [
        "      " + nix_string(disk.name) + " = {",
        '        type = "disk";',
        f"        device = {nix_string(device)};",
        "",
        "        content = {",
        '          type = "gpt";',
        "",
        "          partitions = {",
    ]

    if config.boot is not None:
        lines.extend(
            [
                "            ESP = {",
                f'              size = '
                f'{nix_string(config.boot.size)};',
                '              type = "EF00";',
                "",
                "              content = {",
                '                type = "filesystem";',
                '                format = "vfat";',
                '                mountpoint = "/boot";',
                "",
                "                mountOptions = [",
                '                  "umask=0077"',
                "                ];",
                "              };",
                "            };",
                "",
            ]
        )

    lines.extend(
        [
            "            data = {",
            '              size = "100%";',
            "",
            "              content = {",
        ]
    )

    filesystem_content = render_filesystem_content(
        config
    )

    # The renderer above uses 16-space indentation.
    # Here it belongs inside content at 16 spaces.
    lines.append(filesystem_content)

    lines.extend(
        [
            "              };",
            "            };",
            "          };",
            "        };",
            "      };",
            "",
        ]
    )

    return "\n".join(lines)


def render_config(
    configs: list[DiskConfig],
) -> str:

    lines = [
        "{",
        "  disko.devices = {",
        "    disk = {",
        "",
    ]

    for config in configs:
        lines.append(render_disk(config))

    lines.extend(
        [
            "    };",
            "  };",
            "}",
            "",
        ]
    )

    return "\n".join(lines)


# ============================================================================
# Summary
# ============================================================================


def print_summary(
    configs: list[DiskConfig],
) -> None:

    print()
    print()
    print("========================================")
    print("Disko configuration")
    print("========================================")

    for config in configs:
        disk = config.disk
        filesystem = config.filesystem

        print()
        print(
            f"{disk.path} "
            f"({disk.size_gib:.1f} GiB)"
        )

        if disk.by_id:
            print(f"  ID: {disk.by_id}")

        if config.boot:
            print(
                f"  EFI: {config.boot.size} → /boot"
            )

        encryption = (
            "LUKS"
            if config.encrypted
            else "unencrypted"
        )

        print(
            f"  {encryption} → "
            f"{filesystem.type}"
        )

        for mount in filesystem.mounts:
            if mount.subvolume:
                print(
                    f"    {mount.subvolume} "
                    f"→ {mount.mountpoint}"
                )
            else:
                print(
                    f"    {mount.mountpoint}"
                )

            if mount.mount_options:
                print(
                    "      options: "
                    + ", ".join(
                        mount.mount_options
                    )
                )

    print()


# ============================================================================
# Interactive generation
# ============================================================================


def interactive_generation() -> str:

    disks = discover_disks()

    if not disks:
        raise ConfigurationError(
            "No disks were detected."
        )

    print()
    print("========================================")
    print("Disko configuration generator")
    print("========================================")
    print()
    print(
        "Select the disks that should be included."
    )
    print(
        "The installer will not modify anything "
        "until Disko is explicitly invoked."
    )

    configs: list[DiskConfig] = []

    boot_available = False

    for index, disk in enumerate(disks, start=1):

        if not choose_disk(
            disk,
            index,
            len(disks),
        ):
            continue

        config, boot_available = configure_disk(
            disk,
            boot_available,
        )

        configs.append(config)

    validate_configuration(configs)

    print_summary(configs)

    if not ask_yes_no(
        "Generate this Disko configuration?",
        default=False,
    ):
        raise ConfigurationError(
            "Configuration cancelled."
        )

    return render_config(configs)


# ============================================================================
# CLI
# ============================================================================


def main() -> int:

    parser = argparse.ArgumentParser(
        description=(
            "Interactively generate a Disko "
            "configuration."
        )
    )

    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        help=(
            "Write the generated configuration "
            "to this file instead of stdout."
        ),
    )

    args = parser.parse_args()

    try:
        config = interactive_generation()

        if args.output:
            args.output.parent.mkdir(
                parents=True,
                exist_ok=True,
            )

            args.output.write_text(
                config,
                encoding="utf-8",
            )

            print(
                f"Disko configuration written to "
                f"{args.output}"
            )
        else:
            print(config)

        return 0

    except KeyboardInterrupt:
        print(
            "\nCancelled.",
            file=sys.stderr,
        )
        return 130

    except ConfigurationError as error:
        print(
            f"ERROR: {error}",
            file=sys.stderr,
        )
        return 1

    except Exception as error:
        print(
            f"UNEXPECTED ERROR: {error}",
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    sys.exit(main())