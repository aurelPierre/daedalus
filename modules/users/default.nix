{ config, pkgs, ... }:
{
  users.users.daedalus = {
    isNormalUser = true;
    extraGroups = [
      "wheel"
      "networkmanager"
    ];
  };
}
