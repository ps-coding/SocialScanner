#
# Copyright (c) 2024 Prasham Shah. All rights reserved.
#

pip install instaloader
pip install nltk
# Install the right version of pytorch depending on your system (see https://pytorch.org/get-started/locally)
# Uncomment the appropriate line
# Linux/Windows with CUDA 12.1:
# pip3 install torch torchvision --index-url https://download.pytorch.org/whl/cu121
# Linux/Windows with CUDA 11.8:
# pip3 install torch torchvision --index-url https://download.pytorch.org/whl/cu118
# Linux with ROCm 6.0
# pip3 install torch torchvision --index-url https://download.pytorch.org/whl/rocm6.0
# Linux/Windows/MacOS with only CPU (not recommended):
# pip3 install torch torchvision --index-url https://download.pytorch.org/whl/cpu
pip install easyocr
python prepare.py
