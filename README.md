Compare the current module content with the release one to observe any changes

run the command by:
" # python3 check.py virt:rhel:xxxxxxx virt:rhel:xxxxxxx"

The 1st parameter should be the module which is already released and to be compared with, and the 2nd is the one to be tested.
Parameter in format as: virt:stream:version. In fact, it is the paramter for "yum module info".

install below package before the compare
" # yum install -y rpmdevtools "
