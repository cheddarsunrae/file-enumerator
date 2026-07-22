Name:           file-enumerator
Version:        1.1.1
Release:        1%{?dist}
Summary:        Recursive file inventory tool with include and exclude filters

License:        MIT
URL:            https://github.com/cheddarsunrae/file-enumerator
Source0:        %{name}-%{version}.tar.gz

BuildArch:      noarch
Requires:       python3
Requires:       bash-completion

%description
file-enumerator recursively inventories files beneath a root directory and
member filenames inside supported ZIP and TAR-family archives. It can include
or exclude file extensions, filename globs, and folder globs, and can write TXT,
CSV, and ZIP output. It uses only the Python standard library.

%prep
%autosetup

%build
# No compilation is required.

%install
%make_install PREFIX=%{_prefix}

%check
python3 -m unittest discover -s tests -v

%files
%license LICENSE
%doc README.md CHANGELOG.md docs/INSTALL.md
%{_bindir}/file-enumerator
%{_mandir}/man1/file-enumerator.1*
%{_datadir}/bash-completion/completions/file-enumerator

%changelog
* Tue Jul 21 2026 Cheddar SunRae Logistics Inc. <shane@cheddar.team> - 1.1.1-1
- Release the project publicly under the MIT License

* Tue Jul 21 2026 Cheddar SunRae Logistics Inc. <shane@cheddar.team> - 1.1.0-1
- Add archive member enumeration and timestamped failure logs

* Tue Jul 21 2026 Cheddar SunRae Logistics Inc. <shane@cheddar.team> - 1.0.0-1
- Initial Fedora package
