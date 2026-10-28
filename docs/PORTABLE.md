# Portable fman++ for Windows

The portable Windows release is a zip you can extract and run without installing
fman++. It keeps its settings, plugins and other profile data in a `Data` folder
beside `fman.exe`.

## Start a portable copy

Download `fmanPortable.zip` from the [fman++ GitHub Releases](https://github.com/BenjaminKobjolke/fman/releases)
page and extract it to a folder you can write to, such as a folder on a USB
drive. Open the extracted `fman++` folder and run `fman.exe`. fman creates the
`Data` folder there when needed.

The included `portable.txt` file marks the folder as portable. Keep it beside
`fman.exe` to use the local `Data` profile. Delete the marker to use the normal
Windows profile in `%APPDATA%\fman` instead; deleting the marker does not delete
the existing `Data` folder. `FMAN_DATA_DIRECTORY`, when set by a launcher,
takes precedence over both locations.

The portable folder must allow fman to create and remove files. If it is read-only
or in a protected location such as `C:\Program Files`, fman shows an error and
does not start. Move or extract the folder somewhere writable.

## Updates and multiple copies

In a portable copy, **Check for updates** downloads the new `fmanPortable.zip`.
After you confirm, fman closes and a helper replaces the program files, keeps
the `Data` folder and files stored beside the program, then starts the updated
copy. Leave the folder in place until the update finishes. Installed copies
continue to use the installer update flow.

A portable copy and an installed copy can run at the same time. They use separate
profiles, so plugins and settings in one do not affect the other.

Most profile data moves with the portable folder. Some plugins store absolute
paths in their own data; those paths will not follow the folder if the drive
letter changes. Update those plugin paths after moving the copy to a drive with a
different letter.
