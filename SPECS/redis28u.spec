%global real_name redis
%global ius_suffix 28u

# redis 2.8 sentinel is the first upstream version to work
# however as packaged here it is entirely broken
# FIXME: consider removal into a separate package
%if 0%{?rhel} >= 7
%global with_sentinel 1
%endif

%if 0%{?rhel} >= 7
%global with_systemd 1
%else
%global with_systemd 0
%endif

# tcl 8.4 in EL5.
%if 0%{?rhel} <= 5
%global with_tests 0
%else
%global with_tests 1
%endif

# stock el5 gcc is 4.1.2 - too old!
%if 0%{?rhel} <= 5
%global with_gcc44 1
%else
%global with_gcc44 0
%endif

Name:              %{real_name}%{ius_suffix}
Version:           2.8.18
Release:           1.ius%{?dist}
Summary:           A persistent caching system, key-value and data structures database
%{?el5:Group:      Applications/Databases}
License:           BSD
URL:               http://redis.io
Source0:           http://download.redis.io/releases/%{real_name}-%{version}.tar.gz
Source1:           %{real_name}.logrotate
Source2:           %{real_name}-sentinel.service
Source3:           %{real_name}.service
Source4:           %{real_name}.tmpfiles
Source5:           %{real_name}-sentinel.init
Source6:           %{real_name}.init
Patch1:            redis-2.8.18-deps-library-fPIC-performance-tuning.patch
Patch2:            redis-2.8.11-use-system-jemalloc.patch
Patch5:            redis-2.8.18-redis-conf-systemd.patch
Patch6:            redis-2.8.18-redis-conf-init.patch
Patch7:            redis-2.8.18-deps-lua-cmsgpack.patch
%{?el5:BuildRoot:  %{_tmppath}/%{real_name}-%{version}-%{release}-root-%(%{__id_u} -n)}

BuildRequires:     jemalloc-devel
Requires:          logrotate
Requires(pre):     shadow-utils

%if 0%{?with_tests}
BuildRequires:     tcl
%if 0%{?rhel} >= 7
BuildRequires:     procps-ng
%else
BuildRequires:     procps
%endif
%endif

%if 0%{?with_gcc44}
BuildRequires: gcc44
%endif

%if 0%{?with_systemd}
BuildRequires:     systemd
Requires(post):    systemd
Requires(preun):   systemd
Requires(postun):  systemd
%else
Requires(post):    chkconfig
Requires(preun):   chkconfig
Requires(preun):   initscripts
Requires(postun):  initscripts
%endif

Provides: %{real_name} = %{version}-%{release}
Provides: %{real_name}%{?_isa} = %{version}-%{release}
Provides: config(%{real_name}) = %{version}-%{release}
Conflicts: %{real_name} < %{version}


%description
Redis is an advanced key-value store. It is often referred to as a data 
structure server since keys can contain strings, hashes, lists, sets and 
sorted sets.

You can run atomic operations on these types, like appending to a string;
incrementing the value in a hash; pushing to a list; computing set 
intersection, union and difference; or getting the member with highest 
ranking in a sorted set.

In order to achieve its outstanding performance, Redis works with an 
in-memory dataset. Depending on your use case, you can persist it either 
by dumping the dataset to disk every once in a while, or by appending 
each command to a log.

Redis also supports trivial-to-setup master-slave replication, with very 
fast non-blocking first synchronization, auto-reconnection on net split 
and so forth.

Other features include Transactions, Pub/Sub, Lua scripting, Keys with a 
limited time-to-live, and configuration settings to make Redis behave like 
a cache.

You can use Redis from most programming languages also.


%prep
%setup -q -n %{real_name}-%{version}
%{__rm} -frv deps/jemalloc
%patch1 -p1
%patch2 -p1
%if 0%{?with_systemd}
%patch5 -p1
%else
%patch6 -p1
%endif
%patch7 -p1

# No hidden build.
%{__sed} -i -e 's|\t@|\t|g' deps/lua/src/Makefile
%{__sed} -i -e 's|$(QUIET_CC)||g' src/Makefile
%{__sed} -i -e 's|$(QUIET_LINK)||g' src/Makefile
%{__sed} -i -e 's|$(QUIET_INSTALL)||g' src/Makefile
# Ensure deps are built with proper flags
%{__sed} -i -e 's|$(CFLAGS)|%{optflags}|g' deps/Makefile
%{__sed} -i -e 's|OPTIMIZATION?=-O3|OPTIMIZATION=%{optflags}|g' deps/hiredis/Makefile
%{__sed} -i -e 's|$(LDFLAGS)|%{?__global_ldflags}|g' deps/hiredis/Makefile
%{__sed} -i -e 's|$(CFLAGS)|%{optflags}|g' deps/linenoise/Makefile
%{__sed} -i -e 's|$(LDFLAGS)|%{?__global_ldflags}|g' deps/linenoise/Makefile


