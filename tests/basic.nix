{ self, ... }:
{
  name = "daedalus-basic";

  nodes.machine = {
    imports = [
      self.nixosModules.daedalus
    ];

    virtualisation.memorySize = 2048;
  };

  testScript = ''
    machine.start()

    # 1. The system actually boots.
    machine.wait_for_unit("multi-user.target")

    # 2. Systemd considers the system healthy.
    machine.succeed("systemctl is-system-running --wait")

    # 3. The default user exits.
    machine.succeed("id daedalus")

    # 4. Networking is functionnal.
    machine.succeed("systemctl is-active NetworkManager")
    machine.succeed("ip link")

    # 5. Basic Nix functionality works.
    machine.succeed("nix --version")

    # 6. The expected hostname is applied.
    machine.succeed("hostname")
    machine.succeed("test \"$(hostname)\" = \"labyrinth\"")
  '';
}
