{ pkgs, config, ... }:
{
  imports = [
    ./sway-config.nix
  ];

  fonts = {
    packages = with pkgs; [
      source-code-pro
      font-awesome
      font-awesome_4
      dejavu_fonts
      hack-font
      powerline-fonts
      roboto
      roboto-slab
      fira-code
      fira-code-symbols
    ];
    fontconfig = {
      enable = true;
      defaultFonts = {
        monospace = [
          "Source Code Pro for Powerline"
          "Roboto Mono for Powerline"
        ];
        sansSerif = [ "Roboto" ];
        serif = [ "Roboto Slab" ];
      };
    };
  };

  environment.systemPackages = with pkgs; [
    grim
    slurp
    wl-clipboard
    mako
    #swaylock
    wofi
    i3status-rust
    networkmanagerapplet
    alacritty
  ];

  programs.gnupg.agent.pinentryPackage = pkgs.pinentry-curses;
  programs.nm-applet.enable = true;

  services.gnome.gnome-keyring.enable = true;

  programs.sway = {
    enable = true;
    wrapperFeatures.gtk = true;
  };

  services.greetd = {
    enable = true;
    settings = {
      default_session = {
        command = "${pkgs.tuigreet}/bin/tuigreet --time --cmd sway";
        user = "greeter";
      };
    };
  };
}
