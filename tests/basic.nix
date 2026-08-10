{
  name = "daedalus-basic";

  nodes.machine = { ... }: {
    imports = [
      ../default.nix
    ];

    users.users.test = {
      isNormalUser = true;
      password = "test";
    };

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
