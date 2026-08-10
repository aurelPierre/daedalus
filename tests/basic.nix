{
  name = "daedalus-basic";

  nodes.machine = { pkgs, ... }: {
    imports = [
      ../default.nix
    ];

    networking.hostName = "daedalus-test";

    users.users.test = {
      isNormalUser = true;
      password = "test";
    };

    nix.settings.experimental-features = [
      "nix-command"
      "flakes"
    ];

    virtualisation.memorySize = 2048;
  };

  testScript = ''
    machine.start()

    machine.wait_for_unit("multi-user.target")

    machine.succeed("systemctl is-system-running --wait")

    machine.succeed("id test")

    machine.succeed("systemctl is-active NetworkManager")

    machine.succeed("systemctl is-active polkit")
  '';
}
