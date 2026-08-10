{
  config,
  pkgs,
  lib,
  ...
}:
{
  imports = [ ./firefox.nix ];

  programs.mtr.enable = true;

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
