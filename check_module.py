#!/usr/bin/python3
import re
import subprocess
import sys
import time
import os

# run below cmd to get the file_list first for the released and current module:
# for released module:
# yum module info virt:rhel:8000020190618154454 | grep -A 200 Artifacts  | grep -Ev "^$|[#;]|Hint:"  > ./released.txt
# for current module under test:
# yum module info virt:rhel:80000xxxxxxxxxxxxxx | grep -A 200 Artifacts  | grep -Ev "^$|[#;]|Hint:"  > ./current.txt


def get_file(name, file_name):
    proc1 = subprocess.Popen(['yum', 'module', 'info', name], stdout=subprocess.PIPE)
    proc2 = subprocess.Popen('grep -A 200 Artifacts', stdin=proc1.stdout, stdout=subprocess.PIPE, shell=True)
    proc1.stdout.close()
    f = open(file_name, 'w')
    proc3 = subprocess.Popen("grep -Ev '^$|[#;]|Hint:'", stdin=proc2.stdout, stdout=f, shell=True)
    proc2.stdout.close()
    f.flush()
    f.close()
    while proc3.poll() is None:
        time.sleep(1)


def get_pkg_list(file_list):
    content = None
    with open(file_list, 'r') as f:
        content = f.readlines()
    content = [x.strip('Artifacts :') for x in content]
    package_num = len(content)
    # print("%d packages in the module in %s includes: " % (package_num, f.name))
    # print("%s" % content)
    # get the released package name list
    package_name_list = [re.search('(.*)-[0-9].*:', x).group(1) for x in content]
    # print("package_name_list is %s" % package_name_list)
    return package_num, content, package_name_list


def check_profile(name):
    proc1 = subprocess.Popen(['yum', 'module', 'info', name, '--profile'], stdout=subprocess.PIPE)
    # Asume there is profile named "common"
    f = open('/tmp/cur_profile_list.txt', 'w')
    proc2 = subprocess.Popen('grep -A 20 common', stdin=proc1.stdout, stdout=f, shell=True)
    proc1.stdout.close()
    f.flush()
    f.close()
    while proc2.poll() is None:
        time.sleep(1)
    with open('/tmp/cur_profile_list.txt', 'r') as f:
        content = f.readlines()
    content = [x.strip('common :') for x in content]
    print("profile pkg is %s" % content)
    # compare with current profile content: libguestfs, libvirt-client, libvirt-daemon-config-network, libvirt-daemon-kvm
    release_profile = ['libguestfs\n', 'libvirt-client\n', 'libvirt-daemon-config-network\n', 'libvirt-daemon-kvm\n']
    retD = list(set(content).difference(set(release_profile)))
    retE = list(set(release_profile).difference(set(content)))
    if retD or retE:
        print("Warning: There is changes in the profile pkg!")
    else:
        print("The profile pkg not change.")


def check_profile_name(name):
    proc1 = subprocess.Popen(['yum', 'module', 'info', name], stdout=subprocess.PIPE)
    proc2 = subprocess.Popen('grep -i profiles', stdin=proc1.stdout, stdout=subprocess.PIPE, shell=True)
    profile_info = proc2.communicate()[0].decode("utf-8")
    proc1.stdout.close()
    while proc2.poll() is None:
        time.sleep(1)
    print("Profile info is %s" % profile_info)
    profile_info1 = profile_info.replace(" ", "")
    if "Profiles:common[d]" not in profile_info1:
        print("Warning: No 'Profiles:common[d]' in the profile info!")
    if 'Defaultprofiles:common' not in profile_info1:
        print("Warning: No 'Defaultprofiles:common' in the profile info!")
    print("Profile name check OK")

os.system('yum install -y rpmdevtools')
print("Notes: It is not recommended to compare modules in 2 different streams.")
print("The argv should be in format 'virt:stream:version', like: virt:rhel:8000020190530233731, "
      "argv[1] is the released one(older), and argv[2] is the current one(newer)")
print("\nCompare 2 modules below:")
print(sys.argv[1], sys.argv[2])


get_file(sys.argv[1], '/tmp/release.txt')
get_file(sys.argv[2], '/tmp/current.txt')

release_info = get_pkg_list("/tmp/release.txt")
current_info = get_pkg_list("/tmp/current.txt")

# check the pkg number changes
print("(1) PKG NUM CHECK:")
num1 = int(release_info[0])
num2 = int(current_info[0])

if num2 == num1:
    print("Current pkg num is the same as the released pkg num: %s" % num1)
elif num2 > num1:
    print("Warning: Current pkg num %s is MORE than the released pkg num %s" % (num2, num1))
elif num2 < num1:
    print("Warning: Current pkg num %s is LESS than the released pkg num %s" % (num2, num1))

# check the pkg name changes
print("\n(2) PKG NAME CHECK:")
pkg_name_rel = release_info[2]
pkg_name_cur = current_info[2]

new_add_pkg = list(set(pkg_name_cur).difference(set(pkg_name_rel)))
print("Current new added pkg: %s" % new_add_pkg)

deprecated_pkg = list(set(pkg_name_rel).difference(set(pkg_name_cur)))
print("Current deprecated pkg: %s" % deprecated_pkg)

if not new_add_pkg and not deprecated_pkg:
    print("Package name not change in current module compared the release one!")
else:
    print("Warning: Package name changes in current module, check above info!!!")

# check the version to ensure the package in current module is newer than the released ones
# if there is a situation that the current version is the same as the released one?
print("\n(3)PKG VERSION CHECK:")
pkg_rel_full = release_info[1]
pkg_cur_full = current_info[1]

dict_rel = dict(zip(pkg_name_rel, pkg_rel_full))
dict_cur = dict(zip(pkg_name_cur, pkg_cur_full))
# print(dict_cur)
# print(dict_rel)

print("Run cmd: rpmdev-vercmp $cur_ver $rel_ver one by one to ensure current ver is newer than the released one.")
print("If no waring message, it is fine.")

for x in pkg_name_cur:
    cur_ver = dict_cur.get(x)
    rel_ver = dict_rel.get(x)
    if rel_ver:
        Output = subprocess.Popen(['rpmdev-vercmp', cur_ver, rel_ver], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        stdout, stderr = Output.communicate()
        res = stdout.decode("utf-8")
        result = res.split("problems.\n\n")[1]
        if ">" not in result:
            print("Warning: current pkg is not newer than released one:\n %s" % result)
        if stderr:
            print(stderr)


print("\n(4)CHECK CURRENT PROFILE:")
check_profile(sys.argv[2])

print("\n(5)PROFILE NAME CHECK:")
check_profile_name(sys.argv[2])
