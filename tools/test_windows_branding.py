"""Check visible Windows branding without building the fbs installer."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INSTALLER = ROOT / "src" / "installer" / "windows" / "Installer.nsi"
BUILD_PYTHON = ROOT / "src" / "build" / "python"


def check_version_info_rewrite():
    import importlib.util

    module_path = BUILD_PYTHON / "build_impl" / "version_info.py"
    spec = importlib.util.spec_from_file_location("windows_version_info", module_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    brand_version_info = module.brand_version_info

    source = "\n".join((
        "StringStruct('FileDescription', 'fman')",
        "StringStruct('ProductName', 'fman')",
        "StringStruct('InternalName', 'fman')",
        "StringStruct('OriginalFilename', 'fman.exe')",
    ))
    branded = brand_version_info(source, "fman", "fman++")
    assert "StringStruct('FileDescription', 'fman++')" in branded
    assert "StringStruct('ProductName', 'fman++')" in branded
    assert "StringStruct('InternalName', 'fman')" in branded
    assert "StringStruct('OriginalFilename', 'fman.exe')" in branded


def check_version_info_wrapper_returns_path():
    # fbs passes the return value to PyInstaller as --version-file, so a
    # wrapper returning None crashes the freeze in subprocess.list2cmdline.
    import sys
    import tempfile

    sys.path.insert(0, str(BUILD_PYTHON))
    from build_impl import windows

    with tempfile.TemporaryDirectory() as temp_dir:
        version_info = Path(temp_dir) / "version_info.py"
        version_info.write_text("StringStruct('ProductName', 'fman')")
        windows._create_version_info = lambda: None
        windows.path = lambda _: str(version_info)
        windows.SETTINGS = {"app_name": "fman", "display_name": "fman++"}
        returned = windows._create_version_info_with_display_name()
    assert returned == str(version_info), returned


def check_installer():
    script = INSTALLER.read_text()
    for expected in (
        'Name "${display_name}"',
        (
            'MUI_WELCOMEPAGE_TEXT "This wizard will guide you through the '
            'installation of ${display_name}.'
        ),
        'MUI_FINISHPAGE_RUN_TEXT "Run ${display_name}"',
        'VIAddVersionKey "ProductName" "${display_name}"',
        'VIAddVersionKey "FileDescription" "${display_name}"',
        'CreateShortCut "$SMPROGRAMS\\${display_name}.lnk"',
        '"DisplayName" "${display_name}"',
        '!getdllversion "..\\${app_name}\\${app_name}.exe"',
        '"$InstDir\\${app_name}.exe"',
        '"$PROGRAMFILES\\${app_name}"',
        '"$LOCALAPPDATA\\${app_name}"',
        '"Software\\${app_name}"',
        'Uninstall\\${app_name}',
        'Delete "$SMPROGRAMS\\${app_name}.lnk"',
    ):
        assert expected in script, expected
    uninstall = script.split('Section "Uninstall"', 1)[1]
    assert 'Delete "$SMPROGRAMS\\${app_name}.lnk"' in uninstall
    assert 'Delete "$SMPROGRAMS\\${display_name}.lnk"' in uninstall

    install = script.split("Section\n", 1)[1].split("SectionEnd", 1)[0]
    assert 'Push "add"\n  Call UpdateUserPath' in install
    path_helper = script.split(
        "!macro DefineUpdateUserPath function", 1
    )[1].split("!macroend", 1)[0]
    assert 'StrCpy $0 "$InstDir\\bin"' in path_helper
    assert 'StrCpy $0 "$0;$InstDir\\bin"' in path_helper
    assert (
        '${un.WordReplace} "$0" ";$InstDir\\bin" "" "+" $0'
        in path_helper
    )
    assert '${un.WordReplace} "$0" "$InstDir\\bin;" "" "+" $0' in path_helper
    assert '${un.WordReplace} "$0" "$InstDir\\bin" "" "+" $0' in path_helper
    assert 'WriteRegExpandStr HKCU "Environment" "Path"' in script
    assert (
        'SendMessage ${HWND_BROADCAST} ${WM_SETTINGCHANGE} 0 "STR:Environment"'
        in script
    )
    assert 'DetailPrint "User PATH is too long' in script
    assert 'IntOp $2 ${NSIS_MAX_STRLEN} - 100' in script
    assert 'IntCmp $1 $2 path_too_long path_safe path_too_long' in script
    assert 'WordReplace}' in script
    assert '!insertmacro WordReplace' in script
    assert '!insertmacro un.WordReplace' in script
    assert 'ReadRegStr $0 HKCU "Environment" "Path"' in script
    assert 'Push "remove"\n  Call un.UpdateUserPath' in uninstall


def main():
    check_installer()
    check_version_info_rewrite()
    check_version_info_wrapper_returns_path()


if __name__ == "__main__":
    main()