%build
%if 0%{?with_gcc44}
export CC=gcc44
export LINKCC=gcc44
%endif
%{__make} %{?_smp_mflags} \
    DEBUG="" \
    LDFLAGS="%{?__global_ldflags}" \
    CFLAGS+="%{optflags}" \
    LUA_LDFLAGS+="%{?__global_ldflags}" \
    MALLOC=jemalloc \
    all


%install
%{?el5:%{__rm} -rf %{buildroot}}
%{__make} install INSTALL="install -p" PREFIX=%{buildroot}%{_prefix}

# Filesystem.
%{__install} -d %{buildroot}%{_sharedstatedir}/%{real_name}
%{__install} -d %{buildroot}%{_localstatedir}/lib/%{real_name}
%{__install} -d %{buildroot}%{_localstatedir}/log/%{real_name}
%{__install} -d %{buildroot}%{_localstatedir}/run/%{real_name}

# Install logrotate file.
%{__install} -pDm644 %{S:1} %{buildroot}%{_sysconfdir}/logrotate.d/%{real_name}

# Install configuration files.
%{__install} -pDm644 %{real_name}.conf %{buildroot}%{_sysconfdir}/%{real_name}.conf
%if 0%{?with_sentinel}
%{__install} -pDm644 sentinel.conf %{buildroot}%{_sysconfdir}/%{real_name}-sentinel.conf
%endif

# Install Systemd/SysV files.
%if 0%{?with_systemd}
%{__mkdir} -p %{buildroot}%{_unitdir}
%{__install} -pm644 %{S:3} %{buildroot}%{_unitdir}
%if 0%{?with_sentinel}
%{__install} -pm644 %{S:2} %{buildroot}%{_unitdir}
%endif
%{__install} -pDm644 %{S:4} %{buildroot}%{_tmpfilesdir}/%{real_name}.conf
%else
%if 0%{?with_sentinel}
%{__install} -pDm755 %{S:5} %{buildroot}%{_initrddir}/%{real_name}-sentinel
%endif
%{__install} -pDm755 %{S:6} %{buildroot}%{_initrddir}/%{real_name}
%endif

# Fix non-standard-executable-perm error.
%{__chmod} 755 %{buildroot}%{_bindir}/%{real_name}-*


%{?el5:%clean}
%{?el5:%{__rm} -rf %{buildroot}}


%check
%if 0%{?with_tests}
%{__make} test
%if 0%{?with_sentinel}
%{__make} test-sentinel
%endif
%endif


%pre
getent group %{real_name} &> /dev/null || \
groupadd -r %{real_name} &> /dev/null
getent passwd %{real_name} &> /dev/null || \
useradd -r -g %{real_name} -d %{_sharedstatedir}/%{real_name} -s /sbin/nologin \
-c 'Redis Database Server' %{real_name} &> /dev/null
exit 0


%post
%if 0%{?with_systemd}
%if 0%{?with_sentinel}
%systemd_post %{real_name}-sentinel.service
%endif
%systemd_post %{real_name}.service
%else
%if 0%{?with_sentinel}
chkconfig --add %{real_name}-sentinel
%endif
chkconfig --add %{real_name}
%endif


%preun
%if 0%{?with_systemd}
%if 0%{?with_sentinel}
%systemd_preun %{real_name}-sentinel.service
%endif
%systemd_preun %{real_name}.service
%else
if [ $1 -eq 0 ] ; then
%if 0%{?with_sentinel}
service %{real_name}-sentinel stop &> /dev/null
chkconfig --del %{real_name}-sentinel &> /dev/null
%endif
service %{real_name} stop &> /dev/null
chkconfig --del %{real_name} &> /dev/null
fi
%endif


%postun
%if 0%{?with_systemd}
%if 0%{?with_sentinel}
%systemd_postun_with_restart %{real_name}-sentinel.service
%endif
%systemd_postun_with_restart %{real_name}.service
%else
if [ "$1" -ge "1" ] ; then
%if 0%{?with_sentinel}
    service %{real_name}-sentinel condrestart >/dev/null 2>&1 || :
%endif
    service %{real_name} condrestart >/dev/null 2>&1 || :
fi
%endif


