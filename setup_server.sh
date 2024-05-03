apt update
apt upgrade
apt install emacs-nox ubuntu-drivers-common
apt install nvidia-driver-535
wget https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2204/x86_64/cuda-keyring_1.1-1_all.deb
dpkg -i cuda-keyring_1.1-1_all.deb
apt update
apt -y install cudnn9-cuda-12
git clone https://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@github.com/bensetel/ner-takehome
reboot now
