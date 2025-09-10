"""Image definition (modal's pythonic version of a Dockerfile)

What you'll want to change:
- the base image to a cuda and torch version that matches your method's requirements. Though our defaults have worked
for most methods so far.
- if you already have a Dockerfile and want to keep using it, replace the Image.from_registry() line with Image.from_dockerfile("Dockerfile").
You might also want to change the `workdir` to keep it consistent with the Dockerfile's.
- add your installation commands in the bottom section. Modal's syntax almost identically follows dockerfile's.
  - note that if your install commands needs access to a gpu that's possible
  - also, avoid using conda and use pip instead (installing and initializing conda in dockerfiles has caused us a lot of problems)

See their docs for more info: https://modal.com/docs/guide/images
"""

from pathlib import Path, PurePosixPath

from modal import Image, Volume

method_name = Path.cwd().name
assert method_name != "nvs-bench", (
    "nvs-bench must be called from the method's directory, not the nvs-bench subdirectory. Eg: `modal run nvs-bench/image.py`."
)

nvs_bench_volume = Volume.from_name("nvs-bench", create_if_missing=True)

modal_volumes: dict[str | PurePosixPath, Volume] = {
    "/nvs-bench": nvs_bench_volume,
}

image = (
    Image.from_registry("nvidia/cuda:12.8.0-devel-ubuntu24.04", add_python="3.12") # find others at: https://hub.docker.com/
    .env(
        {
            # Set Torch CUDA Compatbility to be for RTX 4090, T4, L40s, and A100
            # If using a different GPU, make sure its torch cuda architecture version is added to the list
            "TORCH_CUDA_ARCH_LIST": "7.5;8.0;8.9;9.0",
            # Set environment variable to avoid interactive prompts from installing packages
            "DEBIAN_FRONTEND": "noninteractive",
            "TZ": "America/New_York",
        }
    )
    # Install git and various other helper dependencies
    .run_commands(
        "apt-get update && apt-get install -y \
            openssh-server \
            git \
            wget \
            unzip \
            build-essential \
            ninja-build \
            libglew-dev \
            libassimp-dev \
            libboost-all-dev \
            libgtk-3-dev \
            libopencv-dev \
            libglfw3-dev \
            libavdevice-dev \
            libavcodec-dev \
            libeigen3-dev \
            libtbb-dev \
            libopenexr-dev \
            libxi-dev \
            libxrandr-dev \
            libxxf86vm-dev \
            libxxf86dga-dev \
            libxxf86vm-dev"
    )
    # Install gsutil (for downloading datasets the first time)
    .run_commands("apt-get install -y apt-transport-https ca-certificates gnupg curl")
    .run_commands('echo "deb [signed-by=/usr/share/keyrings/cloud.google.gpg] https://packages.cloud.google.com/apt cloud-sdk main" | tee -a /etc/apt/sources.list.d/google-cloud-sdk.list && curl https://packages.cloud.google.com/apt/doc/apt-key.gpg | gpg --dearmor -o /usr/share/keyrings/cloud.google.gpg && apt-get update -y && apt-get install google-cloud-cli -y')
    # For tracking GPU usage
    .run_commands("pip config set global.break-system-packages true") # disable PEP 668 protection globally
    .run_commands("pip install gpu_tracker")
    # Set the working dir
    .workdir(f"/root/{method_name}")
    ######## START OF YOUR CODE ########
    # Probably easiest to pull the repo from github, but you can also copy files from your local machine with .add_local_dir()
    # eg: .run_commands("git clone -b nvs-bench https://github.com/N-Demir/gaussian-splatting.git --recursive .")
    # Install (avoid conda installs because they don't work well in dockerfile situations)
    # Separating these on separate lines helps if there are errors (previous lines will be cached) especially on the large package installs
    # eg:
    # .run_commands("pip install submodules/diff-gaussian-rasterization")
    # .run_commands("pip install -e .")
    # Note: If your run_commands step needs access to a gpu it's actually possible to do that through "run_commands(gpu='L40S', ...)"

    # Install GCC 14
    .run_commands("apt-get install -y build-essential libmpfr-dev libgmp3-dev libmpc-dev")
    .run_commands("apt-get install -y gcc-14 g++-14 gfortran-14")
    # Set gcc14 as default
    .run_commands("update-alternatives --install /usr/bin/gcc gcc /usr/bin/gcc-14 60")
    .run_commands("update-alternatives --install /usr/bin/g++ g++ /usr/bin/g++-14 60")
    .run_commands("update-alternatives --config gcc")
    .run_commands("update-alternatives --config g++")

    # Install LichtFeld-Studio
    .run_commands("git clone https://github.com/N-Demir/LichtFeld-Studio.git --recursive .")
    .run_commands("apt-get install -y curl zip tar")

    # Setup vcpkg
    .run_commands("git clone https://github.com/microsoft/vcpkg.git")
    .run_commands("cd vcpkg && ./bootstrap-vcpkg.sh -disableMetrics && cd ..")
    .env({"VCPKG_ROOT": "/root/LichtFeld-Studio/vcpkg"})

    # Download LibTorch
    .run_commands("wget https://download.pytorch.org/libtorch/cu128/libtorch-cxx11-abi-shared-with-deps-2.7.1%2Bcu128.zip && \
        unzip libtorch-cxx11-abi-shared-with-deps-2.7.1+cu128.zip -d external/ && \
        rm libtorch-cxx11-abi-shared-with-deps-2.7.1+cu128.zip")

    # Install CMake 4.0.3
    .run_commands(
        "wget https://github.com/Kitware/CMake/releases/download/v4.0.3/cmake-4.0.3-linux-x86_64.sh && \
        chmod +x cmake-4.0.3-linux-x86_64.sh && \
        ./cmake-4.0.3-linux-x86_64.sh --skip-license --prefix=/usr/local && \
        rm cmake-4.0.3-linux-x86_64.sh"
    )

    # Note: as of 2025-09-10, modal's L40S gpus have amd and intel cpus and the amd's don't support something in this build
    # in case it was the lichtfeld install that was unsupported, we specifically specify x86-64 and generic
    # but, after making the change, the amd chips mysteriously dissapeared. So we've not been able to verify it made a difference.
    # It's possible instead the problem is with the libtorch binary, which is a much bigger thing to build.... hope not!
    .run_commands("cmake -B build -DCMAKE_BUILD_TYPE=Release -G Ninja -DCMAKE_CXX_FLAGS='-march=x86-64 -mtune=generic'")
    .run_commands("cmake --build build -- -j$(nproc)")
)
