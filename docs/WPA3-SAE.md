# Experimental native WPA3-Personal

The Sequoia and Tahoe native WCL frontend accepts SAE passphrases and delegates
authentication to shared net80211. Both RTW88 and RTW89 use the same implementation;
the HALs supply transport and software-key installation. Donor MLME code is not used.

Implemented scope:

- SAE group 19 (P-256), hunting-and-pecking and Hash-to-Element (H2E).
- Bounded anti-clogging token handling and cached confirm retransmission.
- SAE PMK/PMKID derivation, SHA-256 PTK derivation and AKM-defined EAPOL descriptor 0.
- AES-CMAC EAPOL MICs, AES key wrap, CCMP and BIP management-frame protection.
- Required management keys and authenticated AP RSNXE verification in message 3.
- Kernel randomness, private crypto symbols and credential/session wiping.

PMF connections initially use software CCMP/BIP. Their throughput must be measured
on hardware. Existing WPA2 connections without PMF retain hardware CCMP.
Mixed WPA2/WPA3 networks retain the existing WPA2 compatibility presentation.
This does not add 6 GHz, Wi-Fi 7, FT-SAE, SAE-PK, SAE extended keys or additional SAE
groups, and does not implement SAE credential delivery for the older Apple frontend.

Host tests cover two-party exchanges in both modes, wrong passwords, reflected and
malformed commits, unsupported groups, damaged/truncated confirms, request decoding,
known SHA-256/AES-CMAC/AES-wrap answers, and exponent/output aliasing used by H2E.
CI repeats these tests. A successful build and host tests do not establish device
interoperability: the Galaxy hotspot still needs an actual join, DHCP/data, reconnect,
sleep/wake and wrong-password test with the new native kext.

Crypto is adapted from the local Airport_RTW89 reference. Exact vendor revisions,
licenses and SHA-256 hashes are recorded in `rtw80211/sae/UPSTREAM.json` and the
vendor `UPSTREAM.md` files. Hostap SAE and Mbed TLS sources remain unmodified.
The Mbed TLS adapter uses a temporary for modular exponentiation because hostap
can alias its exponent with the output, which Mbed TLS does not preserve.
No passwords, PMKs, commits, confirms or key dumps are logged.

Build and test on macOS:

```sh
SAE_HOST_TEST=1 DERIVED_FILE_DIR="$PWD/build/tests/sae" bash scripts/build_sae_archive.sh
for test in sae_exchange_test sae_crypto_test; do
  cc -std=c11 -Wall -Wextra -Werror "tests/$test.c" build/tests/sae/librtw_sae.a -o "build/tests/$test"
  "build/tests/$test"
done
python3 tools/validate_sae_backend.py --archive build/tests/sae/librtw_sae.a
bash scripts/build_release_kexts.sh AirportRTW-Tahoe AirportRTW-Sequoia
```

Native controller diagnostics retain the last SAE attempt without key material:
`RTWSAEStage` is 1 (request), 2 (commit prepared), 3 (peer commit accepted),
4 (peer confirmed), 5 (EAPOL received), 6 (message 2 prepared), 7 (message 3
received), or 8 (port authorized). `RTWSAEError` is 1 (message 3 MIC),
2 (key-data decryption), 3 (RSNXE mismatch), 4 (required GTK/IGTK missing),
0x10000 plus a commit status, 0x20000 (confirm rejection), or 0x30000 plus a
four-way deauthentication reason. Zero means no recorded error; a stage alone
does not prove a transmitted frame reached the AP. Values persist across a
failed join and are reset when another SAE join begins.

The PTK known-answer test checks the production MAC/nonce ordering and SAE
48-byte SHA-256 derivation with its 22-byte label (no terminating NUL), plus
legacy WPA2 SHA-1 derivation with its NUL separator. These label formats differ.
