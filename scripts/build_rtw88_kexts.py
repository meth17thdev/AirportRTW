#!/usr/bin/env python3
"""Build isolated RTW88 variants using the shared native frontend's Xcode recipe.

The ordinary RTW89 build supplies generated headers, response files and the
link recipe. All source objects are then recompiled for RTW88 into a separate
output tree; no RTW89 hardware archive is linked into the RTW88 bundle.
"""
import argparse
import json
import os
from pathlib import Path
import plistlib
import shlex
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]
HAL = ROOT / 'rtw/hal_rtw88'
SDK = Path(subprocess.check_output(['xcrun', '--show-sdk-path'], text=True).strip())

def run(args, **kwargs):
    subprocess.run([str(x) for x in args], cwd=ROOT, check=True, **kwargs)

def build(platform, incremental=False):
    target = 'AirportRTW-' + platform
    objdir = ROOT / f'build/releases-obj/AirportRTW.build/Release/{target}.build/Objects-normal/x86_64'
    recipes = sorted((ROOT/'build/releases-obj/XCBuildData').glob('*.xcbuilddata/manifest.json'), key=lambda p:p.stat().st_mtime, reverse=True)
    link = None
    for recipe in recipes:
        for command in json.loads(recipe.read_text()).get('commands', {}).values():
            if command.get('description', '').startswith('Ld ') and f'/Release/{platform}/AirportRTW.kext/' in command['description'] and 'args' in command:
                link = command['args']
                break
        if link: break
    if not link or not list(objdir.glob('*common-args.resp')):
        raise SystemExit('First run: bash scripts/build_release_kexts.sh ' + target)
    dest = ROOT / f'build/rtw88/Release/{platform}'
    objects = ROOT / f'build/rtw88/objects/{platform}'
    objects.mkdir(parents=True, exist_ok=True)
    response = next(objdir.glob('*common-args.resp')).read_text()
    response = response.replace('rtw/hal_rtw89', 'rtw/hal_rtw88')
    response_file = objects/'common-args.resp'
    response_file.write_text(response)
    triple = link[link.index('-target')+1]
    base_list = Path(link[link.index('-filelist')+1])
    new_list = []
    header_roots = [HAL, ROOT/'rtw80211', ROOT/'include', ROOT/'AirportRTW']
    newest_header = max(p.stat().st_mtime for base in header_roots
                        for p in base.rglob('*') if p.suffix in {'.h', '.hpp', '.pch'})
    for old_object in base_list.read_text().splitlines():
        old_object = Path(old_object)
        dep = old_object.with_suffix('.d')
        if not dep.exists():
            # Xcode's generated kmod metadata object has no source dependency file.
            if old_object.name != 'AirportRTW_info.o':
                raise SystemExit('Missing dependency file: ' + str(dep))
            new_list.append(str(old_object))
            continue
        dependencies = shlex.split(dep.read_text().replace('\\\n', ' '))
        source = next((Path(x) for x in dependencies if x.endswith(('.c', '.cpp', '.cc')) and Path(x).is_file()), None)
        if source is None: raise SystemExit('No source in ' + str(dep))
        source = Path(str(source).replace('rtw/hal_rtw89', 'rtw/hal_rtw88'))
        if source.name == 'RTWCore.cpp': source = source.with_name('RTW88Core.cpp')
        source = Path(str(source).replace('Rtw89', 'Rtw88'))
        output = objects/old_object.name
        if incremental and output.exists() and output.stat().st_mtime >= max(source.stat().st_mtime, newest_header):
            new_list.append(str(output))
            continue
        print('CXX', platform, source.relative_to(ROOT), flush=True)
        run(['xcrun', 'clang++', '@'+str(response_file), '-target', triple, '-isysroot', SDK,
             '-fmodules-cache-path='+str(objects/'module-cache'), '-include', ROOT/'rtw/PrivateSPI.pch',
             '-x', 'c++', '-c', source, '-o', output])
        new_list.append(str(output))
    new_filelist = objects/'AirportRTW.LinkFileList'
    new_filelist.write_text('\n'.join(new_list)+'\n')
    bundle = dest/'AirportRTW.kext'
    if bundle.exists(): shutil.rmtree(bundle)
    shutil.copytree(ROOT/f'build/releases/Release/{platform}/AirportRTW.kext', bundle)
    resources = bundle/'Contents/Resources'
    resources.mkdir(exist_ok=True)
    shutil.copyfile(HAL/'firmware/LICENCE.rtlwifi_firmware.txt', resources/'LICENCE.rtlwifi_firmware.txt')
    plist_path = bundle/'Contents/Info.plist'
    plist = plistlib.loads(plist_path.read_bytes())
    for personality in plist['IOKitPersonalities'].values():
        if 'IOPCIMatch' in personality:
            personality['IOPCIMatch'] = '0xc82210ec 0xc82f10ec 0xb82210ec 0xc82110ec 0xb82110ec'
    plist_path.write_bytes(plistlib.dumps(plist))
    for i, arg in enumerate(link):
        if arg == str(base_list): link[i] = str(new_filelist)
        elif arg.endswith('/DerivedSources/librtw89_c.a'): link[i] = str(ROOT/'build/rtw88/archive/librtw88_c.a')
        elif '/Contents/MacOS/AirportRTW' in arg: link[i] = str(bundle/'Contents/MacOS/AirportRTW')
        elif arg.endswith(('_dependency_info.dat', '_lto.o')): link[i] = str(objects/Path(arg).name)
    print('LD', platform, flush=True)
    run(link)
    run(['plutil', '-lint', plist_path])
    unresolved = subprocess.check_output(['nm', '-u', str(bundle/'Contents/MacOS/AirportRTW')], text=True)
    if any(line.strip().startswith(('_rtw', '_airportrtw88')) for line in unresolved.splitlines()):
        raise SystemExit('Unresolved RTW88 backend symbols:\n'+unresolved)
    archive = dest/f'AirportRTW88-{platform}.zip'
    run(['ditto', '-c', '-k', '--keepParent', bundle, archive])
    print('RTW88 bundle:', bundle, flush=True)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('platforms', nargs='*', choices=['Tahoe', 'Sequoia'])
    parser.add_argument('--incremental', action='store_true', help='Reuse native objects newer than their source and project headers')
    options = parser.parse_args()
    archive_dir = ROOT/'build/rtw88/archive'
    env = dict(os.environ, DERIVED_FILE_DIR=str(archive_dir), SDKROOT=str(SDK))
    run(['bash', ROOT/'scripts/build_rtw88_c_archive.sh'], env=env)
    for platform in options.platforms or ['Tahoe', 'Sequoia']: build(platform, options.incremental)
