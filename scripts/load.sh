sudo kextunload -b com.senmiko.RTWCore
sudo chown -R root:wheel ./../Build/Products/Debug/RTWCore.kext
sudo kextutil -v 6 ./../Build/Products/Debug/RTWCore.kext

