{
  description = "Custom NixOS configuration";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-26.05";

    disko.url = "github:nix-community/disko";
    disko.inputs.nixpkgs.follows = "nixpkgs";

    lanzaboote.url = "github:nix-community/lanzaboote";
    lanzaboote.inputs.nixpkgs.follows = "nixpkgs";
  };

  outputs =
    {
      self,
      nixpkgs,
      disko,
      lanzaboote,
      ...
    }:
    let
      system = "x86_64-linux";

      pkgs = import nixpkgs {
        inherit system;
      };

      install = pkgs.writeShellApplication {
        name = "install";

        runtimeInputs = [
          disko.packages.${system}.default
          pkgs.python3
          pkgs.sbctl
        ];

        text = ''
          set -euo pipefail

          echo "[DDL] Generating disk configuration..."

          ${./installer/generateDisk.py} --output /tmp/disk.nix

          echo "[DDL] Formatting and mounting disks..."

          disko --mode destroy,format,mount /tmp/disk.nix

          echo "[DDL] Generating hardware configuration..."

          nixos-generate-config --no-filesystems --root /mnt
          mv /tmp/disk.nix /mnt/etc/nixos

          echo "[DDL] Creating local flake..."

          cp ${./installer/flake.template.nix} /mnt/etc/nixos/flake.nix
          nix flake lock /mnt/etc/nixos --extra-experimental-features "nix-command flakes"

          echo "[DDL] Set secure boot keys..."

          sbctl create-keys
          sbctl enroll-keys --yes-this-might-brick-my-machine
          mv /var/lib/sbctl/ /mnt/etc/secureboot

          echo "[DDL] Installing..."

          nixos-install --root /mnt --flake /mnt/etc/nixos#local

          echo "[DDL] Set user password..."

          nixos-enter -c 'passwd daedalus'
        '';
      };
    in
    {
      nixosConfigurations.test = nixpkgs.lib.nixosSystem {
        inherit system;

        modules = [
          self.nixosModules.daedalus
        ];
      };

      nixosModules.daedalus = {
        imports = [
          lanzaboote.nixosModules.lanzaboote
          ./modules
        ];
      };

      apps.${system}.install = {
        type = "app";
        program = "${install}/bin/install";
      };

      checks.${system}.daedalus = self.nixosConfigurations.test.config.system.build.toplevel;
      formatter.${system} = nixpkgs.legacyPackages.${system}.nixfmt-tree;

      nixosTests.basic = pkgs.testers.runNixOSTest (
        import ./tests/basic.nix {
          inherit self;
        }
      );

    };
}
