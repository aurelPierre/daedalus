{ config, lib, ... }:
let
  inherit (lib) mkOption types;
  cfg = config.daedalus.localization;
in
{
  options.daedalus.localization = {
    timeZone = mkOption {
      type = types.str;
      default = "Europe/Paris";
      description = "System time zone.";
    };

    language = mkOption {
      type = types.str;
      default = "en_US.UTF-8";
      description = "Default system locale.";
    };

    region = mkOption {
      type = types.str;
      default = "fr_FR.UTF-8";
      description = "Locale used for regional formatting.";
    };

    keyboardLayout = mkOption {
      type = types.str;
      default = "us";
      description = "Linux console keyboard layout.";
    };
  };

  config = {
    time.timeZone = cfg.timeZone;

    i18n.defaultLocale = cfg.language;
    i18n.extraLocaleSettings = {
      LC_ADDRESS = cfg.region;
      LC_IDENTIFICATION = cfg.region;
      LC_MEASUREMENT = cfg.region;
      LC_MONETARY = cfg.region;
      LC_NAME = cfg.region;
      LC_NUMERIC = cfg.region;
      LC_PAPER = cfg.region;
      LC_TELEPHONE = cfg.region;
      LC_TIME = cfg.region;
    };

    console.keyMap = cfg.keyboardLayout;
  };
}