%files
%doc 00-RELEASENOTES BUGS CONTRIBUTING COPYING MANIFESTO README
%config(noreplace) %{_sysconfdir}/logrotate.d/%{real_name}
%config(noreplace) %{_sysconfdir}/%{real_name}.conf
%if 0%{?with_sentinel}
%config(noreplace) %{_sysconfdir}/%{real_name}-sentinel.conf
%endif
%dir %attr(0750, redis, redis) %{_sharedstatedir}/%{real_name}
%dir %attr(0750, redis, redis) %{_localstatedir}/lib/%{real_name}
%dir %attr(0750, redis, redis) %{_localstatedir}/log/%{real_name}
%dir %attr(0750, redis, redis) %{_localstatedir}/run/%{real_name}
%{_bindir}/%{real_name}-*
%if 0%{?with_systemd}
%{_tmpfilesdir}/%{real_name}.conf
%if 0%{?with_sentinel}
%{_unitdir}/%{real_name}-sentinel.service
%endif
%{_unitdir}/%{real_name}.service
%else
%if 0%{?with_sentinel}
%{_initrddir}/%{real_name}-sentinel
%endif
%{_initrddir}/%{real_name}
%endif


%changelog
* Thu Dec 04 2014 Carl George <carl.george@rackspace.com> - 2.8.18-1.ius
- Latest upstream source
- Use separate config patches for systemd/init
- Switch to gcc44
- Backport upstream fix (patch7) for el5 builds

* Thu Nov 06 2014 Ben Harper <ben.harper@rackspace.com> - 2.8.17-2.ius
- add /var/lib/redis see LP bug #1389918

* Mon Sep 22 2014 Carl George <carl.george@rackspace.com> - 2.8.17-1.ius
- Latest upstream source

* Tue Sep 16 2014 Carl George <carl.george@rackspace.com> - 2.8.16-1.ius
- Latest upstream source

* Mon Sep 15 2014 Carl George <carl.george@rackspace.com> - 2.8.15-1.ius
- Latest upstream source
- Patch3 fixed upstream
- Patch5 fixed upstream

* Tue Sep 02 2014 Carl George <carl.george@rackspace.com> - 2.8.14-1.ius
- Latest upstream source
- Rebase patch1
- Add patch5 to correct failing 32 bit test suite https://github.com/antirez/redis/issues/1981

* Fri Aug 01 2014 Carl George <carl.george@rackspace.com> - 2.8.13-6.ius
- Correct path issue in init script
- Apply patch to set 'daemonize yes' only if not using systemd
- Correct broken preuninstall script

* Thu Jul 31 2014 Carl George <carl.george@rackspace.com> - 2.8.13-5.ius
- Add in IUS conflicts and provides

* Wed Jul 30 2014 Carl George <carl.george@rackspace.com> - 2.8.13-4.ius
- Port from epel7 to IUS
- Correct build error on 32bit el5

* Tue Jul 29 2014 Warren Togami <warren@slickage.com> - 2.8.13-3
- Revert rename redis.service to redis-server (4 years as packaged service name).
- Revert "daemonize yes" in default redis.conf
  systemd handles background and process tracking on its own, this broke systemd launch.
- Revert redis.init as it too handled daemonizing.
- Revert tcp-keepalive default to 0.
- Revert ExecStartPre hack, /var/lib/redis is owned by the package.
  No %%ghost directories, just own it.
- FIXME: sentinel is broken, mispackaged and quite possibly belongs in an entirely separate package
  because it is not meant to be used concurrently with the ordinary systemd redis and it requires
  a highly specialized custom configuration.

* Wed Jul 23 2014 Warren Togami <warren@slickage.com> - 2.8.13-2
- Fix detection of EL7: systemd unit was missing
- Fix detection of EL5

* Wed Jul 16 2014 Christopher Meng <rpm@cicku.me> - 2.8.13-1
- Update to 2.8.13

* Tue Jun 24 2014 Christopher Meng <rpm@cicku.me> - 2.8.12-1
- Update to 2.8.12

* Wed Jun 18 2014 Christopher Meng <rpm@cicku.me> - 2.8.11-1
- Update to 2.8.11

* Sun Jun 08 2014 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 2.6.16-2
- Rebuilt for https://fedoraproject.org/wiki/Fedora_21_Mass_Rebuild

* Fri Sep 06 2013 Fabian Deutsch <fabian.deutsch@gmx.de> - 2.6.16-1
- Update to 2.6.16
- Fix rhbz#973151
- Fix rhbz#656683
- Fix rhbz#977357 (Jan Vcelak <jvcelak@fedoraproject.org>)

* Sun Aug 04 2013 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 2.6.13-5
- Rebuilt for https://fedoraproject.org/wiki/Fedora_20_Mass_Rebuild

