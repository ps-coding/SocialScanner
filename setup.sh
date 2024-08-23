# Install the right version of pytorch depending on your system (see https://pytorch.org/get-started/locally)
# Uncomment the appropriate line
# Linux/Windows with CUDA 12.1:
# pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121
# Linux/Windows with CUDA 11.8:
# pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118
# Linux with ROCm 6.0
# pip install torch torchvision --index-url https://download.pytorch.org/whl/rocm6.0
# Linux/Windows/MacOS with only CPU (not recommended):
# pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu

# If on MacOS, also uncomment the following line:
# brew install portaudio
# If on Linux, uncomment the following line:
# sudo apt install python3-pyaudio

pip install -r requirements.txt
python prepare.py
