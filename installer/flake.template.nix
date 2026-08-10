{
  description = "Custom NixOS configuration";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-26.05";

    daedalus.url = "github:aurelPierre/daedalus";
    daedalus.inputs.nixpkgs.follows = "nixpkgs";
  };

  outputs =
    {
      self,
      nixpkgs,
      daedalus,
      ...
    }:
    {
      nixosConfigurations.local = nixpkgs.lib.nixosSystem {
        system = "x86_64-linux";

        modules = [
          daedalus.nixosModules.daedalus

          ./hardware-configuration.nix
          ./disk.nix
        ];
      };
    };
}
