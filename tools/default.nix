{ config, pkgs, ... }:
{
  imports = [ ./firefox.nix ];

  programs.mtr.enable = true;

  nixpkgs.config.allowUnfree = true;

  environment.systemPackages = with pkgs; [
    vscodium
    vim-full
    gitFull
    unzip

    discord

    pavucontrol

    nixfmt
  ];
}