* Tue Jul 23 2013 Peter Robinson <pbrobinson@fedoraproject.org> 2.6.13-4
- ARM has gperftools

* Wed Jun 19 2013 Fabian Deutsch <fabiand@fedoraproject.org> - 2.6.13-3
- Modify jemalloc patch for s390 compatibility (Thanks sharkcz)

* Fri Jun 07 2013 Fabian Deutsch <fabiand@fedoraproject.org> - 2.6.13-2
- Unbundle jemalloc

* Fri Jun 07 2013 Fabian Deutsch <fabiand@fedoraproject.org> - 2.6.13-1
- Add compile PIE flag (rhbz#955459)
- Update to redis 2.6.13 (rhbz#820919)

* Thu Feb 14 2013 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 2.6.7-2
- Rebuilt for https://fedoraproject.org/wiki/Fedora_19_Mass_Rebuild

* Thu Dec 27 2012 Silas Sewell <silas@sewell.org> - 2.6.7-1
- Update to redis 2.6.7

* Sat Jul 21 2012 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 2.4.15-3
- Rebuilt for https://fedoraproject.org/wiki/Fedora_18_Mass_Rebuild

* Sun Jul 08 2012 Silas Sewell <silas@sewell.org> - 2.4.15-2
- Remove TODO from docs

* Sun Jul 08 2012 Silas Sewell <silas@sewell.org> - 2.4.15-1
- Update to redis 2.4.15

* Sat May 19 2012 Silas Sewell <silas@sewell.org> - 2.4.13-1
- Update to redis 2.4.13

* Sat Mar 31 2012 Silas Sewell <silas@sewell.org> - 2.4.10-1
- Update to redis 2.4.10

* Fri Feb 24 2012 Silas Sewell <silas@sewell.org> - 2.4.8-1
- Update to redis 2.4.8

* Sat Feb 04 2012 Silas Sewell <silas@sewell.org> - 2.4.7-1
- Update to redis 2.4.7

* Wed Feb 01 2012 Fabian Deutsch <fabiand@fedoraproject.org> - 2.4.6-4
- Fixed a typo in the spec

* Tue Jan 31 2012 Fabian Deutsch <fabiand@fedoraproject.org> - 2.4.6-3
- Fix .service file, to match config (Type=simple).

* Tue Jan 31 2012 Fabian Deutsch <fabiand@fedoraproject.org> - 2.4.6-2
- Fix .service file, credits go to Timon.

* Thu Jan 12 2012 Fabian Deutsch <fabiand@fedoraproject.org> - 2.4.6-1
- Update to 2.4.6
- systemd unit file added
- Compiler flags changed to compile 2.4.6
- Remove doc/ and Changelog

* Sun Jul 24 2011 Silas Sewell <silas@sewell.org> - 2.2.12-1
- Update to redis 2.2.12

* Fri May 06 2011 Dan Horák <dan[at]danny.cz> - 2.2.5-2
- google-perftools exists only on selected architectures

* Sat Apr 23 2011 Silas Sewell <silas@sewell.ch> - 2.2.5-1
- Update to redis 2.2.5

* Sat Mar 26 2011 Silas Sewell <silas@sewell.ch> - 2.2.2-1
- Update to redis 2.2.2

* Wed Feb 09 2011 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 2.0.4-2
- Rebuilt for https://fedoraproject.org/wiki/Fedora_15_Mass_Rebuild

* Sun Dec 19 2010 Silas Sewell <silas@sewell.ch> - 2.0.4-1
- Update to redis 2.0.4

* Tue Oct 19 2010 Silas Sewell <silas@sewell.ch> - 2.0.3-1
- Update to redis 2.0.3

* Fri Oct 08 2010 Silas Sewell <silas@sewell.ch> - 2.0.2-1
- Update to redis 2.0.2
- Disable checks section for el5

* Sat Sep 11 2010 Silas Sewell <silas@sewell.ch> - 2.0.1-1
- Update to redis 2.0.1

* Sat Sep 04 2010 Silas Sewell <silas@sewell.ch> - 2.0.0-1
- Update to redis 2.0.0

* Thu Sep 02 2010 Silas Sewell <silas@sewell.ch> - 1.2.6-3
- Add Fedora build flags
- Send all scriplet output to /dev/null
- Remove debugging flags
- Add redis.conf check to init script

* Mon Aug 16 2010 Silas Sewell <silas@sewell.ch> - 1.2.6-2
- Don't compress man pages
- Use patch to fix redis.conf

* Tue Jul 06 2010 Silas Sewell <silas@sewell.ch> - 1.2.6-1
- Initial package
