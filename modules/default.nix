{ config, pkgs, ... }:
{
  imports = [
    ./filesystems
    ./gui
    ./security
    ./tools
    ./network
    ./users
    ./audio
    ./localization
  ];

  # potential fix for igc pcie disconnect
  #boot.kernelParams = [
  #  "pcie_ports=native"
  #];

  nixpkgs.config.allowUnfree = true;

  nix.settings.experimental-features = [
    "nix-command"
    "flakes"
  ];

  system.stateVersion = "26.05";
}
