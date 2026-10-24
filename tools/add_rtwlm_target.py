#!/usr/bin/env python3
"""Add the rtwlm kext target (itlwm-compatible ethernet frontend) to AirportRTW.xcodeproj.

Clones the AirportRTW-Ventura target wiring, replaces the IO80211Family
frontend sources with the RTWCore/ItlNetworkUserClient ethernet stack and
points the product at rtw/rtwlm-Info.plist (IOClass=itlwm, no dependency on
com.apple.iokit.IO80211Family, so it loads on Sequoia/Tahoe without AMFIPass).

Build file IDs are fresh (one PBXBuildFile per phase, like Xcode does);
file references are shared with the existing targets. IDs are deterministic
(sha1 of "rtwlm:<label>"), so the script is idempotent and reviewable.
"""
from hashlib import sha1
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT / "AirportRTW.xcodeproj" / "project.pbxproj"

VENTURA_SOURCES_PHASE = "F8AE6509285471560085B4CF"
ARCHIVE_PHASE = "A89C00012F00000000000001"
FW_GEN_TARGET = "5066D63825287F7900EE6F38"
CONTAINER_PORTAL = "024A07A323FCBC3C009FBA6C"
RTW_GROUP = "024A07AE23FCBC3C009FBA6C"
PRODUCTS_GROUP = "024A07AD23FCBC3C009FBA6C"

# IO80211Family frontend files compiled by AirportRTW-* targets; the ethernet
# kext must not contain them (they pull in the closed IO80211Family SPI).
DROP_SOURCES = {
    "AirportRTW.cpp",
    "AirportRTWInterface.cpp",
    "AirportSTAIOCTL.cpp",
    "AirportVirtualIOCTL.cpp",
    "AirportAWDL.cpp",
}
# Ethernet frontend: itlwm skeleton (RTWCore + pm), HeliPort user client and
# the itlwm-named subclass that HeliPort's ClientKit looks for.
ETHERNET_SOURCES = ["RTWCore.cpp", "pm.cpp", "ItlNetworkUserClient.cpp", "itlwm.cpp"]
EXTRA_REFS = {
    "itlwm.cpp": "sourcecode.cpp.cpp",
    "itlhdr.h": "sourcecode.c.h",
    "rtwlm-Info.plist": "text.plist.xml",
}


def ident(label: str) -> str:
    return sha1(("rtwlm:" + label).encode()).hexdigest()[:24].upper()


def insert_before(text: str, marker: str, block: str) -> str:
    if marker not in text:
        sys.exit("marker not found: %s" % marker)
    return text.replace(marker, block + marker, 1)


