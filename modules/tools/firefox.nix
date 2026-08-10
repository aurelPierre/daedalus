{
  config,
  pkgs,
  lib,
  ...
}:
let
  inherit (lib) listToAttrs;
in
{
  programs.firefox = {
    enable = true;
    languagePacks = [
      "en-US"
    ];

    nativeMessagingHosts.packages = [ pkgs.tridactyl-native ];

    policies = {
      Homepage = {
        URL = "http://127.0.0.1:8082";
        StartPage = "homepage";
      };

      DisableProfileImport = true;
      NoDefaultBookmarks = true;
      NewTabPage = false;

      PasswordManagerEnabled = false;
      OfferToSaveLogins = false;

      DontCheckDefaultBrowser = true;
      AppAutoUpdate = false;
      DisableAppUpdate = true;

      EncryptedMediaExtensions = {
        Enabled = lib.mkDefault false;
      };

      ExtensionSettings =
        let
          extension = shortId: uuid: {
            name = uuid;
            value = {
              install_url = "https://addons.mozilla.org/en-US/firefox/downloads/latest/${shortId}/latest.xpi";
              installation_mode = "normal_installed";
            };
          };
        in
        {
          "*".installation_mode = "blocked";
        }
        // (listToAttrs [
          (extension "ublock-origin" "uBlock0@raymondhill.net")
        ]);

      DisablePocket = true;
      DisableFirefoxAccounts = true;
      DisableTelemetry = true;
      DisableFirefoxStudies = true;

      UserMessaging = {
        ExtensionRecommendations = false;
        UrlbarInterventions = false;
        MoreFromMozilla = false;
        FirefoxLabs = false;
        Locked = false;
      };

      SearchEngines = {
        Default = "Qwant";
        Remove = [
          "Google"
        ];
        PreventInstalls = true;
      };
    };

    # Let the user override the default.
    preferencesStatus = "default";

    preferences = {
      "privacy.globalprivacycontrol.enabled" = true;
    };
  };
}
