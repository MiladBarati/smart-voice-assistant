import argparse
import sys
import time

import pjsua2 as pj


def pump(ep: pj.Endpoint) -> None:
    try:
        ep.libHandleEvents(50)
    except Exception as e:
        print("***events:", e)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--user", required=True)
    ap.add_argument("--password", required=True)
    ap.add_argument("--domain", required=True)
    ap.add_argument("--auth-user", default=None)
    ap.add_argument("--transport", choices=["udp", "tcp", "tls"], default="udp")
    ap.add_argument("--local-port", type=int, default=5070)
    ap.add_argument("--wait", type=int, default=10)
    args = ap.parse_args()

    ep = pj.Endpoint()
    ep.libCreate()
    ep_cfg = pj.EpConfig()
    ep_cfg.logConfig.level = 4
    ep.libInit(ep_cfg)

    tp = pj.TransportConfig()
    tp.port = args.local_port
    tmap = {
        "udp": pj.PJSIP_TRANSPORT_UDP,
        "tcp": pj.PJSIP_TRANSPORT_TCP,
        "tls": pj.PJSIP_TRANSPORT_TLS,
    }
    ep.transportCreate(tmap[args.transport], tp)
    ep.libStart()

    acfg = pj.AccountConfig()
    acfg.idUri = f"sip:{args.user}@{args.domain}"
    acfg.regConfig.registrarUri = f"sip:{args.domain}"

    # single, stable Contact: no SIP Outbound, no ICE, keepalives ON
    try:
        acfg.natConfig.sipOutboundUse = pj.PJSUA_SIP_OUTBOUND_DISABLED
    except AttributeError:
        # some bindings expose it as integer; 0 == DISABLED
        acfg.natConfig.sipOutboundUse = 0

    # Also disable Contact/Via rewrite heuristics that can change the Contact mid-flight
    try:
        acfg.natConfig.contactRewriteUse = pj.PJSUA_CONTACT_REWRITE_USE_DISABLED
        acfg.natConfig.viaRewriteUse = pj.PJSUA_VIA_REWRITE_USE_DISABLED
    except AttributeError:
        # fallbacks if your binding exposes them as ints
        acfg.natConfig.contactRewriteUse = 0
        acfg.natConfig.viaRewriteUse = 0

    # Do NOT force using the local source port in Contact
    try:
        acfg.natConfig.contactUseSrcPort = False
    except AttributeError:
        pass

    acfg.sipConfig.authCreds.append(
        pj.AuthCredInfo(
            "digest",
            "*",
            args.auth_user or args.user,
            0,
            args.password,
        )
    )

    # Note: We don't subclass `pj.Account` here; polling `getInfo()` is enough
    # for this MWE and keeps test mocking straightforward.
    acc = pj.Account()
    acc.create(acfg)

    # Wait for registration with event pumping
    deadline = time.time() + args.wait
    registration_succeeded = False
    while time.time() < deadline:
        pump(ep)
        info = acc.getInfo()
        # Accept any 2xx status code as success (200, 201, 202, etc.)
        if info.regIsActive and 200 <= info.regStatus < 300:
            print("***Registered successfully")
            registration_succeeded = True
            break

    # Capture final info before destroying endpoint (account becomes invalid
    # after libDestroy)
    final_info = acc.getInfo()
    final_reg_status = final_info.regStatus
    final_reg_active = final_info.regIsActive

    # stay a bit to let Asterisk create/qualify contact
    end = time.time() + 5
    while time.time() < end:
        pump(ep)

    ep.libDestroy()
    if not registration_succeeded:
        print(
            f"***Registration failed: status={final_reg_status}, "
            f"active={final_reg_active}"
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
