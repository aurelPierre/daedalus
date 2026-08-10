{ config, pkgs, ... }:
{
  boot.initrd.systemd.enable = true;

  boot.loader.systemd-boot.enable = false;

  boot.lanzaboote = {
    enable = true;
    pkiBundle = "/etc/secureboot";
  };

  environment.systemPackages = [ pkgs.sbctl ];
}
