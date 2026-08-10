{ config, lib, ... }:
let
  inherit (lib)
    mkOption
    types
    mkIf
    mkMerge
    ;
  cfg = config.daedalus.security;
in
{
  options.daedalus.security = {
    level = mkOption {
      type = types.enum [
        "minimal"
        "intermediate"
        "advanced"
      ];
      default = "minimal";
      description = ''
        Security hardening level.

        minimal:
          Basic security defaults with maximum compatibility.

        intermediate:
          Additional kernel, networking and filesystem hardening
          intended for general-purpose workstations.

        advanced:
          Aggressive hardening that may reduce performance or
          compatibility.
      '';
    };
  };

  config = mkMerge [
    (mkIf (cfg.level == "intermediate" || cfg.level == "advanced") {
      # R8 ANSSI
      boot.kernelParams = [
        "l1tf=full,force"
        "page_poison=on"
        "pti=on"
        "slab_nomerge=yes"
        "slub_debug=FZP"
        "spec_store_bypass_disable=seccomp"
        "spectre_v2=on"
        "mds=full,nosmt"
        "mce=0"
        "page_alloc.shuffle=1"
        "rng_core.default_quality=500"
      ];

      boot.kernel.sysctl = {
        # R9 ANSSI
        "kernel.dmesg_restrict" = "1";
        "kernel.kptr_restrict" = "2";
        "kernel.pid_max" = "1048576";
        "kernel.perf_cpu_time_max_percent" = "1";
        "kernel.perf_event_max_sample_rate" = "1";
        "kernel.perf_event_paranoid" = "2";
        "kernel.randomize_va_space" = "2";
        "kernel.sysrq" = "0";
        "kernel.unprivileged_bpf_disabled" = "1";
        "kernel.panic_on_oops" = "1";

        # R11 ANSSI
        "kernel.yama.ptrace_scope" = "1";

        # R12 ANSSI
        "net.core.bpf_jit_harden" = "2";
        "net.ipv4.ip_forward" = "0";
        "net.ipv4.conf.all.accept_local" = "0";
        "net.ipv4.conf.all.accept_redirects" = "0";
        "net.ipv4.conf.default.accept_redirects" = "0";
        "net.ipv4.conf.all.secure_redirects" = "0";
        "net.ipv4.conf.default.secure_redirects" = "0";
        "net.ipv4.conf.all.shared_media" = "0";
        "net.ipv4.conf.default.shared_media" = "0";
        "net.ipv4.conf.all.arp_filter" = "1";
        "net.ipv4.conf.all.arp_ignore" = "2";
        "net.ipv4.conf.all.route_localnet" = "0";
        "net.ipv4.conf.all.drop_gratuitous_arp" = "1";
        "net.ipv4.conf.default.rp_filter" = "1";
        "net.ipv4.conf.all.rp_filter" = "1";
        "net.ipv4.conf.default.send_redirects" = "0";
        "net.ipv4.conf.all.send_redirects" = "0";
        "net.ipv4.icmp_ignore_bogus_error_responses" = "1";
        "net.ipv4.ip_local_port_range" = "32768 65535";
        "net.ipv4.tcp_rfc1337" = "1";
        "net.ipv4.tcp_syncookies" = "1";

        # R13 ANSSI
        "net.ipv6.conf.default.disable_ipv6" = "1";
        "net.ipv6.conf.all.disable_ipv6" = "1";

        # R14 ANSSI
        "fs.suid_dumpable" = "0";
        "fs.protected_fifos" = "2";
        "fs.protected_regular" = "2";
        "fs.protected_symlinks" = "1";
        "fs.protected_hardlinks" = "1";
      };
    })

    (mkIf (cfg.level == "advanced") {
      #advanced
    })
  ];
}
