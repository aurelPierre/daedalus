{
  description = "Custom NixOS configuration";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-26.05";

    disko.url = "github:nix-community/disko";
    disko.inputs.nixpkgs.follows = "nixpkgs";

    daedalus.url = "github:aurelPierre/daedalus";
    daedalus.inputs.nixpkgs.follows = "nixpkgs";
};

  outputs =
    {
      self,
      nixpkgs,
      disko
      daedalus,
      ...
    }:
    {
      nixosConfigurations.local = nixpkgs.lib.nixosSystem {
        system = "x86_64-linux";

        modules = [
          disko.nixosModules.disko
          daedalus.nixosModules.daedalus

          ./hardware-configuration.nix
          ./disk.nix
        ];
      };
    };
}