def main() -> None:
    text = PROJECT.read_text(encoding="utf8")
    if "/* rtwlm */" in text:
        sys.exit("rtwlm target already present; nothing to do")

    # Map source name -> (PBXBuildFile id, fileRef id) from the existing
    # "in Sources" build file entries.
    by_name = {}
    for bid, name, ref in re.findall(
        r"([0-9A-F]{24}) /\* (.+?) in Sources \*/ = \{isa = PBXBuildFile; "
        r"fileRef = ([0-9A-F]{24})",
        text,
    ):
        by_name.setdefault(name, (bid, ref))

    # Source list: Ventura's set minus the Airport frontend, plus ethernet.
    m = re.search(
        r"%s /\* Sources \*/ = \{.*?files = \((.*?)\);" % VENTURA_SOURCES_PHASE,
        text,
        re.S,
    )
    if not m:
        sys.exit("Ventura Sources phase not found")
    ventura_names = [
        n for _, n in re.findall(r"([0-9A-F]{24}) /\* (.+?) in Sources \*/", m.group(1))
    ]
    # skip empty names and dangling build files (comment "(null)")
    kept = [
        n
        for n in ventura_names
        if n and n not in DROP_SOURCES and n != "(null)"
    ]
    sources = kept + [s for s in ETHERNET_SOURCES if s not in kept]
    missing = [s for s in sources if s not in by_name and s != "itlwm.cpp"]
    if missing:
        sys.exit("no PBXBuildFile/fileRef for: %s" % missing)

    tgt = ident("target:rtwlm")
    cfglist = ident("configlist:rtwlm")
    cfg_debug = ident("config:rtwlm:Debug")
    cfg_release = ident("config:rtwlm:Release")
    ph_headers = ident("phase:headers")
    ph_sources = ident("phase:sources")
    ph_frameworks = ident("phase:frameworks")
    ph_resources = ident("phase:resources")
    ph_archive = ident("phase:archive")
    proxy = ident("proxy:fw_gen")
    dep = ident("dep:fw_gen")
    prod_ref = ident("fileref:rtwlm.kext")

    build_settings = """\t\t\t\tbuildSettings = {
\t\t\t\t\tCONFIGURATION_BUILD_DIR = "$(SYMROOT)/$(CONFIGURATION)/rtwlm";
\t\t\t\t\tCURRENT_PROJECT_VERSION = "$(MODULE_VERSION)";
\t\t\t\t\tGCC_PRECOMPILE_PREFIX_HEADER = NO;
\t\t\t\t\tGCC_PREFIX_HEADER = rtw/PrivateSPI.pch;
\t\t\t\t\tGCC_PREPROCESSOR_DEFINITIONS = (
\t\t\t\t\t\t__PRIVATE_SPI__,
\t\t\t\t\t\t"$(inherited)",
\t\t\t\t\t);
\t\t\t\t\tINFOPLIST_FILE = rtw/rtwlm-Info.plist;
\t\t\t\t\tLIBRARY_SEARCH_PATHS = (
\t\t\t\t\t\t"$(PROJECT_DIR)/rtw80211",
\t\t\t\t\t\t"$(inherited)",
\t\t\t\t\t\t"$(PROJECT_DIR)/rtw80211/openbsd",
\t\t\t\t\t\t"$(PROJECT_DIR)/rtw80211/linux",
\t\t\t\t\t\t"$(PROJECT_DIR)/MacKernelSDK/Library/x86_64",
\t\t\t\t\t);
\t\t\t\t\tMACOSX_DEPLOYMENT_TARGET = 10.15;
\t\t\t\t\tMODULE_VERSION = 2.1.0;
\t\t\t\t\tMODULE_NAME = com.zxystd.rtwlm;
\t\t\t\t\tOTHER_LDFLAGS = (
\t\t\t\t\t\t"$(inherited)",
\t\t\t\t\t\t"$(DERIVED_FILE_DIR)/librtw89_c.a",
\t\t\t\t\t);
\t\t\t\t\tPRODUCT_BUNDLE_IDENTIFIER = com.zxystd.rtwlm;
\t\t\t\t\tPRODUCT_NAME = rtwlm;
\t\t\t\t\tSYSTEM_HEADER_SEARCH_PATHS = "rtw80211/openbsd rtw80211 include rtw/hal_rtw89 rtw/hal_rtw89/compat rtw/hal_rtw89/driver";
\t\t\t\t\tWRAPPER_EXTENSION = kext;
\t\t\t\t};"""

    # --- PBXBuildFile entries (fresh ids, shared fileRefs) ---
    bf_lines = []
    for name in sources:
        if name == "itlwm.cpp":
            ref = ident("fileref:itlwm.cpp")
        else:
            ref = by_name[name][1]
        bf_lines.append(
            "\t\t%s /* %s in Sources */ = {isa = PBXBuildFile; fileRef = %s /* %s */; };"
            % (ident("buildfile:%s" % name), name, ref, name)
        )
    text = insert_before(
        text, "/* End PBXBuildFile section */", "\n".join(bf_lines) + "\n"
    )

    # --- PBXFileReference entries ---
    fr_lines = [
        "\t\t%s /* rtwlm.kext */ = {isa = PBXFileReference; explicitFileType = wrapper.cfbundle; includeInIndex = 0; path = rtwlm.kext; sourceTree = BUILT_PRODUCTS_DIR; };"
        % prod_ref
    ]
    for name, ftype in EXTRA_REFS.items():
        fr_lines.append(
            "\t\t%s /* %s */ = {isa = PBXFileReference; lastKnownFileType = %s; path = %s; sourceTree = \"<group>\"; };"
            % (ident("fileref:%s" % name), name, ftype, name)
        )
    text = insert_before(
        text, "/* End PBXFileReference section */", "\n".join(fr_lines) + "\n"
    )

    # --- group children ---
    anchor = "\t\t\t\t024A07B123FCBC3C009FBA6C /* RTWCore.cpp */,\n"
    if anchor not in text:
        sys.exit("RTWCore.cpp group child not found")
    add = anchor + "".join(
        "\t\t\t\t%s /* %s */,\n" % (ident("fileref:%s" % n), n) for n in EXTRA_REFS
    )
    text = text.replace(anchor, add, 1)

    anchor = "\t\t\t\t024A07AC23FCBC3C009FBA6C /* RTWCore.kext */,\n"
    if anchor not in text:
        sys.exit("Products group anchor not found")
    text = text.replace(
        anchor, anchor + "\t\t\t\t%s /* rtwlm.kext */,\n" % prod_ref, 1
    )

    # --- build phases ---
    ph_headers_block = (
        "\t\t%s /* Headers */ = {\n\t\t\tisa = PBXHeadersBuildPhase;\n\t\t\tbuildActionMask = 2147483647;\n\t\t\tfiles = (\n\t\t\t);\n\t\t\trunOnlyForDeploymentPostprocessing = 0;\n\t\t};\n"
        % ph_headers
    )
    ph_frameworks_block = (
        "\t\t%s /* Frameworks */ = {\n\t\t\tisa = PBXFrameworksBuildPhase;\n\t\t\tbuildActionMask = 2147483647;\n\t\t\tfiles = (\n\t\t\t);\n\t\t\trunOnlyForDeploymentPostprocessing = 0;\n\t\t};\n"
        % ph_frameworks
    )
    ph_resources_block = (
        "\t\t%s /* Resources */ = {\n\t\t\tisa = PBXResourcesBuildPhase;\n\t\t\tbuildActionMask = 2147483647;\n\t\t\tfiles = (\n\t\t\t);\n\t\t\trunOnlyForDeploymentPostprocessing = 0;\n\t\t};\n"
        % ph_resources
    )
    files_list = "".join(
        "\t\t\t\t%s /* %s in Sources */,\n" % (ident("buildfile:%s" % n), n)
        for n in sources
    )
    ph_sources_block = (
        "\t\t%s /* Sources */ = {\n\t\t\tisa = PBXSourcesBuildPhase;\n\t\t\tbuildActionMask = 2147483647;\n\t\t\tfiles = (\n%s\t\t\t);\n\t\t\trunOnlyForDeploymentPostprocessing = 0;\n\t\t};\n"
        % (ph_sources, files_list)
    )
    m = re.search(
        r"\t\t%s /\* Build RTW89 C Archive \*/ = \{.*?\n\t\t\};\n" % ARCHIVE_PHASE,
        text,
        re.S,
    )
    if not m:
        sys.exit("archive phase not found")
    ph_archive_block = m.group(0).replace(ARCHIVE_PHASE, ph_archive, 1)

    text = insert_before(text, "/* End PBXHeadersBuildPhase section */", ph_headers_block)
    text = insert_before(text, "/* End PBXFrameworksBuildPhase section */", ph_frameworks_block)
    text = insert_before(text, "/* End PBXResourcesBuildPhase section */", ph_resources_block)
    text = insert_before(text, "/* End PBXSourcesBuildPhase section */", ph_sources_block)
    text = insert_before(text, "/* End PBXShellScriptBuildPhase section */", ph_archive_block)

    # --- dependency on fw_gen (firmware headers must exist first) ---
    proxy_block = (
        "\t\t%s /* PBXContainerItemProxy */ = {\n\t\t\tisa = PBXContainerItemProxy;\n\t\t\tcontainerPortal = %s /* Project object */;\n\t\t\tproxyType = 1;\n\t\t\tremoteGlobalIDString = %s;\n\t\t\tremoteInfo = fw_gen;\n\t\t};\n"
        % (proxy, CONTAINER_PORTAL, FW_GEN_TARGET)
    )
    dep_block = (
        "\t\t%s /* PBXTargetDependency */ = {\n\t\t\tisa = PBXTargetDependency;\n\t\t\ttarget = %s /* fw_gen */;\n\t\t\ttargetProxy = %s /* PBXContainerItemProxy */;\n\t\t};\n"
        % (dep, FW_GEN_TARGET, proxy)
    )
    text = insert_before(text, "/* End PBXContainerItemProxy section */", proxy_block)
    text = insert_before(text, "/* End PBXTargetDependency section */", dep_block)

    # --- native target ---
    target_block = (
        "\t\t%s /* rtwlm */ = {\n"
        "\t\t\tisa = PBXNativeTarget;\n"
        "\t\t\tbuildConfigurationList = %s /* Build configuration list for PBXNativeTarget \"rtwlm\" */;\n"
        "\t\t\tbuildPhases = (\n"
        "\t\t\t\t%s /* Headers */,\n"
        "\t\t\t\t%s /* Build RTW89 C Archive */,\n"
        "\t\t\t\t%s /* Sources */,\n"
        "\t\t\t\t%s /* Frameworks */,\n"
        "\t\t\t\t%s /* Resources */,\n"
        "\t\t\t);\n"
        "\t\t\tbuildRules = (\n"
        "\t\t\t);\n"
        "\t\t\tdependencies = (\n"
        "\t\t\t\t%s /* PBXTargetDependency */,\n"
        "\t\t\t);\n"
        "\t\t\tname = rtwlm;\n"
        "\t\t\tproductName = rtwlm;\n"
        "\t\t\tproductReference = %s /* rtwlm.kext */;\n"
        "\t\t\tproductType = \"com.apple.product-type.kernel-extension\";\n"
        "\t\t};\n"
        % (tgt, cfglist, ph_headers, ph_archive, ph_sources, ph_frameworks, ph_resources, dep, prod_ref)
    )
    text = insert_before(text, "/* End PBXNativeTarget section */", target_block)

    # --- configurations ---
    for cfg_id, cfg_name in ((cfg_debug, "Debug"), (cfg_release, "Release")):
        block = "\t\t%s /* %s */ = {\n\t\t\tisa = XCBuildConfiguration;\n%s\n\t\t\tname = %s;\n\t\t};\n" % (
            cfg_id,
            cfg_name,
            build_settings,
            cfg_name,
        )
        text = insert_before(text, "/* End XCBuildConfiguration section */", block)
    cfglist_block = (
        "\t\t%s /* Build configuration list for PBXNativeTarget \"rtwlm\" */ = {\n"
        "\t\t\tisa = XCConfigurationList;\n"
        "\t\t\tbuildConfigurations = (\n"
        "\t\t\t\t%s /* Debug */,\n"
        "\t\t\t\t%s /* Release */,\n"
        "\t\t\t);\n"
        "\t\t\tdefaultConfigurationIsVisible = 0;\n"
        "\t\t\tdefaultConfigurationName = Release;\n"
        "\t\t};\n" % (cfglist, cfg_debug, cfg_release)
    )
    text = insert_before(text, "/* End XCConfigurationList section */", cfglist_block)

    # --- register in PBXProject targets ---
    m = re.search(r"(\t\t\ttargets = \(\n)(.*?)(\n\t\t\t\);)", text, re.S)
    if not m:
        sys.exit("PBXProject targets list not found")
    text = text[: m.start(3)] + "\n\t\t\t\t%s /* rtwlm */," % tgt + text[m.start(3) :]

    PROJECT.write_text(text, encoding="utf8", newline="\n")
    print("rtwlm target added: %d sources (%d kept from Ventura + %s)"
          % (len(sources), len(kept), "+".join(ETHERNET_SOURCES)))


if __name__ == "__main__":
    main()
